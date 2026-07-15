import asyncio
import json
import os
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import yaml
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from router.app.aliases import Bean, BeanRegistry
from router.app.config import Settings
from router.app.ledger import LedgerRow, RouterLedger
from router.app.main import (
    EscalationContext,
    RouterState,
    _run_order_and_publish,
    create_app,
    run_order,
)
from router.app.openrouter_client import StreamChunk
from router.app.preferences import PreferenceStore
from router.app.routing import RoutingPolicy
from router.app.sessions import SessionStore
from router.app.uploads import UploadRecord, new_attachment_id, save_upload

FIXTURE_POLICY = {
    "task_types": {
        "code": {
            "status": "evidence_based",
            "primary_bean_alias": "House Blend",
            "fallback_bean_alias": "Second Pour",
            "premium_bean_alias": "Reserve Blend",
            "evidence": ["fixture"],
            "reason": "fixture",
        },
    }
}


def _make_bean_registry(with_premium: bool = True) -> BeanRegistry:
    beans = [
        Bean(
            alias="House Blend",
            role="default",
            model_id="vendor/default:free",
            vision=False,
            code=True,
            price_per_1k_input_usd=0.0,
            price_per_1k_output_usd=0.0,
            status="active",
        ),
        Bean(
            alias="Second Pour",
            role="fallback",
            model_id="vendor/fallback:free",
            vision=False,
            code=True,
            price_per_1k_input_usd=0.0,
            price_per_1k_output_usd=0.0,
            status="active",
        ),
    ]
    if with_premium:
        beans.append(
            Bean(
                alias="Reserve Blend",
                role="premium",
                model_id="vendor/premium",
                vision=False,
                code=True,
                price_per_1k_input_usd=1.0,
                price_per_1k_output_usd=2.0,
                status="active",
            )
        )
    else:
        beans.append(
            Bean(
                alias="Reserve Blend",
                role="premium",
                model_id=None,
                vision=False,
                code=True,
                price_per_1k_input_usd=None,
                price_per_1k_output_usd=None,
                status="not_yet_selected",
            )
        )
    return BeanRegistry(beans)


def _make_bean_registry_with_vision() -> BeanRegistry:
    """A registry with one vision-capable Bean, for the attachment routing
    tests - the real beans.yaml has none today (test_aliases.py::
    test_real_config_has_no_vision_bean_today), so this is a fixture-only
    scenario."""

    return BeanRegistry(
        [
            Bean(
                alias="House Blend",
                role="default",
                model_id="vendor/default:free",
                vision=False,
                code=True,
                price_per_1k_input_usd=0.0,
                price_per_1k_output_usd=0.0,
                status="active",
            ),
            Bean(
                alias="Vision Bean",
                role="fallback",
                model_id="vendor/vision:free",
                vision=True,
                code=True,
                price_per_1k_input_usd=0.0,
                price_per_1k_output_usd=0.0,
                status="active",
            ),
        ]
    )


def _text_bearing_pdf_bytes(text: str = "Hello test PDF text with plenty of margin") -> bytes:
    """A real, minimal single-page PDF with an actual text content stream,
    so pypdf's extract_text() has something real to find. See
    test_uploads.py for the fuller version of this fixture builder - kept
    self-contained here rather than cross-importing another test module."""

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)

    font_dict = DictionaryObject()
    font_dict[NameObject("/Type")] = NameObject("/Font")
    font_dict[NameObject("/Subtype")] = NameObject("/Type1")
    font_dict[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font_ref = writer._add_object(font_dict)

    resources = DictionaryObject()
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font_ref
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources

    stream_obj = DecodedStreamObject()
    stream_obj.set_data(f"BT /F1 24 Tf 20 250 Td ({text}) Tj ET".encode("latin-1"))
    page.replace_contents(stream_obj)

    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _blank_pdf_bytes(page_count: int = 2) -> bytes:
    """A valid PDF with pages but no content stream - the same shape a
    scanned-image-only PDF produces when pypdf tries to extract text."""

    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=300, height=300)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


async def _fake_stream_healthy(model_id, prompt, **_kwargs):
    for word in ["Hello ", "world " * 20]:
        yield StreamChunk(content_delta=word)
    yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 50})
    yield StreamChunk(is_final=True)


async def _fake_stream_empty(model_id, prompt, **_kwargs):
    yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 0})
    yield StreamChunk(is_final=True)


async def _fake_stream_short(model_id, prompt, **_kwargs):
    """A response shorter than one settings.generating_tick_tokens worth
    of content - regression fixture for the real bug the Brew 38 live
    demo found: _consume_stream used to drop any text accumulated since
    the last tick when the stream ended before crossing the tick
    threshold, since CompleteEvent carries no content field."""

    yield StreamChunk(content_delta="Hi")
    yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 1})
    yield StreamChunk(is_final=True)


class RunOrderTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)
        self.policy_path = policy_path
        self.ledger_path = Path(self._tmp_dir.name) / "router_requests.csv"

    def _make_state(
        self,
        with_premium=True,
        escalation_cost_cap_usd=0.50,
        with_session_store=False,
        escalation_approval_timeout_seconds=600.0,
        pantry_index_path=None,
        pantry_top_k=5,
    ):
        registry = _make_bean_registry(with_premium=with_premium)
        policy = RoutingPolicy.from_yaml(self.policy_path, bean_registry=registry)
        settings = Settings(
            escalation_cost_cap_usd=escalation_cost_cap_usd,
            escalation_approval_timeout_seconds=escalation_approval_timeout_seconds,
            generating_tick_tokens=5,
            generating_tick_seconds=999,
            truncation_min_expected_tokens=10,
            refusal_keywords=["i cannot help"],
            pantry_top_k=pantry_top_k,
        )
        ledger = RouterLedger(self.ledger_path)
        session_store = (
            SessionStore(Path(self._tmp_dir.name) / "sessions.db") if with_session_store else None
        )
        kwargs = {}
        if pantry_index_path is not None:
            kwargs["pantry_index_path"] = pantry_index_path
        return RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            session_store=session_store,
            uploads_root=Path(self._tmp_dir.name) / "uploads",
            **kwargs,
        )

    async def _collect(self, state, stream_fn, **kwargs):
        return [
            event
            async for event in run_order(state, prompt="Implement a function.", stream_order_fn=stream_fn, **kwargs)
        ]

    def _register_upload(
        self,
        state,
        request_id,
        filename,
        content_type,
        kind,
        *,
        extracted_text=None,
        file_bytes=b"fixture-bytes",
    ):
        attachment_id = new_attachment_id()
        file_path = save_upload(
            request_id, attachment_id, filename, file_bytes, uploads_root=state.uploads_root
        )
        state.uploads[attachment_id] = UploadRecord(
            attachment_id=attachment_id,
            request_id=request_id,
            filename=filename,
            content_type=content_type,
            kind=kind,
            size_bytes=len(file_bytes),
            file_path=file_path,
            extracted_text=extracted_text,
        )
        return attachment_id

    async def test_happy_path_event_order(self):
        state = self._make_state()
        events = await self._collect(state, _fake_stream_healthy)
        event_names = [e.event for e in events]
        self.assertEqual(
            event_names[:3], ["order_received", "classifying", "route_selected"]
        )
        self.assertIn("generating", event_names)
        self.assertEqual(event_names[-1], "complete")
        complete = events[-1]
        self.assertFalse(complete.escalated)
        self.assertFalse(complete.draft_quality)

    async def test_happy_path_writes_ledger_row(self):
        state = self._make_state()
        await self._collect(state, _fake_stream_healthy)
        rows = state.ledger.read_all_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bean_alias"], "House Blend")
        self.assertEqual(rows[0]["raw_model_id"], "vendor/default:free")
        self.assertEqual(rows[0]["escalation_approved"], "n/a")

    async def test_no_premium_available_produces_draft_quality(self):
        state = self._make_state(with_premium=False)
        events = await self._collect(state, _fake_stream_empty)
        event_names = [e.event for e in events]
        self.assertIn("escalation_pending", event_names)
        self.assertNotIn("escalating", event_names)
        complete = events[-1]
        self.assertTrue(complete.draft_quality)
        self.assertFalse(complete.escalated)
        pending_event = next(e for e in events if e.event == "escalation_pending")
        self.assertIsNone(pending_event.premium_bean_alias)

    async def test_auto_escalate_under_cap(self):
        # Reserve Blend cost: (tokens_in/1000 * 1.0) + (tokens_out/1000 * 2.0),
        # tiny prompt -> well under the 0.50 cap in this fixture's settings.
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.50)
        events = await self._collect(state, _fake_stream_empty)
        event_names = [e.event for e in events]
        self.assertIn("escalation_pending", event_names)
        self.assertIn("escalating", event_names)
        complete = events[-1]
        self.assertTrue(complete.escalated)
        self.assertEqual(complete.bean_alias, "Reserve Blend")

    async def test_escalation_pending_approved_escalates(self):
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)  # force pending, not auto

        async def approve(request_id):
            return "approved"

        events = await self._collect(state, _fake_stream_empty, wait_for_approval=approve)
        event_names = [e.event for e in events]
        self.assertIn("escalation_pending", event_names)
        self.assertIn("escalating", event_names)
        complete = events[-1]
        self.assertTrue(complete.escalated)
        self.assertFalse(complete.draft_quality)

    async def test_escalation_pending_declined_stays_draft(self):
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)

        async def decline(request_id):
            return "declined"

        events = await self._collect(state, _fake_stream_empty, wait_for_approval=decline)
        event_names = [e.event for e in events]
        self.assertIn("escalation_pending", event_names)
        self.assertNotIn("escalating", event_names)
        complete = events[-1]
        self.assertFalse(complete.escalated)
        self.assertTrue(complete.draft_quality)

    async def test_escalation_pending_carries_decision_deadline(self):
        """Contract v1.3: decision_deadline lets a UI render a countdown
        and later distinguish an explicit decline from a timeout."""

        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)

        async def decline(request_id):
            return "declined"

        events = await self._collect(state, _fake_stream_empty, wait_for_approval=decline)
        pending_event = next(e for e in events if e.event == "escalation_pending")
        self.assertIsNotNone(pending_event.decision_deadline)

    async def test_auto_escalate_decision_deadline_is_none(self):
        """No pause happens on the auto-escalate path - nothing to wait
        for, so decision_deadline must stay null, not a guessed value."""

        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.50)
        events = await self._collect(state, _fake_stream_empty)
        pending_event = next(e for e in events if e.event == "escalation_pending")
        self.assertIsNone(pending_event.decision_deadline)

    async def test_escalation_timeout_auto_declines_and_writes_ledger_row(self):
        """No wait_for_approval injected - exercises the real
        asyncio.wait(timeout=...) path in _await_approval with a very
        short configured timeout, rather than a fake."""

        state = self._make_state(
            with_premium=True, escalation_cost_cap_usd=0.0, escalation_approval_timeout_seconds=0.05
        )
        events = await self._collect(state, _fake_stream_empty)
        event_names = [e.event for e in events]
        self.assertIn("escalation_pending", event_names)
        self.assertNotIn("escalating", event_names)
        complete = events[-1]
        self.assertFalse(complete.escalated)
        self.assertTrue(complete.draft_quality)

        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalated"], "False")
        self.assertEqual(rows[0]["escalation_approved"], "False")

    async def test_escalation_pending_approved_writes_ledger_row(self):
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)

        async def approve(request_id):
            return "approved"

        await self._collect(state, _fake_stream_empty, wait_for_approval=approve)
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalated"], "True")
        self.assertEqual(rows[0]["escalation_approved"], "True")

    async def test_escalation_pending_declined_writes_ledger_row(self):
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)

        async def decline(request_id):
            return "declined"

        await self._collect(state, _fake_stream_empty, wait_for_approval=decline)
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalated"], "False")
        self.assertEqual(rows[0]["escalation_approved"], "False")

    async def test_cancel_during_escalation_pending_yields_cancelled(self):
        """Brew 40: cancelling while paused on escalation_pending must
        actually interrupt the wait - previously cancel_flags was never
        checked by _await_approval at all, so a cancel during the pause
        had no effect until the wait resolved some other way. No
        wait_for_approval is injected here - this exercises the real
        cancel-race inside _await_approval, not the test-only seam."""

        state = self._make_state(
            with_premium=True, escalation_cost_cap_usd=0.0, escalation_approval_timeout_seconds=30.0
        )
        request_id = "cancel-during-pause"
        events = []
        async for event in run_order(
            state,
            prompt="Implement a function.",
            request_id=request_id,
            stream_order_fn=_fake_stream_empty,
        ):
            events.append(event)
            if event.event == "escalation_pending":
                state.cancel_flags[request_id].set()

        event_names = [e.event for e in events]
        self.assertIn("cancelled", event_names)
        self.assertNotIn("escalating", event_names)
        self.assertNotIn("complete", event_names)

    async def test_force_escalation_env_var_off_by_default(self):
        """The demo-only force_escalation flag must never be on unless
        the environment variable is explicitly set in the test/process -
        a normal healthy generation must not escalate."""

        self.assertNotIn("COFFEE_ROUTER_FORCE_ESCALATION", os.environ)
        state = self._make_state()
        events = await self._collect(state, _fake_stream_healthy)
        event_names = [e.event for e in events]
        self.assertNotIn("escalation_pending", event_names)

    async def test_force_escalation_env_var_forces_escalation_path(self):
        # Short timeout: no wait_for_approval is injected below, so
        # without this the real 10-minute default would apply and the
        # test would hang waiting out settings.escalation_approval_timeout_seconds.
        state = self._make_state(
            with_premium=True, escalation_cost_cap_usd=0.0, escalation_approval_timeout_seconds=0.05
        )
        os.environ["COFFEE_ROUTER_FORCE_ESCALATION"] = "1"
        try:
            events = await self._collect(state, _fake_stream_healthy)
        finally:
            os.environ.pop("COFFEE_ROUTER_FORCE_ESCALATION", None)
        event_names = [e.event for e in events]
        self.assertIn(
            "escalation_pending", event_names, "force_escalation should force even a healthy stream to escalate"
        )

    async def test_no_raw_model_id_in_any_yielded_event(self):
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)

        async def approve(request_id):
            return "approved"

        events = await self._collect(state, _fake_stream_empty, wait_for_approval=approve)
        raw_ids = state.bean_registry.known_model_ids()
        for event in events:
            frame = event.to_sse()
            for raw_id in raw_ids:
                self.assertNotIn(raw_id, frame)

    async def test_short_response_below_one_tick_still_reaches_the_client(self):
        """Regression test for a real bug the Brew 38 live demo found:
        a response shorter than one generating_tick_tokens worth of
        content must still be flushed as a generating event before
        __final__ - CompleteEvent carries no content field, so this was
        the only way that text ever reached the client."""

        state = self._make_state()
        events = await self._collect(state, _fake_stream_short)
        generating_events = [e for e in events if e.event == "generating"]
        deltas = [e.text_delta for e in generating_events if e.text_delta]
        self.assertTrue(deltas, "expected the short response to still produce a generating event")
        self.assertIn("Hi", "".join(deltas))

    async def test_generating_events_carry_text_delta(self):
        state = self._make_state()
        events = await self._collect(state, _fake_stream_healthy)
        generating_events = [e for e in events if e.event == "generating"]
        self.assertTrue(generating_events, "expected at least one generating event")
        deltas = [e.text_delta for e in generating_events if e.text_delta]
        self.assertTrue(deltas, "expected at least one generating event with a non-empty text_delta")
        self.assertIn("Hello", "".join(deltas))

    async def test_manual_bean_override_bypasses_policy(self):
        """Brew 37: docs/design/coffee-counter-chat-ui-design.md Section 3.2 -
        fixture policy's "code" entry names House Blend as primary, but an
        explicit override to Second Pour must win."""

        state = self._make_state()
        events = [
            event
            async for event in run_order(
                state,
                prompt="Implement a function.",
                stream_order_fn=_fake_stream_healthy,
                bean_alias_override="Second Pour",
            )
        ]
        route_event = next(e for e in events if e.event == "route_selected")
        self.assertEqual(route_event.bean_alias, "Second Pour")
        self.assertEqual(route_event.policy_entry, "manual/second-pour")
        complete = events[-1]
        self.assertEqual(complete.bean_alias, "Second Pour")

    async def test_manual_bean_override_unavailable_bean_yields_error_event(self):
        state = self._make_state(with_premium=False)  # Reserve Blend has no model_id
        events = [
            event
            async for event in run_order(
                state,
                prompt="Implement a function.",
                stream_order_fn=_fake_stream_healthy,
                bean_alias_override="Reserve Blend",
            )
        ]
        self.assertEqual(events[-1].event, "error")
        self.assertEqual(events[-1].error_type, "invalid_bean_override")

    async def test_session_id_persists_user_and_assistant_messages(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")

        await self._collect(state, _fake_stream_healthy, session_id=session_id)

        messages = state.session_store.get_messages(session_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[0].content, "Implement a function.")
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(messages[1].bean_alias, "House Blend")

    async def test_session_id_sets_title_from_first_prompt(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")

        await self._collect(state, _fake_stream_healthy, session_id=session_id)

        sessions = state.session_store.list_sessions("project-a")
        self.assertEqual(sessions[0].title, "Implement a function.")

    async def test_no_session_id_does_not_touch_session_store(self):
        state = self._make_state(with_session_store=True)
        await self._collect(state, _fake_stream_healthy)  # no session_id
        # No session was ever created, so nothing to list - just confirm no crash
        # and the store remains empty for an arbitrary project name.
        self.assertEqual(state.session_store.list_sessions("project-a"), [])

    async def test_cancel_mid_stream_yields_cancelled_not_complete(self):
        state = self._make_state()
        request_id = "cancel-test-request"

        events = []
        async for event in run_order(
            state,
            prompt="Implement a function.",
            request_id=request_id,
            stream_order_fn=_fake_stream_healthy,
        ):
            events.append(event)
            if event.event == "route_selected":
                # Simulate a concurrent POST /v1/cancel for this request_id.
                state.cancel_flags[request_id].set()

        event_names = [e.event for e in events]
        self.assertIn("cancelled", event_names)
        self.assertNotIn("complete", event_names)
        self.assertNotIn("generating", event_names)

    async def test_cancel_flag_cleaned_up_after_request_completes(self):
        state = self._make_state()
        await self._collect(state, _fake_stream_healthy, request_id="req-cleanup")
        self.assertNotIn("req-cleanup", state.cancel_flags)

    def _build_pantry_index(self, *, rows):
        """rows: list of (path, chunk_index, text). Writes a minimal FTS5
        index directly (bypassing the indexer CLI, which is covered by its
        own tests) so these tests only exercise run_order()'s retrieval
        wiring."""

        from router.app.pantry import connect

        index_path = Path(self._tmp_dir.name) / "pantry_index.db"
        with connect(index_path) as conn:
            for path, chunk_index, text in rows:
                conn.execute(
                    "INSERT INTO chunks (path, chunk_index, text) VALUES (?, ?, ?)",
                    (path, chunk_index, text),
                )
        return index_path

    async def test_use_pantry_true_injects_chunks_and_reports_sources(self):
        index_path = self._build_pantry_index(
            rows=[
                ("knowledge/00_index.md", 0, "Implement a function that greets the user."),
                ("knowledge/other.md", 0, "Unrelated coffee brewing notes."),
            ]
        )
        state = self._make_state(pantry_index_path=index_path, pantry_top_k=5)

        captured = {}

        async def _capturing_stream(model_id, prompt, **_kwargs):
            captured["prompt"] = prompt
            async for chunk in _fake_stream_healthy(model_id, prompt, **_kwargs):
                yield chunk

        events = await self._collect(state, _capturing_stream, use_pantry=True)

        self.assertIn("--- Pantry source: knowledge/00_index.md ---", captured["prompt"])
        complete = next(e for e in events if e.event == "complete")
        self.assertIsNotNone(complete.pantry_sources)
        self.assertIn("knowledge/00_index.md", complete.pantry_sources)

    async def test_use_pantry_false_never_retrieves_even_with_index_present(self):
        index_path = self._build_pantry_index(
            rows=[("knowledge/00_index.md", 0, "Implement a function that greets the user.")]
        )
        state = self._make_state(pantry_index_path=index_path)

        events = await self._collect(state, _fake_stream_healthy, use_pantry=False)

        complete = next(e for e in events if e.event == "complete")
        self.assertIsNone(complete.pantry_sources)

    async def test_use_pantry_true_with_missing_index_degrades_gracefully(self):
        missing_index_path = Path(self._tmp_dir.name) / "does-not-exist.db"
        state = self._make_state(pantry_index_path=missing_index_path)

        events = await self._collect(state, _fake_stream_healthy, use_pantry=True)

        complete = next(e for e in events if e.event == "complete")
        self.assertIsNone(complete.pantry_sources)
        self.assertEqual([e.event for e in events][-1], "complete")

    async def test_use_pantry_true_with_no_matching_chunks_yields_none_sources(self):
        index_path = self._build_pantry_index(
            rows=[("knowledge/other.md", 0, "zzzznomatchzzzz qqqqnothingqqqq")]
        )
        state = self._make_state(pantry_index_path=index_path)

        events = await self._collect(state, _fake_stream_healthy, use_pantry=True)

        complete = next(e for e in events if e.event == "complete")
        self.assertIsNone(complete.pantry_sources)


class AttachmentFlowTests(unittest.IsolatedAsyncioTestCase):
    """Brew 38: end-to-end attachment resolution inside run_order() -
    text/PDF inlining, vision routing constraint, ledger fields, and
    upload cleanup. See docs/design/attachments-design.md."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)
        self.policy_path = policy_path
        self.ledger_path = Path(self._tmp_dir.name) / "router_requests.csv"
        self.uploads_root = Path(self._tmp_dir.name) / "uploads"

    def _make_state(self, registry=None):
        registry = registry or _make_bean_registry(with_premium=True)
        policy = RoutingPolicy.from_yaml(self.policy_path, bean_registry=registry)
        settings = Settings(
            generating_tick_tokens=5,
            generating_tick_seconds=999,
            truncation_min_expected_tokens=10,
            refusal_keywords=["i cannot help"],
        )
        ledger = RouterLedger(self.ledger_path)
        return RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            uploads_root=self.uploads_root,
        )

    def _register_upload(
        self, state, request_id, filename, content_type, kind, *, extracted_text=None, file_bytes=b"fixture-bytes"
    ):
        attachment_id = new_attachment_id()
        file_path = save_upload(
            request_id, attachment_id, filename, file_bytes, uploads_root=state.uploads_root
        )
        state.uploads[attachment_id] = UploadRecord(
            attachment_id=attachment_id,
            request_id=request_id,
            filename=filename,
            content_type=content_type,
            kind=kind,
            size_bytes=len(file_bytes),
            file_path=file_path,
            extracted_text=extracted_text,
        )
        return attachment_id

    async def test_text_attachment_inlines_extracted_content_and_updates_ledger(self):
        state = self._make_state()
        request_id = "req-attach-text"
        extracted_text = "The quarterly numbers look strong."
        attachment_id = self._register_upload(
            state, request_id, "notes.txt", "text/plain", "text", extracted_text=extracted_text
        )

        captured = {}

        async def fake_stream(model_id, prompt, **kwargs):
            captured["prompt"] = prompt
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        events = [
            event
            async for event in run_order(
                state,
                prompt="Summarize this.",
                attachment_ids=[attachment_id],
                request_id=request_id,
                stream_order_fn=fake_stream,
            )
        ]

        self.assertIn("--- Attached file: notes.txt ---", captured["prompt"])
        self.assertIn(extracted_text, captured["prompt"])

        route_event = next(e for e in events if e.event == "route_selected")
        self.assertEqual(route_event.complexity, "cold_brew")
        self.assertIsNone(route_event.constraint_reason)

        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["attachment_count"], "1")
        self.assertEqual(rows[0]["attachment_tokens_est"], str(len(extracted_text) // 4))

    async def test_unknown_attachment_id_yields_error_event(self):
        state = self._make_state()
        events = [
            event
            async for event in run_order(
                state,
                prompt="Summarize this.",
                attachment_ids=["nonexistent-id"],
                request_id="req-bad-attach",
                stream_order_fn=_fake_stream_healthy,
            )
        ]
        self.assertEqual(events[-1].event, "error")
        self.assertEqual(events[-1].error_type, "unknown_attachment_id")

    async def test_image_attachment_without_vision_bean_yields_error_event(self):
        """Real state as of Brew 38: no Bean has vision: true, so an image
        attachment must fail loudly, not silently drop the image."""

        state = self._make_state()  # default fixture registry - no vision Bean
        request_id = "req-attach-image-novision"
        attachment_id = self._register_upload(
            state,
            request_id,
            "screenshot.png",
            "image/png",
            "image",
            file_bytes=b"\x89PNG\r\n\x1a\n-fixture",
        )
        events = [
            event
            async for event in run_order(
                state,
                prompt="What is in this screenshot?",
                attachment_ids=[attachment_id],
                request_id=request_id,
                stream_order_fn=_fake_stream_healthy,
            )
        ]
        self.assertEqual(events[-1].event, "error")
        self.assertEqual(events[-1].error_type, "no_vision_bean_available")
        # Uploads must still be cleaned up on the error path.
        self.assertFalse((state.uploads_root / request_id).exists())

    async def test_image_attachment_escalates_to_vision_bean_and_sends_data_url(self):
        state = self._make_state(registry=_make_bean_registry_with_vision())
        request_id = "req-attach-image-vision"
        png_bytes = b"\x89PNG\r\n\x1a\n-fixture-bytes"
        attachment_id = self._register_upload(
            state, request_id, "screenshot.png", "image/png", "image", file_bytes=png_bytes
        )

        captured = {}

        async def fake_stream(model_id, prompt, **kwargs):
            captured["image_data_urls"] = kwargs.get("image_data_urls")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        events = [
            event
            async for event in run_order(
                state,
                prompt="What is in this screenshot?",
                attachment_ids=[attachment_id],
                request_id=request_id,
                stream_order_fn=fake_stream,
            )
        ]

        route_event = next(e for e in events if e.event == "route_selected")
        self.assertEqual(route_event.bean_alias, "Vision Bean")
        self.assertIn("needs_vision", route_event.constraint_reason)

        self.assertEqual(len(captured["image_data_urls"]), 1)
        self.assertTrue(captured["image_data_urls"][0].startswith("data:image/png;base64,"))

    async def test_uploads_cleaned_up_after_request_completes(self):
        state = self._make_state()
        request_id = "req-attach-cleanup"
        attachment_id = self._register_upload(
            state, request_id, "notes.txt", "text/plain", "text", extracted_text="hello"
        )
        request_dir = state.uploads_root / request_id
        self.assertTrue(request_dir.is_dir())

        events = [
            event
            async for event in run_order(
                state,
                prompt="Summarize this.",
                attachment_ids=[attachment_id],
                request_id=request_id,
                stream_order_fn=_fake_stream_healthy,
            )
        ]

        self.assertEqual(events[-1].event, "complete")
        self.assertFalse(request_dir.exists())
        self.assertNotIn(attachment_id, state.uploads)


class FastApiSmokeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)

        registry = _make_bean_registry(with_premium=True)
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        settings = Settings(generating_tick_tokens=5, generating_tick_seconds=999)
        ledger = RouterLedger(Path(self._tmp_dir.name) / "router_requests.csv")
        session_store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        preference_store = PreferenceStore(Path(self._tmp_dir.name) / "preferences.db")
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            session_store=session_store,
            preference_store=preference_store,
            stream_order_fn=_fake_stream_healthy,
            uploads_root=Path(self._tmp_dir.name) / "uploads",
        )
        self.app = create_app(state=self.state)

    async def test_order_endpoint_streams_sse_events(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/v1/order", json={"prompt": "Implement a function."}) as response:
                self.assertEqual(response.status_code, 200)
                body_lines = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        body_lines.append(json.loads(line[len("data: "):]))

        event_names = [item["event"] for item in body_lines]
        self.assertEqual(event_names[0], "order_received")
        self.assertEqual(event_names[-1], "complete")

    async def test_pantry_file_endpoint_serves_real_knowledge_file(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/pantry/file", params={"path": "knowledge/00_index.md"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["path"], "knowledge/00_index.md")
        self.assertIn("Knowledge Index", body["content"])

    async def test_pantry_file_endpoint_rejects_path_traversal(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            for traversal_path in [
                "../router/config/settings.yaml",
                "knowledge/../../router/config/settings.yaml",
                "knowledge/../../.env",
            ]:
                response = await client.get("/v1/pantry/file", params={"path": traversal_path})
                self.assertEqual(response.status_code, 404, msg=traversal_path)

    async def test_pantry_file_endpoint_rejects_absolute_path(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/v1/pantry/file", params={"path": "C:/Windows/win.ini"}
            )
        self.assertEqual(response.status_code, 404)

    async def test_pantry_file_endpoint_404_for_unknown_file(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/v1/pantry/file", params={"path": "knowledge/does-not-exist.md"}
            )
        self.assertEqual(response.status_code, 404)

    async def test_approve_escalation_resolves_pending_future(self):
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.state.pending_escalations["req-123"] = future
        self.state.pending_escalation_context["req-123"] = EscalationContext(
            request_id="req-123",
            session_id=None,
            reason="truncated",
            est_cost_usd=0.5,
            premium_bean_alias="Reserve Blend",
            started_at="2026-07-12T20:00:00+00:00",
            decision_deadline="2026-07-12T20:10:00+00:00",
        )

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/approve_escalation", json={"request_id": "req-123", "approve": True}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(await future, "approved")

    async def test_approve_escalation_unknown_request_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/approve_escalation", json={"request_id": "nonexistent", "approve": True}
            )
        self.assertEqual(response.status_code, 404)

    async def test_double_click_approve_second_call_gets_already_resolved(self):
        """Brew 40 Section 3.6: a duplicate/rapid second click must not
        crash, silently no-op, or double-escalate - it gets a clear
        already_resolved response."""

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.state.pending_escalations["req-dup"] = future
        self.state.pending_escalation_context["req-dup"] = EscalationContext(
            request_id="req-dup",
            session_id=None,
            reason="truncated",
            est_cost_usd=0.5,
            premium_bean_alias="Reserve Blend",
            started_at="2026-07-12T20:00:00+00:00",
            decision_deadline="2026-07-12T20:10:00+00:00",
        )

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/v1/approve_escalation", json={"request_id": "req-dup", "approve": True})
            second = await client.post("/v1/approve_escalation", json={"request_id": "req-dup", "approve": True})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "acknowledged")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["status"], "already_resolved")
        self.assertEqual(await future, "approved")

    async def test_late_approval_after_timeout_gets_already_resolved_timed_out(self):
        """A decision arriving after the timeout already fired must not
        be a bare 404 - the caller deserves to know it's too late, not
        that the request_id is unrecognized."""

        self.state.pending_escalation_context["req-late"] = EscalationContext(
            request_id="req-late",
            session_id=None,
            reason="empty",
            est_cost_usd=0.5,
            premium_bean_alias="Reserve Blend",
            started_at="2026-07-12T20:00:00+00:00",
            decision_deadline="2026-07-12T20:10:00+00:00",
            resolved=True,
            resolution="timed_out",
        )
        # No entry in pending_escalations - _await_approval already popped
        # it once the timeout fired, same as the real flow.

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/approve_escalation", json={"request_id": "req-late", "approve": True}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"request_id": "req-late", "status": "already_resolved", "resolution": "timed_out"})

    async def test_pending_escalation_endpoint_404_when_none_pending(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post("/v1/sessions", json={"project": "project-a"})
            session_id = create_response.json()["id"]
            response = await client.get(f"/v1/sessions/{session_id}/pending_escalation")
        self.assertEqual(response.status_code, 404)

    async def test_pending_escalation_endpoint_unknown_session_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/sessions/nonexistent-session/pending_escalation")
        self.assertEqual(response.status_code, 404)

    async def test_reload_recovery_returns_context_while_genuinely_paused(self):
        """Brew 40 Section 3.5: spawns the background task the same way
        the real /v1/order endpoint does (not a shortcut), drains events
        until escalation_pending confirms the pause is real, then checks
        the recovery endpoint sees it - and no longer does once resolved."""

        self.state.settings = self.state.settings.model_copy(
            update={"escalation_cost_cap_usd": 0.0}
        )
        session_id = self.state.session_store.create_session("project-a")

        hold = asyncio.Event()

        async def block_until_released(request_id):
            await hold.wait()
            return "declined"

        queue: "asyncio.Queue" = asyncio.Queue()
        task = asyncio.create_task(
            _run_order_and_publish(
                self.state,
                queue,
                prompt="Implement a function.",
                stream_order_fn=_fake_stream_empty,
                session_id=session_id,
                wait_for_approval=block_until_released,
            )
        )

        seen_pending = False
        while not seen_pending:
            event = await asyncio.wait_for(queue.get(), timeout=5)
            if event is not None and event.event == "escalation_pending":
                seen_pending = True

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/v1/sessions/{session_id}/pending_escalation")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["premium_bean_alias"], "Reserve Blend")
        self.assertIn("decision_deadline", body)

        hold.set()
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=5)
            if event is None:
                break
        await task

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            after = await client.get(f"/v1/sessions/{session_id}/pending_escalation")
        self.assertEqual(after.status_code, 404)

    async def test_order_endpoint_emits_heartbeat_during_a_long_pause(self):
        """Requirement 4: the SSE stream must survive the wait - a
        heartbeat keeps an otherwise-idle connection alive."""

        self.state.settings = self.state.settings.model_copy(
            update={
                "escalation_cost_cap_usd": 0.0,
                "sse_heartbeat_interval_seconds": 0.05,
                "escalation_approval_timeout_seconds": 5.0,
            }
        )
        self.state.stream_order_fn = _fake_stream_empty

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/v1/order", json={"prompt": "Implement a function."}) as response:
                events = []
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = json.loads(line[len("data: "):])
                    events.append(payload)
                    if payload["event"] == "heartbeat":
                        # Cancel so the test doesn't wait out the full
                        # approval timeout once we've proven a heartbeat
                        # arrived during the pause.
                        await client.post("/v1/cancel", json={"request_id": payload["request_id"]})

        event_names = [e["event"] for e in events]
        self.assertIn("heartbeat", event_names)
        self.assertIn("escalation_pending", event_names)
        heartbeat_index = event_names.index("heartbeat")
        pending_index = event_names.index("escalation_pending")
        self.assertGreater(
            heartbeat_index, pending_index, "heartbeat should arrive during the pause, after escalation_pending"
        )

    async def test_retry_unknown_request_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/retry", json={"request_id": "nonexistent"})
        self.assertEqual(response.status_code, 404)

    async def test_get_preferences_empty_by_default(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/preferences")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    async def test_set_then_get_preference_round_trips(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            set_response = await client.post(
                "/v1/preferences", json={"key": "counter_collapsed", "value": "true"}
            )
            self.assertEqual(set_response.status_code, 200)
            get_response = await client.get("/v1/preferences")
        self.assertEqual(get_response.json(), {"counter_collapsed": "true"})

    async def test_order_request_id_collision_returns_409(self):
        """Brew 38: a client-generated request_id (used to scope uploads)
        that is already in flight must not silently start a second
        request under the same id."""

        self.state.cancel_flags["dup-id"] = asyncio.Event()
        self.addCleanup(self.state.cancel_flags.pop, "dup-id", None)
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/order", json={"prompt": "hi", "request_id": "dup-id"})
        self.assertEqual(response.status_code, 409)

    async def test_cors_header_present_for_allowed_origin(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/beans", headers={"Origin": "http://localhost:3000"}
            )
        # /v1/beans is GET-only, so this POST 405s, but CORS headers are
        # applied by middleware before routing rejects the method - what
        # matters here is proving the middleware is wired in at all.
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/beans", headers={"Origin": "http://localhost:3000"})
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3000")

    async def test_beans_endpoint_returns_aliases_only(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/beans")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        aliases = {b["alias"] for b in body}
        self.assertEqual(aliases, {"House Blend", "Second Pour", "Reserve Blend"})
        raw_ids = self.state.bean_registry.known_model_ids()
        for bean in body:
            for raw_id in raw_ids:
                self.assertNotIn(raw_id, str(bean))

    async def test_create_and_list_sessions(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post("/v1/sessions", json={"project": "project-a"})
            self.assertEqual(create_response.status_code, 200)
            session_id = create_response.json()["id"]

            list_response = await client.get("/v1/sessions", params={"project": "project-a"})
        self.assertEqual(list_response.status_code, 200)
        sessions = list_response.json()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["id"], session_id)
        self.assertEqual(sessions[0]["cost_total_usd"], 0.0)

    async def test_order_with_session_id_populates_session_messages(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post("/v1/sessions", json={"project": "project-a"})
            session_id = create_response.json()["id"]

            async with client.stream(
                "POST",
                "/v1/order",
                json={"prompt": "Implement a function.", "session_id": session_id},
            ) as response:
                self.assertEqual(response.status_code, 200)
                async for _ in response.aiter_lines():
                    pass

            messages_response = await client.get(f"/v1/sessions/{session_id}/messages")
        self.assertEqual(messages_response.status_code, 200)
        messages = messages_response.json()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")

    async def test_order_with_unknown_session_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/order", json={"prompt": "Hi", "session_id": "nonexistent-session"}
            )
        self.assertEqual(response.status_code, 404)

    async def test_messages_for_unknown_session_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/sessions/nonexistent-session/messages")
        self.assertEqual(response.status_code, 404)

    async def test_rate_endpoint_updates_ledger_and_session(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post("/v1/sessions", json={"project": "project-a"})
            session_id = create_response.json()["id"]

            async with client.stream(
                "POST",
                "/v1/order",
                json={"prompt": "Implement a function.", "session_id": session_id},
            ) as response:
                async for _ in response.aiter_lines():
                    pass

            messages = (await client.get(f"/v1/sessions/{session_id}/messages")).json()
            request_id = messages[1]["request_id"]

            rate_response = await client.post(
                "/v1/rate", json={"request_id": request_id, "rating": "good"}
            )
        self.assertEqual(rate_response.status_code, 200)

        ledger_rows = self.state.ledger.read_all_rows()
        self.assertEqual(ledger_rows[0]["rating"], "good")

    async def test_rate_endpoint_rejects_invalid_rating(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/rate", json={"request_id": "req-1", "rating": "amazing"}
            )
        self.assertEqual(response.status_code, 422)

    async def test_rate_endpoint_unknown_request_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/rate", json={"request_id": "nonexistent", "rating": "good"}
            )
        self.assertEqual(response.status_code, 404)

    async def test_cancel_unknown_request_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/cancel", json={"request_id": "nonexistent"})
        self.assertEqual(response.status_code, 404)

    async def test_cancel_sets_flag_for_in_flight_request(self):
        request_id = "in-flight-request"
        cancel_event = asyncio.Event()
        self.state.cancel_flags[request_id] = cancel_event

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/cancel", json={"request_id": request_id})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(cancel_event.is_set())

    async def test_manual_override_via_order_endpoint(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/order",
                json={"prompt": "Implement a function.", "bean_alias_override": "Second Pour"},
            ) as response:
                body_lines = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        body_lines.append(json.loads(line[len("data: "):]))

        route_event = next(item for item in body_lines if item["event"] == "route_selected")
        self.assertEqual(route_event["bean_alias"], "Second Pour")
        self.assertEqual(route_event["policy_entry"], "manual/second-pour")


class MemoryProposalEndpointTests(unittest.IsolatedAsyncioTestCase):
    """Brew 41 (docs/design/memory-and-pantry-design.md Section 3): the
    generate/approve/discard endpoints. memory_proposal_repo_root always
    points at a temp fixture, never the real repo - these tests must
    never write to the real brew-log/ files."""

    VALID_RESPONSE = (
        "### FILE: brew-log/active_context.md\n"
        "# Active Context\n\nUpdated during the session.\n"
        "### END FILE\n\n"
        "### FILE: brew-log/progress.md\n"
        "# Progress\n\nDid a thing.\n"
        "### END FILE\n"
    )

    async def _fake_proposal_stream(self, model_id, prompt, **_kwargs):
        yield StreamChunk(content_delta=self.VALID_RESPONSE)
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 42})
        yield StreamChunk(is_final=True)

    async def _bad_format_stream(self, model_id, prompt, **_kwargs):
        yield StreamChunk(content_delta="not the right format at all")
        yield StreamChunk(is_final=True)

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)

        self.repo_root = Path(self._tmp_dir.name) / "fixture_repo"
        (self.repo_root / "brew-log").mkdir(parents=True)
        (self.repo_root / "brew-log" / "active_context.md").write_text(
            "# Active Context\n\nOriginal line.\n", encoding="utf-8"
        )
        (self.repo_root / "brew-log" / "progress.md").write_text(
            "# Progress\n\nOriginal progress line.\n", encoding="utf-8"
        )

        registry = _make_bean_registry(with_premium=True)
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        settings = Settings(generating_tick_tokens=5, generating_tick_seconds=999)
        ledger = RouterLedger(Path(self._tmp_dir.name) / "router_requests.csv")
        session_store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            session_store=session_store,
            uploads_root=Path(self._tmp_dir.name) / "uploads",
            stream_order_fn=self._fake_proposal_stream,
            memory_proposal_repo_root=self.repo_root,
        )
        self.session_id = session_store.create_session("default")
        session_store.add_message(
            self.session_id, request_id="r1", role="user", content="Implement the widget."
        )
        session_store.add_message(
            self.session_id, request_id="r1", role="assistant", content="Done, widget implemented."
        )
        self.app = create_app(state=self.state)

    async def test_generate_returns_diffs_for_both_files(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/v1/sessions/{self.session_id}/memory_proposal")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        paths = {f["path"] for f in body["files"]}
        self.assertEqual(paths, {"brew-log/active_context.md", "brew-log/progress.md"})
        self.assertIn(body["proposal_id"], self.state.memory_proposals)

    async def test_generate_unknown_session_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/sessions/does-not-exist/memory_proposal")
        self.assertEqual(response.status_code, 404)

    async def test_generate_unparseable_response_returns_422_and_stores_nothing(self):
        self.state.stream_order_fn = self._bad_format_stream
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/v1/sessions/{self.session_id}/memory_proposal")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.state.memory_proposals, {})

    async def test_approve_writes_files_logs_ledger_and_clears_proposal(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            generate_response = await client.post(f"/v1/sessions/{self.session_id}/memory_proposal")
            proposal_id = generate_response.json()["proposal_id"]

            approve_response = await client.post(f"/v1/memory_proposals/{proposal_id}/approve")

        self.assertEqual(approve_response.status_code, 200)
        self.assertNotIn(proposal_id, self.state.memory_proposals)
        self.assertIn(
            "Updated during the session.",
            (self.repo_root / "brew-log" / "active_context.md").read_text(encoding="utf-8"),
        )
        ledger_rows = self.state.ledger.read_all_rows()
        memory_rows = [row for row in ledger_rows if row["task_type"] == "memory"]
        self.assertEqual(len(memory_rows), 1)
        self.assertEqual(memory_rows[0]["request_id"], proposal_id)

    async def test_approve_unknown_proposal_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/memory_proposals/does-not-exist/approve")
        self.assertEqual(response.status_code, 404)

    async def test_discard_clears_proposal_and_writes_nothing(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            generate_response = await client.post(f"/v1/sessions/{self.session_id}/memory_proposal")
            proposal_id = generate_response.json()["proposal_id"]

            discard_response = await client.post(f"/v1/memory_proposals/{proposal_id}/discard")

        self.assertEqual(discard_response.status_code, 200)
        self.assertNotIn(proposal_id, self.state.memory_proposals)
        self.assertEqual(
            (self.repo_root / "brew-log" / "active_context.md").read_text(encoding="utf-8"),
            "# Active Context\n\nOriginal line.\n",
        )
        ledger_rows = self.state.ledger.read_all_rows()
        self.assertEqual([row for row in ledger_rows if row["task_type"] == "memory"], [])

    async def test_discard_unknown_proposal_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/memory_proposals/does-not-exist/discard")
        self.assertEqual(response.status_code, 404)

    async def test_approve_re_checks_guardrail_and_returns_422_on_race(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            generate_response = await client.post(f"/v1/sessions/{self.session_id}/memory_proposal")
            proposal_id = generate_response.json()["proposal_id"]

            # Simulate a concurrent edit that makes the already-generated
            # new_content look like an over-50% deletion by the time
            # approval runs.
            (self.repo_root / "brew-log" / "active_context.md").write_text(
                "line one\nline two\nline three\nline four\nline five\nline six\n",
                encoding="utf-8",
            )

            approve_response = await client.post(f"/v1/memory_proposals/{proposal_id}/approve")

        self.assertEqual(approve_response.status_code, 422)
        # Nothing was written - the race-triggering edit is still intact.
        self.assertIn(
            "line six",
            (self.repo_root / "brew-log" / "active_context.md").read_text(encoding="utf-8"),
        )


FIXTURE_TASTING_NOTES = """# Tasting Notes

### 2026-07-14 - Fixture Entry

Task file:

roastery/cup_tests/002-tiny-python-fix.md

| Bean | Status | Latency | Tokens | Cost | Captured | Reviewed | Score | Use again? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `vendor/default:free` | ok | 1000ms | 500 total | $0.00 | yes | yes | 7 | yes |
| `vendor/fallback:free` | ok | 900ms | 400 total | $0.00 | yes | yes | 6 | yes |
"""


class PolicyRebuildEndpointTests(unittest.IsolatedAsyncioTestCase):
    """Brew 42 (docs/design/learning-loop-and-release-design.md Section
    3.2): the policy rebuild preview/apply/discard endpoints.
    routing_policy_path/tasting_notes_path always point at temp fixtures,
    never the real repo files - these tests must never write to the real
    router/config/routing_policy.yaml or roastery/tasting_notes.md."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)

        self.tasting_notes_path = Path(self._tmp_dir.name) / "tasting_notes.md"
        self.tasting_notes_path.write_text(FIXTURE_TASTING_NOTES, encoding="utf-8")
        self.routing_policy_path = Path(self._tmp_dir.name) / "generated_routing_policy.yaml"

        registry = _make_bean_registry(with_premium=True)
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        settings = Settings(generating_tick_tokens=5, generating_tick_seconds=999)
        self.ledger = RouterLedger(Path(self._tmp_dir.name) / "router_requests.csv")
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=self.ledger,
            uploads_root=Path(self._tmp_dir.name) / "uploads",
            routing_policy_path=self.routing_policy_path,
            tasting_notes_path=self.tasting_notes_path,
        )
        self.app = create_app(state=self.state)

    def _append_rating(self, *, bean_alias, rating, escalated=False, task_type="code"):
        self.ledger.append(
            LedgerRow(
                timestamp="2026-07-14T00:00:00+00:00",
                request_id=f"req-{bean_alias}-{rating}-{escalated}",
                task_type=task_type,
                bean_alias=bean_alias,
                raw_model_id="vendor/x:free",
                tokens_in=10,
                tokens_out=10,
                cost_usd=0.0,
                latency_ms=100,
                escalated=escalated,
                escalation_approved=None,
                rating=rating,
            )
        )

    async def test_preview_computes_diff_against_current_on_disk_file(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/policy/rebuild_preview")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("proposal_id", body)
        self.assertIn("task_types:", body["diff"])
        self.assertEqual(body["escalation_candidates"], [])
        self.assertIn(body["proposal_id"], self.state.policy_rebuild_proposals)
        # Never written by preview.
        self.assertFalse(self.routing_policy_path.is_file())

    async def test_preview_below_rating_threshold_does_not_shift_primary_bean(self):
        for _ in range(4):
            self._append_rating(bean_alias="Second Pour", rating="good")

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/policy/rebuild_preview")

        body = response.json()
        self.assertNotIn("shifted the primary Bean", body["diff"])

    async def test_preview_at_threshold_can_shift_primary_bean_and_apply_hot_swaps_policy(self):
        for _ in range(5):
            self._append_rating(bean_alias="House Blend", rating="failed")
        for _ in range(5):
            self._append_rating(bean_alias="Second Pour", rating="good")

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            preview_response = await client.post("/v1/policy/rebuild_preview")
            proposal_id = preview_response.json()["proposal_id"]
            self.assertIn("shifted the primary Bean", preview_response.json()["diff"])

            apply_response = await client.post(f"/v1/policy/rebuild_apply/{proposal_id}")

        self.assertEqual(apply_response.status_code, 200)
        self.assertTrue(self.routing_policy_path.is_file())
        self.assertNotIn(proposal_id, self.state.policy_rebuild_proposals)
        # Hot-swapped without a restart - a fresh route selection reflects
        # the newly written policy.
        route = self.state.routing_policy.select_route("code")
        self.assertEqual(route.bean_alias, "Second Pour")

    async def test_apply_unknown_proposal_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/policy/rebuild_apply/does-not-exist")
        self.assertEqual(response.status_code, 404)

    async def test_apply_refuses_when_file_changed_since_preview(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            preview_response = await client.post("/v1/policy/rebuild_preview")
            proposal_id = preview_response.json()["proposal_id"]

            # Simulate a concurrent edit/apply landing between preview and
            # this apply call.
            self.routing_policy_path.write_text("# raced\n", encoding="utf-8")

            apply_response = await client.post(f"/v1/policy/rebuild_apply/{proposal_id}")

        self.assertEqual(apply_response.status_code, 422)
        self.assertEqual(self.routing_policy_path.read_text(encoding="utf-8"), "# raced\n")
        self.assertNotIn(proposal_id, self.state.policy_rebuild_proposals)

    async def test_discard_clears_proposal_and_writes_nothing(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            preview_response = await client.post("/v1/policy/rebuild_preview")
            proposal_id = preview_response.json()["proposal_id"]

            discard_response = await client.post(f"/v1/policy/rebuild_discard/{proposal_id}")

        self.assertEqual(discard_response.status_code, 200)
        self.assertNotIn(proposal_id, self.state.policy_rebuild_proposals)
        self.assertFalse(self.routing_policy_path.is_file())

    async def test_discard_unknown_proposal_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/policy/rebuild_discard/does-not-exist")
        self.assertEqual(response.status_code, 404)

    async def test_escalation_candidates_surfaced_in_preview(self):
        for _ in range(4):
            self._append_rating(bean_alias="House Blend", rating="good", escalated=True)
        for _ in range(6):
            self._append_rating(bean_alias="House Blend", rating="good", escalated=False)

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/policy/rebuild_preview")

        self.assertIn("code", response.json()["escalation_candidates"])


class UploadEndpointTests(unittest.IsolatedAsyncioTestCase):
    """Brew 38: POST /v1/upload - validation, PDF extraction happy/scanned
    paths, and storage under uploads_root."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)

        registry = _make_bean_registry(with_premium=True)
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        settings = Settings(max_upload_size_bytes=1024, pdf_min_extracted_chars=20, upload_ttl_seconds=3600)
        ledger = RouterLedger(Path(self._tmp_dir.name) / "router_requests.csv")
        self.uploads_root = Path(self._tmp_dir.name) / "uploads"
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            uploads_root=self.uploads_root,
        )
        self.app = create_app(state=self.state)

    async def _upload(self, filename, content, content_type, request_id="req-upload-1"):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/v1/upload",
                data={"request_id": request_id},
                files={"file": (filename, content, content_type)},
            )

    async def test_valid_text_upload_returns_200_and_is_recorded(self):
        response = await self._upload("notes.txt", b"hello world", "text/plain")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["kind"], "text")
        self.assertEqual(body["filename"], "notes.txt")
        self.assertIn(body["attachment_id"], self.state.uploads)

    async def test_disallowed_extension_returns_422(self):
        response = await self._upload("archive.zip", b"binary-ish", "application/zip")
        self.assertEqual(response.status_code, 422)
        self.assertIn("not allowed", response.json()["detail"])

    async def test_oversized_file_returns_422(self):
        # settings.max_upload_size_bytes is 1024 in this fixture.
        response = await self._upload("big.txt", b"x" * 2000, "text/plain")
        self.assertEqual(response.status_code, 422)
        self.assertIn("exceeding", response.json()["detail"])

    async def test_pdf_with_real_text_extracts_and_returns_char_count(self):
        pdf_bytes = _text_bearing_pdf_bytes()
        response = await self._upload("doc.pdf", pdf_bytes, "application/pdf")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["kind"], "pdf")
        self.assertGreater(body["extracted_text_chars"], 0)
        record = self.state.uploads[body["attachment_id"]]
        self.assertIn("Hello test PDF text", record.extracted_text)

    async def test_scanned_pdf_returns_422_clear_error(self):
        pdf_bytes = _blank_pdf_bytes()
        response = await self._upload("scanned.pdf", pdf_bytes, "application/pdf")
        self.assertEqual(response.status_code, 422)
        self.assertIn("no extractable text", response.json()["detail"])

    async def test_upload_writes_file_under_request_scoped_directory(self):
        response = await self._upload("notes.txt", b"hello world", "text/plain", request_id="req-scope-1")
        attachment_id = response.json()["attachment_id"]
        record = self.state.uploads[attachment_id]
        self.assertEqual(record.file_path.parent, self.uploads_root / "req-scope-1")
        self.assertTrue(record.file_path.is_file())


if __name__ == "__main__":
    unittest.main()
