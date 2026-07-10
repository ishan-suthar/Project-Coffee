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
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from router.app.aliases import BeanRegistry
from router.app.classifier import Attachment as ClassifierAttachment
from router.app.classifier import classify
from router.app.config import Settings, assert_no_key_like_strings, load_router_config_paths
from router.app.escalation import (
    GenerationResult,
    check_for_failure,
    decide_escalation,
    resolve_pending_escalation,
)
from router.app.events import (
    BaseEvent,
    CancelledEvent,
    ClassifyingEvent,
    CompleteEvent,
    ErrorEvent,
    EscalatingEvent,
    EscalationPendingEvent,
    GeneratingEvent,
    OrderReceivedEvent,
    RouteSelectedEvent,
)
from router.app.ledger import LedgerRow, RouterLedger
from router.app.openrouter_client import OpenRouterClientError, StreamChunk, stream_order
from router.app.routing import NoVisionBeanError, RoutingError, RoutingPolicy
from router.app.sessions import SessionStore
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

ESCALATION_APPROVAL_TIMEOUT_SECONDS = 300.0
DEFAULT_PROJECT = "default"


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


async def _consume_stream(
    stream_order_fn: StreamOrderFn,
    model_id: str,
    prompt: str,
    *,
    settings: Settings,
    request_id: str,
    cancel_event: Optional[asyncio.Event] = None,
    image_data_urls: Optional[List[str]] = None,
) -> AsyncIterator[Any]:
    """Wrap a raw OpenRouter stream, emitting periodic `generating` ticks
    (with the incremental text_delta since the last tick - contract v1.1)
    per settings.generating_tick_tokens / generating_tick_seconds, and
    yield a final ("__final__", text, tokens_out, finish_reason, usage)
    sentinel tuple once the stream ends, or a ("__cancelled__",) sentinel
    if cancel_event is set mid-stream. image_data_urls (Brew 38) is passed
    straight through to stream_order_fn - see router/app/openrouter_client.py."""

    accumulated_text = ""
    tokens_out = 0
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    last_tick_time = time.monotonic()
    tokens_since_tick = 0
    text_since_tick = ""

    async for chunk in stream_order_fn(model_id, prompt, image_data_urls=image_data_urls):
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
            stream_order_fn=stream_order_fn,
            wait_for_approval=wait_for_approval,
            cancel_event=cancel_event,
            started_at=started_at,
        ):
            yield event
    finally:
        state.cancel_flags.pop(request_id, None)
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

    classification = classify(
        prompt,
        resolved_attachments,
        model_fallback_enabled=state.settings.classifier_model_fallback_enabled,
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
        prompt, upload_records, max_inline_text_chars=state.settings.max_inline_text_chars
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

    generation = GenerationResult(text=final_text, tokens_out=tokens_out, finish_reason=finish_reason)
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
        yield EscalationPendingEvent(
            request_id=request_id,
            reason=decision.reason,
            est_cost_usd=decision.est_cost_usd,
            premium_bean_alias=decision.premium_bean_alias,
        )

        if decision.outcome == "no_premium_available":
            draft_quality = True
        elif decision.outcome == "auto_escalate":
            yield EscalatingEvent(request_id=request_id, bean_alias=premium_bean.alias)
            async for item in _run_escalation(
                state, request_id, premium_bean, outbound_text, stream_order_fn, image_data_urls
            ):
                if isinstance(item, tuple) and item[0] == "__escalation_final__":
                    _, final_text, tokens_out, _spare = item
                else:
                    yield item
            escalated, draft_quality = True, False
        elif decision.outcome == "escalation_pending":
            approval = await _await_approval(state, request_id, wait_for_approval)
            resolution = resolve_pending_escalation(approval)
            if resolution.should_escalate:
                yield EscalatingEvent(request_id=request_id, bean_alias=premium_bean.alias)
                async for item in _run_escalation(
                    state, request_id, premium_bean, outbound_text, stream_order_fn, image_data_urls
                ):
                    if isinstance(item, tuple) and item[0] == "__escalation_final__":
                        _, final_text, tokens_out, _spare = item
                    else:
                        yield item
                escalated, draft_quality = True, False
            else:
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
        )
    )

    if session_id is not None and state.session_store is not None:
        state.session_store.add_message(
            session_id, request_id=request_id, role="user", content=prompt
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
    state, request_id, premium_bean, prompt, stream_order_fn, image_data_urls=None
):
    """Async generator: relays `generating` ticks from the premium re-run,
    then yields a ("__escalation_final__", text, tokens_out) sentinel.
    image_data_urls (Brew 38) is resent so an escalation re-run still
    includes any attached images."""

    final_text = ""
    tokens_out = 0
    async for item in _consume_stream(
        stream_order_fn,
        premium_bean.model_id,
        prompt,
        settings=state.settings,
        request_id=request_id,
        image_data_urls=image_data_urls,
    ):
        if isinstance(item, tuple) and item[0] == "__final__":
            _, final_text, tokens_out, _finish_reason, _usage = item
        else:
            yield item
    yield ("__escalation_final__", final_text, tokens_out, None)


async def _await_approval(state: RouterState, request_id: str, wait_for_approval) -> str:
    if wait_for_approval is not None:
        return await wait_for_approval(request_id)

    loop = asyncio.get_event_loop()
    future: "asyncio.Future[str]" = loop.create_future()
    state.pending_escalations[request_id] = future
    try:
        return await asyncio.wait_for(future, timeout=ESCALATION_APPROVAL_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return "declined"
    finally:
        state.pending_escalations.pop(request_id, None)


def _build_outbound_content(
    prompt: str,
    upload_records: List[UploadRecord],
    *,
    max_inline_text_chars: int,
) -> Tuple[str, Optional[List[str]]]:
    """Builds the text actually sent to OpenRouter (prompt plus any
    extracted PDF/text attachment content, inlined with a clear delimiter -
    docs/design/attachments-design.md Section 5) and the list of base64
    `data:` URLs for image attachments. Images are read from disk and
    encoded at send time, not pre-encoded at upload time, to avoid keeping
    a redundant ~33%-larger base64 copy alongside the raw file. Returns
    `None` for image_data_urls when there are no images, so
    stream_order()'s plain-string content path (the common case) is used
    unchanged."""

    text_parts = [prompt]
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
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


async def sse_stream(events: AsyncIterator[BaseEvent]) -> AsyncIterator[bytes]:
    try:
        async for event in events:
            yield event.to_sse().encode("utf-8")
    except asyncio.CancelledError:
        raise


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
        state = RouterState(
            bean_registry=bean_registry,
            routing_policy=routing_policy,
            settings=settings,
            ledger=ledger,
            session_store=session_store,
        )

    app.state.coffee = state

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.post("/v1/order")
    async def order(body: OrderRequest):
        store = app.state.coffee.session_store
        if body.session_id is not None and store is not None and not store.session_exists(
            body.session_id
        ):
            raise HTTPException(status_code=404, detail="Unknown session_id.")
        if body.request_id is not None and body.request_id in app.state.coffee.cancel_flags:
            raise HTTPException(
                status_code=409, detail=f"request_id {body.request_id!r} is already in flight."
            )

        events = run_order(
            app.state.coffee,
            prompt=body.prompt,
            attachment_ids=body.attachment_ids or None,
            request_id=body.request_id,
            session_id=body.session_id,
            bean_alias_override=body.bean_alias_override,
            stream_order_fn=app.state.coffee.stream_order_fn,
        )
        return StreamingResponse(sse_stream(events), media_type="text/event-stream")

    @app.post("/v1/upload", response_model=UploadResponse)
    async def upload(request_id: str = Form(...), file: UploadFile = File(...)):
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
    async def retry(body: RetryRequest):
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
    async def approve_escalation(body: ApproveEscalationRequest):
        future = app.state.coffee.pending_escalations.get(body.request_id)
        if future is None:
            raise HTTPException(status_code=404, detail="No pending escalation for this request_id.")
        if not future.done():
            future.set_result("approved" if body.approve else "declined")
        return {"request_id": body.request_id, "approve": body.approve, "status": "acknowledged"}

    @app.post("/v1/cancel")
    async def cancel(body: CancelRequest):
        cancel_event = app.state.coffee.cancel_flags.get(body.request_id)
        if cancel_event is None:
            raise HTTPException(
                status_code=404, detail="No in-flight request for this request_id."
            )
        cancel_event.set()
        return {"request_id": body.request_id, "status": "cancel_requested"}

    @app.post("/v1/rate")
    async def rate(body: RateRequest):
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
    async def beans():
        return [
            {"alias": bean.alias, "role": bean.role, "available": bean.is_available}
            for bean in app.state.coffee.bean_registry.all_beans()
        ]

    @app.post("/v1/sessions")
    async def create_session(body: CreateSessionRequest):
        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        session_id = store.create_session(body.project)
        return {"id": session_id, "project": body.project}

    @app.get("/v1/sessions")
    async def list_sessions(project: str = DEFAULT_PROJECT):
        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        return [
            {
                "id": s.id,
                "project": s.project,
                "title": s.title,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "cost_total_usd": s.cost_total_usd,
            }
            for s in store.list_sessions(project)
        ]

    @app.get("/v1/sessions/{session_id}/messages")
    async def session_messages(session_id: str):
        store = app.state.coffee.session_store
        if store is None:
            raise HTTPException(status_code=503, detail="Session storage is not configured.")
        if not store.session_exists(session_id):
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
            }
            for m in store.get_messages(session_id)
        ]

    return app


app = create_app()
