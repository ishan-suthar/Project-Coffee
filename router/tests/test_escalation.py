import unittest

from router.app.escalation import (
    GenerationResult,
    check_for_failure,
    decide_escalation,
    resolve_pending_escalation,
)

REFUSAL_KEYWORDS = ["i cannot help with that", "i'm not able to assist"]


class CheckForFailureTests(unittest.TestCase):
    def test_healthy_generation_does_not_fail(self):
        result = GenerationResult(text="Here is the answer." * 10, tokens_out=50, finish_reason="stop")
        check = check_for_failure(
            result, truncation_min_expected_tokens=32, refusal_keywords=REFUSAL_KEYWORDS
        )
        self.assertFalse(check.failed)

    def test_empty_response_fails(self):
        result = GenerationResult(text="   ", tokens_out=0, finish_reason="stop")
        check = check_for_failure(
            result, truncation_min_expected_tokens=32, refusal_keywords=REFUSAL_KEYWORDS
        )
        self.assertTrue(check.failed)
        self.assertEqual(check.reason, "empty")

    def test_refusal_shaped_response_fails(self):
        result = GenerationResult(
            text="I cannot help with that request.", tokens_out=40, finish_reason="stop"
        )
        check = check_for_failure(
            result, truncation_min_expected_tokens=32, refusal_keywords=REFUSAL_KEYWORDS
        )
        self.assertTrue(check.failed)
        self.assertEqual(check.reason, "refusal_shaped")

    def test_truncated_by_finish_reason_length(self):
        result = GenerationResult(text="Some long answer here", tokens_out=999, finish_reason="length")
        check = check_for_failure(
            result, truncation_min_expected_tokens=32, refusal_keywords=REFUSAL_KEYWORDS
        )
        self.assertTrue(check.failed)
        self.assertEqual(check.reason, "truncated")

    def test_truncated_by_low_token_count(self):
        result = GenerationResult(text="ok", tokens_out=3, finish_reason="stop")
        check = check_for_failure(
            result, truncation_min_expected_tokens=32, refusal_keywords=REFUSAL_KEYWORDS
        )
        self.assertTrue(check.failed)
        self.assertEqual(check.reason, "truncated")

    def test_caller_reported_failure_takes_priority(self):
        result = GenerationResult(
            text="Looks fine to me.",
            tokens_out=50,
            finish_reason="stop",
            caller_reported_failure=True,
        )
        check = check_for_failure(
            result, truncation_min_expected_tokens=32, refusal_keywords=REFUSAL_KEYWORDS
        )
        self.assertTrue(check.failed)
        self.assertEqual(check.reason, "caller_reported")


class DecideEscalationTests(unittest.TestCase):
    def test_no_decision_when_not_failed(self):
        healthy_check = check_for_failure(
            GenerationResult(text="fine " * 20, tokens_out=50, finish_reason="stop"),
            truncation_min_expected_tokens=32,
            refusal_keywords=REFUSAL_KEYWORDS,
        )
        decision = decide_escalation(
            healthy_check,
            premium_bean_alias="Reserve Blend",
            est_premium_cost_usd=0.10,
            escalation_cost_cap_usd=0.50,
        )
        self.assertIsNone(decision)

    def test_no_premium_bean_configured(self):
        """Section 3, Gap 1: no premium Bean has ever been selected. This
        must be an explicit, real outcome, not an exception or a silent
        substitution of the fallback Bean as if it were premium."""

        failed_check = check_for_failure(
            GenerationResult(text="", tokens_out=0, finish_reason="stop"),
            truncation_min_expected_tokens=32,
            refusal_keywords=REFUSAL_KEYWORDS,
        )
        decision = decide_escalation(
            failed_check,
            premium_bean_alias=None,
            est_premium_cost_usd=None,
            escalation_cost_cap_usd=0.50,
        )
        self.assertEqual(decision.outcome, "no_premium_available")
        self.assertIsNone(decision.premium_bean_alias)

    def test_auto_escalate_when_under_cap(self):
        failed_check = check_for_failure(
            GenerationResult(text="", tokens_out=0, finish_reason="stop"),
            truncation_min_expected_tokens=32,
            refusal_keywords=REFUSAL_KEYWORDS,
        )
        decision = decide_escalation(
            failed_check,
            premium_bean_alias="Reserve Blend",
            est_premium_cost_usd=0.10,
            escalation_cost_cap_usd=0.50,
        )
        self.assertEqual(decision.outcome, "auto_escalate")
        self.assertEqual(decision.est_cost_usd, 0.10)

    def test_escalation_pending_when_at_or_above_cap(self):
        failed_check = check_for_failure(
            GenerationResult(text="", tokens_out=0, finish_reason="stop"),
            truncation_min_expected_tokens=32,
            refusal_keywords=REFUSAL_KEYWORDS,
        )
        decision = decide_escalation(
            failed_check,
            premium_bean_alias="Reserve Blend",
            est_premium_cost_usd=0.50,  # exactly at cap
            escalation_cost_cap_usd=0.50,
        )
        self.assertEqual(decision.outcome, "escalation_pending")

    def test_escalation_pending_above_cap(self):
        failed_check = check_for_failure(
            GenerationResult(text="", tokens_out=0, finish_reason="stop"),
            truncation_min_expected_tokens=32,
            refusal_keywords=REFUSAL_KEYWORDS,
        )
        decision = decide_escalation(
            failed_check,
            premium_bean_alias="Reserve Blend",
            est_premium_cost_usd=5.00,
            escalation_cost_cap_usd=0.50,
        )
        self.assertEqual(decision.outcome, "escalation_pending")


class ResolvePendingEscalationTests(unittest.TestCase):
    def test_approved_continues_to_premium(self):
        resolution = resolve_pending_escalation("approved")
        self.assertTrue(resolution.should_escalate)
        self.assertFalse(resolution.draft_quality)

    def test_declined_returns_draft_quality_true(self):
        resolution = resolve_pending_escalation("declined")
        self.assertFalse(resolution.should_escalate)
        self.assertTrue(resolution.draft_quality)


if __name__ == "__main__":
    unittest.main()
