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
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from fastapi import FastAPI, HTTPException
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
from router.app.routing import RoutingPolicy

ESCALATION_APPROVAL_TIMEOUT_SECONDS = 300.0


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


async def _consume_stream(
    stream_order_fn: StreamOrderFn,
    model_id: str,
    prompt: str,
    *,
    settings: Settings,
    request_id: str,
) -> AsyncIterator[Any]:
    """Wrap a raw OpenRouter stream, emitting periodic `generating` ticks
    per settings.generating_tick_tokens / generating_tick_seconds, and
    yield a final ("__final__", text, tokens_out, finish_reason, usage)
    sentinel tuple once the stream ends."""

    accumulated_text = ""
    tokens_out = 0
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    last_tick_time = time.monotonic()
    tokens_since_tick = 0

    async for chunk in stream_order_fn(model_id, prompt):
        if chunk.is_final:
            break
        if chunk.content_delta:
            accumulated_text += chunk.content_delta
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
            yield GeneratingEvent(request_id=request_id, tokens_out=tokens_out, est_cost_usd=0.0)
            tokens_since_tick = 0
            last_tick_time = now

    if usage and isinstance(usage.get("completion_tokens"), int):
        tokens_out = usage["completion_tokens"]

    yield ("__final__", accumulated_text, tokens_out, finish_reason, usage)


async def run_order(
    state: RouterState,
    *,
    prompt: str,
    attachments: Optional[List[ClassifierAttachment]] = None,
    request_id: Optional[str] = None,
    stream_order_fn: StreamOrderFn = stream_order,
    wait_for_approval: Optional[Callable[[str], "asyncio.Future[str]"]] = None,
) -> AsyncIterator[BaseEvent]:
    """Core orchestration generator. Pure aside from stream_order_fn (an
    injectable OpenRouter caller) and wait_for_approval (an injectable
    approval-wait function) - both default to real implementations but
    tests always inject fakes, so no network call happens in tests."""

    request_id = request_id or str(uuid.uuid4())
    started_at = time.monotonic()

    yield OrderReceivedEvent(request_id=request_id, prompt_chars=len(prompt))
    yield ClassifyingEvent(request_id=request_id)

    classification = classify(
        prompt,
        attachments,
        model_fallback_enabled=state.settings.classifier_model_fallback_enabled,
    )

    route = state.routing_policy.select_route(classification.task_type)
    yield RouteSelectedEvent(
        request_id=request_id,
        bean_alias=route.bean_alias,
        task_type=classification.task_type,
        complexity=classification.complexity,
        est_cost_usd=route.est_cost_usd,
        policy_entry=route.policy_entry,
    )

    bean = state.bean_registry.by_alias(route.bean_alias)
    model_id = bean.model_id
    tokens_in = max(1, len(prompt) // 4)

    try:
        final_text = ""
        tokens_out = 0
        finish_reason = None
        async for item in _consume_stream(
            stream_order_fn, model_id, prompt, settings=state.settings, request_id=request_id
        ):
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
            async for item in _run_escalation(state, request_id, premium_bean, prompt, stream_order_fn):
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
                    state, request_id, premium_bean, prompt, stream_order_fn
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
        )
    )


async def _run_escalation(state, request_id, premium_bean, prompt, stream_order_fn):
    """Async generator: relays `generating` ticks from the premium re-run,
    then yields a ("__escalation_final__", text, tokens_out) sentinel."""

    final_text = ""
    tokens_out = 0
    async for item in _consume_stream(
        stream_order_fn, premium_bean.model_id, prompt, settings=state.settings, request_id=request_id
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


class RetryRequest(BaseModel):
    request_id: str


class ApproveEscalationRequest(BaseModel):
    request_id: str
    approve: bool


def create_app(state: Optional[RouterState] = None) -> FastAPI:
    app = FastAPI(title="Coffee Core Router")

    if state is None:
        config_paths = load_router_config_paths()
        assert_no_key_like_strings(config_paths)
        bean_registry = BeanRegistry.from_yaml()
        routing_policy = RoutingPolicy.from_yaml(bean_registry=bean_registry)
        settings = Settings.from_yaml()
        ledger = RouterLedger()
        state = RouterState(
            bean_registry=bean_registry,
            routing_policy=routing_policy,
            settings=settings,
            ledger=ledger,
        )

    app.state.coffee = state

    @app.post("/v1/order")
    async def order(body: OrderRequest):
        events = run_order(
            app.state.coffee,
            prompt=body.prompt,
            stream_order_fn=app.state.coffee.stream_order_fn,
        )
        return StreamingResponse(sse_stream(events), media_type="text/event-stream")

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

    return app


app = create_app()
