import asyncio
import json
import os
import unittest
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import httpx
import yaml
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from router.app.aliases import Bean, BeanRegistry
from router.app.auth import get_current_user
from router.app.config import Settings
from router.app.ledger import LedgerRow, RouterLedger
from router.app.main import (
    DEFAULT_CORS_ALLOWED_ORIGINS,
    EscalationContext,
    RouterState,
    _cors_allowed_origins,
    _distinct_web_sources,
    _run_order_and_publish,
    _with_system_message,
    check_rate_limit,
    check_spend_cap,
    create_app,
    run_order,
)
from router.app.openrouter_client import OpenRouterClientError, StreamChunk
from router.app.preferences import PreferenceStore
from router.app.routing import RoutingPolicy
from router.app.sessions import SessionStore, UserRecord
from router.app.uploads import UploadRecord, new_attachment_id, save_upload

# Brew 43 (docs/design/auth-projects-chat-management-design.md Section
# 3.1, Gap 3): every /v1/* endpoint now requires Depends(get_current_user).
# Rather than adding a real Authorization header to the ~100 existing
# httpx.AsyncClient call sites in this file, every HTTP-level test class
# overrides the dependency wholesale via _override_auth(app) right after
# create_app() - the real header-based path is exercised separately and
# thoroughly in router/tests/test_auth.py.
FAKE_USER = UserRecord(
    id=1,
    username="test-user",
    password_hash="",
    display_name="Test User",
    created_at="2026-01-01T00:00:00+00:00",
)


def _override_auth(app) -> None:
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER


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
                # Matches the real beans.yaml Reserve Blend pricing (not
                # round test numbers) - now load-bearing, not decorative:
                # estimate_cost_usd() is real now (spend-cap Brew fixed
                # the shared estimator), so escalation_cost_cap_usd
                # actually gates on this value. A typical escalation at
                # this pricing is a cent or two, comfortably under every
                # test fixture's 0.50 escalation_cost_cap_usd default.
                price_per_1k_input_usd=0.003,
                price_per_1k_output_usd=0.015,
                status="active",
                # Matches the real beans.yaml Reserve Blend, which is
                # tool_calling-capable - load-bearing for the web-search
                # Brew's routing constraint (needs_tool_calling escalates a
                # non-capable primary Bean to the cheapest capable one).
                tool_calling=True,
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


async def _fake_stream_empty_reported_cost(model_id, prompt, **_kwargs):
    """Same shape as _fake_stream_empty (triggers the "empty" failure ->
    auto_escalate), but the finish chunk carries a real OpenRouter usage.cost
    - used to test resolve_cost()'s "reported" path end to end through
    _run_order_body/_run_escalation."""

    yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 0, "cost": 0.0042})
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


def _make_capturing_stream_fn(calls):
    """Web search cost optimization Brew: records (model_id, tools) for
    every call, so a test can assert what was actually sent to OpenRouter
    without depending on real network I/O."""

    async def _fake(model_id, prompt, **kwargs):
        calls.append({"model_id": model_id, "tools": kwargs.get("tools")})
        yield StreamChunk(content_delta="Hello world")
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 5})
        yield StreamChunk(is_final=True)

    return _fake


def _make_capturing_stream_fn_with_reported_cost(calls, *, cost_usd):
    async def _fake(model_id, prompt, **kwargs):
        calls.append({"model_id": model_id, "tools": kwargs.get("tools")})
        yield StreamChunk(content_delta="Hello world")
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 5, "cost": cost_usd})
        yield StreamChunk(is_final=True)

    return _fake


def _make_capturing_stream_fn_empty(calls):
    """Same empty-content/zero-token shape as _fake_stream_empty (triggers
    the "empty" failure -> auto_escalate), capturing kwargs per call."""

    async def _fake(model_id, prompt, **kwargs):
        calls.append({"model_id": model_id, "tools": kwargs.get("tools")})
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 0})
        yield StreamChunk(is_final=True)

    return _fake


_REALISTIC_ANNOTATION = {
    "type": "url_citation",
    "url_citation": {
        "url": "https://example.com/equities",
        "title": "Top Equities This Week",
        "start_index": 0,
        "end_index": 42,
        "content": "a long excerpt that must never reach web_sources",
    },
}


def _make_stream_fn_with_annotations(calls=None):
    """Web search citations Brew: a realistic shape - the annotation
    arrives whole on an early chunk (role+empty content), matching real
    OpenRouter behavior confirmed live during the cost optimization
    Brew's demo, with prose content following in later chunks."""

    async def _fake(model_id, prompt, **kwargs):
        if calls is not None:
            calls.append({"model_id": model_id, "tools": kwargs.get("tools")})
        yield StreamChunk(content_delta="", annotations=[_REALISTIC_ANNOTATION])
        yield StreamChunk(content_delta="Based on my search, Alphabet led this week.")
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 12})
        yield StreamChunk(is_final=True)

    return _fake


def _make_stream_fn_empty_no_annotations(calls=None):
    """Triggers auto_escalate (empty draft), never carrying annotations -
    the draft itself never used web search successfully in this shape."""

    async def _fake(model_id, prompt, **kwargs):
        if calls is not None:
            calls.append({"model_id": model_id, "tools": kwargs.get("tools")})
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 0})
        yield StreamChunk(is_final=True)

    return _fake


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
        registry=None,
        # Generous by default (unlike the real settings.yaml defaults) so
        # tests not specifically about the spend-cap Brew never trip it
        # incidentally - same "explicit, overridable test kwarg" precedent
        # as escalation_cost_cap_usd above. Tests that DO want to exercise
        # enforcement pass a small value explicitly.
        per_user_daily_cost_cap_usd=100.0,
        global_daily_cost_cap_usd=1000.0,
        per_user_requests_per_minute=1000,
        # Web search cost optimization Brew. Defaults match Settings' own
        # real defaults ("parallel"/"Kimi K2") - the fixture registry has
        # no "Kimi K2" Bean, so that default is a harmless no-op for every
        # test that doesn't build a registry with one.
        web_search_engine="parallel",
        preferred_web_search_bean_alias="Kimi K2",
    ):
        registry = registry or _make_bean_registry(with_premium=with_premium)
        policy = RoutingPolicy.from_yaml(self.policy_path, bean_registry=registry)
        settings = Settings(
            escalation_cost_cap_usd=escalation_cost_cap_usd,
            escalation_approval_timeout_seconds=escalation_approval_timeout_seconds,
            generating_tick_tokens=5,
            generating_tick_seconds=999,
            truncation_min_expected_tokens=10,
            refusal_keywords=["i cannot help"],
            pantry_top_k=pantry_top_k,
            per_user_daily_cost_cap_usd=per_user_daily_cost_cap_usd,
            global_daily_cost_cap_usd=global_daily_cost_cap_usd,
            per_user_requests_per_minute=per_user_requests_per_minute,
            web_search_engine=web_search_engine,
            preferred_web_search_bean_alias=preferred_web_search_bean_alias,
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
        # Reserve Blend's real per-1k pricing at a tiny prompt and the
        # default assumed_output_tokens - a cent or two, well under the
        # 0.50 cap in this fixture's settings (estimate_cost_usd() is now
        # real - spend-cap Brew).
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

    async def test_escalation_pending_declined_sets_over_cap_declined_in_ledger(self):
        """Brew 47 Section 2/resolved question 4: a human declining a real
        /v1/order approval card ("keep the cheap cup") is the strongest
        quality signal in the system - must be logged, not just the
        forced-decline case on /v1/chat/completions."""

        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)

        async def decline(request_id):
            return "declined"

        await self._collect(state, _fake_stream_empty, wait_for_approval=decline)
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["over_cap_declined"], "True")

    async def test_auto_escalate_leaves_over_cap_declined_false(self):
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.50)
        await self._collect(state, _fake_stream_empty)
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["over_cap_declined"], "False")

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

    async def test_free_tier_bean_writes_real_zero_cost_computed_source(self):
        """Cost-inconsistency fix: a free-tier Bean's cost_usd is a real
        $0.00 with cost_source="computed", never "unknown" - resolve_cost()
        replaces the old _is_free_tier()-only convention."""

        state = self._make_state()
        events = await self._collect(state, _fake_stream_healthy)
        complete = events[-1]
        self.assertEqual(complete.cost_usd, 0.0)
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["cost_usd"], "0.0")
        self.assertEqual(rows[0]["cost_source"], "computed")

    async def test_auto_escalate_prefers_reported_cost_from_usage(self):
        """resolve_cost()'s "reported" path, exercised end to end through
        _run_escalation - previously the escalation sentinel always
        discarded usage, forcing this row to fall back to computed-or-
        unknown regardless of what OpenRouter actually reported."""

        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.50)
        events = await self._collect(state, _fake_stream_empty_reported_cost)
        complete = events[-1]
        self.assertTrue(complete.escalated)
        self.assertEqual(complete.cost_usd, 0.0042)
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["cost_usd"], "0.0042")
        self.assertEqual(rows[0]["cost_source"], "reported")

    async def test_escalation_pending_approved_prefers_reported_cost(self):
        """Same "reported" preference on the escalation_pending -> approved
        path (a distinct code path from auto_escalate in
        _run_order_body)."""

        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)

        async def approve(request_id):
            return "approved"

        events = await self._collect(state, _fake_stream_empty_reported_cost, wait_for_approval=approve)
        complete = events[-1]
        self.assertTrue(complete.escalated)
        self.assertEqual(complete.cost_usd, 0.0042)
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["cost_source"], "reported")

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

    # --- Brew 46: conversation memory (docs/design/conversation-memory-design.md) --

    async def test_remember_chat_false_sends_no_history(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        await self._collect(state, _fake_stream_healthy, session_id=session_id)  # turn 1

        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream, session_id=session_id, remember_chat=False)
        # remember_chat=False means no conversation history was sent - but
        # the date-awareness system message (system_prompt_include_date,
        # default on) still rides along regardless of remember_chat, since
        # that toggle governs conversation history, not knowledge of the
        # current date. Assert on the property that actually matters (no
        # user/assistant turns) rather than history_messages being None,
        # which was only ever a proxy for that.
        roles = [m["role"] for m in captured["history_messages"] or []]
        self.assertNotIn("user", roles)
        self.assertNotIn("assistant", roles)

    async def test_remember_chat_true_sends_prior_turn_as_history(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=True)

        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream, session_id=session_id, remember_chat=True)
        self.assertIsNotNone(captured["history_messages"])
        # [0] is the date-awareness system message (rides along on every
        # /v1/order request, not a conversation turn) - the actual prior
        # turn starts at [1].
        self.assertEqual(captured["history_messages"][0]["role"], "system")
        self.assertEqual(captured["history_messages"][1]["role"], "user")
        self.assertEqual(captured["history_messages"][1]["content"], "Implement a function.")
        self.assertEqual(captured["history_messages"][2]["role"], "assistant")

    async def test_first_message_in_session_has_no_history_and_does_not_break(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")

        events = await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=True)
        complete = events[-1]
        self.assertEqual(complete.history_turns, 0)
        self.assertEqual(complete.history_tokens_est, 0)

    async def test_complete_event_history_fields_none_when_remember_chat_false(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        events = await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=False)
        complete = events[-1]
        self.assertIsNone(complete.history_turns)
        self.assertIsNone(complete.history_tokens_est)

    async def test_errored_prior_turn_is_never_persisted_so_never_sent_as_history(self):
        """The router already never persists a failed turn (see
        _run_order_body's early-return-before-add_message on any
        ErrorEvent/CancelledEvent path) - confirms that holds end to end
        through history assembly, not just in isolation."""

        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")

        async def _erroring_stream(model_id, prompt, **_kwargs):
            raise OpenRouterClientError("boom")
            yield  # pragma: no cover - never reached, makes this a generator

        await self._collect(state, _erroring_stream, session_id=session_id, remember_chat=True)
        self.assertEqual(state.session_store.get_messages(session_id), [])

        # A second, healthy request in the same session sees zero history -
        # nothing was ever stored for the errored first attempt.
        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream, session_id=session_id, remember_chat=True)
        # No conversation history (the errored turn was never persisted) -
        # but the date system message still rides along. See
        # test_remember_chat_false_sends_no_history for why this asserts
        # on roles rather than None.
        roles = [m["role"] for m in captured["history_messages"] or []]
        self.assertNotIn("user", roles)
        self.assertNotIn("assistant", roles)

    async def test_history_max_messages_drops_oldest_whole_turns(self):
        state = self._make_state(with_session_store=True)
        state.settings.history_max_messages = 2  # 1 turn
        session_id = state.session_store.create_session("project-a")

        for _ in range(3):
            await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=True)

        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream, session_id=session_id, remember_chat=True)
        # 1 turn (2 messages) plus the leading date system message.
        self.assertEqual(len(captured["history_messages"]), 3)
        self.assertEqual(captured["history_messages"][0]["role"], "system")

    async def test_oversized_current_prompt_sends_with_no_history_and_logs_warning(self):
        state = self._make_state(with_session_store=True)
        state.settings.history_max_chars = 10  # trivially small
        session_id = state.session_store.create_session("project-a")
        await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=True)

        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        with self.assertLogs("router.app.history", level="WARNING"):
            await self._collect(state, _capturing_stream, session_id=session_id, remember_chat=True)
        # history_max_chars trimmed away all conversation history - but the
        # date system message still rides along. Same reasoning as
        # test_remember_chat_false_sends_no_history.
        roles = [m["role"] for m in captured["history_messages"] or []]
        self.assertNotIn("user", roles)
        self.assertNotIn("assistant", roles)

    async def test_ledger_row_records_remember_chat_and_history_fields(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=False)
        await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=True)

        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["remember_chat"], "False")
        self.assertEqual(rows[1]["remember_chat"], "True")
        self.assertEqual(rows[1]["history_turns"], "1")

    async def test_ledger_row_remember_chat_false_has_no_history_tokens(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=False)

        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["remember_chat"], "False")
        self.assertEqual(rows[0]["history_turns"], "0")
        self.assertEqual(rows[0]["history_tokens_est"], "unknown")

    # --- Date-awareness system prompt (see router/app/system_prompt.py) --

    async def test_date_system_message_present_and_correctly_dated_by_default(self):
        state = self._make_state()  # system_prompt_include_date defaults True
        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream)  # no session_id, remember_chat=False

        self.assertIsNotNone(captured["history_messages"])
        self.assertEqual(len(captured["history_messages"]), 1)
        system_message = captured["history_messages"][0]
        self.assertEqual(system_message["role"], "system")
        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        self.assertIn(f"Today's date is {today}", system_message["content"])
        self.assertIn("UTC", system_message["content"])
        self.assertIn("do not assume a date from your training data", system_message["content"])

    async def test_date_system_message_absent_when_setting_disabled(self):
        """Brew 56 note: this asserted `history_messages is None` when it
        was written, because the date was then the only thing that could
        be injected. The identity block is now a second, independently
        gated part, so "date off" no longer implies "nothing sent" - it
        implies "no date sentence". Both-off is covered by
        test_all_four_setting_combinations_send_at_most_one_system_message."""

        state = self._make_state()
        state.settings.system_prompt_include_date = False
        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream)

        for message in captured["history_messages"] or []:
            self.assertNotIn("Today's date is", message["content"])

    async def test_date_system_message_not_persisted_as_conversation_turn(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        await self._collect(state, _fake_stream_healthy, session_id=session_id)

        messages = state.session_store.get_messages(session_id)
        roles = [m.role for m in messages]
        self.assertNotIn("system", roles)
        for message in messages:
            self.assertNotIn("Today's date is", message.content)

    async def test_date_system_message_does_not_affect_history_window_counts(self):
        """The system message is prepended after history_result (turns_
        included/tokens_est) and total_input_chars (chars_included +
        len(outbound_text)) are already computed - so every count-facing
        field must be identical whether the setting is on or off. This
        also means the system message sits outside the history_max_chars
        budget by construction: it is never a trimming candidate and
        never counted against that budget."""

        state_on = self._make_state(with_session_store=True)
        session_on = state_on.session_store.create_session("project-a")
        await self._collect(state_on, _fake_stream_healthy, session_id=session_on, remember_chat=True)
        events_on = await self._collect(
            state_on, _fake_stream_healthy, session_id=session_on, remember_chat=True
        )
        complete_on = events_on[-1]
        rows_on = state_on.ledger.read_all_rows()

        state_off = self._make_state(with_session_store=True)
        state_off.settings.system_prompt_include_date = False
        session_off = state_off.session_store.create_session("project-a")
        await self._collect(state_off, _fake_stream_healthy, session_id=session_off, remember_chat=True)
        events_off = await self._collect(
            state_off, _fake_stream_healthy, session_id=session_off, remember_chat=True
        )
        complete_off = events_off[-1]
        rows_off = state_off.ledger.read_all_rows()

        self.assertEqual(complete_on.history_turns, complete_off.history_turns)
        self.assertEqual(complete_on.history_tokens_est, complete_off.history_tokens_est)
        self.assertEqual(rows_on[1]["message_count"], rows_off[1]["message_count"])
        self.assertEqual(rows_on[1]["total_input_chars"], rows_off[1]["total_input_chars"])
        self.assertEqual(rows_on[1]["history_tokens_est"], rows_off[1]["history_tokens_est"])

    def test_with_system_message_merges_into_existing_leading_system_message(self):
        """Dead code today (assemble_history()/pair_turns() in history.py
        can only ever produce user/assistant turns - no code path builds a
        history list starting with a system message) - exercised directly
        here so the merge behavior is real, not aspirational, in case that
        ever changes."""

        settings = Settings()
        history = [
            {"role": "system", "content": "Existing system instructions."},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        merged = _with_system_message(settings, history)

        self.assertEqual(len(merged), 3)  # merged into one, not appended as a fourth
        self.assertEqual(merged[0]["role"], "system")
        self.assertIn("Existing system instructions.", merged[0]["content"])
        self.assertIn("Today's date is", merged[0]["content"])
        self.assertEqual(merged[1], {"role": "user", "content": "hi"})
        self.assertEqual(merged[2], {"role": "assistant", "content": "hello"})
        # The input list itself must never be mutated - history_result.
        # messages (used for history_turns/message_count/etc.) has to stay
        # exactly what it was.
        self.assertEqual(history[0]["content"], "Existing system instructions.")

    def test_with_system_message_disabled_returns_input_unchanged(self):
        settings = Settings(
            system_prompt_include_date=False, system_prompt_include_identity=False
        )
        self.assertIsNone(_with_system_message(settings, None))
        history = [{"role": "user", "content": "hi"}]
        self.assertIs(_with_system_message(settings, history), history)

    # --- History trim reporting (Brew 57, contract v1.7) ----------------

    async def _complete_after_two_turns(self, state, session_id):
        """Runs one order to create a stored turn, then a second whose
        complete event reports whether that turn survived the window."""

        await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=True)
        events = await self._collect(
            state, _fake_stream_healthy, session_id=session_id, remember_chat=True
        )
        return events[-1]

    async def test_trim_fields_report_a_real_drop_on_complete(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        # A window far too small for the first turn to survive into the
        # second request.
        state.settings.history_max_chars = 40

        complete = await self._complete_after_two_turns(state, session_id)

        self.assertEqual(complete.history_turns, 0)
        self.assertEqual(complete.history_turns_dropped, 1)
        self.assertGreater(complete.history_chars_dropped, 0)
        self.assertIsNotNone(complete.history_drop_reason)

    async def test_trim_fields_are_zero_not_none_when_nothing_was_dropped(self):
        """The distinction the UI depends on: a real 0 means "the toggle
        is on and nothing was dropped", None means "not applicable"."""

        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")

        complete = await self._complete_after_two_turns(state, session_id)

        self.assertEqual(complete.history_turns, 1)
        self.assertEqual(complete.history_turns_dropped, 0)
        self.assertEqual(complete.history_chars_dropped, 0)
        self.assertIsNone(complete.history_drop_reason)

    async def test_trim_fields_are_none_when_remember_chat_is_off(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")

        await self._collect(
            state, _fake_stream_healthy, session_id=session_id, remember_chat=False
        )
        events = await self._collect(
            state, _fake_stream_healthy, session_id=session_id, remember_chat=False
        )
        complete = events[-1]

        self.assertIsNone(complete.history_turns)
        self.assertIsNone(complete.history_turns_dropped)
        self.assertIsNone(complete.history_chars_dropped)
        self.assertIsNone(complete.history_drop_reason)

    async def test_trim_fields_never_appear_on_any_generating_event(self):
        """Asserted over every yielded event, not just the last - a field
        added to the wrong event model must fail here."""

        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        state.settings.history_max_chars = 40

        await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=True)
        events = await self._collect(
            state, _fake_stream_healthy, session_id=session_id, remember_chat=True
        )

        trim_fields = {
            "history_turns_dropped",
            "history_chars_dropped",
            "history_drop_reason",
        }
        saw_generating = False
        for event in events:
            payload = event.model_dump()
            if payload.get("event") == "generating":
                saw_generating = True
            if payload.get("event") != "complete":
                self.assertEqual(
                    trim_fields & payload.keys(),
                    set(),
                    f"trim fields leaked onto a {payload.get('event')} event",
                )
        self.assertTrue(saw_generating, "fixture produced no generating event to check")

    async def test_trim_reporting_does_not_change_what_is_actually_sent(self):
        """Additive-only proof at the orchestration level: the history
        actually put in front of the Bean is unchanged by this Brew's
        reporting."""

        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _fake_stream_healthy, session_id=session_id, remember_chat=True)
        events = await self._collect(
            state, _capturing_stream, session_id=session_id, remember_chat=True
        )
        complete = events[-1]

        history_roles = [
            m["role"] for m in captured["history_messages"] if m.get("role") != "system"
        ]
        self.assertEqual(len(history_roles), complete.history_turns * 2)
        self.assertEqual(complete.history_turns_dropped, 0)

    # --- Identity block (Brew 56, see router/app/system_prompt.py) -------

    async def test_identity_block_present_by_default(self):
        state = self._make_state()  # system_prompt_include_identity defaults True
        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream)

        self.assertEqual(len(captured["history_messages"]), 1)
        content = captured["history_messages"][0]["content"]
        self.assertIn("Project Coffee", content)
        self.assertIn("Ishan Suthar", content)

    async def test_identity_block_absent_when_setting_disabled_but_date_survives(self):
        state = self._make_state()
        state.settings.system_prompt_include_identity = False
        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream)

        self.assertEqual(len(captured["history_messages"]), 1)
        content = captured["history_messages"][0]["content"]
        self.assertNotIn("Ishan Suthar", content)
        self.assertIn("Today's date is", content)

    async def test_all_four_setting_combinations_send_at_most_one_system_message(self):
        """The composition contract: identity and date are independently
        gated but must never produce two leading system messages, and with
        both off must produce none at all."""

        async def _capture(identity: bool, date: bool):
            state = self._make_state()
            state.settings.system_prompt_include_identity = identity
            state.settings.system_prompt_include_date = date
            captured = {}

            async def _capturing_stream(model_id, prompt, **kwargs):
                captured["history_messages"] = kwargs.get("history_messages")
                async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                    yield chunk

            await self._collect(state, _capturing_stream)
            return captured["history_messages"]

        for identity, date, expect_identity, expect_date in (
            (True, True, True, True),
            (True, False, True, False),
            (False, True, False, True),
            (False, False, False, False),
        ):
            with self.subTest(identity=identity, date=date):
                messages = await _capture(identity, date)

                if not identity and not date:
                    # Byte-identical to the pre-system-prompt behaviour:
                    # nothing is sent at all, not an empty system message.
                    self.assertIsNone(messages)
                    continue

                system_messages = [m for m in messages if m.get("role") == "system"]
                self.assertEqual(len(system_messages), 1)
                content = system_messages[0]["content"]
                self.assertEqual("Ishan Suthar" in content, expect_identity)
                self.assertEqual("Today's date is" in content, expect_date)

    def test_with_system_message_merges_identity_and_date_into_one_existing_system_message(self):
        """The three-way merge: identity + date + a caller's own leading
        system message all end up in ONE message, in that order, with the
        caller's content preserved intact and nothing duplicated."""

        settings = Settings(
            system_prompt_include_identity=True, system_prompt_include_date=True
        )
        history = [
            {"role": "system", "content": "Existing system instructions."},
            {"role": "user", "content": "hi"},
        ]
        merged = _with_system_message(settings, history)

        self.assertEqual(len(merged), 2)
        system_messages = [m for m in merged if m.get("role") == "system"]
        self.assertEqual(len(system_messages), 1)

        content = system_messages[0]["content"]
        self.assertEqual(content.count("Ishan Suthar"), 1)
        self.assertEqual(content.count("Today's date is"), 1)
        self.assertEqual(content.count("Existing system instructions."), 1)
        self.assertLess(content.index("Ishan Suthar"), content.index("Today's date is"))
        self.assertLess(
            content.index("Today's date is"), content.index("Existing system instructions.")
        )
        self.assertEqual(history[0]["content"], "Existing system instructions.")

    async def test_attachment_text_persisted_and_reattached_on_a_later_turn(self):
        state = self._make_state(with_session_store=True)
        session_id = state.session_store.create_session("project-a")
        attachment_id = self._register_upload(
            state,
            "req-pdf",
            "notes.pdf",
            "application/pdf",
            "pdf",
            extracted_text="The quarterly revenue was $4.2 million.",
        )
        await self._collect(
            state,
            _fake_stream_healthy,
            session_id=session_id,
            remember_chat=True,
            request_id="req-pdf",
            attachment_ids=[attachment_id],
        )

        message = state.session_store.get_messages(session_id)[0]
        self.assertTrue(message.has_attachments)
        self.assertIn("$4.2 million", message.attachments_json)

        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream, session_id=session_id, remember_chat=True)
        # [0] is the date system message - the reattached prior turn is [1].
        self.assertEqual(captured["history_messages"][0]["role"], "system")
        self.assertIn("$4.2 million", captured["history_messages"][1]["content"])
        self.assertIn("notes.pdf", captured["history_messages"][1]["content"])

    async def test_image_attachment_never_resent_on_a_later_turn(self):
        state = self._make_state(with_session_store=True, registry=_make_bean_registry_with_vision())
        session_id = state.session_store.create_session("project-a")
        attachment_id = self._register_upload(
            state, "req-img", "photo.png", "image/png", "image", file_bytes=b"\x89PNG fake bytes"
        )
        await self._collect(
            state,
            _fake_stream_healthy,
            session_id=session_id,
            remember_chat=True,
            request_id="req-img",
            attachment_ids=[attachment_id],
        )

        captured = {}

        async def _capturing_stream(model_id, prompt, **kwargs):
            captured["history_messages"] = kwargs.get("history_messages")
            captured["image_data_urls"] = kwargs.get("image_data_urls")
            async for chunk in _fake_stream_healthy(model_id, prompt, **kwargs):
                yield chunk

        await self._collect(state, _capturing_stream, session_id=session_id, remember_chat=True)
        self.assertIsNone(captured["image_data_urls"])  # no image resent on this later turn
        # [0] is the date system message - the reattached prior turn is [1].
        self.assertEqual(captured["history_messages"][0]["role"], "system")
        self.assertNotIn("base64", captured["history_messages"][1]["content"])
        self.assertIn(
            "not included in this conversation history", captured["history_messages"][1]["content"]
        )

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

    async def test_spend_cap_refusal_is_an_sse_error_event(self):
        """/v1/order's only error-surfacing mechanism has ever been an
        ErrorEvent on the stream - a spend-cap refusal follows the exact
        same shape, never a literal HTTP status (Decaf plan sign-off)."""

        state = self._make_state(with_session_store=True, per_user_daily_cost_cap_usd=0.10)
        state.ledger.append(
            LedgerRow(
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id="seed",
                task_type="code",
                bean_alias="House Blend",
                raw_model_id="vendor/default:free",
                tokens_in=10,
                tokens_out=10,
                cost_usd=0.10,
                latency_ms=100,
                escalated=False,
                escalation_approved=None,
                cost_source="computed",
                user_id=1,
            )
        )

        events = await self._collect(state, _fake_stream_healthy, user_id=1, bean_alias_override="Reserve Blend")

        event_names = [e.event for e in events]
        self.assertIn("error", event_names)
        self.assertNotIn("complete", event_names)
        error_event = next(e for e in events if e.event == "error")
        self.assertEqual(error_event.error_type, "spend_cap_exceeded")
        self.assertFalse(error_event.retryable)
        self.assertIn("midnight UTC", error_event.message)

    async def test_under_cap_request_streams_normally(self):
        state = self._make_state(with_session_store=True, per_user_daily_cost_cap_usd=100.0)
        events = await self._collect(state, _fake_stream_healthy, user_id=1)
        self.assertEqual(events[-1].event, "complete")

    async def test_rate_limit_refusal_is_an_sse_error_event(self):
        state = self._make_state(with_session_store=True, per_user_requests_per_minute=1)
        await self._collect(state, _fake_stream_healthy, user_id=1)  # consumes the only slot
        events = await self._collect(state, _fake_stream_healthy, user_id=1)
        error_event = next(e for e in events if e.event == "error")
        self.assertEqual(error_event.error_type, "rate_limit_exceeded")
        self.assertTrue(error_event.retryable)

    async def test_escalation_stage_cap_denial_falls_back_to_draft(self):
        """The already-generated draft is a valid, already-paid-for
        answer - a second-order cap hit on the escalation re-run must not
        discard it (Decaf plan sign-off)."""

        state = self._make_state(
            with_premium=True,
            with_session_store=True,
            escalation_cost_cap_usd=0.50,
            per_user_daily_cost_cap_usd=0.001,
        )
        events = await self._collect(state, _fake_stream_empty, user_id=1)
        event_names = [e.event for e in events]
        self.assertNotIn("escalating", event_names)
        self.assertNotIn("error", event_names)
        complete = events[-1]
        self.assertFalse(complete.escalated)
        self.assertTrue(complete.draft_quality)


class CheckSpendCapTests(unittest.IsolatedAsyncioTestCase):
    """Direct unit tests of check_spend_cap()/check_rate_limit() (spend-
    cap Brew) - the numeric boundary conditions are tested here rather
    than indirectly through routing/pricing, which is exercised
    separately below."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.ledger_path = Path(self._tmp_dir.name) / "router_requests.csv"
        self.ledger = RouterLedger(self.ledger_path)
        self.session_store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        registry = _make_bean_registry(with_premium=True)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        self.settings = Settings(per_user_daily_cost_cap_usd=1.00, global_daily_cost_cap_usd=5.00)
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=self.settings,
            ledger=self.ledger,
            session_store=self.session_store,
        )

    def _seed_spend(self, *, user_id, cost_usd, is_shadow=False):
        self.ledger.append(
            LedgerRow(
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id=str(uuid.uuid4()),
                task_type="code",
                bean_alias="House Blend",
                raw_model_id="vendor/default:free",
                tokens_in=10,
                tokens_out=10,
                cost_usd=cost_usd,
                latency_ms=100,
                escalated=False,
                escalation_approved=None,
                cost_source="computed",
                user_id=user_id,
                is_shadow=is_shadow,
            )
        )

    async def test_no_session_store_skips_enforcement(self):
        self.state.session_store = None
        denial = await check_spend_cap(self.state, 1, 999.0)
        self.assertIsNone(denial)

    async def test_no_user_id_skips_enforcement(self):
        """Distinct from the no-session_store case above - a real
        session_store but no user_id is what an internal-orchestration
        test fixture looks like, not a real unauthenticated request
        (impossible - Depends(get_current_user) guarantees a real user_id
        on every real endpoint)."""

        denial = await check_spend_cap(self.state, None, 999.0)
        self.assertIsNone(denial)

    async def test_estimate_aware_refusal_at_point_99_of_cap(self):
        """The scenario from the Decaf plan: at 0.99 of a 1.00 cap, a
        0.50 request must be refused before it starts, not allowed to
        land at 1.40."""

        self._seed_spend(user_id=1, cost_usd=0.99)
        denial = await check_spend_cap(self.state, 1, 0.50)
        self.assertIsNotNone(denial)
        self.assertEqual(denial.cap_type, "per_user")

    async def test_under_cap_request_allowed(self):
        self._seed_spend(user_id=1, cost_usd=0.10)
        denial = await check_spend_cap(self.state, 1, 0.50)
        self.assertIsNone(denial)

    async def test_exactly_at_cap_boundary_is_allowed_not_over(self):
        """today_spent + estimate == cap must be allowed - only strictly
        over the cap is refused."""

        self._seed_spend(user_id=1, cost_usd=0.50)
        denial = await check_spend_cap(self.state, 1, 0.50)
        self.assertIsNone(denial)

    async def test_global_cap_refuses_even_when_under_the_per_user_cap(self):
        self._seed_spend(user_id=1, cost_usd=0.10)
        self._seed_spend(user_id=2, cost_usd=4.85)
        denial = await check_spend_cap(self.state, 1, 0.10)
        self.assertIsNotNone(denial)
        self.assertEqual(denial.cap_type, "global")

    async def test_unknown_estimate_refuses_never_treated_as_free(self):
        denial = await check_spend_cap(self.state, 1, None)
        self.assertIsNotNone(denial)
        self.assertEqual(denial.cap_type, "unknown_estimate")

    async def test_no_prior_spend_today_does_not_divide_by_zero_or_refuse(self):
        denial = await check_spend_cap(self.state, 999, 0.10)
        self.assertIsNone(denial)

    async def test_per_user_override_column_takes_precedence_over_settings_default(self):
        user_id = self.session_store.create_user("alice", "hash", "Alice")
        self.session_store.set_user_daily_cost_cap("alice", 0.05)
        self._seed_spend(user_id=user_id, cost_usd=0.0)
        denial = await check_spend_cap(self.state, user_id, 0.10)
        self.assertIsNotNone(denial)
        self.assertEqual(denial.cap, 0.05)

    async def test_shadow_row_spend_counts_toward_the_triggering_users_cap(self):
        self._seed_spend(user_id=1, cost_usd=0.99, is_shadow=True)
        denial = await check_spend_cap(self.state, 1, 0.10)
        self.assertIsNotNone(denial)

    async def test_day_boundary_reset_old_spend_not_counted(self):
        self.ledger.append(
            LedgerRow(
                timestamp="2020-01-01T00:00:00+00:00",
                request_id="old-request",
                task_type="code",
                bean_alias="House Blend",
                raw_model_id="vendor/default:free",
                tokens_in=10,
                tokens_out=10,
                cost_usd=0.99,
                latency_ms=100,
                escalated=False,
                escalation_approved=None,
                cost_source="computed",
                user_id=1,
            )
        )
        denial = await check_spend_cap(self.state, 1, 0.50)
        self.assertIsNone(denial)

    async def test_rate_limit_allows_under_the_limit(self):
        self.settings.per_user_requests_per_minute = 3
        for _ in range(3):
            self.assertTrue(await check_rate_limit(self.state, 1))

    async def test_rate_limit_refuses_over_the_limit(self):
        self.settings.per_user_requests_per_minute = 3
        for _ in range(3):
            await check_rate_limit(self.state, 1)
        self.assertFalse(await check_rate_limit(self.state, 1))

    async def test_rate_limit_is_tracked_independently_per_user(self):
        self.settings.per_user_requests_per_minute = 1
        self.assertTrue(await check_rate_limit(self.state, 1))
        self.assertFalse(await check_rate_limit(self.state, 1))
        self.assertTrue(await check_rate_limit(self.state, 2))

    async def test_concurrent_requests_from_same_user_do_not_overshoot_the_cap(self):
        """The chosen concurrency behavior (Decaf plan): a per-user
        asyncio.Lock closes the race - two concurrent 0.60 requests
        against a 1.00 cap with 0.50 already spent must not both be
        admitted (0.50 + 0.60 + 0.60 = 1.70, well over cap)."""

        self._seed_spend(user_id=1, cost_usd=0.50)
        results = await asyncio.gather(
            check_spend_cap(self.state, 1, 0.60),
            check_spend_cap(self.state, 1, 0.60),
        )
        allowed_count = sum(1 for denial in results if denial is None)
        self.assertLessEqual(allowed_count, 1)


class UsageEndpointTests(unittest.IsolatedAsyncioTestCase):
    """GET /v1/usage (spend-cap Brew)."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)
        registry = _make_bean_registry(with_premium=True)
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        settings = Settings(per_user_daily_cost_cap_usd=1.00)
        self.ledger = RouterLedger(Path(self._tmp_dir.name) / "router_requests.csv")
        self.session_store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=self.ledger,
            session_store=self.session_store,
        )
        self.app = create_app(state=self.state)
        _override_auth(self.app)

    async def _get_usage(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/v1/usage")

    async def test_zero_spend_by_default(self):
        response = await self._get_usage()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["today_spend_usd"], 0.0)
        self.assertEqual(body["cap_usd"], 1.00)
        self.assertIn("reset_at", body)

    async def test_reflects_real_ledger_spend(self):
        self.ledger.append(
            LedgerRow(
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id="r1",
                task_type="code",
                bean_alias="House Blend",
                raw_model_id="vendor/default:free",
                tokens_in=10,
                tokens_out=10,
                cost_usd=0.34,
                latency_ms=100,
                escalated=False,
                escalation_approved=None,
                cost_source="computed",
                user_id=FAKE_USER.id,
            )
        )
        response = await self._get_usage()
        self.assertEqual(response.json()["today_spend_usd"], 0.34)

    async def test_reflects_per_user_cap_override(self):
        self.session_store.create_user(FAKE_USER.username, "hash", FAKE_USER.display_name)
        self.session_store.set_user_daily_cost_cap(FAKE_USER.username, 3.00)
        response = await self._get_usage()
        self.assertEqual(response.json()["cap_usd"], 3.00)


class DistinctWebSourcesTests(unittest.TestCase):
    """web search citations Brew - router.app.main._distinct_web_sources()."""

    def test_none_when_no_annotations(self):
        self.assertIsNone(_distinct_web_sources(None))
        self.assertIsNone(_distinct_web_sources([]))

    def test_extracts_url_and_title_only(self):
        annotations = [
            {
                "type": "url_citation",
                "url_citation": {
                    "url": "https://example.com/a",
                    "title": "Example A",
                    "start_index": 0,
                    "end_index": 10,
                    "content": "a long excerpt that must never reach the chip",
                },
            }
        ]
        sources = _distinct_web_sources(annotations)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].url, "https://example.com/a")
        self.assertEqual(sources[0].title, "Example A")

    def test_dedupes_by_url_keeping_first_title(self):
        annotations = [
            {"type": "url_citation", "url_citation": {"url": "https://example.com/a", "title": "First"}},
            {"type": "url_citation", "url_citation": {"url": "https://example.com/b", "title": "B"}},
            {"type": "url_citation", "url_citation": {"url": "https://example.com/a", "title": "Second"}},
        ]
        sources = _distinct_web_sources(annotations)
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].url, "https://example.com/a")
        self.assertEqual(sources[0].title, "First")
        self.assertEqual(sources[1].url, "https://example.com/b")

    def test_missing_title_falls_back_to_url(self):
        annotations = [{"type": "url_citation", "url_citation": {"url": "https://example.com/a"}}]
        sources = _distinct_web_sources(annotations)
        self.assertEqual(sources[0].title, "https://example.com/a")

    def test_annotation_missing_url_is_skipped(self):
        annotations = [{"type": "url_citation", "url_citation": {"title": "No URL"}}]
        self.assertIsNone(_distinct_web_sources(annotations))


class WebSearchOrderTests(RunOrderTestCase):
    """docs/design/web-search-design.md - /v1/order's use_web toggle end
    to end. Reuses RunOrderTestCase's setUp/_make_state/_collect - the
    fixture registry's Reserve Blend (premium) is tool_calling=True,
    House Blend (default) and Second Pour (fallback) are not."""

    async def test_use_web_routes_to_tool_calling_bean(self):
        state = self._make_state(with_premium=True)
        calls = []
        events = await self._collect(
            state, _make_capturing_stream_fn(calls), use_web=True
        )
        route_event = next(e for e in events if e.event == "route_selected")
        self.assertEqual(route_event.bean_alias, "Reserve Blend")
        self.assertIn("needs_tool_calling", route_event.constraint_reason)
        self.assertEqual(route_event.complexity, "cold_brew")

    async def test_use_web_false_stays_on_default_bean_espresso_shot(self):
        state = self._make_state(with_premium=True)
        calls = []
        events = await self._collect(state, _make_capturing_stream_fn(calls), use_web=False)
        route_event = next(e for e in events if e.event == "route_selected")
        self.assertEqual(route_event.bean_alias, "House Blend")
        self.assertEqual(route_event.complexity, "espresso_shot")

    async def test_use_web_sends_web_search_tool_with_configured_engine(self):
        """Web search cost optimization Brew: the deprecated
        plugins:[{"id":"web"}] mechanism is gone - a use_web request sends
        a single openrouter:web_search tool entry, engine taken from
        settings.web_search_engine (default "parallel" here, since
        _make_state's Settings(...) doesn't override it)."""

        state = self._make_state(with_premium=True)
        calls = []
        await self._collect(state, _make_capturing_stream_fn(calls), use_web=True)
        self.assertEqual(
            calls[0]["tools"],
            [{"type": "openrouter:web_search", "parameters": {"engine": "parallel"}}],
        )

    async def test_use_web_false_omits_web_search_tool(self):
        state = self._make_state(with_premium=True)
        calls = []
        await self._collect(state, _make_capturing_stream_fn(calls), use_web=False)
        self.assertIsNone(calls[0]["tools"])

    async def test_use_web_uses_configured_engine(self):
        state = self._make_state(with_premium=True, web_search_engine="exa")
        calls = []
        await self._collect(state, _make_capturing_stream_fn(calls), use_web=True)
        self.assertEqual(calls[0]["tools"][0]["parameters"]["engine"], "exa")

    async def test_use_web_no_capable_bean_anywhere_yields_error_event(self):
        """with_premium=False leaves no tool_calling=True Bean in the
        fixture registry at all - must be a clear error, never a silent
        drop of the web-search request."""

        state = self._make_state(with_premium=False)
        calls = []
        events = await self._collect(state, _make_capturing_stream_fn(calls), use_web=True)
        self.assertEqual(events[-1].event, "error")
        self.assertEqual(events[-1].error_type, "no_web_search_bean_available")
        self.assertEqual(calls, [])  # never reached OpenRouter

    async def test_use_web_ledger_web_search_cost_usd_populated_when_reported(self):
        state = self._make_state(with_premium=True)
        calls = []
        # 5 tokens_in (fixture prompt "Implement a function." -> tokens_in
        # = max(1, len//4)), 5 tokens_out; Reserve Blend pricing 0.003/0.015.
        await self._collect(
            state,
            _make_capturing_stream_fn_with_reported_cost(calls, cost_usd=0.01),
            use_web=True,
        )
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["cost_source"], "reported")
        self.assertNotEqual(rows[0]["web_search_cost_usd"], "")
        self.assertGreater(float(rows[0]["web_search_cost_usd"]), 0.0)

    async def test_use_web_ledger_web_search_cost_usd_blank_when_computed(self):
        """No reported usage.cost - nothing to isolate a search fee from,
        so this stays genuinely unknown, never fabricated."""

        state = self._make_state(with_premium=True)
        calls = []
        await self._collect(state, _make_capturing_stream_fn(calls), use_web=True)
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["cost_source"], "computed")
        self.assertEqual(rows[0]["web_search_cost_usd"], "")

    async def test_use_web_false_ledger_web_search_cost_usd_always_blank(self):
        state = self._make_state(with_premium=True)
        calls = []
        await self._collect(
            state,
            _make_capturing_stream_fn_with_reported_cost(calls, cost_usd=0.01),
            use_web=False,
        )
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["web_search_cost_usd"], "")

    async def test_use_web_carried_through_escalation_when_premium_tool_calling(self):
        """The fixture's premium Bean (Reserve Blend) IS tool_calling -
        use_web must be carried through the auto-escalation re-run."""

        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.50)
        calls = []
        events = await self._collect(
            state, _make_capturing_stream_fn_empty(calls), use_web=True
        )
        # Draft (needs_tool_calling already escalates House Blend to
        # Reserve Blend - the only capable Bean in this fixture) then the
        # failure-triggered escalation re-run: both real calls carried the
        # web_search tool.
        self.assertEqual(len(calls), 2)
        self.assertTrue(
            all(c["tools"] == [{"type": "openrouter:web_search", "parameters": {"engine": "parallel"}}] for c in calls)
        )
        complete = events[-1]
        self.assertEqual(complete.bean_alias, "Reserve Blend")
        self.assertTrue(complete.escalated)

    async def test_use_web_dropped_on_escalation_when_premium_not_tool_calling(self):
        """Correction 2 (escalation carry-through): when the premium Bean
        can't call tools, drop use_web for that re-run with a logged
        warning rather than hard-failing - the escalation must still
        succeed, just without search."""

        registry = BeanRegistry(
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
                    alias="Web Capable",
                    role="fallback",
                    model_id="vendor/web-capable",
                    vision=False,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.0,
                    price_per_1k_output_usd=0.0,
                    status="active",
                ),
                Bean(
                    alias="Reserve Blend",
                    role="premium",
                    model_id="vendor/premium",
                    vision=False,
                    code=True,
                    tool_calling=False,
                    price_per_1k_input_usd=0.003,
                    price_per_1k_output_usd=0.015,
                    status="active",
                ),
            ]
        )
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.50, registry=registry)
        calls = []
        with self.assertLogs("router.app.main", level="WARNING") as log_ctx:
            events = await self._collect(
                state, _make_capturing_stream_fn_empty(calls), use_web=True
            )
        self.assertTrue(any("use_web dropped for escalation" in msg for msg in log_ctx.output))
        # Draft call (Web Capable, tool_calling) carried the web_search
        # tool; escalation call (Reserve Blend, not tool_calling) did not.
        self.assertEqual(
            calls[0]["tools"], [{"type": "openrouter:web_search", "parameters": {"engine": "parallel"}}]
        )
        self.assertIsNone(calls[1]["tools"])
        complete = events[-1]
        self.assertEqual(complete.bean_alias, "Reserve Blend")
        rows = state.ledger.read_all_rows()
        self.assertEqual(rows[0]["web_search_cost_usd"], "")

    def _make_registry_with_kimi_and_deepseek(self):
        """Mirrors the real beans.yaml pricing (web search cost
        optimization Brew): DeepSeek V3.2 is genuinely cheaper than Kimi
        K2 combined (0.000669 vs 0.00287 per 1k) - proves the preference
        override, not price, decides the winner."""

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
                    alias="Kimi K2",
                    role="web_search_primary",
                    model_id="moonshotai/kimi-k2",
                    vision=False,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.00057,
                    price_per_1k_output_usd=0.0023,
                    status="active",
                ),
                Bean(
                    alias="DeepSeek V3.2",
                    role="web_search_fallback",
                    model_id="deepseek/deepseek-v3.2",
                    vision=False,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.000269,
                    price_per_1k_output_usd=0.0004,
                    status="active",
                ),
            ]
        )

    async def test_use_web_routes_to_kimi_over_cheaper_deepseek(self):
        """The explicit ask this Brew exists for: DeepSeek V3.2 is ~4.3x
        cheaper combined, but preferred_web_search_bean_alias="Kimi K2"
        (Settings' real default, matching _make_state's default) must win
        outright over plain cheapest-price selection."""

        registry = self._make_registry_with_kimi_and_deepseek()
        state = self._make_state(with_premium=True, registry=registry)
        calls = []
        events = await self._collect(state, _make_capturing_stream_fn(calls), use_web=True)
        route_event = next(e for e in events if e.event == "route_selected")
        self.assertEqual(route_event.bean_alias, "Kimi K2")
        complete = events[-1]
        self.assertEqual(complete.bean_alias, "Kimi K2")

    async def test_use_web_falls_back_to_cheapest_when_preferred_bean_unavailable(self):
        """DeepSeek V3.2 is a genuine fallback, not decorative: remove
        Kimi K2 from the pool and capable_bean() must fall through to
        plain cheapest-price selection, landing on DeepSeek V3.2 (the only
        remaining capable Bean here)."""

        registry = BeanRegistry(
            [
                bean
                for bean in self._make_registry_with_kimi_and_deepseek().all_beans()
                if bean.alias != "Kimi K2"
            ]
        )
        state = self._make_state(with_premium=True, registry=registry)
        calls = []
        events = await self._collect(state, _make_capturing_stream_fn(calls), use_web=True)
        route_event = next(e for e in events if e.event == "route_selected")
        self.assertEqual(route_event.bean_alias, "DeepSeek V3.2")

    async def test_use_web_annotations_reach_complete_event_web_sources(self):
        """The core fix this Brew exists for: a real citation, previously
        silently dropped, now reaches CompleteEvent.web_sources."""

        state = self._make_state(with_premium=True)
        events = await self._collect(state, _make_stream_fn_with_annotations(), use_web=True)
        complete = events[-1]
        self.assertEqual(complete.event, "complete")
        self.assertIsNotNone(complete.web_sources)
        self.assertEqual(len(complete.web_sources), 1)
        self.assertEqual(complete.web_sources[0].url, "https://example.com/equities")
        self.assertEqual(complete.web_sources[0].title, "Top Equities This Week")

    async def test_no_annotations_leaves_web_sources_none(self):
        state = self._make_state(with_premium=True)
        events = await self._collect(state, _make_capturing_stream_fn([]), use_web=True)
        complete = events[-1]
        self.assertIsNone(complete.web_sources)

    async def test_annotations_arriving_despite_use_web_false_still_surfaced(self):
        """Edge case: annotations present but use_web was off should never
        happen in practice (no web_search_tools sent means OpenRouter has
        no reason to cite anything), but handle it gracefully rather than
        crashing - if they somehow arrive, they're real citation data and
        are surfaced faithfully, same as Coffee never second-guessing any
        other model output."""

        state = self._make_state(with_premium=True)
        events = await self._collect(state, _make_stream_fn_with_annotations(), use_web=False)
        complete = events[-1]
        self.assertIsNotNone(complete.web_sources)

    async def test_web_sources_never_appears_on_generating_event(self):
        state = self._make_state(with_premium=True)
        events = await self._collect(state, _make_stream_fn_with_annotations(), use_web=True)
        generating_events = [e for e in events if e.event == "generating"]
        self.assertTrue(generating_events)
        for event in generating_events:
            self.assertFalse(hasattr(event, "web_sources"))

    async def test_annotations_deduped_and_missing_title_falls_back_to_url(self):
        async def _fake(model_id, prompt, **kwargs):
            yield StreamChunk(
                content_delta="",
                annotations=[
                    _REALISTIC_ANNOTATION,
                    _REALISTIC_ANNOTATION,  # same URL cited twice
                    {"type": "url_citation", "url_citation": {"url": "https://example.com/no-title"}},
                ],
            )
            yield StreamChunk(content_delta="Summary.")
            yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 5})
            yield StreamChunk(is_final=True)

        state = self._make_state(with_premium=True)
        events = await self._collect(state, _fake, use_web=True)
        complete = events[-1]
        self.assertEqual(len(complete.web_sources), 2)
        self.assertEqual(complete.web_sources[1].url, "https://example.com/no-title")
        self.assertEqual(complete.web_sources[1].title, "https://example.com/no-title")

    async def test_annotations_on_escalation_rerun_reach_complete_event(self):
        """The draft's own empty response triggers auto_escalate; the
        premium re-run (also tool_calling, per the fixture) is the one
        that actually cites a source - web_sources must reflect the
        escalation's citations, not the draft's (which had none)."""

        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.50)
        call_count = 0

        async def _fake(model_id, prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Draft: empty, triggers auto_escalate, no annotations.
                yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 0})
                yield StreamChunk(is_final=True)
            else:
                yield StreamChunk(content_delta="", annotations=[_REALISTIC_ANNOTATION])
                yield StreamChunk(content_delta="Alphabet led this week.")
                yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 10})
                yield StreamChunk(is_final=True)

        events = await self._collect(state, _fake, use_web=True)
        complete = events[-1]
        self.assertTrue(complete.escalated)
        self.assertIsNotNone(complete.web_sources)
        self.assertEqual(complete.web_sources[0].url, "https://example.com/equities")


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
        # Generous spend-cap defaults - this class uses a real session_store
        # and the real /v1/order endpoint (a real user_id), and some tests
        # here resolve a real escalation to the premium Bean; the real
        # settings.yaml defaults would incidentally trip the new cap on
        # tests that aren't about it at all.
        settings = Settings(
            generating_tick_tokens=5,
            generating_tick_seconds=999,
            per_user_daily_cost_cap_usd=100.0,
            global_daily_cost_cap_usd=1000.0,
            per_user_requests_per_minute=1000,
        )
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
        _override_auth(self.app)

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
        session_id = self.state.session_store.create_session("project-a", user_id=FAKE_USER.id)

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

    async def test_cors_rejects_lan_origin_when_env_var_unset(self):
        """Default behavior (CORS_ALLOWED_ORIGINS unset) must stay exactly
        what it was before LAN support existed - a LAN IP origin gets no
        access-control-allow-origin header back."""

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/beans", headers={"Origin": "http://192.168.1.42:3000"})
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    async def test_cors_allows_lan_origin_when_configured_via_env_var(self):
        """CORS_ALLOWED_ORIGINS (comma-separated) lets a LAN device's
        origin through once the operator opts in explicitly."""

        with mock.patch.dict(
            os.environ,
            {"CORS_ALLOWED_ORIGINS": "http://localhost:3000,http://192.168.1.42:3000"},
        ):
            app = create_app(state=self.state)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/beans", headers={"Origin": "http://192.168.1.42:3000"})
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://192.168.1.42:3000")

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


class CorsAllowedOriginsTests(unittest.TestCase):
    """_cors_allowed_origins() (LAN access support) - unit-level coverage
    of the CORS_ALLOWED_ORIGINS parsing, independent of the HTTP-level
    CORS behavior covered in FastApiSmokeTests."""

    def test_defaults_to_localhost_3000_when_unset(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CORS_ALLOWED_ORIGINS", None)
            self.assertEqual(_cors_allowed_origins(), DEFAULT_CORS_ALLOWED_ORIGINS)

    def test_parses_comma_separated_list(self):
        with mock.patch.dict(
            os.environ, {"CORS_ALLOWED_ORIGINS": "http://localhost:3000,http://192.168.1.42:3000"}
        ):
            self.assertEqual(
                _cors_allowed_origins(),
                ["http://localhost:3000", "http://192.168.1.42:3000"],
            )

    def test_strips_whitespace_around_each_origin(self):
        with mock.patch.dict(
            os.environ, {"CORS_ALLOWED_ORIGINS": " http://localhost:3000 , http://192.168.1.42:3000 "}
        ):
            self.assertEqual(
                _cors_allowed_origins(),
                ["http://localhost:3000", "http://192.168.1.42:3000"],
            )

    def test_blank_env_var_falls_back_to_default(self):
        with mock.patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "   "}):
            self.assertEqual(_cors_allowed_origins(), DEFAULT_CORS_ALLOWED_ORIGINS)


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
        self.session_id = session_store.create_session("default", user_id=FAKE_USER.id)
        session_store.add_message(
            self.session_id, request_id="r1", role="user", content="Implement the widget."
        )
        session_store.add_message(
            self.session_id, request_id="r1", role="assistant", content="Done, widget implemented."
        )
        self.app = create_app(state=self.state)
        _override_auth(self.app)

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
        _override_auth(self.app)

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


class ProjectEndpointTests(unittest.IsolatedAsyncioTestCase):
    """Brew 43 (docs/design/auth-projects-chat-management-design.md
    Section 4): project CRUD endpoints. Uses the single-fixed-FAKE_USER
    override (Section 3.1, Gap 3) - cross-user isolation for projects is
    covered separately in test_auth.py with two real logins, since that
    is what the override pattern is deliberately not designed to
    exercise."""

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
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            session_store=session_store,
            uploads_root=Path(self._tmp_dir.name) / "uploads",
        )
        self.app = create_app(state=self.state)
        _override_auth(self.app)

    async def test_create_and_list_projects(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post("/v1/projects", json={"name": "Recipes"})
            self.assertEqual(create_response.status_code, 200)
            project_id = create_response.json()["id"]

            list_response = await client.get("/v1/projects")
        projects = list_response.json()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["id"], project_id)
        self.assertEqual(projects[0]["name"], "Recipes")

    async def test_rename_project(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post("/v1/projects", json={"name": "Old name"})
            project_id = create_response.json()["id"]

            rename_response = await client.patch(f"/v1/projects/{project_id}", json={"name": "New name"})
            self.assertEqual(rename_response.status_code, 200)

            list_response = await client.get("/v1/projects")
        self.assertEqual(list_response.json()[0]["name"], "New name")

    async def test_rename_unknown_project_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch("/v1/projects/999999", json={"name": "New name"})
        self.assertEqual(response.status_code, 404)

    async def test_delete_project_moves_sessions_to_default(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            project_id = (await client.post("/v1/projects", json={"name": "Temp"})).json()["id"]
            session_id = (
                await client.post("/v1/sessions", json={"project_id": project_id})
            ).json()["id"]

            delete_response = await client.delete(f"/v1/projects/{project_id}")
            self.assertEqual(delete_response.status_code, 200)

            default_sessions = await client.get("/v1/sessions")
            all_sessions = await client.get("/v1/sessions", params={"project_id": "all"})

        # Session was moved to default (project_id null), not deleted.
        self.assertIn(session_id, {s["id"] for s in default_sessions.json()})
        self.assertIn(session_id, {s["id"] for s in all_sessions.json()})

    async def test_delete_unknown_project_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/v1/projects/999999")
        self.assertEqual(response.status_code, 404)

    async def test_create_session_with_unknown_project_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/sessions", json={"project_id": 999999})
        self.assertEqual(response.status_code, 404)

    async def test_list_sessions_filtered_by_project_id(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            project_id = (await client.post("/v1/projects", json={"name": "A project"})).json()["id"]
            project_session = (
                await client.post("/v1/sessions", json={"project_id": project_id})
            ).json()["id"]
            default_session = (await client.post("/v1/sessions", json={})).json()["id"]

            project_list = await client.get("/v1/sessions", params={"project_id": str(project_id)})
            default_list = await client.get("/v1/sessions")
            all_list = await client.get("/v1/sessions", params={"project_id": "all"})

        self.assertEqual({s["id"] for s in project_list.json()}, {project_session})
        self.assertEqual({s["id"] for s in default_list.json()}, {default_session})
        self.assertEqual({s["id"] for s in all_list.json()}, {project_session, default_session})


class ChatManagementEndpointTests(unittest.IsolatedAsyncioTestCase):
    """Brew 43 (docs/design/auth-projects-chat-management-design.md
    Section 5): PATCH/DELETE /v1/sessions/{id}."""

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
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            session_store=session_store,
            uploads_root=Path(self._tmp_dir.name) / "uploads",
        )
        self.app = create_app(state=self.state)
        _override_auth(self.app)

    async def test_rename_session(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = (await client.post("/v1/sessions", json={})).json()["id"]

            rename_response = await client.patch(
                f"/v1/sessions/{session_id}", json={"title": "Renamed chat"}
            )
            self.assertEqual(rename_response.status_code, 200)

            list_response = await client.get("/v1/sessions")
        self.assertEqual(list_response.json()[0]["title"], "Renamed chat")

    async def test_rename_unknown_session_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch("/v1/sessions/nonexistent-id", json={"title": "x"})
        self.assertEqual(response.status_code, 404)

    async def test_new_session_defaults_remember_chat_true(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = (await client.post("/v1/sessions", json={})).json()
            self.assertTrue(created["remember_chat"])
            listed = (await client.get("/v1/sessions")).json()
        self.assertTrue(listed[0]["remember_chat"])

    async def test_patch_remember_chat_flips_it(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = (await client.post("/v1/sessions", json={})).json()["id"]

            response = await client.patch(f"/v1/sessions/{session_id}", json={"remember_chat": False})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["remember_chat"], False)

            listed = (await client.get("/v1/sessions")).json()
        self.assertFalse(listed[0]["remember_chat"])

    async def test_patch_can_set_title_and_remember_chat_together(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = (await client.post("/v1/sessions", json={})).json()["id"]
            response = await client.patch(
                f"/v1/sessions/{session_id}", json={"title": "Renamed", "remember_chat": False}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Renamed")
        self.assertEqual(response.json()["remember_chat"], False)

    async def test_patch_with_neither_field_is_422(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = (await client.post("/v1/sessions", json={})).json()["id"]
            response = await client.patch(f"/v1/sessions/{session_id}", json={})
        self.assertEqual(response.status_code, 422)

    async def test_patch_remember_chat_unknown_session_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch("/v1/sessions/nonexistent-id", json={"remember_chat": False})
        self.assertEqual(response.status_code, 404)

    async def test_messages_endpoint_reports_has_attachments(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = (await client.post("/v1/sessions", json={})).json()["id"]
        self.state.session_store.add_message(
            session_id,
            request_id="r1",
            role="user",
            content="hi",
            attachments_json='[{"filename": "a.pdf"}]',
        )
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            messages = (await client.get(f"/v1/sessions/{session_id}/messages")).json()
        self.assertTrue(messages[0]["has_attachments"])

    async def test_delete_session_excludes_from_list(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = (await client.post("/v1/sessions", json={})).json()["id"]

            delete_response = await client.delete(f"/v1/sessions/{session_id}")
            self.assertEqual(delete_response.status_code, 200)

            list_response = await client.get("/v1/sessions")
            messages_response = await client.get(f"/v1/sessions/{session_id}/messages")

        self.assertEqual(list_response.json(), [])
        # Soft delete - the endpoint still 404s (excluded from queries),
        # but the underlying row/messages are never physically removed
        # (verified directly against SessionStore in test_sessions.py).
        self.assertEqual(messages_response.status_code, 404)

    async def test_delete_unknown_session_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/v1/sessions/nonexistent-id")
        self.assertEqual(response.status_code, 404)


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
        _override_auth(self.app)

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


async def _fake_openai_stream_healthy(model_id, prompt="", **kwargs):
    # completion_tokens must clear RunOrderTestCase-style fixtures'
    # truncation_min_expected_tokens=10 - otherwise check_for_failure()
    # flags this as truncated and triggers an unwanted auto-escalation
    # re-run, same as _fake_stream_healthy's own "world " * 20 padding.
    for word in ["Hello ", "world"]:
        yield StreamChunk(content_delta=word)
    yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 50})
    yield StreamChunk(is_final=True)


async def _fake_openai_stream_with_tool_call(model_id, prompt="", **kwargs):
    yield StreamChunk(
        tool_calls_delta=[
            {"index": 0, "id": "call_1", "type": "function", "function": {"name": "get_weather", "arguments": ""}}
        ]
    )
    yield StreamChunk(
        tool_calls_delta=[{"index": 0, "function": {"arguments": '{"city": "NYC"}'}}]
    )
    yield StreamChunk(finish_reason="tool_calls", usage={"completion_tokens": 50})
    yield StreamChunk(is_final=True)


async def _fake_openai_stream_empty(model_id, prompt="", **kwargs):
    """No content, no failure keywords - triggers check_for_failure's
    "empty" path, same fixture role as _fake_stream_empty for /v1/order."""

    yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 0})
    yield StreamChunk(is_final=True)


async def _fake_openai_stream_reported_cost(model_id, prompt="", **kwargs):
    """Same shape as _fake_openai_stream_healthy, but the finish chunk
    carries a real OpenRouter usage.cost - used to test resolve_cost()'s
    "reported" preference through _run_chat_completion."""

    for word in ["Hello ", "world"]:
        yield StreamChunk(content_delta=word)
    yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 50, "cost": 0.0091})
    yield StreamChunk(is_final=True)


async def _fake_openai_stream_by_model(model_id, prompt="", **kwargs):
    """Draft (House Blend, vendor/default:free) is truncated/empty enough
    to trigger auto_escalate; premium (Reserve Blend, vendor/premium)
    returns distinct content and a distinct completion_tokens count, so
    tests can assert the client/Ledger reflect the premium call's own
    output rather than the discarded draft's - this is what the live
    "Hello there youHello there, friend!" concatenation bug looked like
    before the fix (docs/design/openai-compat-endpoint-design.md)."""

    if model_id == "vendor/premium":
        for word in ["Hello there, ", "friend!"]:
            yield StreamChunk(content_delta=word)
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 99})
        yield StreamChunk(is_final=True)
    else:
        for word in ["Hello ", "there ", "you"]:
            yield StreamChunk(content_delta=word)
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 1})
        yield StreamChunk(is_final=True)


class ChatCompletionsEndpointTests(unittest.IsolatedAsyncioTestCase):
    """POST /v1/chat/completions (Brew 47, docs/design/
    openai-compat-endpoint-design.md Section 1). Deliberately mirrors
    FastApiSmokeTests' create_app()/_override_auth() pattern rather than
    calling _run_chat_completion() directly, since the shape of what a
    client actually receives (SSE frames vs. a single JSON body) is the
    thing under test."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)
        self.policy_path = policy_path
        self.ledger_path = Path(self._tmp_dir.name) / "router_requests.csv"

    def _make_app(
        self,
        stream_fn=_fake_openai_stream_healthy,
        with_premium=True,
        escalation_cost_cap_usd=0.50,
        with_session_store=False,
        **settings_overrides,
    ):
        registry = _make_bean_registry(with_premium=with_premium)
        policy = RoutingPolicy.from_yaml(self.policy_path, bean_registry=registry)
        # Generous spend-cap defaults (unlike the real settings.yaml
        # defaults) so tests not specifically about the spend-cap Brew
        # never trip it incidentally - the real endpoint always threads a
        # real user_id through, unlike RunOrderTestCase's direct
        # _run_order_body() calls, so this matters here even for tests
        # that never mention caps at all. Tests exercising enforcement
        # override via **settings_overrides, same as any other setting.
        settings_kwargs = {
            "escalation_cost_cap_usd": escalation_cost_cap_usd,
            "generating_tick_tokens": 5,
            "generating_tick_seconds": 999,
            "truncation_min_expected_tokens": 10,
            "refusal_keywords": ["i cannot help"],
            "per_user_daily_cost_cap_usd": 100.0,
            "global_daily_cost_cap_usd": 1000.0,
            "per_user_requests_per_minute": 1000,
        }
        settings_kwargs.update(settings_overrides)
        settings = Settings(**settings_kwargs)
        ledger = RouterLedger(self.ledger_path)
        session_store = (
            SessionStore(Path(self._tmp_dir.name) / "sessions.db") if with_session_store else None
        )
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            stream_order_fn=stream_fn,
            uploads_root=Path(self._tmp_dir.name) / "uploads",
            session_store=session_store,
        )
        app = create_app(state=self.state)
        _override_auth(app)
        return app

    async def _post(self, app, body, headers=None):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/v1/chat/completions", json=body, headers=headers or {})

    async def _stream_chunks(self, app, body, headers=None):
        transport = httpx.ASGITransport(app=app)
        chunks = []
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST", "/v1/chat/completions", json=body, headers=headers or {}
            ) as response:
                status = response.status_code
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[len("data: "):]
                    if raw == "[DONE]":
                        continue
                    chunks.append(json.loads(raw))
        return status, chunks

    async def test_auth_rejected_without_bearer_token(self):
        app = self._make_app()
        app.dependency_overrides.clear()  # undo _override_auth for this one test
        response = await self._post(app, {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(response.status_code, 401)

    async def test_stream_true_yields_sse_chunks_ending_in_done(self):
        app = self._make_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
            ) as response:
                self.assertEqual(response.status_code, 200)
                raw_lines = [line async for line in response.aiter_lines() if line.startswith("data: ")]
        self.assertEqual(raw_lines[-1], "data: [DONE]")
        content = "".join(
            json.loads(line[len("data: "):]).get("choices", [{}])[0].get("delta", {}).get("content", "")
            for line in raw_lines[:-1]
        )
        self.assertEqual(content, "Hello world")

    async def test_stream_false_returns_single_json_body(self):
        app = self._make_app()
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["object"], "chat.completion")
        self.assertEqual(body["choices"][0]["message"]["content"], "Hello world")
        self.assertEqual(body["choices"][0]["message"]["role"], "assistant")

    async def test_stream_true_and_false_accumulate_identical_content(self):
        """Section 1: the two modes must produce byte-identical
        accumulated content - only the flush-per-chunk-vs-buffer edge
        differs, never the underlying generation."""

        app = self._make_app()
        _, chunks = await self._stream_chunks(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": True}
        )
        streamed_content = "".join(
            c.get("choices", [{}])[0].get("delta", {}).get("content", "") for c in chunks
        )

        app2 = self._make_app()
        response = await self._post(
            app2, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        buffered_content = response.json()["choices"][0]["message"]["content"]

        self.assertEqual(streamed_content, buffered_content)

    async def test_usage_and_model_present_on_final_chunk(self):
        app = self._make_app()
        _, chunks = await self._stream_chunks(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": True}
        )
        final = chunks[-1]
        self.assertIn("usage", final)
        self.assertGreater(final["usage"]["completion_tokens"], 0)
        self.assertEqual(final["choices"][0]["finish_reason"], "stop")

    async def test_model_field_is_always_a_bean_alias_never_a_raw_model_id(self):
        """docs/design/openai-compat-endpoint-design.md Section 1: the
        raw model ID (`vendor/default:free`) must never leave the router
        in an API-visible field, same invariant router/app/aliases.py
        enforces everywhere else."""

        app = self._make_app()
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        self.assertEqual(response.json()["model"], "House Blend")
        self.assertNotIn("vendor/default:free", json.dumps(response.json()))

    async def test_client_model_field_ignored_for_routing_when_not_a_bean_alias(self):
        app = self._make_app()
        response = await self._post(
            app,
            {
                "messages": [{"role": "user", "content": "hi"}],
                "model": "gpt-4o",
                "stream": False,
            },
        )
        self.assertEqual(response.json()["model"], "House Blend")
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["requested_model"], "gpt-4o")
        self.assertEqual(rows[0]["bean_alias"], "House Blend")

    async def test_client_model_field_as_exact_bean_alias_is_a_manual_override(self):
        app = self._make_app()
        response = await self._post(
            app,
            {
                "messages": [{"role": "user", "content": "hi"}],
                "model": "Second Pour",
                "stream": False,
            },
        )
        self.assertEqual(response.json()["model"], "Second Pour")

    async def test_no_model_field_at_all_routes_normally(self):
        """Edge case (Section 6): model absent entirely, not just empty."""

        app = self._make_app()
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        self.assertEqual(response.status_code, 200)
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["requested_model"], "")

    async def test_client_source_is_user_agent_when_present(self):
        app = self._make_app()
        await self._post(
            app,
            {"messages": [{"role": "user", "content": "hi"}], "stream": False},
            headers={"User-Agent": "Cursor/1.2.3"},
        )
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["client_source"], "Cursor/1.2.3")

    async def test_client_source_falls_back_to_openai_api_when_user_agent_absent(self):
        # httpx.AsyncClient always sends its own default User-Agent unless
        # overridden - simulate a genuinely absent/empty header explicitly.
        app = self._make_app()
        await self._post(
            app,
            {"messages": [{"role": "user", "content": "hi"}], "stream": False},
            headers={"User-Agent": ""},
        )
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["client_source"], "openai_api")

    async def test_free_tier_bean_writes_real_zero_cost_computed_source(self):
        """Cost-inconsistency fix: replaces the old _is_free_tier()-only
        convention (which wrote cost_usd=None for the "free" branch's
        sibling every paid Bean fell into) - House Blend's real $0.00
        must be cost_source="computed", never "unknown"."""

        app = self._make_app()
        await self._post(app, {"messages": [{"role": "user", "content": "hi"}], "stream": False})
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["cost_usd"], "0.0")
        self.assertEqual(rows[0]["cost_source"], "computed")

    async def test_prefers_reported_cost_from_usage(self):
        """Previously this row's cost_usd was always None (any paid Bean
        fell through _is_free_tier()'s else branch) - resolve_cost() now
        prefers OpenRouter's own usage.cost when present."""

        app = self._make_app(stream_fn=_fake_openai_stream_reported_cost)
        await self._post(app, {"messages": [{"role": "user", "content": "hi"}], "stream": False})
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["cost_usd"], "0.0091")
        self.assertEqual(rows[0]["cost_source"], "reported")

    async def test_escalation_prefers_reported_cost_from_premium_call(self):
        """The escalated (premium) call's own usage.cost must win, not the
        discarded draft's - mirrors the "Hello there youHello there,
        friend!" concatenation-bug precedent this endpoint already guards
        against, applied to cost instead of content."""

        async def stream_by_model(model_id, prompt="", **kwargs):
            if model_id == "vendor/premium":
                yield StreamChunk(content_delta="Hello there, friend!")
                yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 99, "cost": 0.077})
                yield StreamChunk(is_final=True)
            else:
                yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 0})
                yield StreamChunk(is_final=True)

        app = self._make_app(stream_fn=stream_by_model)
        response = await self._post(app, {"messages": [{"role": "user", "content": "hi"}], "stream": False})
        self.assertEqual(response.json()["model"], "Reserve Blend")
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["cost_usd"], "0.077")
        self.assertEqual(rows[0]["cost_source"], "reported")

    async def test_tools_passthrough_round_trip(self):
        """Coffee never interprets tools/tool_calls - full round-trip
        fidelity, both directions."""

        app = self._make_app(stream_fn=_fake_openai_stream_with_tool_call)
        tools = [{"type": "function", "function": {"name": "get_weather", "parameters": {}}}]
        response = await self._post(
            app,
            {
                "messages": [{"role": "user", "content": "weather in NYC?"}],
                "tools": tools,
                "tool_choice": "auto",
                "stream": False,
            },
        )
        body = response.json()
        tool_calls = body["choices"][0]["message"]["tool_calls"]
        self.assertEqual(tool_calls[0]["id"], "call_1")
        self.assertEqual(tool_calls[0]["function"]["name"], "get_weather")
        self.assertEqual(tool_calls[0]["function"]["arguments"], '{"city": "NYC"}')
        self.assertEqual(body["choices"][0]["finish_reason"], "tool_calls")

    async def test_tool_calls_only_response_never_triggers_escalation(self):
        """Regression: check_for_failure() predates tool calling and
        treats any empty `text` as failed/"empty" - a tool_calls-only
        turn (no prose) is a well-formed success, not a failure, and must
        not auto-escalate or double the tool_calls via a rerun."""

        app = self._make_app(stream_fn=_fake_openai_stream_with_tool_call, escalation_cost_cap_usd=0.50)
        response = await self._post(
            app,
            {"messages": [{"role": "user", "content": "weather?"}], "stream": False},
        )
        self.assertEqual(response.json()["model"], "House Blend")  # not escalated
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalated"], "False")

    async def test_tools_relayed_unchanged_to_stream_order_fn(self):
        captured = {}

        async def fake(model_id, prompt="", **kwargs):
            captured["tools"] = kwargs.get("tools")
            captured["tool_choice"] = kwargs.get("tool_choice")
            captured["messages_override"] = kwargs.get("messages_override")
            yield StreamChunk(content_delta="ok")
            yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 1})
            yield StreamChunk(is_final=True)

        app = self._make_app(stream_fn=fake)
        tools = [{"type": "function", "function": {"name": "get_weather", "parameters": {}}}]
        await self._post(
            app,
            {
                "messages": [{"role": "user", "content": "hi"}],
                "tools": tools,
                "tool_choice": "auto",
                "stream": False,
            },
        )
        self.assertEqual(captured["tools"], tools)
        self.assertEqual(captured["tool_choice"], "auto")
        self.assertEqual(captured["messages_override"], [{"role": "user", "content": "hi"}])

    async def test_no_system_prompt_injected_on_chat_completions(self):
        """Scope check (see router/app/system_prompt.py's docstring):
        BOTH composed parts - the date-awareness sentence and the Brew 56
        identity block - are /v1/order only. A client's own messages -
        including one that already starts with its own system message, as
        Cursor and similar tools send - must reach stream_order_fn
        completely unmodified: no injection, no merge, no extra message of
        any kind. This holds regardless of
        settings.system_prompt_include_date/_include_identity, both of
        which default True and are left at their defaults here on purpose -
        proving the endpoint itself never reads those settings, not just
        that a test happened to turn them off."""

        captured = {}

        async def fake(model_id, prompt="", **kwargs):
            captured["messages_override"] = kwargs.get("messages_override")
            yield StreamChunk(content_delta="ok")
            yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 1})
            yield StreamChunk(is_final=True)

        app = self._make_app(stream_fn=fake)  # both settings left at their True defaults
        client_messages = [
            {"role": "system", "content": "You are a helpful coding assistant with tool access."},
            {"role": "user", "content": "hi"},
        ]
        await self._post(app, {"messages": client_messages, "stream": False})

        self.assertEqual(captured["messages_override"], client_messages)
        # Belt-and-braces on the equality above: neither part's marker text
        # appears anywhere in what was sent, including merged into the
        # client's own system message.
        sent_text = " ".join(m["content"] for m in captured["messages_override"])
        self.assertNotIn("Ishan Suthar", sent_text)
        self.assertNotIn("Today's date is", sent_text)

    async def test_client_history_sent_as_is_no_session_lookup(self):
        """Section 1: the client's own messages array is used verbatim -
        no SQLite session assembly, no remember_chat toggle involved."""

        captured = {}

        async def fake(model_id, prompt="", **kwargs):
            captured["messages_override"] = kwargs.get("messages_override")
            yield StreamChunk(content_delta="ok")
            yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 1})
            yield StreamChunk(is_final=True)

        app = self._make_app(stream_fn=fake)
        messages = [
            {"role": "user", "content": "earlier question"},
            {"role": "assistant", "content": "earlier answer"},
            {"role": "user", "content": "follow-up"},
        ]
        await self._post(app, {"messages": messages, "stream": False})
        self.assertEqual(captured["messages_override"], messages)

    async def test_no_session_row_created(self):
        registry = _make_bean_registry(with_premium=True)
        policy = RoutingPolicy.from_yaml(self.policy_path, bean_registry=registry)
        settings = Settings(generating_tick_tokens=5, generating_tick_seconds=999)
        ledger = RouterLedger(self.ledger_path)
        session_store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            session_store=session_store,
            stream_order_fn=_fake_openai_stream_healthy,
            uploads_root=Path(self._tmp_dir.name) / "uploads",
        )
        app = create_app(state=self.state)
        _override_auth(app)

        await self._post(app, {"messages": [{"role": "user", "content": "hi"}], "stream": False})

        self.assertEqual(session_store.list_sessions(), [])

    async def test_auto_escalate_under_cap(self):
        app = self._make_app(stream_fn=_fake_openai_stream_empty, escalation_cost_cap_usd=0.50)
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        self.assertEqual(response.json()["model"], "Reserve Blend")
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalated"], "True")
        self.assertEqual(rows[0]["over_cap_declined"], "False")

    async def test_streamed_escalation_returns_only_draft_no_concatenation(self):
        """Escalation-concatenation fix (docs/design/
        openai-compat-endpoint-design.md "Known issue", resolved): a
        streamed request that would have auto-escalated must never run
        the premium re-run - the client gets only the draft's content,
        cleanly, with no second stream glued onto it."""

        app = self._make_app(stream_fn=_fake_openai_stream_by_model, escalation_cost_cap_usd=0.50)
        status, chunks = await self._stream_chunks(
            app,
            {"messages": [{"role": "user", "content": "say hello in exactly three words"}], "stream": True},
        )
        self.assertEqual(status, 200)
        content = "".join(
            c.get("choices", [{}])[0].get("delta", {}).get("content", "") for c in chunks
        )
        self.assertEqual(content, "Hello there you")  # draft only, never the premium text
        final = chunks[-1]
        self.assertEqual(final.get("system_fingerprint"), "draft_quality")
        self.assertEqual(final["choices"][0]["finish_reason"], "stop")
        self.assertEqual([c["model"] for c in chunks if c.get("choices")][0], "House Blend")

        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalated"], "False")
        self.assertEqual(rows[0]["would_have_escalated"], "True")
        self.assertEqual(rows[0]["bean_alias"], "House Blend")

    async def test_nonstreamed_escalation_returns_only_premium_response(self):
        """Same fix, stream=False path: the draft is buffered internally
        and discarded entirely once escalation fires - the client only
        ever sees the premium response, no draft text present anywhere
        in the body."""

        app = self._make_app(stream_fn=_fake_openai_stream_by_model, escalation_cost_cap_usd=0.50)
        response = await self._post(
            app,
            {"messages": [{"role": "user", "content": "say hello in exactly three words"}], "stream": False},
        )
        body = response.json()
        self.assertEqual(body["choices"][0]["message"]["content"], "Hello there, friend!")
        self.assertNotIn("Hello there you", body["choices"][0]["message"]["content"])
        self.assertEqual(body["model"], "Reserve Blend")

        # The under-reporting risk this fix must not reintroduce: usage
        # must reflect the premium call's tokens, not the discarded
        # draft's - that's exactly where cost under-reporting would hide.
        self.assertEqual(body["usage"]["completion_tokens"], 99)

        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalated"], "True")
        self.assertEqual(rows[0]["would_have_escalated"], "False")
        self.assertEqual(rows[0]["bean_alias"], "Reserve Blend")
        self.assertEqual(rows[0]["tokens_out"], "99")

    async def test_over_cap_forces_immediate_decline_no_waiting(self):
        """Section 1: cannot pause for human approval on this endpoint -
        escalation_pending must become an immediate decline, never a
        hang."""

        app = self._make_app(stream_fn=_fake_openai_stream_empty, escalation_cost_cap_usd=0.0)
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "House Blend")  # draft, not escalated
        self.assertEqual(response.json().get("system_fingerprint"), "draft_quality")
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalated"], "False")
        self.assertEqual(rows[0]["over_cap_declined"], "True")

    async def test_draft_quality_absent_when_not_over_cap(self):
        app = self._make_app()
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        self.assertNotIn("system_fingerprint", response.json())

    async def test_no_vision_bean_available_returns_error_chunk(self):
        app = self._make_app()
        response = await self._post(
            app,
            {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "what is this"},
                            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA="}},
                        ],
                    }
                ],
                "stream": False,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["type"], "no_vision_bean_available")

    async def test_tools_present_routes_to_tool_calling_capable_bean(self):
        """web-search Brew: /v1/chat/completions has no use_web toggle -
        a raw OpenAI client's own `tools` array is for its own function-
        calling loop - but it still needs a Bean that can actually call
        them, so the same routing constraint machinery applies. Replaces
        the old passive log-only warning with real enforcement."""

        app = self._make_app(stream_fn=_fake_openai_stream_healthy)
        tools = [{"type": "function", "function": {"name": "get_weather", "parameters": {}}}]
        response = await self._post(
            app,
            {"messages": [{"role": "user", "content": "hi"}], "tools": tools, "stream": False},
        )
        self.assertEqual(response.json()["model"], "Reserve Blend")

    async def test_no_tools_stays_on_default_bean(self):
        app = self._make_app(stream_fn=_fake_openai_stream_healthy)
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        self.assertEqual(response.json()["model"], "House Blend")

    async def test_tools_present_no_capable_bean_anywhere_returns_error_chunk(self):
        app = self._make_app(stream_fn=_fake_openai_stream_healthy, with_premium=False)
        tools = [{"type": "function", "function": {"name": "get_weather", "parameters": {}}}]
        response = await self._post(
            app,
            {"messages": [{"role": "user", "content": "hi"}], "tools": tools, "stream": False},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["type"], "no_web_search_bean_available")

    async def test_ledger_row_has_prompt_shape_facts(self):
        app = self._make_app()
        await self._post(
            app,
            {
                "messages": [
                    {"role": "system", "content": "be terse"},
                    {"role": "user", "content": "```python\nprint(1)\n```"},
                ],
                "stream": False,
            },
        )
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(rows[0]["has_code_fence"], "True")
        self.assertEqual(rows[0]["message_count"], "2")
        self.assertGreater(int(rows[0]["total_input_chars"]), 0)

    async def test_ledger_row_client_source_is_openai_api_family_not_chat_ui(self):
        app = self._make_app()
        await self._post(app, {"messages": [{"role": "user", "content": "hi"}], "stream": False})
        rows = self.state.ledger.read_all_rows()
        self.assertNotEqual(rows[0]["client_source"], "chat_ui")

    async def test_long_prior_history_pushes_toward_cold_brew_bean_via_task_type_signal(self):
        """Section 1: history contributes via turn *count*
        (classifier_long_history_turns), never via raw char volume of
        prior turns alone - verified indirectly through task_type/
        complexity staying stable regardless of a huge prior context, by
        checking the classifier signal directly is covered in
        test_classifier.py; here we just confirm a large prior context
        does not crash routing and total_input_chars reflects it."""

        app = self._make_app()
        huge_prior = [
            {"role": "user", "content": "x" * 20000},
            {"role": "assistant", "content": "y" * 20000},
        ]
        response = await self._post(
            app,
            {"messages": huge_prior + [{"role": "user", "content": "hi"}], "stream": False},
        )
        self.assertEqual(response.status_code, 200)
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(int(rows[0]["total_input_chars"]), 40002)

    # --- Brew 47 Section 2: retry detection -----------------------------

    async def test_retry_detected_and_linked_in_ledger(self):
        app = self._make_app(with_session_store=True)
        body = {"messages": [{"role": "user", "content": "same question"}], "stream": False}
        headers = {"User-Agent": "cursor/1.0"}

        first = await self._post(app, body, headers=headers)
        second = await self._post(app, body, headers=headers)

        first_id = first.json()["id"][len("chatcmpl-"):]
        second_id = second.json()["id"][len("chatcmpl-"):]

        rows = {row["request_id"]: row for row in self.state.ledger.read_all_rows()}
        self.assertEqual(rows[second_id]["retry_of"], first_id)
        self.assertEqual(rows[first_id]["retry_count"], "1")

    async def test_retry_not_detected_for_different_message(self):
        app = self._make_app(with_session_store=True)
        headers = {"User-Agent": "cursor/1.0"}
        await self._post(
            app, {"messages": [{"role": "user", "content": "question A"}], "stream": False}, headers=headers
        )
        second = await self._post(
            app, {"messages": [{"role": "user", "content": "question B"}], "stream": False}, headers=headers
        )
        second_id = second.json()["id"][len("chatcmpl-"):]
        rows = {row["request_id"]: row for row in self.state.ledger.read_all_rows()}
        self.assertEqual(rows[second_id]["retry_of"], "")

    async def test_no_retry_detection_without_session_store(self):
        """Graceful degradation, matching every other Optional[SessionStore]
        precedent in this router (Pantry retrieval, remember_chat)."""

        app = self._make_app(with_session_store=False)
        body = {"messages": [{"role": "user", "content": "same question"}], "stream": False}
        headers = {"User-Agent": "cursor/1.0"}
        await self._post(app, body, headers=headers)
        second = await self._post(app, body, headers=headers)
        second_id = second.json()["id"][len("chatcmpl-"):]
        rows = {row["request_id"]: row for row in self.state.ledger.read_all_rows()}
        self.assertEqual(rows[second_id]["retry_of"], "")

    async def test_concurrent_identical_requests_not_flagged_as_retries(self):
        """The parallelism-vs-retry edge case (Section 2): two requests
        fired at the same instant with identical content must not match
        each other - neither has a completed response yet when the other
        starts."""

        gate = asyncio.Event()

        async def fake(model_id, prompt="", **kwargs):
            await gate.wait()
            yield StreamChunk(content_delta="ok")
            yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 50})
            yield StreamChunk(is_final=True)

        app = self._make_app(stream_fn=fake, with_session_store=True)
        body = {"messages": [{"role": "user", "content": "same question"}], "stream": False}
        headers = {"User-Agent": "cursor/1.0"}

        task1 = asyncio.create_task(self._post(app, body, headers=headers))
        await asyncio.sleep(0.05)
        task2 = asyncio.create_task(self._post(app, body, headers=headers))
        await asyncio.sleep(0.05)
        gate.set()
        await asyncio.gather(task1, task2)

        rows = self.state.ledger.read_all_rows()
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["retry_of"], "")

    # --- Brew 47 Section 2: shadow mode ----------------------------------

    async def test_shadow_mode_disabled_by_default_schedules_nothing(self):
        app = self._make_app(with_session_store=True)  # shadow_mode_enabled defaults False
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}, headers={"User-Agent": "cursor"}
        )
        self.assertEqual(response.status_code, 200)
        await asyncio.gather(*list(self.state.background_tasks))
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(len(rows), 1)

    async def test_shadow_mode_enabled_schedules_a_real_shadow_run(self):
        app = self._make_app(
            with_session_store=True, shadow_mode_enabled=True, shadow_mode_sample_rate=1.0
        )
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}, headers={"User-Agent": "cursor"}
        )
        primary_id = response.json()["id"][len("chatcmpl-"):]
        await asyncio.gather(*list(self.state.background_tasks))

        rows = self.state.ledger.read_all_rows()
        self.assertEqual(len(rows), 2)
        shadow_row = next(r for r in rows if r["is_shadow"] == "True")
        self.assertEqual(shadow_row["shadow_of"], primary_id)
        self.assertEqual(shadow_row["bean_alias"], "Reserve Blend")

        record = self.state.session_store.get_api_request(primary_id)
        self.assertIsNotNone(record.shadow_response_text)
        self.assertEqual(record.shadow_bean_alias, "Reserve Blend")

    async def test_shadow_run_computes_real_cost_via_resolve_cost(self):
        """Shadow rows already used _real_cost_usd() before this fix -
        this documents that _run_shadow now goes through the same
        resolve_cost() as every other row, preferring a reported cost when
        the shadow call's own usage carries one."""

        async def fake(model_id, prompt="", **kwargs):
            yield StreamChunk(content_delta="ok")
            yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 50, "cost": 0.033})
            yield StreamChunk(is_final=True)

        app = self._make_app(
            stream_fn=fake, with_session_store=True, shadow_mode_enabled=True, shadow_mode_sample_rate=1.0
        )
        await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}, headers={"User-Agent": "cursor"}
        )
        await asyncio.gather(*list(self.state.background_tasks))

        rows = self.state.ledger.read_all_rows()
        shadow_row = next(r for r in rows if r["is_shadow"] == "True")
        self.assertEqual(shadow_row["cost_usd"], "0.033")
        self.assertEqual(shadow_row["cost_source"], "reported")

    async def test_shadow_mode_never_delays_the_client_response(self):
        """The client's response must be fully returned before the shadow
        run's own generation even starts, not merely before it finishes."""

        call_count = {"n": 0}
        release_shadow = asyncio.Event()

        async def fake(model_id, prompt="", **kwargs):
            call_count["n"] += 1
            if call_count["n"] > 1:
                await release_shadow.wait()
            yield StreamChunk(content_delta="ok")
            yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 50})
            yield StreamChunk(is_final=True)

        app = self._make_app(
            stream_fn=fake, with_session_store=True, shadow_mode_enabled=True, shadow_mode_sample_rate=1.0
        )
        response = await asyncio.wait_for(
            self._post(app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}, headers={"User-Agent": "cursor"}),
            timeout=2.0,
        )
        self.assertEqual(response.status_code, 200)
        # The client response above already completed while the shadow
        # call (call #2) is still blocked on release_shadow - proves the
        # client never waited on it.
        self.assertEqual(len(self.state.background_tasks), 1)

        release_shadow.set()
        await asyncio.gather(*list(self.state.background_tasks))
        self.assertEqual(len(self.state.ledger.read_all_rows()), 2)

    async def test_shadow_run_never_recursive(self):
        app = self._make_app(
            with_session_store=True, shadow_mode_enabled=True, shadow_mode_sample_rate=1.0
        )
        await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}, headers={"User-Agent": "cursor"}
        )
        await asyncio.gather(*list(self.state.background_tasks))
        # Exactly one shadow row (primary + its one shadow) - a recursive
        # shadow-of-a-shadow would produce a third row.
        self.assertEqual(len(self.state.ledger.read_all_rows()), 2)
        self.assertEqual(len(self.state.background_tasks), 0)

    async def test_shadow_mode_skips_when_primary_already_used_premium_bean(self):
        app = self._make_app(
            with_session_store=True, shadow_mode_enabled=True, shadow_mode_sample_rate=1.0
        )
        await self._post(
            app,
            {"messages": [{"role": "user", "content": "hi"}], "model": "Reserve Blend", "stream": False},
            headers={"User-Agent": "cursor"},
        )
        await asyncio.gather(*list(self.state.background_tasks))
        self.assertEqual(len(self.state.ledger.read_all_rows()), 1)

    async def test_shadow_run_failure_is_silent_and_logged(self):
        call_count = {"n": 0}

        async def fake(model_id, prompt="", **kwargs):
            call_count["n"] += 1
            if call_count["n"] > 1:
                raise OpenRouterClientError("simulated shadow failure")
            yield StreamChunk(content_delta="ok")
            yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 50})
            yield StreamChunk(is_final=True)

        app = self._make_app(
            stream_fn=fake, with_session_store=True, shadow_mode_enabled=True, shadow_mode_sample_rate=1.0
        )
        with self.assertLogs("router.app.main", level="WARNING") as log_ctx:
            response = await self._post(
                app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}, headers={"User-Agent": "cursor"}
            )
            await asyncio.gather(*list(self.state.background_tasks))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(any("shadow run failed" in message for message in log_ctx.output))
        # The failed shadow never got far enough to append a Ledger row.
        self.assertEqual(len(self.state.ledger.read_all_rows()), 1)

    async def test_daily_shadow_cost_cap_trips_mid_request_and_is_skipped(self):
        app = self._make_app(
            with_session_store=True,
            shadow_mode_enabled=True,
            shadow_mode_sample_rate=1.0,
            shadow_mode_daily_cost_cap_usd=1.00,
        )
        # A prior shadow row today that already exhausted the cap.
        self.state.ledger.append(
            LedgerRow(
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id="shadow-already-ran",
                task_type="explain",
                bean_alias="Reserve Blend",
                raw_model_id="vendor/premium",
                tokens_in=100,
                tokens_out=100,
                cost_usd=2.00,
                latency_ms=0,
                escalated=False,
                escalation_approved=None,
                is_shadow=True,
                shadow_of="some-other-request",
            )
        )

        with self.assertLogs("router.app.main", level="INFO") as log_ctx:
            response = await self._post(
                app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}, headers={"User-Agent": "cursor"}
            )
            await asyncio.gather(*list(self.state.background_tasks))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(any("daily cap reached" in message for message in log_ctx.output))
        # Only the pre-seeded row plus this request's own primary row -
        # no new shadow row was appended.
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(len(rows), 2)
        self.assertFalse(any(r["shadow_of"] == "" and r["is_shadow"] == "True" for r in rows))

    async def test_shadow_mode_sample_rate_zero_never_schedules(self):
        app = self._make_app(
            with_session_store=True, shadow_mode_enabled=True, shadow_mode_sample_rate=0.0
        )
        await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}, headers={"User-Agent": "cursor"}
        )
        await asyncio.gather(*list(self.state.background_tasks))
        self.assertEqual(len(self.state.ledger.read_all_rows()), 1)

    async def test_shadow_mode_disabled_stream_true_still_returns_normally(self):
        """Shadow scheduling is wired into the SSE path's finally block too
        (not just stream=false) - must not break streaming."""

        app = self._make_app(with_session_store=True)
        status, chunks = await self._stream_chunks(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": True}, headers={"User-Agent": "cursor"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(len(chunks) > 0)


class SpendCapChatCompletionsTests(ChatCompletionsEndpointTests):
    """Spend-cap Brew: /v1/chat/completions' pre-stream cap/rate-limit
    enforcement - a real HTTP 429 with an OpenAI-compatible error body and
    a Retry-After header, on both stream modes, and the stream must never
    start on a denial."""

    def _seed_spend(self, *, cost_usd):
        self.state.ledger.append(
            LedgerRow(
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id="seed",
                task_type="code",
                bean_alias="House Blend",
                raw_model_id="vendor/default:free",
                tokens_in=10,
                tokens_out=10,
                cost_usd=cost_usd,
                latency_ms=100,
                escalated=False,
                escalation_approved=None,
                cost_source="computed",
                user_id=FAKE_USER.id,
            )
        )

    async def test_spend_cap_returns_429_with_openai_error_body_and_retry_after(self):
        app = self._make_app(with_session_store=True, per_user_daily_cost_cap_usd=0.10)
        self._seed_spend(cost_usd=0.10)
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "model": "Reserve Blend", "stream": False}
        )
        self.assertEqual(response.status_code, 429)
        body = response.json()
        self.assertEqual(body["error"]["type"], "spend_cap_exceeded")
        self.assertIn("midnight UTC", body["error"]["message"])
        self.assertIn("Retry-After", response.headers)
        self.assertGreater(int(response.headers["Retry-After"]), 0)

    async def test_spend_cap_on_stream_true_returns_429_not_an_sse_stream(self):
        """The load-bearing case: once StreamingResponse commits, the
        HTTP status is locked at 200 forever - the cap check must run
        (and refuse) before that happens, so this must be a real 429
        JSON response, never a 200 SSE stream carrying an error frame."""

        app = self._make_app(with_session_store=True, per_user_daily_cost_cap_usd=0.10)
        self._seed_spend(cost_usd=0.10)
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "model": "Reserve Blend", "stream": True}
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["type"], "spend_cap_exceeded")
        self.assertNotEqual(response.headers.get("content-type", ""), "text/event-stream")

    async def test_under_cap_request_succeeds_normally(self):
        app = self._make_app(with_session_store=True, per_user_daily_cost_cap_usd=100.0)
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        self.assertEqual(response.status_code, 200)

    async def test_rate_limit_returns_429_with_distinct_error_type(self):
        app = self._make_app(with_session_store=True, per_user_requests_per_minute=1)
        await self._post(app, {"messages": [{"role": "user", "content": "hi"}], "stream": False})
        response = await self._post(app, {"messages": [{"role": "user", "content": "hi"}], "stream": False})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["type"], "rate_limit_exceeded")

    async def test_escalation_stage_cap_denial_falls_back_to_draft(self):
        """Same fallback-to-draft treatment as /v1/order - the draft is
        already paid for and a valid answer (Decaf plan sign-off)."""

        async def fake(model_id, prompt="", **kwargs):
            yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 0})
            yield StreamChunk(is_final=True)

        app = self._make_app(
            stream_fn=fake,
            with_session_store=True,
            with_premium=True,
            escalation_cost_cap_usd=0.50,
            per_user_daily_cost_cap_usd=0.001,
        )
        response = await self._post(
            app, {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "House Blend")
        self.assertEqual(response.json()["system_fingerprint"], "draft_quality")

    async def test_client_max_tokens_used_as_assumed_output_tokens(self):
        """The client's own max_tokens (strictly better information than
        a guess) shapes the estimate - a request that would be refused
        under the default assumed_output_tokens must be allowed when the
        client caps output small enough to fit under the cap."""

        app = self._make_app(with_session_store=True, per_user_daily_cost_cap_usd=0.02)
        response = await self._post(
            app,
            {
                "messages": [{"role": "user", "content": "hi"}],
                "model": "Reserve Blend",
                "max_tokens": 10,
                "stream": False,
            },
        )
        # Reserve Blend at 0.003/0.015 per 1k, ~10 output tokens: a tiny
        # fraction of a cent - comfortably under a 0.02 cap even though
        # the default assumed_output_tokens (1000) would have exceeded it.
        self.assertEqual(response.status_code, 200)


class MemoryProposalSpendCapTests(unittest.IsolatedAsyncioTestCase):
    """Spend-cap Brew: generate_memory_proposal() now writes a real
    Ledger row and is gated the same as every other real spend site -
    previously this endpoint spent real money with no Ledger row at all."""

    VALID_RESPONSE = (
        "### FILE: brew-log/active_context.md\n"
        "# Active Context\n\nUpdated.\n"
        "### END FILE\n\n"
        "### FILE: brew-log/progress.md\n"
        "# Progress\n\nDid a thing.\n"
        "### END FILE\n"
    )

    async def _fake_proposal_stream(self, model_id, prompt, **_kwargs):
        yield StreamChunk(content_delta=self.VALID_RESPONSE)
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 42})
        yield StreamChunk(is_final=True)

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)

        self.repo_root = Path(self._tmp_dir.name) / "fixture_repo"
        (self.repo_root / "brew-log").mkdir(parents=True)
        (self.repo_root / "brew-log" / "active_context.md").write_text("# Active Context\n", encoding="utf-8")
        (self.repo_root / "brew-log" / "progress.md").write_text("# Progress\n", encoding="utf-8")

        registry = _make_bean_registry(with_premium=True)
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        self.ledger = RouterLedger(Path(self._tmp_dir.name) / "router_requests.csv")
        self.session_store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")

    def _make_app(self, **settings_overrides):
        settings_kwargs = {
            "memory_proposal_bean_alias": "House Blend",
            "per_user_daily_cost_cap_usd": 100.0,
            "per_user_requests_per_minute": 1000,
        }
        settings_kwargs.update(settings_overrides)
        settings = Settings(**settings_kwargs)
        registry = _make_bean_registry(with_premium=True)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=self.ledger,
            session_store=self.session_store,
            stream_order_fn=self._fake_proposal_stream,
            memory_proposal_repo_root=self.repo_root,
        )
        app = create_app(state=self.state)
        _override_auth(app)
        return app

    async def _create_session_with_message(self, store):
        session_id = store.create_session(user_id=FAKE_USER.id)
        store.add_message(session_id, request_id="r1", role="user", content="What did we do today?")
        return session_id

    async def test_generation_writes_a_real_ledger_row(self):
        app = self._make_app()
        session_id = await self._create_session_with_message(self.session_store)

        response = await httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ).post(f"/v1/sessions/{session_id}/memory_proposal")

        self.assertEqual(response.status_code, 200)
        rows = self.state.ledger.read_all_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["task_type"], "memory_proposal")
        self.assertEqual(rows[0]["cost_usd"], "0.0")  # House Blend is free-tier
        self.assertEqual(rows[0]["cost_source"], "computed")
        self.assertEqual(rows[0]["user_id"], str(FAKE_USER.id))

    async def test_over_cap_request_refused_with_429(self):
        app = self._make_app(per_user_daily_cost_cap_usd=0.0)
        # A paid Bean forces a real nonzero estimate so a $0.00 cap trips.
        self.state.settings = self.state.settings.model_copy(
            update={"memory_proposal_bean_alias": "Reserve Blend"}
        )
        session_id = await self._create_session_with_message(self.session_store)

        response = await httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ).post(f"/v1/sessions/{session_id}/memory_proposal")

        self.assertEqual(response.status_code, 429)
        # No model call was made, no Ledger row written.
        self.assertEqual(len(self.state.ledger.read_all_rows()), 0)


if __name__ == "__main__":
    unittest.main()
