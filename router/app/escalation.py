"""Failure checks and escalation engine for the Coffee Core Router.

Escalation states reuse the vocabulary already established in
docs/design/remote-call-approval-design.md Section 5 rather than inventing
a parallel one - `escalation_pending` and `escalating` map onto that
existing approval-state machine. This module is pure decision logic: it
does not call OpenRouter itself (see router/app/openrouter_client.py) and
does not write to the Ledger itself (see router/app/ledger.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

FailureReason = Literal["truncated", "empty", "refusal_shaped", "caller_reported"]


@dataclass(frozen=True)
class GenerationResult:
    text: str
    tokens_out: int
    finish_reason: Optional[str]
    caller_reported_failure: bool = False


@dataclass(frozen=True)
class FailureCheckResult:
    failed: bool
    reason: Optional[FailureReason] = None


def check_for_failure(
    result: GenerationResult,
    *,
    truncation_min_expected_tokens: int,
    refusal_keywords: List[str],
) -> FailureCheckResult:
    """Requirement 5's three failure checks, in priority order:
    truncation, empty/refusal-shaped, caller-reported."""

    if result.caller_reported_failure:
        return FailureCheckResult(failed=True, reason="caller_reported")

    if not result.text.strip():
        return FailureCheckResult(failed=True, reason="empty")

    lowered = result.text.strip().lower()
    if any(keyword in lowered for keyword in refusal_keywords):
        return FailureCheckResult(failed=True, reason="refusal_shaped")

    if (
        result.finish_reason == "length"
        or result.tokens_out < truncation_min_expected_tokens
    ):
        return FailureCheckResult(failed=True, reason="truncated")

    return FailureCheckResult(failed=False)


EscalationOutcome = Literal["auto_escalate", "escalation_pending", "no_premium_available"]


@dataclass(frozen=True)
class EscalationDecision:
    outcome: EscalationOutcome
    reason: FailureReason
    est_cost_usd: float
    premium_bean_alias: Optional[str]


def decide_escalation(
    failure: FailureCheckResult,
    *,
    premium_bean_alias: Optional[str],
    est_premium_cost_usd: Optional[float],
    escalation_cost_cap_usd: float,
) -> Optional[EscalationDecision]:
    """Decide whether a failed generation should auto-escalate, pause for
    approval, or cannot escalate at all (Section 3, Gap 1: no premium Bean
    has ever been selected in this repo, so this path is reachable and
    real, not hypothetical)."""

    if not failure.failed:
        return None

    assert failure.reason is not None  # failed=True always sets a reason

    if premium_bean_alias is None or est_premium_cost_usd is None:
        return EscalationDecision(
            outcome="no_premium_available",
            reason=failure.reason,
            est_cost_usd=0.0,
            premium_bean_alias=None,
        )

    if est_premium_cost_usd < escalation_cost_cap_usd:
        return EscalationDecision(
            outcome="auto_escalate",
            reason=failure.reason,
            est_cost_usd=est_premium_cost_usd,
            premium_bean_alias=premium_bean_alias,
        )

    return EscalationDecision(
        outcome="escalation_pending",
        reason=failure.reason,
        est_cost_usd=est_premium_cost_usd,
        premium_bean_alias=premium_bean_alias,
    )


# "cancelled" (Brew 40 - a POST /v1/cancel arriving while paused on
# escalation_pending, see docs/design/escalation-approval-ui-design.md
# Section 3.3) is a real outcome of the approval wait, but it is handled
# by the caller (router/app/main.py:_run_order_body) *before*
# resolve_pending_escalation() is ever invoked - a cancelled request
# yields CancelledEvent and returns immediately, the same as a cancel
# during generation, rather than resolving to any kind of completed
# result. resolve_pending_escalation() itself only ever needs to
# distinguish "approved" from "declined" (which a timeout also resolves
# to - see _await_approval), so its own signature stays a plain two-value
# decision, not three.
ApprovalResponse = Literal["approved", "declined"]


@dataclass(frozen=True)
class EscalationResolution:
    should_escalate: bool
    draft_quality: bool


def resolve_pending_escalation(response: ApprovalResponse) -> EscalationResolution:
    """The /v1/approve_escalation endpoint's business-logic outcome. This
    is a per-request approval gate distinct from the Governance
    human-approves-the-plan gate that authorized building this router in
    the first place - see docs/design/coffee-core-router-design.md
    Section 11."""

    if response == "approved":
        return EscalationResolution(should_escalate=True, draft_quality=False)
    return EscalationResolution(should_escalate=False, draft_quality=True)
