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
import hashlib
import json
import logging
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from router.app.aliases import AliasError, Bean, BeanRegistry, assert_active_beans_priced
from router.app.auth import InvalidCredentialsError, get_current_user, login as auth_login
from router.app.classifier import Attachment as ClassifierAttachment
from router.app.classifier import classify
from router.app.config import Settings, assert_no_key_like_strings, load_router_config_paths
from router.app.escalation import (
    FailureCheckResult,
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
    WebSource,
)
from router.app.ledger import LedgerRow, RouterLedger, estimate_web_search_component_usd, resolve_cost
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
from router.app.routing import (
    DEFAULT_ROUTING_POLICY_PATH,
    NoToolCallingBeanError,
    NoVisionBeanError,
    RoutingError,
    RoutingPolicy,
    estimate_cost_usd,
)
from router.app.sessions import (
    TITLE_MAX_CHARS,
    ProjectRecord,
    SessionStore,
    UserRecord,
    UsernameTakenError,
)
from router.app.system_prompt import build_system_message
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


# CORS_ALLOWED_ORIGINS: comma-separated list of allowed origins, e.g.
# "http://localhost:3000,http://192.168.1.42:3000" for LAN access from
# another device. An environment variable rather than a settings.yaml
# field, matching FORCE_ESCALATION_ENV_VAR/OPENROUTER_API_KEY's existing
# convention for deployment-shape config that shouldn't live in a
# committed file. Defaults to today's single-origin localhost allowlist
# when unset, so nothing changes for an existing local setup.
CORS_ALLOWED_ORIGINS_ENV_VAR = "CORS_ALLOWED_ORIGINS"
DEFAULT_CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]


def _cors_allowed_origins() -> List[str]:
    raw = os.environ.get(CORS_ALLOWED_ORIGINS_ENV_VAR)
    if not raw:
        return DEFAULT_CORS_ALLOWED_ORIGINS
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or DEFAULT_CORS_ALLOWED_ORIGINS


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
    # Spend-cap Brew: per-user asyncio.Lock, created lazily, held across
    # each check_spend_cap() call's read-then-decide critical section -
    # closes the concurrent-request-race edge case within this router's
    # single OS process (see sessions.py's own "single-user means single
    # process" precedent). Same in-memory, no-TTL-sweep pattern as
    # cancel_flags/pending_escalations.
    spend_cap_locks: Dict[int, "asyncio.Lock"] = field(default_factory=dict)
    # Spend-cap Brew: per-user recent request timestamps (time.monotonic()),
    # pruned to a rolling 60s window on each check_rate_limit() call - a
    # sanity limit against a runaway loop/tight retry cycle, tracked and
    # enforced independently of the cost caps above.
    rate_limit_hits: Dict[int, List[float]] = field(default_factory=dict)


@dataclass(frozen=True)
class SpendCapDenial:
    """What check_spend_cap() returns when a request must be refused.
    cap_type is "per_user", "global", or "unknown_estimate" (the estimate
    itself was unavailable - see check_spend_cap()'s docstring) - kept
    distinct so a log line/future UI can always say which one fired."""

    cap_type: str
    today_spent: float
    cap: float
    reset_at_iso: str


def _utc_midnight_reset_iso() -> str:
    """The next UTC midnight, as an ISO string - what every cap resets
    at, and what GET /v1/usage reports as reset_at."""

    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).date()
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc).isoformat()


def _effective_daily_cap_usd(state: RouterState, user_id: int) -> float:
    """The per-user cap that actually applies: the users.daily_cost_cap_usd
    override when set, else settings.per_user_daily_cost_cap_usd."""

    if state.session_store is not None:
        user = state.session_store.get_user_by_id(user_id)
        if user is not None and user.daily_cost_cap_usd is not None:
            return user.daily_cost_cap_usd
    return state.settings.per_user_daily_cost_cap_usd


async def check_spend_cap(
    state: RouterState, user_id: Optional[int], estimated_cost_usd: Optional[float]
) -> Optional[SpendCapDenial]:
    """Pre-call admission check for every real OpenRouter-spending call
    site (spend-cap Brew) - /v1/order's draft and escalation re-run,
    /v1/chat/completions' draft and escalation re-run, memory proposal
    generation. Returns None to allow the call, or a SpendCapDenial
    naming which cap would be exceeded.

    Held under a per-user asyncio.Lock across the whole
    read-today's-spend -> compare -> decide critical section, so two
    concurrent requests from the same user cannot both be admitted against
    the same stale snapshot - this router is single-process by design
    (sessions.py), so an in-process lock closes this race completely
    rather than merely narrowing it.

    A genuinely unknown estimate (estimated_cost_usd is None) is treated
    as maximally risky and refused (cap_type="unknown_estimate") - should
    be impossible for an active Bean given
    router.app.aliases.assert_active_beans_priced(), but this function
    never assumes that holds; an unpriced/unestimable request must never
    be let through as if it were free.

    Enforcement is skipped (returns None) whenever session_store or
    user_id is missing - every real HTTP endpoint's
    Depends(get_current_user) structurally guarantees a real user_id
    reaches here, so this is never reachable on the real request path;
    it only fires for tests that exercise orchestration functions
    directly with a real SessionStore fixture (for unrelated reasons -
    escalation, shadow mode, etc.) but without wiring a real user_id.
    A hard assertion here was considered and rejected: it would fail
    loudly for exactly those legitimate, unrelated tests, not just for a
    genuine bug - the real safety guarantee already lives at the
    endpoint layer, not here."""

    if state.session_store is None or user_id is None:
        return None

    lock = state.spend_cap_locks.setdefault(user_id, asyncio.Lock())
    async with lock:
        reset_at_iso = _utc_midnight_reset_iso()

        if estimated_cost_usd is None:
            per_user_spent, _ = state.ledger.today_spend_usd(user_id=user_id)
            return SpendCapDenial("unknown_estimate", per_user_spent, _effective_daily_cap_usd(state, user_id), reset_at_iso)

        per_user_cap = _effective_daily_cap_usd(state, user_id)
        per_user_spent, _ = state.ledger.today_spend_usd(user_id=user_id)
        if per_user_spent + estimated_cost_usd > per_user_cap:
            return SpendCapDenial("per_user", per_user_spent, per_user_cap, reset_at_iso)

        global_cap = state.settings.global_daily_cost_cap_usd
        global_spent, _ = state.ledger.today_spend_usd(user_id=None)
        if global_spent + estimated_cost_usd > global_cap:
            return SpendCapDenial("global", global_spent, global_cap, reset_at_iso)

        return None


async def check_rate_limit(state: RouterState, user_id: Optional[int]) -> bool:
    """Returns True if the request is allowed, False if the user is over
    settings.per_user_requests_per_minute in the trailing 60 seconds - a
    sanity limit against a runaway loop or a tight client retry cycle,
    not a cost control, tracked and enforced independently of
    check_spend_cap(). Same graceful-degradation-when-session_store-or-
    user_id-is-missing precedent as check_spend_cap() - see that
    function's docstring for why a hard assertion here was rejected."""

    if state.session_store is None or user_id is None:
        return True

    now = time.monotonic()
    window_start = now - 60.0
    hits = state.rate_limit_hits.setdefault(user_id, [])
    hits[:] = [hit for hit in hits if hit >= window_start]
    if len(hits) >= state.settings.per_user_requests_per_minute:
        return False
    hits.append(now)
    return True


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
    tools: Optional[List[Dict[str, Any]]] = None,
) -> AsyncIterator[Any]:
    """Wrap a raw OpenRouter stream, emitting periodic `generating` ticks
    (with the incremental text_delta since the last tick - contract v1.1)
    per settings.generating_tick_tokens / generating_tick_seconds, and
    yield a final ("__final__", text, tokens_out, finish_reason, usage,
    annotations) sentinel tuple once the stream ends, or a
    ("__cancelled__",) sentinel if cancel_event is set mid-stream.
    image_data_urls (Brew 38), history_messages (Brew 46), and tools (web
    search cost optimization Brew - carries the openrouter:web_search tool
    entry when use_web is set, replacing the deprecated
    plugins:[{id:"web"}] mechanism) are passed straight through to
    stream_order_fn - see router/app/openrouter_client.py. annotations
    (web search citations Brew) accumulates every chunk's whole annotation
    objects into one flat list - unlike tool_calls_delta, an annotation
    never arrives split across chunks by index, so this is a plain
    extend(), never an index-merge - surfaced only via CompleteEvent, per
    design (see _distinct_web_sources in this module)."""

    accumulated_text = ""
    tokens_out = 0
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    annotations: List[Dict[str, Any]] = []
    last_tick_time = time.monotonic()
    tokens_since_tick = 0
    text_since_tick = ""

    async for chunk in stream_order_fn(
        model_id,
        prompt,
        image_data_urls=image_data_urls,
        history_messages=history_messages,
        tools=tools,
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
        if chunk.annotations:
            annotations.extend(chunk.annotations)

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

    yield ("__final__", accumulated_text, tokens_out, finish_reason, usage, annotations)


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
    use_web: bool = False,
    remember_chat: bool = False,
    stream_order_fn: StreamOrderFn = stream_order,
    wait_for_approval: Optional[Callable[[str], "asyncio.Future[str]"]] = None,
    user_id: Optional[int] = None,
) -> AsyncIterator[BaseEvent]:
    """Core orchestration generator. Pure aside from stream_order_fn (an
    injectable OpenRouter caller) and wait_for_approval (an injectable
    approval-wait function) - both default to real implementations but
    tests always inject fakes, so no network call happens in tests.

    attachment_ids (Brew 38) are resolved against state.uploads inside
    _run_order_body; `attachments` remains a separate, directly-injectable
    seam (pre-built ClassifierAttachment objects) for tests that don't want
    to go through the /v1/upload flow.

    use_web (web-search Brew): a per-request toggle, mirroring use_pantry -
    see docs/design/web-search-design.md."""

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
            use_web=use_web,
            remember_chat=remember_chat,
            stream_order_fn=stream_order_fn,
            wait_for_approval=wait_for_approval,
            cancel_event=cancel_event,
            started_at=started_at,
            user_id=user_id,
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
    use_web: bool = False,
    remember_chat: bool = False,
    stream_order_fn: StreamOrderFn,
    wait_for_approval: Optional[Callable[[str], "asyncio.Future[str]"]],
    cancel_event: asyncio.Event,
    started_at: float,
    user_id: Optional[int] = None,
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
        use_web=use_web,
    )

    # Computed before routing (unlike before this Brew) so a real pre-call
    # cost estimate can be attached to the route itself - see
    # router.app.routing.estimate_cost_usd(). /v1/order carries no
    # max_tokens field, so the spend-cap admission estimate always uses
    # settings.spend_cap_assumed_output_tokens here.
    tokens_in = max(1, len(prompt) // 4)
    assumed_output_tokens = state.settings.spend_cap_assumed_output_tokens

    if bean_alias_override is not None:
        try:
            route = state.routing_policy.manual_route(
                classification.task_type,
                bean_alias_override,
                needs_vision=classification.needs_vision,
                needs_tool_calling=use_web,
                tokens_in=tokens_in,
                assumed_output_tokens=assumed_output_tokens,
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
                classification.task_type,
                needs_vision=classification.needs_vision,
                needs_tool_calling=use_web,
                # Only set when use_web is actually driving the constraint -
                # never biases the general-purpose select_route() path.
                preferred_tool_calling_bean_alias=(
                    state.settings.preferred_web_search_bean_alias if use_web else None
                ),
                tokens_in=tokens_in,
                assumed_output_tokens=assumed_output_tokens,
            )
        except NoVisionBeanError as exc:
            yield ErrorEvent(
                request_id=request_id,
                error_type="no_vision_bean_available",
                message=str(exc),
                retryable=False,
            )
            return
        except NoToolCallingBeanError as exc:
            yield ErrorEvent(
                request_id=request_id,
                error_type="no_web_search_bean_available",
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

    if not await check_rate_limit(state, user_id):
        logger.warning("rate_limit_refused user_id=%s endpoint=/v1/order", user_id)
        yield ErrorEvent(
            request_id=request_id,
            error_type="rate_limit_exceeded",
            message="You're sending requests too quickly. Please wait a moment and try again.",
            retryable=True,
        )
        return

    denial = await check_spend_cap(state, user_id, route.est_cost_usd)
    if denial is not None:
        logger.warning(
            "spend_cap_refused user_id=%s cap_type=%s estimate=%s today_spent=%.6f cap=%.2f",
            user_id, denial.cap_type, route.est_cost_usd, denial.today_spent, denial.cap,
        )
        yield ErrorEvent(
            request_id=request_id,
            error_type="spend_cap_exceeded",
            message="You've reached today's spending limit. It resets at midnight UTC.",
            retryable=False,
        )
        return

    bean = state.bean_registry.by_alias(route.bean_alias)
    model_id = bean.model_id
    # web search cost optimization Brew: bean is already guaranteed
    # tool_calling-capable when use_web is set (needs_tool_calling above),
    # so this is always the real openrouter:web_search call, never a
    # silently-ignored no-op. Replaces the deprecated
    # plugins:[{"id": "web"}] mechanism (confirmed deprecated against
    # OpenRouter's live docs) - only this tools-array form exposes an
    # engine, which is what makes web_search_engine configurable at all.
    web_search_tools = (
        [{"type": "openrouter:web_search", "parameters": {"engine": state.settings.web_search_engine}}]
        if use_web
        else None
    )

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

    # Computed once and reused for both the draft call below and any
    # escalation re-run of this same request - so a draft and its
    # escalation answer the same "today" consistently, even though an
    # escalation_pending pause can last up to
    # escalation_approval_timeout_seconds (600s default). Built from
    # history_result.messages but never mutates it - see
    # _with_system_message's docstring for why history_turns/
    # history_tokens_est/message_count/total_input_chars below are
    # unaffected.
    outbound_history_messages = _with_system_message(state.settings, history_result.messages or None)

    try:
        final_text = ""
        tokens_out = 0
        finish_reason = None
        usage: Optional[Dict[str, Any]] = None
        annotations: List[Dict[str, Any]] = []
        async for item in _consume_stream(
            stream_order_fn,
            model_id,
            outbound_text,
            settings=state.settings,
            request_id=request_id,
            cancel_event=cancel_event,
            image_data_urls=image_data_urls,
            history_messages=outbound_history_messages,
            tools=web_search_tools,
        ):
            if isinstance(item, tuple) and item[0] == "__cancelled__":
                yield CancelledEvent(request_id=request_id, reason="client_cancel_request")
                return
            if isinstance(item, tuple) and item[0] == "__final__":
                _, final_text, tokens_out, finish_reason, usage, annotations = item
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
    est_premium_cost = (
        estimate_cost_usd(premium_bean, tokens_in, assumed_output_tokens) if premium_alias else None
    )

    # web-search Brew: carry use_web through an escalation re-run, but only
    # when the premium Bean can actually call tools - otherwise drop it
    # with a logged warning rather than hard-failing an escalation that
    # would otherwise still produce a valid (just non-web) answer.
    escalation_tools = None
    if use_web and premium_bean is not None:
        if premium_bean.tool_calling:
            escalation_tools = web_search_tools
        else:
            logger.warning(
                "request_id=%s use_web dropped for escalation re-run - premium_bean_alias=%r "
                "lacks tool_calling support",
                request_id,
                premium_bean.alias,
            )

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
            escalation_denial = await check_spend_cap(state, user_id, decision.est_cost_usd)
            if escalation_denial is not None:
                # The draft already generated a valid, already-paid-for
                # answer - a second-order cap hit on the escalation re-run
                # falls back to it rather than discarding a good answer
                # (Decaf plan sign-off). Never a hard error here.
                logger.warning(
                    "spend_cap_refused_escalation user_id=%s cap_type=%s estimate=%s today_spent=%.6f cap=%.2f",
                    user_id,
                    escalation_denial.cap_type,
                    decision.est_cost_usd,
                    escalation_denial.today_spent,
                    escalation_denial.cap,
                )
                draft_quality = True
            else:
                yield EscalatingEvent(request_id=request_id, bean_alias=premium_bean.alias)
                async for item in _run_escalation(
                    state,
                    request_id,
                    premium_bean,
                    outbound_text,
                    stream_order_fn,
                    image_data_urls,
                    outbound_history_messages,
                    escalation_tools,
                ):
                    if isinstance(item, tuple) and item[0] == "__escalation_final__":
                        _, final_text, tokens_out, usage, annotations = item
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
                escalation_denial = await check_spend_cap(state, user_id, decision.est_cost_usd)
                if escalation_denial is not None:
                    # Same fallback-to-draft treatment as the auto_escalate
                    # branch above - a human already approved this, but the
                    # cap still wins; the draft is a valid, already-paid-for
                    # answer, not a hard error.
                    logger.warning(
                        "spend_cap_refused_escalation user_id=%s cap_type=%s estimate=%s today_spent=%.6f cap=%.2f",
                        user_id,
                        escalation_denial.cap_type,
                        decision.est_cost_usd,
                        escalation_denial.today_spent,
                        escalation_denial.cap,
                    )
                    draft_quality = True
                else:
                    yield EscalatingEvent(request_id=request_id, bean_alias=premium_bean.alias)
                    async for item in _run_escalation(
                        state,
                        request_id,
                        premium_bean,
                        outbound_text,
                        stream_order_fn,
                        image_data_urls,
                        outbound_history_messages,
                        escalation_tools,
                    ):
                        if isinstance(item, tuple) and item[0] == "__escalation_final__":
                            _, final_text, tokens_out, usage, annotations = item
                        else:
                            yield item
                    escalated, draft_quality = True, False
            else:
                context.resolution = "timed_out" if _is_past_deadline(decision_deadline) else "declined"
                draft_quality = True

    latency_ms = int((time.monotonic() - started_at) * 1000)
    final_bean_alias = premium_bean.alias if escalated and premium_bean else route.bean_alias
    final_model_id = premium_bean.model_id if escalated and premium_bean else model_id
    final_bean = state.bean_registry.by_alias(final_bean_alias)
    cost_usd, cost_source = resolve_cost(final_bean, tokens_in, tokens_out, usage)
    # web-search Brew: reflects whichever run actually won (the draft's own
    # web_search_tools, or escalation_tools if this request escalated -
    # which is None whenever use_web was dropped for the escalation
    # re-run above).
    final_tools_used = escalation_tools if escalated else web_search_tools
    web_search_cost_usd = (
        estimate_web_search_component_usd(final_bean, tokens_in, tokens_out, cost_usd, cost_source)
        if final_tools_used is not None
        else None
    )
    # Web search citations Brew: annotations already reflects whichever
    # run actually won - _run_order_body's own accumulator for the draft,
    # or _run_escalation's replacement value on escalation (see both
    # unpacking sites above) - so no separate "final" selection is needed
    # here, unlike final_tools_used.
    web_sources = _distinct_web_sources(annotations)

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
        # Brew 57: same None-when-toggle-off convention as the two above.
        # turns_dropped stays a real 0 when the toggle is on and nothing
        # was dropped, so the UI can distinguish that from "not applicable".
        history_turns_dropped=history_result.turns_dropped if remember_chat else None,
        history_chars_dropped=history_result.chars_dropped if remember_chat else None,
        history_drop_reason=history_result.drop_reason if remember_chat else None,
        web_sources=web_sources,
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

    # Brew 47 (docs/design/openai-compat-endpoint-design.md Section 3):
    # over_cap_declined is True for a real human decline/timeout on the
    # escalation_pending path - decision/escalated are already in scope
    # here, no new state needed. prompt_shape facts describe what was
    # actually sent to the model this request (history + current turn).
    over_cap_declined = decision is not None and decision.outcome == "escalation_pending" and not escalated
    has_code_fence = "```" in prompt
    message_count = len(history_result.messages) + 1
    total_input_chars = history_result.chars_included + len(outbound_text)

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
            client_source="chat_ui",
            over_cap_declined=over_cap_declined,
            has_code_fence=has_code_fence,
            message_count=message_count,
            total_input_chars=total_input_chars,
            cost_source=cost_source,
            user_id=user_id,
            web_search_cost_usd=web_search_cost_usd,
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
    state,
    request_id,
    premium_bean,
    prompt,
    stream_order_fn,
    image_data_urls=None,
    history_messages=None,
    tools=None,
):
    """Async generator: relays `generating` ticks from the premium re-run,
    then yields a ("__escalation_final__", text, tokens_out, usage,
    annotations) sentinel - usage (added alongside the cost-inconsistency
    fix) is resolve_cost()'s preferred "reported" cost source for the
    escalated row; previously always discarded here, forcing every
    escalated request's cost_usd to fall back to computed-or-unknown.
    image_data_urls (Brew 38) is resent so an escalation re-run still
    includes any attached images. history_messages (Brew 46) is resent
    too - an escalation re-run is still the same conversational turn.
    tools (web search cost optimization Brew) is None unless the caller
    already confirmed premium_bean supports tool_calling - see
    _run_order_body's escalation_tools computation. annotations (web
    search citations Brew) is whatever this re-run's own web_search tool
    (if any) actually cited - replaces the draft's annotations entirely,
    same as every other field here, since the escalated response is the
    one the client actually sees."""

    final_text = ""
    tokens_out = 0
    usage: Optional[Dict[str, Any]] = None
    annotations: List[Dict[str, Any]] = []
    async for item in _consume_stream(
        stream_order_fn,
        premium_bean.model_id,
        prompt,
        settings=state.settings,
        request_id=request_id,
        image_data_urls=image_data_urls,
        history_messages=history_messages,
        tools=tools,
    ):
        if isinstance(item, tuple) and item[0] == "__final__":
            _, final_text, tokens_out, _finish_reason, usage, annotations = item
        else:
            yield item
    yield ("__escalation_final__", final_text, tokens_out, usage, annotations)


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


def _retrieve_pantry_chunks(state: RouterState, prompt: str) -> List[PantryChunk]:
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


def _distinct_web_sources(annotations: Optional[List[Dict[str, Any]]]) -> Optional[List[WebSource]]:
    """Deduplicates OpenRouter's raw url_citation annotations by URL,
    first-appearance order, keeping the first title seen for each - a
    model may cite the same source multiple times across a response.
    Drops content/start_index/end_index entirely (never needed by a chip,
    same "path only, not the full chunk" precedent as
    _distinct_pantry_sources). An annotation missing a title falls back to
    the URL itself as the label, rather than a blank chip. Never an
    empty-but-claimed list - None when annotations is None/empty, same
    convention as pantry_sources."""

    if not annotations:
        return None
    seen: set = set()
    sources: List[WebSource] = []
    for annotation in annotations:
        citation = (annotation or {}).get("url_citation") or {}
        url = citation.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append(WebSource(url=url, title=citation.get("title") or url))
    return sources or None


def _with_system_message(
    settings: Settings, history_messages: Optional[List[Dict[str, str]]]
) -> Optional[List[Dict[str, str]]]:
    """Prepends the composed system message (router/app/system_prompt.py's
    build_system_message: the identity block and/or the date sentence,
    each independently gated, always joined into ONE message) at the head
    of the messages list actually sent to OpenRouter for /v1/order - never
    applied to history_result.messages itself (the caller always passes
    that in, this always returns a new list), so history_turns/
    history_tokens_est/message_count/total_input_chars - all computed from
    history_result before this is called - never see it. It is not a
    conversation turn: it is never passed to session_store.add_message.

    If history_messages already starts with a system message, merges into
    it rather than sending two leading system messages - dead code today
    (assemble_history()/pair_turns() in history.py can only ever produce
    user/assistant turns), kept for forward-compatibility and exercised
    directly by test_main.py.

    Returns history_messages unchanged (including None, and by identity
    for a list) when every part is disabled - so with both
    system_prompt_include_identity and system_prompt_include_date False,
    what reaches OpenRouter is byte-identical to the pre-Brew-53
    no-system-prompt behaviour."""

    system_message = build_system_message(settings)
    if system_message is None:
        return history_messages

    messages = list(history_messages or [])
    if messages and messages[0].get("role") == "system":
        messages[0] = {
            "role": "system",
            "content": f"{system_message}\n\n{messages[0]['content']}",
        }
    else:
        messages.insert(0, {"role": "system", "content": system_message})
    return messages


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


# --- Brew 47: POST /v1/chat/completions (docs/design/
# openai-compat-endpoint-design.md) --------------------------------------


def _extract_content_text(content: Any) -> str:
    """OpenAI message content is either a plain string or a list of
    content-part dicts (`{"type": "text", "text": ...}`,
    `{"type": "image_url", ...}`). Returns just the text portion,
    concatenated - used for classification and prompt_shape's
    has_code_fence/char-count facts only. The original `content` value is
    always relayed to OpenRouter verbatim via `messages_override`; this
    extraction never touches what's actually sent."""

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def _content_has_image(content: Any) -> bool:
    if not isinstance(content, list):
        return False
    return any(isinstance(part, dict) and part.get("type") == "image_url" for part in content)


def _count_prior_turns(messages: List[Dict[str, Any]]) -> int:
    """The OpenAI-shape analogue of Brew 46's prior_turns count: the
    number of user messages in everything before the last message,
    feeding the same classifier `long_history` signal (Section 1) - a
    request with lots of prior turns is real generation work, independent
    of the current message's own length."""

    return sum(1 for m in messages[:-1] if m.get("role") == "user")


def _client_source_from_user_agent(user_agent: Optional[str]) -> str:
    """Brew 47 Section 3: the raw User-Agent header (truncated), or the
    literal "openai_api" fallback when absent - undetectable spoofing is a
    documented blind spot, not something this function tries to catch."""

    if not user_agent or not user_agent.strip():
        return "openai_api"
    return user_agent.strip()[:120]


def _client_fingerprint(user_id: int, user_agent: Optional[str]) -> str:
    """Brew 47 Section 2 (Signal A): sha256(user_id + User-Agent), falling
    back to the literal "unknown" when the header is absent/blank - widens
    the match window to per-user rather than narrowing it to zero, since
    the time-window + exact-message-match conditions in
    SessionStore.find_retry_candidate still have to hold too, and a false
    "retry" flag is a soft, non-blocking signal, not a billing or routing
    decision."""

    basis = user_agent.strip() if user_agent and user_agent.strip() else "unknown"
    return hashlib.sha256(f"{user_id}|{basis}".encode("utf-8")).hexdigest()


def _message_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _merge_tool_call_deltas(
    accumulated: List[Dict[str, Any]], deltas: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Merges OpenAI-shape streamed tool_call delta fragments (each keyed
    by `index`, with `function.arguments` arriving as string fragments to
    concatenate in order) into whole tool_call objects - needed to
    reconstruct one `tool_calls` array for a `stream=false` response from
    the same deltas `stream=true` relays unmerged. Coffee never
    interprets the merged result, only reassembles it."""

    merged = [
        {**entry, "function": dict(entry.get("function") or {})} for entry in accumulated
    ]
    for delta in deltas:
        index = delta.get("index", 0)
        while len(merged) <= index:
            merged.append({"id": None, "type": "function", "function": {"name": "", "arguments": ""}})
        entry = merged[index]
        if delta.get("id"):
            entry["id"] = delta["id"]
        if delta.get("type"):
            entry["type"] = delta["type"]
        function_delta = delta.get("function") or {}
        if function_delta.get("name"):
            entry["function"]["name"] = entry["function"].get("name", "") + function_delta["name"]
        if function_delta.get("arguments"):
            entry["function"]["arguments"] = (
                entry["function"].get("arguments", "") + function_delta["arguments"]
            )
    return merged


async def _prepend_chunk(
    first_chunk: Dict[str, Any], rest: AsyncIterator[Dict[str, Any]]
) -> AsyncIterator[Dict[str, Any]]:
    """Re-attaches a chunk already consumed via generator.__anext__()
    (the endpoint handler's pre-stream cap/rate-limit peek - see
    chat_completions()) back onto the front of the remaining generator,
    so downstream code sees the exact same sequence it would have without
    the peek."""

    yield first_chunk
    async for chunk in rest:
        yield chunk


def _spend_cap_error_chunk(denial: SpendCapDenial) -> Dict[str, Any]:
    """OpenAI-compatible error body for a spend-cap refusal on
    /v1/chat/completions - `retry_after_seconds` is a sibling of `error`,
    not nested inside it (not part of OpenAI's error shape), read only by
    the endpoint handler to set the real HTTP Retry-After header before
    the response is sent; harmless as an extra field for any client that
    ignores it."""

    reset_at = datetime.fromisoformat(denial.reset_at_iso)
    retry_after_seconds = max(1, int((reset_at - datetime.now(timezone.utc)).total_seconds()))
    return {
        "error": {
            "message": "You've reached today's spending limit. It resets at midnight UTC.",
            "type": "spend_cap_exceeded",
            "code": "spend_cap_exceeded",
        },
        "retry_after_seconds": retry_after_seconds,
    }


def _rate_limit_error_chunk() -> Dict[str, Any]:
    """OpenAI-compatible error body for a rate-limit refusal - a fixed
    Retry-After (the rolling window size itself) rather than computed
    from internal per-user state, which is precise enough for a sanity
    limit, not a cost control."""

    return {
        "error": {
            "message": "Too many requests. Please slow down and try again shortly.",
            "type": "rate_limit_exceeded",
            "code": "rate_limit_exceeded",
        },
        "retry_after_seconds": 60,
    }


def _openai_chunk(
    request_id: str,
    created: int,
    bean_alias: str,
    *,
    role: Optional[str] = None,
    content: Optional[str] = None,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    finish_reason: Optional[str] = None,
    usage: Optional[Dict[str, Any]] = None,
    system_fingerprint: Optional[str] = None,
) -> Dict[str, Any]:
    """Builds one OpenAI-shape chat.completion.chunk dict. `model` is
    always the Bean alias, never a raw model id (docs/design/
    openai-compat-endpoint-design.md Section 1) - the same invariant
    router/app/aliases.py enforces for every other API-visible field."""

    delta: Dict[str, Any] = {}
    if role is not None:
        delta["role"] = role
    if content is not None:
        delta["content"] = content
    if tool_calls is not None:
        delta["tool_calls"] = tool_calls

    chunk: Dict[str, Any] = {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion.chunk",
        "created": created,
        "model": bean_alias,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    if usage is not None:
        chunk["usage"] = usage
    if system_fingerprint is not None:
        chunk["system_fingerprint"] = system_fingerprint
    return chunk


async def _stream_raw_openai_chunks(
    stream_order_fn: StreamOrderFn,
    model_id: str,
    messages: List[Dict[str, Any]],
    *,
    tools: Optional[List[Dict[str, Any]]],
    tool_choice: Optional[Any],
    temperature: Optional[float],
    max_tokens: Optional[int],
) -> AsyncIterator[StreamChunk]:
    """True passthrough for /v1/chat/completions - one outbound chunk per
    inbound provider chunk, tool-call deltas included. Deliberately does
    NOT reuse _consume_stream(): that helper batches into `generating`
    ticks to reduce the Coffee Counter chat UI's render frequency, and
    silently drops a chunk whose only content is a tool_calls delta (its
    content_delta is "" in that case) - wrong for an OpenAI-compatible
    endpoint, which needs every provider chunk relayed. See
    docs/design/openai-compat-endpoint-design.md Section 1."""

    async for chunk in stream_order_fn(
        model_id,
        messages_override=messages,
        tools=tools,
        tool_choice=tool_choice,
        temperature=temperature,
        max_tokens=max_tokens,
    ):
        if chunk.is_final:
            break
        yield chunk


async def _run_chat_completion(
    state: RouterState,
    *,
    request_id: str,
    messages: List[Dict[str, Any]],
    requested_model: Optional[str],
    tools: Optional[List[Dict[str, Any]]],
    tool_choice: Optional[Any],
    temperature: Optional[float],
    max_tokens: Optional[int],
    client_source: str,
    stream_order_fn: StreamOrderFn,
    stream: bool = False,
    user_id: Optional[int] = None,
    user_agent: Optional[str] = None,
    shadow_context: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """Core orchestration for POST /v1/chat/completions (Brew 47). Yields
    OpenAI-shape chat.completion.chunk dicts (or, on a routing/provider
    failure, a single `{"error": {...}}` dict) - the endpoint either
    flushes each one as an SSE frame (stream=true) or accumulates them
    into one chat.completion JSON body (stream=false).

    Deliberately its own orchestration, not a reuse of run_order()/
    _run_order_body() - see docs/design/openai-compat-endpoint-design.md
    Section 1 for the reasoning (no session rows, no Pantry, true
    passthrough streaming instead of tick-batched SSE events, and no
    escalation-approval pause since nothing here can render that UI).

    user_id/user_agent (Brew 47 Section 2) feed retry-fingerprinting only
    - this endpoint still creates no session row. shadow_context, when
    given, is mutated in place with everything the caller needs to decide
    whether to schedule a shadow run - an async generator can't `return`
    a value through `async for`, and shadow scheduling has to happen at
    the endpoint-handler level (after the client has actually received
    the response), not from inside this function - see
    docs/design/openai-compat-endpoint-design.md Section 2.

    `stream` (escalation-concatenation fix, docs/design/
    openai-compat-endpoint-design.md "Known issue", resolved) governs how
    an `auto_escalate` decision is acted on:
    - stream=False: the draft's per-chunk deltas are never yielded live -
      only captured internally - so if escalation fires, the draft is
      discarded with nothing having reached the client yet, and a single
      buffered chunk carrying the premium response's full content is
      yielded once the outcome is known. Free, since a non-streamed
      response is already buffered into one JSON body at the edge.
    - stream=True: the draft streams live as it always has, but an
      `auto_escalate` decision is never acted on - running a second call
      and gluing its chunks onto an already-flushed stream is exactly
      the bug this fix closes. The draft is returned as final, and
      `would_have_escalated` is logged instead so the measurement signal
      survives even though the action doesn't."""

    started_at = time.monotonic()
    created = int(time.time())

    last_user_text = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            last_user_text = _extract_content_text(message.get("content"))
            break

    has_code_fence = "```" in last_user_text
    message_count = len(messages)
    total_input_chars = sum(len(_extract_content_text(m.get("content"))) for m in messages)
    has_image = any(_content_has_image(m.get("content")) for m in messages)
    prior_turn_count = _count_prior_turns(messages)

    # Brew 47 Section 2 (Signal A - retry detection): the api_requests row
    # is inserted now, before generation starts, so a concurrent duplicate
    # request sees it as in-flight (response_text IS NULL) rather than a
    # completed answer it could falsely match against - see
    # SessionStore.create_api_request's docstring for why this ordering is
    # what makes parallelism structurally distinct from a retry.
    retry_of: Optional[str] = None
    if state.session_store is not None and user_id is not None:
        client_fingerprint = _client_fingerprint(user_id, user_agent)
        message_hash = _message_hash(last_user_text)
        state.session_store.create_api_request(
            request_id,
            user_id=user_id,
            client_fingerprint=client_fingerprint,
            last_user_message_hash=message_hash,
        )
        retry_of = state.session_store.find_retry_candidate(
            user_id=user_id,
            client_fingerprint=client_fingerprint,
            last_user_message_hash=message_hash,
            exclude_request_id=request_id,
            window_seconds=state.settings.retry_detection_window_seconds,
        )
        if retry_of is not None:
            state.session_store.set_retry_of(request_id, retry_of)
            state.session_store.increment_retry_count(retry_of)
            state.ledger.increment_retry_count(retry_of)

    attachments: List[ClassifierAttachment] = (
        [ClassifierAttachment(filename="(image)", content_type="image/jpeg")] if has_image else []
    )
    classification = classify(
        last_user_text,
        attachments,
        model_fallback_enabled=state.settings.classifier_model_fallback_enabled,
        history_turn_count=prior_turn_count,
        long_history_turns_threshold=state.settings.classifier_long_history_turns,
    )

    bean_alias_override: Optional[str] = None
    if requested_model:
        try:
            state.bean_registry.by_alias(requested_model)
            bean_alias_override = requested_model
        except AliasError:
            bean_alias_override = None

    # Computed before routing (unlike before this Brew) so a real
    # pre-call cost estimate can be attached to the route itself - see
    # router.app.routing.estimate_cost_usd(). Uses the client's own
    # max_tokens when given (strictly better information than a guess -
    # Cursor usually sends one), else settings.spend_cap_assumed_output_tokens.
    tokens_in = max(1, total_input_chars // 4)
    assumed_output_tokens = max_tokens or state.settings.spend_cap_assumed_output_tokens

    # web-search Brew: /v1/chat/completions has no use_web toggle (a raw
    # OpenAI client's own `tools` array is for its own function-calling
    # loop, unrelated to Coffee-side web search) - but a client that sends
    # any `tools` still needs a Bean that can actually call them, so this
    # reuses the same routing constraint machinery, without ever sending
    # OpenRouter's web plugin.
    needs_tool_calling = bool(tools)

    try:
        if bean_alias_override is not None:
            route = state.routing_policy.manual_route(
                classification.task_type,
                bean_alias_override,
                needs_vision=classification.needs_vision,
                needs_tool_calling=needs_tool_calling,
                tokens_in=tokens_in,
                assumed_output_tokens=assumed_output_tokens,
            )
        else:
            route = state.routing_policy.select_route(
                classification.task_type,
                needs_vision=classification.needs_vision,
                needs_tool_calling=needs_tool_calling,
                tokens_in=tokens_in,
                assumed_output_tokens=assumed_output_tokens,
            )
    except NoVisionBeanError as exc:
        yield {"error": {"message": str(exc), "type": "no_vision_bean_available"}}
        return
    except NoToolCallingBeanError as exc:
        yield {"error": {"message": str(exc), "type": "no_web_search_bean_available"}}
        return
    except RoutingError as exc:
        yield {"error": {"message": str(exc), "type": "invalid_bean_override"}}
        return

    bean = state.bean_registry.by_alias(route.bean_alias)

    if not await check_rate_limit(state, user_id):
        logger.warning("rate_limit_refused user_id=%s endpoint=/v1/chat/completions", user_id)
        yield _rate_limit_error_chunk()
        return

    cap_denial = await check_spend_cap(state, user_id, route.est_cost_usd)
    if cap_denial is not None:
        logger.warning(
            "spend_cap_refused user_id=%s cap_type=%s estimate=%s today_spent=%.6f cap=%.2f",
            user_id, cap_denial.cap_type, route.est_cost_usd, cap_denial.today_spent, cap_denial.cap,
        )
        yield _spend_cap_error_chunk(cap_denial)
        return

    async def _run_against(model_id: str, bean_alias: str, *, send_role: bool) -> AsyncIterator[Any]:
        text = ""
        tool_calls: List[Dict[str, Any]] = []
        finish_reason: Optional[str] = None
        usage: Optional[Dict[str, Any]] = None
        role_sent = not send_role
        async for chunk in _stream_raw_openai_chunks(
            stream_order_fn,
            model_id,
            messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            role = None
            if not role_sent:
                role = "assistant"
                role_sent = True
            if chunk.content_delta:
                text += chunk.content_delta
            if chunk.tool_calls_delta:
                tool_calls = _merge_tool_call_deltas(tool_calls, chunk.tool_calls_delta)
            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
            if chunk.usage:
                usage = chunk.usage
            if role is not None or chunk.content_delta or chunk.tool_calls_delta:
                yield _openai_chunk(
                    request_id,
                    created,
                    bean_alias,
                    role=role,
                    content=chunk.content_delta or None,
                    tool_calls=chunk.tool_calls_delta,
                )
        yield ("__done__", text, tool_calls, finish_reason, usage)

    accumulated_text = ""
    tool_calls_accum: List[Dict[str, Any]] = []
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None

    try:
        async for item in _run_against(bean.model_id, route.bean_alias, send_role=True):
            if isinstance(item, tuple) and item[0] == "__done__":
                _, accumulated_text, tool_calls_accum, finish_reason, usage = item
            elif stream:
                # stream=False: the draft's deltas are held back rather than
                # relayed live - see this function's docstring - so that an
                # escalation later in this request has nothing to unwind.
                yield item
    except OpenRouterClientError as exc:
        yield {"error": {"message": str(exc), "type": "provider_error"}}
        return

    tokens_out = (
        usage["completion_tokens"]
        if usage and isinstance(usage.get("completion_tokens"), int)
        else max(1, len(accumulated_text) // 4)
        if accumulated_text
        else 0
    )

    # A tool_calls-only response (empty `text`, finish_reason "tool_calls")
    # is a well-formed, successful turn, not a failure - check_for_failure()
    # was written before tool calling existed and treats any empty `text`
    # as the "empty" failure reason unconditionally. Coffee never
    # interprets tool_calls, but it must not punish a Bean for correctly
    # producing one instead of prose. Skip the failure check entirely when
    # tool_calls were produced (see docs/design/
    # openai-compat-endpoint-design.md Section 1 - "Tools passthrough").
    if tool_calls_accum:
        failure = FailureCheckResult(failed=False)
    else:
        generation = GenerationResult(
            text=accumulated_text,
            tokens_out=tokens_out,
            finish_reason=finish_reason,
            caller_reported_failure=_force_escalation_enabled(),
        )
        failure = check_for_failure(
            generation,
            truncation_min_expected_tokens=state.settings.truncation_min_expected_tokens,
            refusal_keywords=state.settings.refusal_keywords,
        )
    premium_bean = state.bean_registry.by_role("premium")
    premium_alias = premium_bean.alias if premium_bean and premium_bean.is_available else None
    est_premium_cost = (
        estimate_cost_usd(premium_bean, tokens_in, assumed_output_tokens) if premium_alias else None
    )
    decision = decide_escalation(
        failure,
        premium_bean_alias=premium_alias,
        est_premium_cost_usd=est_premium_cost,
        escalation_cost_cap_usd=state.settings.escalation_cost_cap_usd,
    )

    escalated = False
    draft_quality = False
    over_cap_declined = False
    would_have_escalated = False
    final_bean_alias = route.bean_alias
    final_model_id = bean.model_id

    if decision is not None:
        if decision.outcome == "no_premium_available":
            draft_quality = True
        elif decision.outcome == "auto_escalate":
            if stream:
                # Never act on an escalation once the draft has already
                # started streaming - see this function's docstring. Log
                # the outcome that would have fired instead of firing it.
                would_have_escalated = True
                draft_quality = True
            else:
                escalation_denial = await check_spend_cap(state, user_id, decision.est_cost_usd)
                if escalation_denial is not None:
                    # Same fallback-to-draft treatment as /v1/order - the
                    # draft is already paid for and a valid answer; a
                    # second-order cap hit on the escalation re-run must
                    # not discard it (Decaf plan sign-off).
                    logger.warning(
                        "spend_cap_refused_escalation user_id=%s cap_type=%s estimate=%s today_spent=%.6f cap=%.2f",
                        user_id,
                        escalation_denial.cap_type,
                        decision.est_cost_usd,
                        escalation_denial.today_spent,
                        escalation_denial.cap,
                    )
                    draft_quality = True
                else:
                    try:
                        async for item in _run_against(
                            premium_bean.model_id, premium_bean.alias, send_role=False
                        ):
                            if isinstance(item, tuple) and item[0] == "__done__":
                                _, accumulated_text, tool_calls_accum, finish_reason, usage = item
                    except OpenRouterClientError as exc:
                        yield {"error": {"message": str(exc), "type": "provider_error"}}
                        return
                    escalated = True
                    final_bean_alias = premium_bean.alias
                    final_model_id = premium_bean.model_id
                    if usage and isinstance(usage.get("completion_tokens"), int):
                        tokens_out = usage["completion_tokens"]
        elif decision.outcome == "escalation_pending":
            # Cannot pause for human approval on this endpoint (Section 1) -
            # immediate decline, the already-generated draft is returned.
            draft_quality = True
            over_cap_declined = True

    if not stream:
        # The draft's (or, on escalation, the premium run's) deltas were
        # never yielded live - emit the whole winning response as one
        # buffered chunk now that the outcome is fully known.
        yield _openai_chunk(
            request_id,
            created,
            final_bean_alias,
            role="assistant",
            content=accumulated_text or None,
            tool_calls=tool_calls_accum or None,
        )

    system_fingerprint = "draft_quality" if draft_quality else None
    yield _openai_chunk(
        request_id,
        created,
        final_bean_alias,
        finish_reason=finish_reason or "stop",
        usage={
            "prompt_tokens": tokens_in,
            "completion_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        },
        system_fingerprint=system_fingerprint,
    )

    latency_ms = int((time.monotonic() - started_at) * 1000)
    cost_usd, cost_source = resolve_cost(
        state.bean_registry.by_alias(final_bean_alias), tokens_in, tokens_out, usage
    )

    logger.info(
        "request_id=%s client_source=%s requested_model=%r bean_alias=%s escalated=%s "
        "over_cap_declined=%s retry_of=%s would_have_escalated=%s",
        request_id,
        client_source,
        requested_model,
        final_bean_alias,
        escalated,
        over_cap_declined,
        retry_of,
        would_have_escalated,
    )

    if state.session_store is not None and user_id is not None:
        state.session_store.complete_api_request(
            request_id, accumulated_text, max_stored_chars=state.settings.shadow_response_max_stored_chars
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
            escalation_approved=None,
            attachment_count=1 if has_image else 0,
            attachment_tokens_est=None if has_image else 0,
            remember_chat=False,
            history_turns=0,
            history_tokens_est=None,
            client_source=client_source,
            requested_model=requested_model or "",
            over_cap_declined=over_cap_declined,
            has_code_fence=has_code_fence,
            message_count=message_count,
            total_input_chars=total_input_chars,
            retry_of=retry_of or "",
            would_have_escalated=would_have_escalated,
            cost_source=cost_source,
            user_id=user_id,
        )
    )

    # Brew 47 Section 2 (Signal C - shadow mode): filled in only now, once
    # the primary's own outcome is fully known, so the endpoint handler can
    # decide whether to schedule a shadow run - see this function's
    # docstring for why that scheduling can't happen from in here.
    if shadow_context is not None:
        shadow_context.update(
            {
                "request_id": request_id,
                "messages": messages,
                "tools": tools,
                "tool_choice": tool_choice,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "bean_alias": final_bean_alias,
                "is_premium": premium_bean is not None and final_bean_alias == premium_bean.alias,
                "task_type": classification.task_type,
                "client_source": client_source,
                "requested_model": requested_model or "",
                "has_code_fence": has_code_fence,
                "message_count": message_count,
                "total_input_chars": total_input_chars,
                "user_id": user_id,
            }
        )


def _todays_shadow_spend_usd(ledger: RouterLedger) -> float:
    """Cheap sum-over-today's-CSV-rows query (Section 2) - checked
    immediately before scheduling a shadow task, not after, so "over the
    cap, skip sampling" never touches the request path. "Today" is the
    current UTC date, matching every other timestamp this router writes."""

    today = datetime.now(timezone.utc).date().isoformat()
    total = 0.0
    for row in ledger.read_all_rows():
        if (row.get("is_shadow") or "").strip().lower() != "true":
            continue
        if not (row.get("timestamp") or "").startswith(today):
            continue
        try:
            total += float(row.get("cost_usd") or 0.0)
        except ValueError:
            continue
    return total


async def _run_shadow(state: RouterState, shadow_context: Dict[str, Any], premium_bean: Bean) -> None:
    """Fire-and-forget: re-runs the same messages/tools payload against
    the premium Bean, silently, after the primary client already has its
    answer. Never re-enters _run_chat_completion (or anything that could
    schedule another shadow run) - it calls _stream_raw_openai_chunks
    directly, which is a structurally stronger "never recursive" guarantee
    than a boolean flag would be. Its entire body is wrapped in
    try/except: a shadow failure must be silent to the client (there is
    no client waiting on this) and merely logged (docs/design/
    openai-compat-endpoint-design.md Section 2)."""

    primary_request_id = shadow_context["request_id"]
    try:
        text = ""
        usage: Optional[Dict[str, Any]] = None
        async for chunk in _stream_raw_openai_chunks(
            state.stream_order_fn,
            premium_bean.model_id,
            shadow_context["messages"],
            tools=shadow_context["tools"],
            tool_choice=shadow_context["tool_choice"],
            temperature=shadow_context["temperature"],
            max_tokens=shadow_context["max_tokens"],
        ):
            if chunk.content_delta:
                text += chunk.content_delta
            if chunk.usage:
                usage = chunk.usage

        tokens_in = max(1, shadow_context["total_input_chars"] // 4)
        tokens_out = (
            usage["completion_tokens"]
            if usage and isinstance(usage.get("completion_tokens"), int)
            else max(1, len(text) // 4)
            if text
            else 0
        )

        shadow_cost_usd, shadow_cost_source = resolve_cost(premium_bean, tokens_in, tokens_out, usage)
        state.ledger.append(
            LedgerRow(
                timestamp=_iso_now(),
                request_id=str(uuid.uuid4()),
                task_type=shadow_context["task_type"],
                bean_alias=premium_bean.alias,
                raw_model_id=premium_bean.model_id,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=shadow_cost_usd,
                latency_ms=0,
                escalated=False,
                escalation_approved=None,
                client_source=shadow_context["client_source"],
                requested_model=shadow_context["requested_model"],
                is_shadow=True,
                shadow_of=primary_request_id,
                has_code_fence=shadow_context["has_code_fence"],
                message_count=shadow_context["message_count"],
                total_input_chars=shadow_context["total_input_chars"],
                cost_source=shadow_cost_source,
                user_id=shadow_context["user_id"],
            )
        )

        if state.session_store is not None:
            state.session_store.record_shadow_result(
                primary_request_id,
                text,
                premium_bean.alias,
                max_stored_chars=state.settings.shadow_response_max_stored_chars,
            )
    except Exception:
        logger.warning("shadow run failed for primary request_id=%s", primary_request_id, exc_info=True)


async def _maybe_schedule_shadow(state: RouterState, shadow_context: Optional[Dict[str, Any]]) -> None:
    """Called from the endpoint handler only after the primary response
    has been fully sent to the client (Section 2) - the shadow task
    itself is never awaited, only ever asyncio.create_task()'d, so it
    structurally cannot delay or affect the client response that already
    went out. This function itself is awaited only long enough to run the
    (cheap, local) cap checks below before scheduling."""

    if not shadow_context:
        return  # error path (routing/provider failure) - nothing to shadow
    if not state.settings.shadow_mode_enabled:
        return
    if shadow_context.get("is_premium"):
        return  # shadowing a premium request against itself is pointless
    if state.session_store is None:
        return
    if random.random() >= state.settings.shadow_mode_sample_rate:
        return
    premium_bean = state.bean_registry.by_role("premium")
    if premium_bean is None or not premium_bean.is_available:
        return
    spend_today = _todays_shadow_spend_usd(state.ledger)
    if spend_today >= state.settings.shadow_mode_daily_cost_cap_usd:
        logger.info(
            "shadow sampling skipped: daily cap reached (spend_today_usd=%.4f, cap=%.4f)",
            spend_today,
            state.settings.shadow_mode_daily_cost_cap_usd,
        )
        return

    # Spend-cap Brew: a shadow run is real money, attributed to the user
    # whose request triggered it - it must respect that user's per-user
    # cap and the global cap too, on top of shadow mode's own
    # shadow_mode_daily_cost_cap_usd above. Never touches the primary
    # response either way (already sent by the time this runs) - "would
    # cross the cap" just means "never scheduled," logged the same way
    # the shadow-specific cap already is.
    tokens_in = max(1, shadow_context["total_input_chars"] // 4)
    assumed_output_tokens = shadow_context.get("max_tokens") or state.settings.spend_cap_assumed_output_tokens
    shadow_estimate = estimate_cost_usd(premium_bean, tokens_in, assumed_output_tokens)
    shadow_denial = await check_spend_cap(state, shadow_context["user_id"], shadow_estimate)
    if shadow_denial is not None:
        logger.info(
            "shadow sampling skipped: spend cap reached (cap_type=%s, estimate=%s, today_spent=%.6f, cap=%.2f)",
            shadow_denial.cap_type,
            shadow_estimate,
            shadow_denial.today_spent,
            shadow_denial.cap,
        )
        return

    task = asyncio.create_task(_run_shadow(state, shadow_context, premium_bean))
    state.background_tasks.add(task)
    task.add_done_callback(state.background_tasks.discard)


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
    # web-search Brew (docs/design/web-search-design.md): same per-request
    # toggle shape as use_pantry. Routes to a tool-calling-capable Bean
    # (never free-tier - see NoToolCallingBeanError) and sends OpenRouter's
    # web plugin with no tuning parameters.
    use_web: bool = False


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


class ChatCompletionMessage(BaseModel):
    """One OpenAI-shape message. `content` is deliberately untyped (`Any`)
    rather than `str` - a real client's content is either a plain string
    or a multimodal content-part array, and this router relays it to
    OpenRouter verbatim (docs/design/openai-compat-endpoint-design.md
    Section 1) rather than re-validating its internal shape."""

    role: str
    content: Any = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """POST /v1/chat/completions body (Brew 47). `model` is optional and
    ignored for routing unless it exactly matches a Bean alias (a manual
    override) - Coffee always classifies and routes as usual otherwise.
    Extra OpenAI fields this router doesn't use (`top_p`,
    `presence_penalty`, etc.) are accepted and ignored, not rejected -
    real clients send more than this router needs."""

    model: Optional[str] = None
    messages: List[ChatCompletionMessage]
    stream: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None


VALID_RATINGS = {"good", "needed_fixing", "failed"}


def create_app(state: Optional[RouterState] = None) -> FastAPI:
    app = FastAPI(title="Coffee Core Router")

    if state is None:
        config_paths = load_router_config_paths()
        assert_no_key_like_strings(config_paths)
        bean_registry = BeanRegistry.from_yaml()
        assert_active_beans_priced(bean_registry)
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
        allow_origins=_cors_allowed_origins(),
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
                use_web=body.use_web,
                remember_chat=remember_chat,
                stream_order_fn=state.stream_order_fn,
                user_id=current_user.id,
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

    @app.post("/v1/chat/completions")
    async def chat_completions(
        body: ChatCompletionRequest,
        user_agent: Optional[str] = Header(default=None),
        current_user: UserRecord = Depends(get_current_user),
    ):
        """OpenAI-compatible endpoint (Brew 47, docs/design/
        openai-compat-endpoint-design.md) - stateless with respect to
        Coffee's session store (the client carries its own `messages`
        history every turn; no session row is created). Same Bearer auth
        as every other endpoint."""

        state = app.state.coffee
        request_id = str(uuid.uuid4())
        client_source = _client_source_from_user_agent(user_agent)
        messages = [m.model_dump(exclude_none=True) for m in body.messages]

        # Brew 47 Section 2: mutated in place by _run_chat_completion once
        # the primary's outcome is known - read back after the generator is
        # exhausted (i.e. after the client has actually received the
        # response) to decide whether to schedule a shadow run. Never
        # touched at all on an error path (stays {}).
        shadow_context: Dict[str, Any] = {}

        generator = _run_chat_completion(
            state,
            request_id=request_id,
            messages=messages,
            requested_model=body.model,
            tools=body.tools,
            tool_choice=body.tool_choice,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            client_source=client_source,
            stream_order_fn=state.stream_order_fn,
            stream=body.stream,
            user_id=current_user.id,
            user_agent=user_agent,
            shadow_context=shadow_context,
        )

        # Spend-cap Brew: the cap/rate-limit check lives inside
        # _run_chat_completion (right after routing resolves the target
        # Bean, so it has a real cost estimate) and, on denial, is the
        # FIRST thing the generator ever yields. Advancing it by one step
        # here - before either response mode commits to anything - is
        # what lets a denial become a real HTTP 429 with a real
        # Retry-After header on stream=true too: once StreamingResponse
        # is returned, the HTTP status is locked at 200 and there is no
        # way back. This also means the stream never starts on a denial,
        # satisfying "never start a stream you will kill mid-token" for
        # free.
        try:
            first_chunk: Optional[Dict[str, Any]] = await generator.__anext__()
        except StopAsyncIteration:
            first_chunk = None

        if first_chunk is not None and "error" in first_chunk:
            error_type = first_chunk["error"].get("type")
            status_code = 429 if error_type in ("spend_cap_exceeded", "rate_limit_exceeded") else 400
            headers: Dict[str, str] = {}
            retry_after = first_chunk.pop("retry_after_seconds", None)
            if retry_after is not None:
                headers["Retry-After"] = str(retry_after)
            return JSONResponse(status_code=status_code, content=first_chunk, headers=headers)

        full_generator = generator if first_chunk is None else _prepend_chunk(first_chunk, generator)

        if body.stream:

            async def _sse() -> AsyncIterator[bytes]:
                try:
                    async for chunk in full_generator:
                        yield f"data: {json.dumps(chunk)}\n\n".encode("utf-8")
                    yield b"data: [DONE]\n\n"
                finally:
                    # Fire-and-forget, scheduled only once every real chunk
                    # has already been yielded to the client (or the stream
                    # ended early) - see _maybe_schedule_shadow's docstring.
                    await _maybe_schedule_shadow(state, shadow_context)

            return StreamingResponse(_sse(), media_type="text/event-stream")

        # stream=false (Section 1): every call still streams from
        # OpenRouter internally via the same generator - only the edge
        # differs, buffering translated chunks into one JSON body instead
        # of flushing each as SSE, so stream=true/false are guaranteed to
        # accumulate byte-identical content/tool_calls/usage.
        content_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        final_model: Optional[str] = None
        finish_reason = "stop"
        usage: Optional[Dict[str, Any]] = None
        system_fingerprint: Optional[str] = None
        try:
            async for chunk in full_generator:
                if "error" in chunk:
                    return JSONResponse(status_code=400, content=chunk)
                delta = chunk["choices"][0]["delta"]
                if delta.get("content"):
                    content_parts.append(delta["content"])
                if delta.get("tool_calls"):
                    tool_calls = _merge_tool_call_deltas(tool_calls, delta["tool_calls"])
                if chunk["choices"][0].get("finish_reason"):
                    finish_reason = chunk["choices"][0]["finish_reason"]
                if chunk.get("usage"):
                    usage = chunk["usage"]
                if chunk.get("system_fingerprint"):
                    system_fingerprint = chunk["system_fingerprint"]
                final_model = chunk["model"]
        finally:
            await _maybe_schedule_shadow(state, shadow_context)

        message: Dict[str, Any] = {"role": "assistant", "content": "".join(content_parts) or None}
        if tool_calls:
            message["tool_calls"] = tool_calls

        response: Dict[str, Any] = {
            "id": f"chatcmpl-{request_id}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": final_model,
            "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
            "usage": usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
        if system_fingerprint:
            response["system_fingerprint"] = system_fingerprint
        return response

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

    @app.get("/v1/usage")
    async def usage(current_user: UserRecord = Depends(get_current_user)):
        """Spend-cap Brew: today's real spend/cap/reset for the current
        user, computed server-side via the exact same
        RouterLedger.today_spend_usd()/_effective_daily_cap_usd() the cap
        enforcement itself uses - the UI reads this rather than computing
        it, so the displayed number and the enforced number can never
        drift apart."""

        state = app.state.coffee
        today_spend_usd, _ = state.ledger.today_spend_usd(user_id=current_user.id)
        return {
            "today_spend_usd": today_spend_usd,
            "cap_usd": _effective_daily_cap_usd(state, current_user.id),
            "reset_at": _utc_midnight_reset_iso(),
        }

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

        # Spend-cap Brew: this call spends real money, same as any other
        # real call site - gated the same way, before the model is ever
        # called. tokens_in is estimated from the configured transcript
        # cap (an upper bound, not the real prompt - conservative by
        # design, consistent with every other pre-call estimate here).
        proposal_bean = state.bean_registry.by_alias(state.settings.memory_proposal_bean_alias)
        proposal_tokens_in_estimate = max(1, state.settings.memory_proposal_max_transcript_chars // 4)
        proposal_estimate = estimate_cost_usd(
            proposal_bean, proposal_tokens_in_estimate, state.settings.spend_cap_assumed_output_tokens
        )
        if not await check_rate_limit(state, current_user.id):
            logger.warning(
                "rate_limit_refused user_id=%s endpoint=/v1/sessions/memory_proposal", current_user.id
            )
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down and try again shortly.",
                headers={"Retry-After": "60"},
            )
        denial = await check_spend_cap(state, current_user.id, proposal_estimate)
        if denial is not None:
            logger.warning(
                "spend_cap_refused user_id=%s cap_type=%s estimate=%s today_spent=%.6f cap=%.2f "
                "endpoint=/v1/sessions/memory_proposal",
                current_user.id, denial.cap_type, proposal_estimate, denial.today_spent, denial.cap,
            )
            reset_at = datetime.fromisoformat(denial.reset_at_iso)
            retry_after = max(1, int((reset_at - datetime.now(timezone.utc)).total_seconds()))
            raise HTTPException(
                status_code=429,
                detail="You've reached today's spending limit. It resets at midnight UTC.",
                headers={"Retry-After": str(retry_after)},
            )

        try:
            proposal = await generate_memory_proposal(
                session_id=session_id,
                session_store=store,
                bean_registry=state.bean_registry,
                bean_alias=state.settings.memory_proposal_bean_alias,
                max_transcript_chars=state.settings.memory_proposal_max_transcript_chars,
                stream_order_fn=state.stream_order_fn,
                repo_root=state.memory_proposal_repo_root,
                ledger=state.ledger,
                user_id=current_user.id,
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
