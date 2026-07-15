"""Coffee Core Router FastAPI app.

POST /v1/order streams the full event contract (see router/EVENT_CONTRACT.md)
over Server-Sent Events. The orchestration logic lives in `run_order()`, a
pure async generator that takes its OpenRouter client, Bean registry,
routing policy, and approval-wait function as parameters - so it is fully
unit-testable without a live ASGI server or a live network call. The
FastAPI routes below are thin adapters around it.

Run only from the repository root:
    python -m uvicorn router.app.main:app --port 8765
"""

from __future__ import annotations

import asyncio
import base64
import difflib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from router.app.aliases import BeanRegistry
from router.app.auth import InvalidCredentialsError, get_current_user, login as auth_login
from router.app.classifier import Attachment as ClassifierAttachment
from router.app.classifier import classify
from router.app.config import Settings, assert_no_key_like_strings, load_router_config_paths
from router.app.escalation import (
    GenerationResult,
    check_for_failure,
    decide_escalation,
    resolve_pending_escalation,
)
from router.app.history import EMPTY_HISTORY_RESULT, assemble_history, pair_turns
from router.app.events import (
    BaseEvent,
    CancelledEvent,
    ClassifyingEvent,
    CompleteEvent,
    ErrorEvent,
    EscalatingEvent,
    EscalationPendingEvent,
    GeneratingEvent,
    HeartbeatEvent,
    OrderReceivedEvent,
    RouteSelectedEvent,
)
from router.app.ledger import LedgerRow, RouterLedger
from router.app.memory_proposals import REPO_ROOT as MEMORY_PROPOSALS_REPO_ROOT
from router.app.memory_proposals import (
    MemoryProposal,
    MemoryProposalError,
    MemoryProposalGuardrailError,
    approve_memory_proposal,
    generate_memory_proposal,
)
from router.app.openrouter_client import OpenRouterClientError, StreamChunk, stream_order
from router.app.pantry import (
    DEFAULT_INDEX_PATH,
    PantryChunk,
    build_fts_query,
    resolve_pantry_file_path,
    retrieve_chunks,
)
from router.app.pantry import connect as pantry_connect
from router.app.preferences import PreferenceStore
from router.app.routing import DEFAULT_ROUTING_POLICY_PATH, NoVisionBeanError, RoutingError, RoutingPolicy
from router.app.sessions import (
    TITLE_MAX_CHARS,
    ProjectRecord,
    SessionStore,
    UserRecord,
    UsernameTakenError,
)
from router.app.uploads import (
    DEFAULT_UPLOADS_ROOT,
    PdfExtractionError,
    UploadRecord,
    UploadValidationError,
    cleanup_request_uploads,
    extract_pdf_text,
    extract_text_file,
    new_attachment_id,
    save_upload,
    sweep_stale_uploads,
    truncate_inline_text,
    validate_upload,
)
from tools.generate_policy import DEFAULT_TASTING_NOTES, build_policy, parse_tasting_notes, render_policy_yaml

DEFAULT_PROJECT = "default"

logger = logging.getLogger(__name__)

# Test/demo-only: forces every generation through the escalation path
# regardless of its real content, so the approval-gate UI can be
# demonstrated without crafting a real failing prompt. A raw environment
# variable rather than a settings.yaml field on purpose - a config file
# can be committed by accident, an environment variable someone has to
# set deliberately every time cannot. Never read anywhere except
# _force_escalation_enabled() below.
FORCE_ESCALATION_ENV_VAR = "COFFEE_ROUTER_FORCE_ESCALATION"


def _force_escalation_enabled() -> bool:
    return os.environ.get(FORCE_ESCALATION_ENV_VAR) == "1"


@dataclass
class RequestRecord:
    """Enough state to support /v1/retry after /v1/order's stream closes."""

    task_type: str
    bean_alias: str
    raw_model_id: str
    prompt: str
    tokens_in: int
    accumulated_text: str = ""
    tokens_out: int = 0
    finish_reason: Optional[str] = None


@dataclass
class EscalationContext:
    """Everything a reloaded client needs to redraw the approval card for
    a request currently paused on escalation_pending (Brew 40 - see
    docs/design/escalation-approval-ui-design.md Section 3.5), plus
    enough to answer a late/duplicate POST /v1/approve_escalation
    meaningfully instead of a bare 404 (Section 3.6). Mutable (not
    frozen): `resolved`/`resolution` are set in place once the wait ends,
    so a late request can still find out what happened. Cleaned up in
    run_order()'s `finally` block once the whole request completes."""

    request_id: str
    session_id: Optional[str]
    reason: str
    est_cost_usd: float
    premium_bean_alias: str
    started_at: str
    decision_deadline: str
    resolved: bool = False
    resolution: Optional[str] = None  # "approved" | "declined" | "timed_out" | "cancelled"


@dataclass(frozen=True)
class PolicyRebuildProposal:
    """A rebuilt router/config/routing_policy.yaml proposal (Brew 42,
    docs/design/learning-loop-and-release-design.md Section 3.2) - never
    applied without an explicit POST .../rebuild_apply/{id} call, which
    re-reads the on-disk file and refuses if it no longer matches
    `based_on_policy_yaml` (defense against a race, same pattern as Brew
    41's memory-proposal approve-time guardrail re-check)."""

    proposal_id: str
    new_policy_yaml: str
    diff: str
    escalation_candidates: List[str]
    based_on_policy_yaml: str


StreamOrderFn = Callable[..., AsyncIterator[StreamChunk]]


@dataclass
class RouterState:
    bean_registry: BeanRegistry
    routing_policy: RoutingPolicy
    settings: Settings
    ledger: RouterLedger
    # Stored on state, not as a plain function-default parameter, because a
    # def-time default (`stream_order_fn: StreamOrderFn = stream_order`)
    # binds once at import time - monkeypatching the module-level
    # `stream_order` name afterward would not reach it. Tests inject a fake
    # here instead.
    stream_order_fn: StreamOrderFn = field(default=stream_order)
    pending_escalations: Dict[str, "asyncio.Future[str]"] = field(default_factory=dict)
    request_records: Dict[str, RequestRecord] = field(default_factory=dict)
    session_store: Optional[SessionStore] = None
    cancel_flags: Dict[str, asyncio.Event] = field(default_factory=dict)
    # Brew 38: uploaded-file metadata, keyed by attachment_id. In-memory
    # only, never SQLite - uploads are ephemeral per-request (docs/design/
    # attachments-design.md Section 7, Decision 5). uploads_root is a
    # field (not a hardcoded path) so tests can point it at a temp dir.
    uploads: Dict[str, UploadRecord] = field(default_factory=dict)
    uploads_root: Path = field(default=DEFAULT_UPLOADS_ROOT)
    # Brew 39 (docs/design/counter-scene-design.md Section 5): device-wide
    # UI preferences (e.g. the Coffee Counter scene's collapse state).
    # Optional so tests that don't touch preferences don't need a real
    # SQLite file - endpoints construct a default store lazily if absent.
    preference_store: Optional[PreferenceStore] = None
    # Brew 40 (docs/design/escalation-approval-ui-design.md Section 3.5):
    # pending/resolved escalation info, keyed by request_id, for reload
    # recovery and late/duplicate-approval handling.
    pending_escalation_context: Dict[str, EscalationContext] = field(default_factory=dict)
    # Brew 40 Section 3.1: references to the background asyncio.Task
    # objects that run each order to completion independent of the
    # /v1/order HTTP connection that started them - held here only so
    # asyncio doesn't garbage-collect an in-flight task (a well-known
    # asyncio footgun), discarded once a task finishes.
    background_tasks: set = field(default_factory=set)
    # Brew 41 (docs/design/memory-and-pantry-design.md Section 4.2): the
    # FTS5 index built by router/tools/index_pantry.py. A field (not a
    # hardcoded path), matching uploads_root, so tests can point it at a
    # temp/fixture index instead of the real router/data/pantry_index.db.
    pantry_index_path: Path = field(default=DEFAULT_INDEX_PATH)
    # Brew 41 (docs/design/memory-and-pantry-design.md Section 3.1): a
    # generated-but-not-yet-approved-or-discarded proposal, keyed by
    # proposal_id. Same in-memory, no-TTL-sweep precedent as
    # pending_escalation_context - fine at this router's real request
    # volume.
    memory_proposals: Dict[str, MemoryProposal] = field(default_factory=dict)
    # A field (not a hardcoded constant), matching uploads_root/
    # pantry_index_path, so tests never touch the real brew-log/ files -
    # defaults to the real repo root only for the actual running router.
    memory_proposal_repo_root: Path = field(default=MEMORY_PROPOSALS_REPO_ROOT)
    # Brew 42 (docs/design/learning-loop-and-release-design.md Section 3.2):
    # a generated-but-not-yet-applied-or-discarded routing_policy.yaml
    # rebuild, keyed by proposal_id. Same in-memory/no-TTL-sweep precedent
    # as memory_proposals. routing_policy_path/tasting_notes_path are
    # fields (not hardcoded constants), matching every other Brew 41/42
    # path override, so tests never touch the real routing_policy.yaml or
    # tasting_notes.md.
    policy_rebuild_proposals: Dict[str, PolicyRebuildProposal] = field(default_factory=dict)
    routing_policy_path: Path = field(default=DEFAULT_ROUTING_POLICY_PATH)
    tasting_notes_path: Path = field(default=DEFAULT_TASTING_NOTES)


async def _consume_stream(
    stream_order_fn: StreamOrderFn,
    model_id: str,
    prompt: str,
    *,
    settings: Settings,
    request_id: str,
    cancel_event: Optional[asyncio.Event] = None,
    image_data_urls: Optional[List[str]] = None,
    history_messages: Optional[List[Dict[str, str]]] = None,
) -> AsyncIterator[Any]:
    """Wrap a raw OpenRouter stream, emitting periodic `generating` ticks
    (with the incremental text_delta since the last tick - contract v1.1)
    per settings.generating_tick_tokens / generating_tick_seconds, and
    yield a final ("__final__", text, tokens_out, finish_reason, usage)
    sentinel tuple once the stream ends, or a ("__cancelled__",) sentinel
    if cancel_event is set mid-stream. image_data_urls (Brew 38) and
    history_messages (Brew 46) are passed straight through to
    stream_order_fn - see router/app/openrouter_client.py."""

    accumulated_text = ""
    tokens_out = 0
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    last_tick_time = time.monotonic()
    tokens_since_tick = 0
    text_since_tick = ""

    async for chunk in stream_order_fn(
        model_id, prompt, image_data_urls=image_data_urls, history_messages=history_messages
    ):
        if cancel_event is not None and cancel_event.is_set():
            yield ("__cancelled__",)
            return

        if chunk.is_final:
            break
        if chunk.content_delta:
            accumulated_text += chunk.content_delta
            text_since_tick += chunk.content_delta
            approx_new_tokens = max(1, len(chunk.content_delta) // 4)
            tokens_out += approx_new_tokens
            tokens_since_tick += approx_new_tokens
        if chunk.finish_reason:
            finish_reason = chunk.finish_reason
        if chunk.usage:
            usage = chunk.usage

        now = time.monotonic()
        if (
            tokens_since_tick >= settings.generating_tick_tokens
            or (now - last_tick_time) >= settings.generating_tick_seconds
        ):
            yield GeneratingEvent(
                request_id=request_id,
                tokens_out=tokens_out,
                est_cost_usd=0.0,
                text_delta=text_since_tick or None,
            )
            tokens_since_tick = 0
            text_since_tick = ""
            last_tick_time = now

    if usage and isinstance(usage.get("completion_tokens"), int):
        tokens_out = usage["completion_tokens"]

    if text_since_tick:
        # Flush whatever text arrived since the last tick but never crossed
        # settings.generating_tick_tokens/_seconds before the stream ended -
        # otherwise a short response (fewer tokens than one tick's worth)
        # never reaches the client at all, since CompleteEvent carries no
        # content field and text only travels via generating.text_delta.
        yield GeneratingEvent(
            request_id=request_id,
            tokens_out=tokens_out,
            est_cost_usd=0.0,
            text_delta=text_since_tick,
        )

    yield ("__final__", accumulated_text, tokens_out, finish_reason, usage)


async def run_order(
    state: RouterState,
    *,
    prompt: str,
    attachments: Optional[List[ClassifierAttachment]] = None,
    attachment_ids: Optional[List[str]] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    bean_alias_override: Optional[str] = None,
    use_pantry: bool = False,
    remember_chat: bool = False,
    stream_order_fn: StreamOrderFn = stream_order,
    wait_for_approval: Optional[Callable[[str], "asyncio.Future[str]"]] = None,
) -> AsyncIterator[BaseEvent]:
    """Core orchestration generator. Pure aside from stream_order_fn (an
    injectable OpenRouter caller) and wait_for_approval (an injectable
    approval-wait function) - both default to real implementations but
    tests always inject fakes, so no network call happens in tests.

    attachment_ids (Brew 38) are resolved against state.uploads inside
    _run_order_body; `attachments` remains a separate, directly-injectable
    seam (pre-built ClassifierAttachment objects) for tests that don't want
    to go through the /v1/upload flow."""

    request_id = request_id or str(uuid.uuid4())
    started_at = time.monotonic()

    cancel_event = asyncio.Event()
    state.cancel_flags[request_id] = cancel_event

    try:
        async for event in _run_order_body(
            state,
            prompt=prompt,
            attachments=attachments,
            attachment_ids=attachment_ids,
            request_id=request_id,
            session_id=session_id,
            bean_alias_override=bean_alias_override,
            use_pantry=use_pantry,
            remember_chat=remember_chat,
            stream_order_fn=stream_order_fn,
            wait_for_approval=wait_for_approval,
            cancel_event=cancel_event,
            started_at=started_at,
        ):
            yield event
    finally:
        state.cancel_flags.pop(request_id, None)
        # pending_escalation_context is deliberately NOT popped here: a
        # resolved context must stay available so a late or duplicate
        # POST /v1/approve_escalation arriving after the request has
        # already finished still gets a clear already_resolved response
        # (docs/design/escalation-approval-ui-design.md Section 3.6)
        # instead of a bare 404. Same ephemeral-in-memory, no-TTL-sweep
        # precedent as the rest of RouterState's per-request dicts - fine
        # for this single-process/local-dev router's real request volume.
        if attachment_ids:
            cleanup_request_uploads(request_id, uploads_root=state.uploads_root)
            for attachment_id in attachment_ids:
                state.uploads.pop(attachment_id, None)


async def _run_order_body(
    state: RouterState,
    *,
    prompt: str,
    attachments: Optional[List[ClassifierAttachment]],
    attachment_ids: Optional[List[str]],
    request_id: str,
    session_id: Optional[str],
    bean_alias_override: Optional[str],
    use_pantry: bool = False,
    remember_chat: bool = False,
    stream_order_fn: StreamOrderFn,
    wait_for_approval: Optional[Callable[[str], "asyncio.Future[str]"]],
    cancel_event: asyncio.Event,
    started_at: float,
) -> AsyncIterator[BaseEvent]:
    yield OrderReceivedEvent(request_id=request_id, prompt_chars=len(prompt))
    yield ClassifyingEvent(request_id=request_id)

    upload_records: List[UploadRecord] = []
    if attachment_ids:
        for attachment_id in attachment_ids:
            record = state.uploads.get(attachment_id)
            if record is None:
                yield ErrorEvent(
                    request_id=request_id,
                    error_type="unknown_attachment_id",
                    message=f"No uploaded attachment found for id {attachment_id!r}.",
                    retryable=False,
                )
                return
            upload_records.append(record)

    resolved_attachments = list(attachments or [])
    resolved_attachments.extend(
        ClassifierAttachment(filename=record.filename, content_type=record.content_type)
        for record in upload_records
    )

    pantry_chunks = _retrieve_pantry_chunks(state, prompt) if use_pantry else []

    # Brew 46 (docs/design/conversation-memory-design.md): fetched once,
    # early - the classifier needs a turn count for its long_history
    # signal, and the windowed history payload is assembled later (once
    # outbound_text's real char length is known, for the "reserve the
    # current prompt first" budget). remember_chat is resolved
    # server-side by the /v1/order handler and never accepted from the
    # client on this request itself.
    prior_turns = (
        pair_turns(state.session_store.get_messages(session_id))
        if remember_chat and session_id is not None and state.session_store is not None
        else []
    )

    classification = classify(
        prompt,
        resolved_attachments,
        model_fallback_enabled=state.settings.classifier_model_fallback_enabled,
        history_turn_count=len(prior_turns),
        long_history_turns_threshold=state.settings.classifier_long_history_turns,
    )

    if bean_alias_override is not None:
        try:
            route = state.routing_policy.manual_route(
                classification.task_type,
                bean_alias_override,
                needs_vision=classification.needs_vision,
            )
        except NoVisionBeanError as exc:
            yield ErrorEvent(
                request_id=request_id,
                error_type="no_vision_bean_available",
                message=str(exc),
                retryable=False,
            )
            return
        except RoutingError as exc:
            yield ErrorEvent(
                request_id=request_id,
                error_type="invalid_bean_override",
                message=str(exc),
                retryable=False,
            )
            return
    else:
        try:
            route = state.routing_policy.select_route(
                classification.task_type, needs_vision=classification.needs_vision
            )
        except NoVisionBeanError as exc:
            yield ErrorEvent(
                request_id=request_id,
                error_type="no_vision_bean_available",
                message=str(exc),
                retryable=False,
            )
            return

    yield RouteSelectedEvent(
        request_id=request_id,
        bean_alias=route.bean_alias,
        task_type=classification.task_type,
        complexity=classification.complexity,
        est_cost_usd=route.est_cost_usd,
        policy_entry=route.policy_entry,
        constraint_reason=route.constraint_reason,
    )

    bean = state.bean_registry.by_alias(route.bean_alias)
    model_id = bean.model_id
    tokens_in = max(1, len(prompt) // 4)

    outbound_text, image_data_urls = _build_outbound_content(
        prompt,
        upload_records,
        max_inline_text_chars=state.settings.max_inline_text_chars,
        pantry_chunks=pantry_chunks,
    )
    pantry_sources = _distinct_pantry_sources(pantry_chunks)

    history_result = (
        assemble_history(
            prior_turns,
            current_prompt_chars=len(outbound_text),
            max_messages=state.settings.history_max_messages,
            max_chars=state.settings.history_max_chars,
        )
        if remember_chat
        else EMPTY_HISTORY_RESULT
    )

    try:
        final_text = ""
        tokens_out = 0
        finish_reason = None
        async for item in _consume_stream(
            stream_order_fn,
            model_id,
            outbound_text,
            settings=state.settings,
            request_id=request_id,
            cancel_event=cancel_event,
            image_data_urls=image_data_urls,
            history_messages=history_result.messages or None,
        ):
            if isinstance(item, tuple) and item[0] == "__cancelled__":
                yield CancelledEvent(request_id=request_id, reason="client_cancel_request")
                return
            if isinstance(item, tuple) and item[0] == "__final__":
                _, final_text, tokens_out, finish_reason, _usage = item
            else:
                yield item
    except OpenRouterClientError as exc:
        yield ErrorEvent(
            request_id=request_id,
            error_type="provider_error",
            message=str(exc),
            retryable=True,
        )
        return

    generation = GenerationResult(
        text=final_text, tokens_out=tokens_out, finish_reason=finish_reason,
        # Test/demo-only escape hatch (docs/design/escalation-approval-ui-design.md
        # Section 5): forces every generation to look like a failure so the
        # escalation approval flow can be demoed on demand, without
        # crafting a real failing prompt. A raw environment variable, not
        # a settings.yaml field, so a committed config file can never ship
        # this "on" by accident. Off unless explicitly set.
        caller_reported_failure=_force_escalation_enabled(),
    )
    failure = check_for_failure(
        generation,
        truncation_min_expected_tokens=state.settings.truncation_min_expected_tokens,
        refusal_keywords=state.settings.refusal_keywords,
    )

    premium_bean = state.bean_registry.by_role("premium")
    premium_alias = premium_bean.alias if premium_bean and premium_bean.is_available else None
    est_premium_cost = 0.0 if premium_alias else None

    decision = decide_escalation(
        failure,
        premium_bean_alias=premium_alias,
        est_premium_cost_usd=est_premium_cost,
        escalation_cost_cap_usd=state.settings.escalation_cost_cap_usd,
    )

    escalated = False
    draft_quality = False

    if decision is not None:
        decision_deadline = (
            _iso_deadline(state.settings.escalation_approval_timeout_seconds)
            if decision.outcome == "escalation_pending"
            else None
        )
        yield EscalationPendingEvent(
            request_id=request_id,
            reason=decision.reason,
            est_cost_usd=decision.est_cost_usd,
            premium_bean_alias=decision.premium_bean_alias,
            decision_deadline=decision_deadline,
        )

        if decision.outcome == "no_premium_available":
            draft_quality = True
        elif decision.outcome == "auto_escalate":
            yield EscalatingEvent(request_id=request_id, bean_alias=premium_bean.alias)
            async for item in _run_escalation(
                state,
                request_id,
                premium_bean,
                outbound_text,
                stream_order_fn,
                image_data_urls,
                history_result.messages or None,
            ):
                if isinstance(item, tuple) and item[0] == "__escalation_final__":
                    _, final_text, tokens_out, _spare = item
                else:
                    yield item
            escalated, draft_quality = True, False
        elif decision.outcome == "escalation_pending":
            assert decision.premium_bean_alias is not None  # guaranteed by decide_escalation for this outcome
            context = EscalationContext(
                request_id=request_id,
                session_id=session_id,
                reason=decision.reason,
                est_cost_usd=decision.est_cost_usd,
                premium_bean_alias=decision.premium_bean_alias,
                started_at=_iso_now(),
                decision_deadline=decision_deadline,
            )
            state.pending_escalation_context[request_id] = context

            approval = await _await_approval(
                state,
                request_id,
                wait_for_approval,
                cancel_event,
                state.settings.escalation_approval_timeout_seconds,
            )

            if approval == "cancelled":
                context.resolved, context.resolution = True, "cancelled"
                yield CancelledEvent(request_id=request_id, reason="client_cancel_request")
                return

            resolution = resolve_pending_escalation(approval)
            context.resolved = True
            if resolution.should_escalate:
                context.resolution = "approved"
                yield EscalatingEvent(request_id=request_id, bean_alias=premium_bean.alias)
                async for item in _run_escalation(
                    state,
                    request_id,
                    premium_bean,
                    outbound_text,
                    stream_order_fn,
                    image_data_urls,
                    history_result.messages or None,
                ):
                    if isinstance(item, tuple) and item[0] == "__escalation_final__":
                        _, final_text, tokens_out, _spare = item
                    else:
                        yield item
                escalated, draft_quality = True, False
            else:
                context.resolution = "timed_out" if _is_past_deadline(decision_deadline) else "declined"
                draft_quality = True

    latency_ms = int((time.monotonic() - started_at) * 1000)
    final_bean_alias = premium_bean.alias if escalated and premium_bean else route.bean_alias
    final_model_id = premium_bean.model_id if escalated and premium_bean else model_id
    cost_usd = 0.0 if (final_bean_alias and _is_free_tier(state, final_bean_alias)) else None

    yield CompleteEvent(
        request_id=request_id,
        bean_alias=final_bean_alias,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        escalated=escalated,
        draft_quality=draft_quality,
        pantry_sources=pantry_sources,
        history_turns=history_result.turns_included if remember_chat else None,
        history_tokens_est=history_result.tokens_est if remember_chat else None,
    )

    state.request_records[request_id] = RequestRecord(
        task_type=classification.task_type,
        bean_alias=final_bean_alias,
        raw_model_id=final_model_id,
        prompt=prompt,
        tokens_in=tokens_in,
        accumulated_text=final_text,
        tokens_out=tokens_out,
        finish_reason=finish_reason,
    )

    attachment_count = len(upload_records)
    attachment_tokens_est = _estimate_attachment_tokens(upload_records)

    logger.info(
        "request_id=%s remember_chat=%s history_turns=%d history_tokens_est=%d",
        request_id,
        remember_chat,
        history_result.turns_included,
        history_result.tokens_est,
    )

    state.ledger.append(
        LedgerRow(
            timestamp=_iso_now(),
            request_id=request_id,
            task_type=classification.task_type,
            bean_alias=final_bean_alias,
            raw_model_id=final_model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            escalated=escalated,
            escalation_approved=(
                None if decision is None or decision.outcome != "escalation_pending" else escalated
            ),
            attachment_count=attachment_count,
            attachment_tokens_est=attachment_tokens_est,
            remember_chat=remember_chat,
            history_turns=history_result.turns_included if remember_chat else 0,
            history_tokens_est=history_result.tokens_est if remember_chat else None,
        )
    )

    if session_id is not None and state.session_store is not None:
        state.session_store.add_message(
            session_id,
            request_id=request_id,
            role="user",
            content=prompt,
            attachments_json=_build_attachments_json(
                upload_records, attachment_max_stored_chars=state.settings.attachment_max_stored_chars
            ),
        )
        state.session_store.add_message(
            session_id,
            request_id=request_id,
            role="assistant",
            content=final_text,
            bean_alias=final_bean_alias,
            task_type=classification.task_type,
            complexity=classification.complexity,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            escalated=escalated,
            draft_quality=draft_quality,
        )
        state.session_store.set_title_if_default(session_id, prompt)


async def _run_escalation(
    state, request_id, premium_bean, prompt, stream_order_fn, image_data_urls=None, history_messages=None
):
    """Async generator: relays `generating` ticks from the premium re-run,
    then yields a ("__escalation_final__", text, tokens_out) sentinel.
    image_data_urls (Brew 38) is resent so an escalation re-run still
    includes any attached images. history_messages (Brew 46) is resent
    too - an escalation re-run is still the same conversational turn."""

    final_text = ""
    tokens_out = 0
    async for item in _consume_stream(
        stream_order_fn,
        premium_bean.model_id,
        prompt,
        settings=state.settings,
        request_id=request_id,
        image_data_urls=image_data_urls,
        history_messages=history_messages,
    ):
        if isinstance(item, tuple) and item[0] == "__final__":
            _, final_text, tokens_out, _finish_reason, _usage = item
        else:
            yield item
    yield ("__escalation_final__", final_text, tokens_out, None)


async def _await_approval(
    state: RouterState,
    request_id: str,
    wait_for_approval,
    cancel_event: asyncio.Event,
    timeout_seconds: float,
) -> str:
    """Returns "approved" | "declined" | "cancelled". A timeout resolves
    to "declined" - EVENT_CONTRACT.md's decision_deadline is how a UI
    tells an explicit decline apart from a timeout, not this return value.
    Also races the wait against cancel_event (Brew 40, docs/design/
    escalation-approval-ui-design.md Section 3.3) so POST /v1/cancel
    actually interrupts a pending approval instead of being silently
    ignored until the wait resolves some other way."""

    if wait_for_approval is not None:
        return await wait_for_approval(request_id)

    loop = asyncio.get_event_loop()
    future: "asyncio.Future[str]" = loop.create_future()
    state.pending_escalations[request_id] = future
    cancel_wait_task = asyncio.create_task(cancel_event.wait())
    try:
        done, pending = await asyncio.wait(
            {future, cancel_wait_task}, timeout=timeout_seconds, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        if cancel_wait_task in done:
            return "cancelled"
        if future in done:
            return future.result()
        return "declined"  # timed out - neither future nor cancel_wait_task completed
    finally:
        state.pending_escalations.pop(request_id, None)


def _retrieve_pantry_chunks(state: "RouterState", prompt: str) -> List[PantryChunk]:
    """Brew 41 (docs/design/memory-and-pantry-design.md Section 4.2):
    retrieves the top-k Pantry chunks for `prompt` from the FTS5 index at
    state.pantry_index_path. Degrades gracefully to an empty list - never
    raises - when the index hasn't been built yet or the prompt has no
    tokens an FTS5 MATCH query can use, so a request with `use_pantry=True`
    still completes normally."""

    if not state.pantry_index_path.is_file():
        return []
    fts_query = build_fts_query(prompt)
    if fts_query is None:
        return []
    with pantry_connect(state.pantry_index_path) as conn:
        return retrieve_chunks(conn, prompt, top_k=state.settings.pantry_top_k)


def _distinct_pantry_sources(pantry_chunks: List[PantryChunk]) -> Optional[List[str]]:
    """Distinct source paths in first-appearance (relevance) order - never
    an empty-but-claimed list (contract v1.4: None means nothing was
    actually injected)."""

    seen: set = set()
    sources: List[str] = []
    for chunk in pantry_chunks:
        if chunk.path not in seen:
            seen.add(chunk.path)
            sources.append(chunk.path)
    return sources or None


def _build_outbound_content(
    prompt: str,
    upload_records: List[UploadRecord],
    *,
    max_inline_text_chars: int,
    pantry_chunks: Optional[List[PantryChunk]] = None,
) -> Tuple[str, Optional[List[str]]]:
    """Builds the text actually sent to OpenRouter (prompt plus any
    extracted PDF/text attachment content, inlined with a clear delimiter -
    docs/design/attachments-design.md Section 5) and the list of base64
    `data:` URLs for image attachments. Images are read from disk and
    encoded at send time, not pre-encoded at upload time, to avoid keeping
    a redundant ~33%-larger base64 copy alongside the raw file. Returns
    `None` for image_data_urls when there are no images, so
    stream_order()'s plain-string content path (the common case) is used
    unchanged.

    Pantry chunks (Brew 41), when present, are prepended before the
    prompt with an uncertainty instruction (Constitution Article 6.4 -
    never fabricate citations) so the model treats them as background
    material to ground its answer in, not as the question itself."""

    text_parts: List[str] = []

    if pantry_chunks:
        text_parts.append(
            "The following Pantry excerpts may help answer the question "
            "below. Only rely on them if they actually cover the question - "
            "if they don't, say so plainly instead of guessing, and never "
            "claim a source supports something it doesn't."
        )
        for chunk in pantry_chunks:
            text_parts.append(
                f"--- Pantry source: {chunk.path} ---\n{chunk.text}\n--- end of {chunk.path} ---"
            )

    text_parts.append(prompt)
    image_data_urls: List[str] = []

    for record in upload_records:
        if record.kind == "image":
            encoded = base64.b64encode(record.file_path.read_bytes()).decode("ascii")
            image_data_urls.append(f"data:{record.content_type};base64,{encoded}")
        else:
            extracted = truncate_inline_text(
                record.extracted_text or "", max_inline_text_chars=max_inline_text_chars
            )
            text_parts.append(
                f"--- Attached file: {record.filename} ---\n{extracted}\n--- end of {record.filename} ---"
            )

    outbound_text = "\n\n".join(text_parts)
    return outbound_text, (image_data_urls or None)


def _build_attachments_json(
    upload_records: List[UploadRecord], *, attachment_max_stored_chars: int
) -> Optional[str]:
    """Brew 46 (docs/design/conversation-memory-design.md Section 3): what
    survives past this request into sessions.db, for a later turn to
    reattach. Images get metadata only (filename/kind/content_type) -
    never base64 bytes, since they are never resent on a later turn
    (router/app/history.py's IMAGE_HISTORY_NOTE covers that turn instead)
    - persisting bytes that will never be reused would be pure bloat.
    PDF/text attachments get their extracted text, capped independently
    of max_inline_text_chars (that setting bounds what's inlined into
    *this* request; this one bounds what's durably stored for *future*
    requests)."""

    if not upload_records:
        return None

    attachments = []
    for record in upload_records:
        entry = {"filename": record.filename, "kind": record.kind, "content_type": record.content_type}
        if record.kind != "image":
            entry["extracted_text"] = truncate_inline_text(
                record.extracted_text or "", max_inline_text_chars=attachment_max_stored_chars
            )
        attachments.append(entry)
    return json.dumps(attachments)


def _estimate_attachment_tokens(upload_records: List[UploadRecord]) -> Optional[int]:
    """Coffee Ledger discipline never invents a number it cannot support
    (docs/design/attachments-design.md Section 8): zero attachments is a
    known zero, an image's token cost is provider/size-dependent and not
    reliably computable client-side (-> None/"unknown"), and PDF/text
    attachments get a rough len(extracted_text) // 4 estimate."""

    if not upload_records:
        return 0
    if any(record.kind == "image" for record in upload_records):
        return None
    return sum(len(record.extracted_text or "") // 4 for record in upload_records)


def _is_free_tier(state: RouterState, bean_alias: str) -> bool:
    bean = state.bean_registry.by_alias(bean_alias)
    return bean.price_per_1k_input_usd == 0.0 and bean.price_per_1k_output_usd == 0.0


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_deadline(seconds_from_now: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds_from_now)).isoformat()


def _is_past_deadline(deadline_iso: str) -> bool:
    return datetime.now(timezone.utc) >= datetime.fromisoformat(deadline_iso)


async def sse_stream(events: AsyncIterator[BaseEvent]) -> AsyncIterator[bytes]:
    try:
        async for event in events:
            yield event.to_sse().encode("utf-8")
    except asyncio.CancelledError:
        raise


async def _run_order_and_publish(
    state: RouterState,
    queue: "asyncio.Queue[Optional[BaseEvent]]",
    **run_order_kwargs: Any,
) -> None:
    """Runs run_order() to completion, publishing each event into `queue`
    instead of yielding directly to an HTTP response. This decouples the
    whole order - including a multi-minute escalation_pending pause -
    from any one /v1/order connection's lifetime (Brew 40, docs/design/
    escalation-approval-ui-design.md Section 3.1): if the client
    disconnects, only the draining side (sse_stream_from_queue) stops;
    this producer keeps running, still writes the Ledger/SessionStore
    normally, and a still-open approval wait is unaffected. Always queues
    a final `None` sentinel, even on an unexpected exception, so the
    draining side never hangs forever waiting for one."""

    try:
        async for event in run_order(state, **run_order_kwargs):
            await queue.put(event)
    finally:
        await queue.put(None)


async def sse_stream_from_queue(
    queue: "asyncio.Queue[Optional[BaseEvent]]",
    *,
    request_id: str,
    heartbeat_interval_seconds: float,
) -> AsyncIterator[bytes]:
    """Drains `queue` (fed by _run_order_and_publish) as SSE frames,
    sending a `heartbeat` frame (contract v1.3) whenever nothing real has
    arrived for heartbeat_interval_seconds - long idle gaps happen mainly
    during an escalation_pending pause. Stops on the `None` sentinel."""

    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval_seconds)
        except asyncio.TimeoutError:
            yield HeartbeatEvent(request_id=request_id).to_sse().encode("utf-8")
            continue
        if event is None:
            return
        yield event.to_sse().encode("utf-8")


# --- FastAPI wiring -------------------------------------------------------


class OrderRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None
    bean_alias_override: Optional[str] = None
    # Brew 38: attachment_ids are resolved against state.uploads at order
    # time. request_id is client-generated the moment a file is first
    # attached (before this order exists), so the order runs under the
    # same id its attachments were stored under - see
    # docs/design/attachments-design.md Section 7, Decision 2. Text-only
    # messages leave this None and the server generates one as before.
    attachment_ids: List[str] = []
    request_id: Optional[str] = None
    # Brew 41 (docs/design/memory-and-pantry-design.md Section 4.2): a
    # per-request toggle, not a session-wide or global setting - the order
    # box asks for Pantry context explicitly on the requests that need it.
    use_pantry: bool = False


class UploadResponse(BaseModel):
    attachment_id: str
    filename: str
    content_type: str
    kind: str
    size_bytes: int
    extracted_text_chars: Optional[int] = None


class RetryRequest(BaseModel):
    request_id: str


class ApproveEscalationRequest(BaseModel):
    request_id: str
    approve: bool


class RateRequest(BaseModel):
    request_id: str
    rating: str  # "good" | "needed_fixing" | "failed"


class CancelRequest(BaseModel):
    request_id: str


class CreateSessionRequest(BaseModel):
    project: str = DEFAULT_PROJECT
    # Brew 43 (docs/design/auth-projects-chat-management-design.md
    # Section 4.1): the real projects table's id. None means "default"
    # (no project) - the old free-form `project` string above is kept
    # only for the pre-Brew-43 SessionStore call shape, never read by
    # the new project system.
    project_id: Optional[int] = None


class SetPreferenceRequest(BaseModel):
    key: str
    value: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateProjectRequest(BaseModel):
    name: str


class RenameProjectRequest(BaseModel):
    name: str


class UpdateSessionRequest(BaseModel):
    """PATCH /v1/sessions/{id} - extended in Brew 46 to also carry the
    remember_chat toggle (docs/design/conversation-memory-design.md
    Section 1), rather than adding a second endpoint. At least one field
    must be given; both may be given together."""

    title: Optional[str] = None
    remember_chat: Optional[bool] = None


VALID_RATINGS = {"good", "needed_fixing", "failed"}


def create_app(state: Optional[RouterState] = None) -> FastAPI:
    app = FastAPI(title="Coffee Core Router")

    if state is None:
        config_paths = load_router_config_paths()
        assert_no_key_like_strings(config_paths)
        bean_registry = BeanRegistry.from_yaml()
        routing_policy = RoutingPolicy.from_yaml(bean_registry=bean_registry)
        settings = Settings.from_yaml()
        ledger = RouterLedger()
        session_store = SessionStore()
        preference_store = PreferenceStore()
        state = RouterState(
            bean_registry=bean_registry,
            routing_policy=routing_policy,
            settings=settings,
            ledger=ledger,
            session_store=session_store,
            preference_store=preference_store,
        )

    app.state.coffee = state

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.post("/v1/login")
    async def login_endpoint(body: LoginRequest):
        """Brew 43 (docs/design/auth-projects-chat-management-design.md
        Section 3.1). The only unauthenticated /v1/* endpoint - every
        other endpoint requires Depends(get_current_user). Never reveals
        whether a wrong username or a wrong password caused the
        failure."""

        state = app.state.coffee
        try:
            token, user = auth_login(state.session_store, body.username, body.password)
        except InvalidCredentialsError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        return {
            "token": token,
            "user": {"id": user.id, "username": user.username, "display_name": user.display_name},
        }

    @app.post("/v1/logout")
    async def logout_endpoint(
        authorization: Optional[str] = Header(default=None),
        current_user: UserRecord = Depends(get_current_user),
    ):
        state = app.state.coffee
        # get_current_user already validated this header is well-formed
        # and the token is live - re-parsing here just to know which
        # token row to delete.
        token = authorization[len("Bearer "):]
        state.session_store.delete_token(token)
        return {"status": "logged_out"}

    @app.post("/v1/order")
    async def order(body: OrderRequest, current_user: UserRecord = Depends(get_current_user)):
        state = app.state.coffee
        store = state.session_store
        # Brew 46: remember_chat is resolved here, server-side, from the
        # session row itself - OrderRequest has no remember_chat field, so
        # it can never drift between what the UI shows and what actually
        # gets sent/billed (docs/design/conversation-memory-design.md
        # Section 1). This single get_session() call also replaces the
        # old session_exists() 404 check.
        remember_chat = False
        if body.session_id is not None:
            if store is None:
                raise HTTPException(status_code=404, detail="Unknown session_id.")
            session_record = store.get_session(body.session_id, user_id=current_user.id)
            if session_record is None:
                raise HTTPException(status_code=404, detail="Unknown session_id.")
            remember_chat = session_record.remember_chat
        if body.request_id is not None and body.request_id in state.cancel_flags:
            raise HTTPException(
                status_code=409, detail=f"request_id {body.request_id!r} is already in flight."
            )

        # request_id is chosen here, not inside run_order(), so
        # sse_stream_from_queue can label heartbeat frames correctly even
        # before the first real event (OrderReceivedEvent) is queued.
        request_id = body.request_id or str(uuid.uuid4())
        queue: "asyncio.Queue[Optional[BaseEvent]]" = asyncio.Queue()

        task = asyncio.create_task(
            _run_order_and_publish(
                state,
                queue,
                prompt=body.prompt,
                attachment_ids=body.attachment_ids or None,
                request_id=request_id,
                session_id=body.session_id,
                bean_alias_override=body.bean_alias_override,
                use_pantry=body.use_pantry,
                remember_chat=remember_chat,
                stream_order_fn=state.stream_order_fn,
            )
        )
        # Held on RouterState so asyncio never garbage-collects an
        # in-flight task (see https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task's
        # own warning about this) - discarded automatically once done.
        state.background_tasks.add(task)
        task.add_done_callback(state.background_tasks.discard)

        return StreamingResponse(
            sse_stream_from_queue(
                queue,
                request_id=request_id,
                heartbeat_interval_seconds=state.settings.sse_heartbeat_interval_seconds,
            ),
            media_type="text/event-stream",
        )

    @app.post("/v1/upload", response_model=UploadResponse)
    async def upload(
        request_id: str = Form(...),
        file: UploadFile = File(...),
        current_user: UserRecord = Depends(get_current_user),
    ):
        state = app.state.coffee
        sweep_stale_uploads(uploads_root=state.uploads_root, ttl_seconds=state.settings.upload_ttl_seconds)

        file_bytes = await file.read()
        content_type = file.content_type or ""

        try:
            kind = validate_upload(
                file.filename,
                content_type,
                len(file_bytes),
                max_upload_size_bytes=state.settings.max_upload_size_bytes,
            )
        except UploadValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        extracted_text: Optional[str] = None
        if kind == "pdf":
            try:
                extracted_text = extract_pdf_text(
                    file_bytes, min_extracted_chars=state.settings.pdf_min_extracted_chars
                )
            except PdfExtractionError as exc:
                raise HTTPException(status_code=422, detail=str(exc))
        elif kind == "text":
            extracted_text = extract_text_file(file_bytes)

        attachment_id = new_attachment_id()
        file_path = save_upload(
            request_id, attachment_id, file.filename, file_bytes, uploads_root=state.uploads_root
        )

        record = UploadRecord(
            attachment_id=attachment_id,
            request_id=request_id,
            filename=file.filename,
            content_type=content_type,
            kind=kind,
            size_bytes=len(file_bytes),
            file_path=file_path,
            extracted_text=extracted_text,
        )
        state.uploads[attachment_id] = record

        return UploadResponse(
            attachment_id=attachment_id,
            filename=file.filename,
            content_type=content_type,
            kind=kind,
            size_bytes=len(file_bytes),
            extracted_text_chars=len(extracted_text) if extracted_text is not None else None,
        )

    @app.post("/v1/retry")
    async def retry(body: RetryRequest, current_user: UserRecord = Depends(get_current_user)):
        record = app.state.coffee.request_records.get(body.request_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Unknown request_id.")

        async def _retry_events() -> AsyncIterator[BaseEvent]:
            generation = GenerationResult(
                text=record.accumulated_text,
                tokens_out=record.tokens_out,
                finish_reason=record.finish_reason,
                caller_reported_failure=True,
            )
            failure = check_for_failure(
                generation,
                truncation_min_expected_tokens=app.state.coffee.settings.truncation_min_expected_tokens,
                refusal_keywords=app.state.coffee.settings.refusal_keywords,
            )
            premium_bean = app.state.coffee.bean_registry.by_role("premium")
            premium_alias = premium_bean.alias if premium_bean and premium_bean.is_available else None
            decision = decide_escalation(
                failure,
                premium_bean_alias=premium_alias,
                est_premium_cost_usd=0.0 if premium_alias else None,
                escalation_cost_cap_usd=app.state.coffee.settings.escalation_cost_cap_usd,
            )
            if decision is not None:
                yield EscalationPendingEvent(
                    request_id=body.request_id,
                    reason=decision.reason,
                    est_cost_usd=decision.est_cost_usd,
                    premium_bean_alias=decision.premium_bean_alias,
                )

        return StreamingResponse(sse_stream(_retry_events()), media_type="text/event-stream")

    @app.post("/v1/approve_escalation")
    async def approve_escalation(
        body: ApproveEscalationRequest, current_user: UserRecord = Depends(get_current_user)
    ):
        state = app.state.coffee
        context = state.pending_escalation_context.get(body.request_id)
        if context is None:
            raise HTTPException(status_code=404, detail="No pending escalation for this request_id.")

        if context.resolved:
            return {
                "request_id": body.request_id,
                "status": "already_resolved",
                "resolution": context.resolution,
            }

        future = state.pending_escalations.get(body.request_id)
        if future is None or future.done():
            # The wait already resolved (e.g. a near-simultaneous duplicate
            # click) but _run_order_body hasn't updated context.resolved
            # yet - treat it the same as already_resolved rather than
            # silently pretending this call changed anything.
            return {
                "request_id": body.request_id,
                "status": "already_resolved",
                "resolution": context.resolution,
            }

        future.set_result("approved" if body.approve else "declined")
        return {"request_id": body.request_id, "approve": body.approve, "status": "acknowledged"}

    @app.get("/v1/sessions/{session_id}/pending_escalation")
    async def get_pending_escalation(
        session_id: str, current_user: UserRecord = Depends(get_current_user)
    ):
        state = app.state.coffee
        store = state.session_store
        if store is not None and not store.session_exists(session_id, user_id=current_user.id):
            raise HTTPException(status_code=404, detail="Unknown session_id.")

        for context in state.pending_escalation_context.values():
            if context.session_id == session_id and not context.resolved:
                return {
                    "request_id": context.request_id,
                    "reason": context.reason,
                    "est_cost_usd": context.est_cost_usd,
                    "premium_bean_alias": context.premium_bean_alias,
                    "started_at": context.started_at,
                    "decision_deadline": context.decision_deadline,
                }
        raise HTTPException(status_code=404, detail="No pending escalation for this session_id.")

    @app.post("/v1/cancel")
    async def cancel(body: CancelRequest, current_user: UserRecord = Depends(get_current_user)):
        cancel_event = app.state.coffee.cancel_flags.get(body.request_id)
        if cancel_event is None:
            raise HTTPException(
                status_code=404, detail="No in-flight request for this request_id."
            )
        cancel_event.set()
        return {"request_id": body.request_id, "status": "cancel_requested"}

    @app.post("/v1/rate")
    async def rate(body: RateRequest, current_user: UserRecord = Depends(get_current_user)):
        if body.rating not in VALID_RATINGS:
            raise HTTPException(
                status_code=422,
                detail=f"rating must be one of {sorted(VALID_RATINGS)}.",
            )
        ledger_updated = app.state.coffee.ledger.update_rating(body.request_id, body.rating)
        store = app.state.coffee.session_store
        session_updated = (
            store.update_message_rating(body.request_id, body.rating) if store is not None else False
        )
        if not ledger_updated and not session_updated:
            raise HTTPException(status_code=404, detail="Unknown request_id.")
        return {"request_id": body.request_id, "rating": body.rating, "status": "recorded"}

    @app.get("/v1/beans")
    async def beans(current_user: UserRecord = Depends(get_current_user)):
        return [
            {"alias": bean.alias, "role": bean.role, "available": bean.is_available}
            for bean in app.state.coffee.bean_registry.all_beans()
        ]

    @app.get("/v1/pantry/file")
    async def pantry_file(path: str, current_user: UserRecord = Depends(get_current_user)):
        """Serves raw file content for the citation chip file viewer
        (docs/design/memory-and-pantry-design.md Section 4.3). Read-only,
        scoped to knowledge/ only via resolve_pantry_file_path() - never
        serves anything outside that directory, regardless of `..` or
        absolute-path tricks in `path`."""

        resolved = resolve_pantry_file_path(path)
        if resolved is None:
            raise HTTPException(status_code=404, detail="No such Pantry file.")
        try:
            content = resolved.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            raise HTTPException(status_code=404, detail="No such Pantry file.")
        return {"path": path, "content": content}

    @app.get("/v1/preferences")
    async def get_preferences(current_user: UserRecord = Depends(get_current_user)):
        store = app.state.coffee.preference_store
        if store is None:
            raise HTTPException(status_code=503, detail="Preference storage is not configured.")
        return store.get_all()

    @app.post("/v1/preferences")
    async def set_preference(
        body: SetPreferenceRequest, current_user: UserRecord = Depends(get_current_user)
    ):
        store = app.state.coffee.preference_store
        if store is None:
            raise HTTPException(status_code=503, detail="Preference storage is not configured.")
        store.set(body.key, body.value)
        return {"key": body.key, "value": body.value, "status": "saved"}

    @app.post("/v1/sessions")
    async def create_session(
        body: CreateSessionRequest, current_user: UserRecord = Depends(get_current_user)
    ):
        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        if body.project_id is not None and store.get_project(body.project_id, user_id=current_user.id) is None:
            raise HTTPException(status_code=404, detail="Unknown project_id.")
        session_id = store.create_session(body.project, user_id=current_user.id, project_id=body.project_id)
        return {
            "id": session_id,
            "project": body.project,
            "project_id": body.project_id,
            "remember_chat": True,
        }

    @app.get("/v1/sessions")
    async def list_sessions(
        project_id: Optional[str] = None, current_user: UserRecord = Depends(get_current_user)
    ):
        """Brew 43 (docs/design/auth-projects-chat-management-design.md
        Section 4.1): project_id is a query string, not an int, so it can
        carry the literal sentinel "all" ("All chats") alongside a real
        numeric id; omitted or "default" means project_id IS NULL."""

        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")

        all_projects = project_id == "all"
        real_project_id: Optional[int] = None
        if not all_projects and project_id not in (None, "default"):
            try:
                real_project_id = int(project_id)
            except ValueError:
                raise HTTPException(status_code=422, detail="project_id must be an integer, 'default', or 'all'.")

        return [
            {
                "id": s.id,
                "project": s.project,
                "project_id": s.project_id,
                "title": s.title,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "cost_total_usd": s.cost_total_usd,
                "remember_chat": s.remember_chat,
            }
            for s in store.list_sessions(
                user_id=current_user.id, project_id=real_project_id, all_projects=all_projects
            )
        ]

    @app.get("/v1/sessions/{session_id}/messages")
    async def session_messages(
        session_id: str, current_user: UserRecord = Depends(get_current_user)
    ):
        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        if not store.session_exists(session_id, user_id=current_user.id):
            raise HTTPException(status_code=404, detail="Unknown session_id.")
        return [
            {
                "id": m.id,
                "request_id": m.request_id,
                "role": m.role,
                "content": m.content,
                "bean_alias": m.bean_alias,
                "task_type": m.task_type,
                "complexity": m.complexity,
                "cost_usd": m.cost_usd,
                "latency_ms": m.latency_ms,
                "escalated": m.escalated,
                "draft_quality": m.draft_quality,
                "rating": m.rating,
                "created_at": m.created_at,
                "has_attachments": m.has_attachments,
            }
            for m in store.get_messages(session_id)
        ]

    @app.patch("/v1/sessions/{session_id}")
    async def update_session(
        session_id: str,
        body: UpdateSessionRequest,
        current_user: UserRecord = Depends(get_current_user),
    ):
        """Brew 43 (docs/design/auth-projects-chat-management-design.md
        Section 5.1): an explicit human rename - always overwrites the
        title, unlike set_title_if_default()'s first-message auto-title,
        which deliberately never does. Extended in Brew 46
        (docs/design/conversation-memory-design.md Section 1) to also
        carry the remember_chat toggle - flipping it never deletes
        anything, it only changes whether the *next* request assembles
        history."""

        if body.title is None and body.remember_chat is None:
            raise HTTPException(status_code=422, detail="Provide title and/or remember_chat.")

        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")

        response: Dict[str, Any] = {"id": session_id}
        if body.title is not None:
            if not store.rename_session(session_id, body.title, user_id=current_user.id):
                raise HTTPException(status_code=404, detail="Unknown session_id.")
            response["title"] = body.title[:TITLE_MAX_CHARS]
        if body.remember_chat is not None:
            if not store.set_remember_chat(session_id, body.remember_chat, user_id=current_user.id):
                raise HTTPException(status_code=404, detail="Unknown session_id.")
            response["remember_chat"] = body.remember_chat
        return response

    @app.delete("/v1/sessions/{session_id}")
    async def delete_session(session_id: str, current_user: UserRecord = Depends(get_current_user)):
        """Soft delete (Section 5.1) - sets deleted_at, excluded from
        every existing query rather than physically removed."""

        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        if not store.soft_delete_session(session_id, user_id=current_user.id):
            raise HTTPException(status_code=404, detail="Unknown session_id.")
        return {"id": session_id, "status": "deleted"}

    @app.post("/v1/sessions/{session_id}/memory_proposal")
    async def create_memory_proposal(
        session_id: str, current_user: UserRecord = Depends(get_current_user)
    ):
        """Brew 41 (docs/design/memory-and-pantry-design.md Section 3.1):
        a plain blocking request/response, not SSE - one bounded model
        call, no multi-minute human-wait phase to justify Brew 40's
        background-task machinery. Never writes memory itself - only
        POST .../approve does that, and only after re-checking both
        guardrails."""

        state = app.state.coffee
        store = state.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        if not store.session_exists(session_id, user_id=current_user.id):
            raise HTTPException(status_code=404, detail="Unknown session_id.")

        try:
            proposal = await generate_memory_proposal(
                session_id=session_id,
                session_store=store,
                bean_registry=state.bean_registry,
                bean_alias=state.settings.memory_proposal_bean_alias,
                max_transcript_chars=state.settings.memory_proposal_max_transcript_chars,
                stream_order_fn=state.stream_order_fn,
                repo_root=state.memory_proposal_repo_root,
            )
        except (MemoryProposalError, MemoryProposalGuardrailError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        state.memory_proposals[proposal.proposal_id] = proposal
        return {
            "proposal_id": proposal.proposal_id,
            "files": [
                {"path": f.path, "diff": f.diff, "new_content": f.new_content}
                for f in proposal.files
            ],
        }

    @app.post("/v1/memory_proposals/{proposal_id}/approve")
    async def approve_memory_proposal_endpoint(
        proposal_id: str, current_user: UserRecord = Depends(get_current_user)
    ):
        state = app.state.coffee
        proposal = state.memory_proposals.get(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Unknown proposal_id.")

        try:
            approve_memory_proposal(proposal, repo_root=state.memory_proposal_repo_root)
        except MemoryProposalGuardrailError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        state.ledger.append(
            LedgerRow(
                timestamp=_iso_now(),
                request_id=proposal.proposal_id,
                task_type="memory",
                bean_alias=proposal.bean_alias,
                raw_model_id=proposal.model_id or "unknown",
                tokens_in=proposal.tokens_in,
                tokens_out=proposal.tokens_out,
                cost_usd=proposal.cost_usd,
                latency_ms=proposal.latency_ms,
                escalated=False,
                escalation_approved=None,
            )
        )
        state.memory_proposals.pop(proposal_id, None)
        return {"proposal_id": proposal_id, "status": "approved"}

    @app.post("/v1/memory_proposals/{proposal_id}/discard")
    async def discard_memory_proposal_endpoint(
        proposal_id: str, current_user: UserRecord = Depends(get_current_user)
    ):
        state = app.state.coffee
        if proposal_id not in state.memory_proposals:
            raise HTTPException(status_code=404, detail="Unknown proposal_id.")
        state.memory_proposals.pop(proposal_id, None)
        return {"proposal_id": proposal_id, "status": "discarded"}

    @app.post("/v1/policy/rebuild_preview")
    async def policy_rebuild_preview(current_user: UserRecord = Depends(get_current_user)):
        """Brew 42 (docs/design/learning-loop-and-release-design.md
        Section 3.2): computes a proposed router/config/routing_policy.yaml
        rebuild (Roastery Cup Test evidence blended with real accumulated
        ratings once a (task_type, Bean) pair clears
        settings.min_rating_sample_size) and returns a diff against the
        current on-disk file. Never writes anything - only
        POST .../rebuild_apply/{id} does that."""

        state = app.state.coffee
        tasting_notes_text = state.tasting_notes_path.read_text(encoding="utf-8")
        beans_config = {
            "beans": [
                {"alias": bean.alias, "role": bean.role, "model_id": bean.model_id}
                for bean in state.bean_registry.all_beans()
            ]
        }
        ledger_rows = state.ledger.read_all_rows()

        evidence = parse_tasting_notes(tasting_notes_text)
        policy = build_policy(
            evidence,
            beans_config,
            ledger_rows=ledger_rows,
            min_rating_sample_size=state.settings.min_rating_sample_size,
            roastery_weight=state.settings.policy_roastery_weight,
            escalation_rate_flag_threshold=state.settings.escalation_rate_flag_threshold,
        )
        new_policy_yaml = render_policy_yaml(policy)
        current_policy_yaml = (
            state.routing_policy_path.read_text(encoding="utf-8")
            if state.routing_policy_path.is_file()
            else ""
        )
        diff = "".join(
            difflib.unified_diff(
                current_policy_yaml.splitlines(keepends=True),
                new_policy_yaml.splitlines(keepends=True),
                fromfile=str(state.routing_policy_path),
                tofile=f"{state.routing_policy_path} (proposed)",
            )
        )

        proposal = PolicyRebuildProposal(
            proposal_id=str(uuid.uuid4()),
            new_policy_yaml=new_policy_yaml,
            diff=diff,
            escalation_candidates=policy["escalation_candidates"],
            based_on_policy_yaml=current_policy_yaml,
        )
        state.policy_rebuild_proposals[proposal.proposal_id] = proposal
        return {
            "proposal_id": proposal.proposal_id,
            "diff": proposal.diff,
            "escalation_candidates": proposal.escalation_candidates,
        }

    @app.post("/v1/policy/rebuild_apply/{proposal_id}")
    async def policy_rebuild_apply(
        proposal_id: str, current_user: UserRecord = Depends(get_current_user)
    ):
        state = app.state.coffee
        proposal = state.policy_rebuild_proposals.get(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Unknown proposal_id.")

        current_policy_yaml = (
            state.routing_policy_path.read_text(encoding="utf-8")
            if state.routing_policy_path.is_file()
            else ""
        )
        if current_policy_yaml != proposal.based_on_policy_yaml:
            state.policy_rebuild_proposals.pop(proposal_id, None)
            raise HTTPException(
                status_code=422,
                detail=(
                    "routing_policy.yaml changed on disk since this proposal was "
                    "generated. Discard this proposal and request a fresh preview."
                ),
            )

        state.routing_policy_path.write_text(proposal.new_policy_yaml, encoding="utf-8")
        # Hot-swap - no router restart needed (RouterState is a plain
        # mutable dataclass, same pattern every other endpoint already
        # relies on to mutate state in place).
        state.routing_policy = RoutingPolicy.from_yaml(
            state.routing_policy_path, bean_registry=state.bean_registry
        )
        state.policy_rebuild_proposals.pop(proposal_id, None)
        return {"proposal_id": proposal_id, "status": "applied"}

    @app.post("/v1/policy/rebuild_discard/{proposal_id}")
    async def policy_rebuild_discard(
        proposal_id: str, current_user: UserRecord = Depends(get_current_user)
    ):
        state = app.state.coffee
        if proposal_id not in state.policy_rebuild_proposals:
            raise HTTPException(status_code=404, detail="Unknown proposal_id.")
        state.policy_rebuild_proposals.pop(proposal_id, None)
        return {"proposal_id": proposal_id, "status": "discarded"}

    @app.post("/v1/projects")
    async def create_project(
        body: CreateProjectRequest, current_user: UserRecord = Depends(get_current_user)
    ):
        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        project = store.create_project(current_user.id, body.name)
        return {
            "id": project.id,
            "name": project.name,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        }

    @app.get("/v1/projects")
    async def list_projects(current_user: UserRecord = Depends(get_current_user)):
        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        return [
            {"id": p.id, "name": p.name, "created_at": p.created_at, "updated_at": p.updated_at}
            for p in store.list_projects(current_user.id)
        ]

    @app.patch("/v1/projects/{project_id}")
    async def rename_project(
        project_id: int,
        body: RenameProjectRequest,
        current_user: UserRecord = Depends(get_current_user),
    ):
        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        if not store.rename_project(project_id, body.name, user_id=current_user.id):
            raise HTTPException(status_code=404, detail="Unknown project_id.")
        return {"id": project_id, "name": body.name}

    @app.delete("/v1/projects/{project_id}")
    async def delete_project(
        project_id: int, current_user: UserRecord = Depends(get_current_user)
    ):
        """Deletes the project and moves its sessions to project_id NULL
        ("default") - never deletes the sessions themselves (docs/design/
        auth-projects-chat-management-design.md Section 4.1)."""

        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        if not store.delete_project(project_id, user_id=current_user.id):
            raise HTTPException(status_code=404, detail="Unknown project_id.")
        return {"id": project_id, "status": "deleted"}

    return app


app = create_app()
