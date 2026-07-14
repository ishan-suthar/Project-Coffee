"""SSE event models for the Coffee Core Router.

The full contract is documented with JSON examples in router/EVENT_CONTRACT.md.
Treat this contract as frozen once router/EVENT_CONTRACT.md is committed:
field additions should be additive-only, never a rename or removal, without
a version bump. See docs/design/coffee-core-router-design.md Section 4.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
