"""SSE event models for the Coffee Core Router.

The full contract is documented with JSON examples in router/EVENT_CONTRACT.md.
Treat this contract as frozen once router/EVENT_CONTRACT.md is committed:
field additions should be additive-only, never a rename or removal, without
a version bump. See docs/design/coffee-core-router-design.md Section 4.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from router.app.history import HistoryDropReason


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WebSource(BaseModel):
    """One deduplicated web search citation (web search citations Brew) -
    url/title only, mirroring pantry_sources' path-only shape: a chip
    needs a link and a label, never the full excerpt/indices OpenRouter's
    annotation also carries. See CompleteEvent.web_sources."""

    url: str
    title: str


class BaseEvent(BaseModel):
    request_id: str
    ts: datetime = Field(default_factory=_now)

    def to_sse(self) -> str:
        """Render as one `data: <json>\\n\\n` Server-Sent Events frame."""

        return f"data: {self.model_dump_json()}\n\n"


class OrderReceivedEvent(BaseEvent):
    event: Literal["order_received"] = "order_received"
    prompt_chars: int


class ClassifyingEvent(BaseEvent):
    event: Literal["classifying"] = "classifying"


class RouteSelectedEvent(BaseEvent):
    event: Literal["route_selected"] = "route_selected"
    bean_alias: str
    task_type: str
    complexity: Literal["espresso_shot", "cold_brew"]
    est_cost_usd: Optional[float] = None
    policy_entry: str
    # Added in contract version 1.2 (Brew 38): why routing deviated from
    # the plain policy/manual pick, e.g. a vision-needing request being
    # escalated to a vision-capable Bean. None when routing was not
    # constrained by anything - the normal case. Optional and additive -
    # existing consumers that ignore it are unaffected. See
    # docs/design/attachments-design.md Section 6.3.
    constraint_reason: Optional[str] = None


class GeneratingEvent(BaseEvent):
    event: Literal["generating"] = "generating"
    tokens_out: int
    est_cost_usd: Optional[float] = None
    # Added in contract version 1.1 (Brew 37): the incremental text chunk
    # produced since the last tick, so a UI can render markdown as it
    # streams instead of waiting for `complete`. Optional and additive -
    # existing consumers that ignore it are unaffected. None on any
    # `generating` tick that produced no new visible text (should not
    # happen in practice, but kept optional for forward safety).
    text_delta: Optional[str] = None


class EscalationPendingEvent(BaseEvent):
    event: Literal["escalation_pending"] = "escalation_pending"
    reason: Literal["truncated", "empty", "refusal_shaped", "caller_reported"]
    est_cost_usd: float
    premium_bean_alias: Optional[str] = None
    # Added in contract version 1.3 (Brew 40): the UTC instant by which a
    # human must respond via POST /v1/approve_escalation before the pause
    # auto-declines (settings.escalation_approval_timeout_seconds after
    # this event). Lets a UI render an accurate countdown and later
    # distinguish "declined" from "timed out" without a new event - see
    # docs/design/escalation-approval-ui-design.md Section 3.4. Optional
    # and additive; None only if a premium Bean isn't configured, since
    # then there's nothing to wait for.
    decision_deadline: Optional[datetime] = None


class EscalatingEvent(BaseEvent):
    event: Literal["escalating"] = "escalating"
    bean_alias: str


class CompleteEvent(BaseEvent):
    event: Literal["complete"] = "complete"
    bean_alias: str
    tokens_in: int
    tokens_out: int
    cost_usd: Optional[float] = None
    latency_ms: int
    escalated: bool
    draft_quality: bool
    # Added in contract version 1.4 (Brew 41): the distinct repo-root-
    # relative source paths of the Pantry chunks actually injected into
    # this request's context (router/app/pantry.py) - not a model self-
    # report of what it "used." None when the request didn't ask for
    # Pantry retrieval (OrderRequest.use_pantry was false) or no chunks
    # matched - never an empty-but-claimed list. See docs/design/
    # memory-and-pantry-design.md Section 4.2.
    pantry_sources: Optional[List[str]] = None
    # Added in contract version 1.5 (Brew 46): how much conversation
    # history rode along on this request (router/app/history.py). Both
    # None when the session's remember_chat was false - deliberately not
    # 0, so a UI can tell "toggle is off" apart from "toggle is on but
    # this was turn one" (a real 0). See docs/design/
    # conversation-memory-design.md Section 4.
    history_turns: Optional[int] = None
    history_tokens_est: Optional[int] = None
    # Added in contract version 1.7 (Brew 57): what conversation history
    # was DROPPED to fit the window, so silent trimming becomes visible
    # (router/app/history.py's assemble_history). Same None-vs-0
    # convention as history_turns above: all three are None when the
    # session's remember_chat was false, and history_turns_dropped is a
    # real 0 - not None - when the toggle is on and nothing was dropped,
    # so a UI can tell "nothing was dropped" apart from "not applicable".
    # history_drop_reason is None if and only if history_turns_dropped is
    # 0. Never populated on GeneratingEvent: the three belong with the
    # other history fields on `complete`, and splitting them across two
    # events would let a consumer render half the picture.
    history_turns_dropped: Optional[int] = None
    history_chars_dropped: Optional[int] = None
    history_drop_reason: Optional[HistoryDropReason] = None
    # Added in contract version 1.6 (web search citations Brew): the
    # distinct source URLs OpenRouter's web search tool actually cited in
    # this request's response (router/app/openrouter_client.py's
    # StreamChunk.annotations), deduplicated by URL. None when use_web
    # was false, no citations arrived, or the request never reached
    # CompleteEvent's web_search_tools path - never an empty-but-claimed
    # list, same convention as pantry_sources. Never populated on
    # GeneratingEvent - citations arrive whole per annotation but are only
    # meaningful once the full set for a request is known, matching how
    # this was designed. See router/app/main.py's _distinct_web_sources().
    web_sources: Optional[List[WebSource]] = None


class ErrorEvent(BaseEvent):
    event: Literal["error"] = "error"
    error_type: str
    message: str
    retryable: bool


class CancelledEvent(BaseEvent):
    event: Literal["cancelled"] = "cancelled"
    reason: Literal["client_disconnect", "client_cancel_request"]


class HeartbeatEvent(BaseEvent):
    """Added in contract version 1.3 (Brew 40): a keep-alive frame sent
    when no real event has been queued for settings.sse_heartbeat_interval_seconds
    - purely to stop an idle connection (most likely during a long
    escalation_pending pause) from being dropped by a proxy or browser.
    No extra fields beyond the shared base. Any consumer must ignore this
    for state purposes - it never becomes a UI's "latest event"."""

    event: Literal["heartbeat"] = "heartbeat"


RouterEvent = Union[
    OrderReceivedEvent,
    ClassifyingEvent,
    RouteSelectedEvent,
    GeneratingEvent,
    EscalationPendingEvent,
    EscalatingEvent,
    CompleteEvent,
    ErrorEvent,
    CancelledEvent,
    HeartbeatEvent,
]
