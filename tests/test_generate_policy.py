import unittest

from tools.generate_policy import (
    RatingEvidence,
    ScoredRun,
    TaskTypeEvidence,
    build_policy,
    compute_escalation_rates,
    load_rating_evidence,
    render_policy_yaml,
)

BEANS_CONFIG = {
    "beans": [
        {"alias": "House Blend", "role": "default", "model_id": "vendor/house:free"},
        {"alias": "Second Pour", "role": "fallback", "model_id": "vendor/second:free"},
        {"alias": "Reserve Blend", "role": "premium", "model_id": None},
    ]
}


def _evidence_with_two_beans(house_score=7, second_score=6) -> dict:
    evidence = {task_type: TaskTypeEvidence() for task_type in ["code", "research", "explain", "refactor", "doc", "analysis"]}
    evidence["code"].runs = [
        ScoredRun(
            task_type="code",
            bean_model_id="vendor/house:free",
            score=house_score,
            tokens_total=500,
            source_heading="fixture",
            cup_test_file="roastery/cup_tests/002-tiny-python-fix.md",
        ),
        ScoredRun(
            task_type="code",
            bean_model_id="vendor/second:free",
            score=second_score,
            tokens_total=400,
            source_heading="fixture",
            cup_test_file="roastery/cup_tests/002-tiny-python-fix.md",
        ),
    ]
    return evidence


class LoadRatingEvidenceTests(unittest.TestCase):
    def test_averages_numeric_mapping_per_task_type_and_bean(self):
        rows = [
            {"task_type": "code", "bean_alias": "House Blend", "rating": "good"},
            {"task_type": "code", "bean_alias": "House Blend", "rating": "needed_fixing"},
            {"task_type": "code", "bean_alias": "House Blend", "rating": "failed"},
        ]
        result = load_rating_evidence(rows)
        evidence = result[("code", "House Blend")]
        self.assertEqual(evidence.rating_count, 3)
        self.assertAlmostEqual(evidence.avg_rating, 0.5)

    def test_empty_and_unknown_ratings_are_ignored(self):
        rows = [
            {"task_type": "code", "bean_alias": "House Blend", "rating": ""},
            {"task_type": "code", "bean_alias": "House Blend", "rating": "not_a_real_rating"},
        ]
        result = load_rating_evidence(rows)
        self.assertNotIn(("code", "House Blend"), result)

    def test_different_task_types_and_beans_kept_separate(self):
        rows = [
            {"task_type": "code", "bean_alias": "House Blend", "rating": "good"},
            {"task_type": "explain", "bean_alias": "House Blend", "rating": "failed"},
            {"task_type": "code", "bean_alias": "Second Pour", "rating": "failed"},
        ]
        result = load_rating_evidence(rows)
        self.assertAlmostEqual(result[("code", "House Blend")].avg_rating, 1.0)
        self.assertAlmostEqual(result[("explain", "House Blend")].avg_rating, 0.0)
        self.assertAlmostEqual(result[("code", "Second Pour")].avg_rating, 0.0)


class ComputeEscalationRatesTests(unittest.TestCase):
    def test_rate_is_escalated_over_total_for_that_task_type(self):
        rows = [
            {"task_type": "code", "escalated": "True"},
            {"task_type": "code", "escalated": "False"},
            {"task_type": "code", "escalated": "False"},
            {"task_type": "code", "escalated": "False"},
        ]
        rates = compute_escalation_rates(rows)
        self.assertAlmostEqual(rates["code"], 0.25)

    def test_task_type_with_zero_rows_is_absent(self):
        rates = compute_escalation_rates([{"task_type": "code", "escalated": "False"}])
        self.assertNotIn("explain", rates)


class BuildPolicyRatingsWeightingTests(unittest.TestCase):
    def test_below_sample_threshold_ranking_unaffected(self):
        """4 ratings, threshold 5: Second Pour's real ratings must not
        change anything - primary Bean stays whoever the unweighted Cup
        Test ranking already picked (House Blend, higher avg_score)."""

        evidence = _evidence_with_two_beans(house_score=7, second_score=6)
        ledger_rows = [
            {"task_type": "code", "bean_alias": "Second Pour", "rating": "good", "escalated": "False"}
        ] * 4

        policy = build_policy(
            evidence, BEANS_CONFIG, ledger_rows=ledger_rows, min_rating_sample_size=5, roastery_weight=0.6
        )
        self.assertEqual(policy["task_types"]["code"]["primary_bean_alias"], "House Blend")

    def test_at_threshold_low_rating_can_shift_primary_bean(self):
        """House Blend has the better Cup Test score but a real rock-
        bottom rating average once 5 real ratings land - the blended
        combined_score should let Second Pour take over as primary."""

        evidence = _evidence_with_two_beans(house_score=7, second_score=6)
        ledger_rows = (
            [{"task_type": "code", "bean_alias": "House Blend", "rating": "failed", "escalated": "False"}] * 5
            + [{"task_type": "code", "bean_alias": "Second Pour", "rating": "good", "escalated": "False"}] * 5
        )

        policy = build_policy(
            evidence, BEANS_CONFIG, ledger_rows=ledger_rows, min_rating_sample_size=5, roastery_weight=0.6
        )
        entry = policy["task_types"]["code"]
        self.assertEqual(entry["primary_bean_alias"], "Second Pour")
        self.assertIn("shifted the primary Bean", entry["reason"])
        self.assertIn("House Blend", entry["ratings"])
        self.assertEqual(entry["ratings"]["House Blend"]["rating_count"], 5)
        self.assertTrue(entry["ratings"]["House Blend"]["met_sample_threshold"])

    def test_no_ledger_rows_behaves_like_pre_brew_42(self):
        evidence = _evidence_with_two_beans(house_score=7, second_score=6)
        policy = build_policy(evidence, BEANS_CONFIG, ledger_rows=None)
        entry = policy["task_types"]["code"]
        self.assertEqual(entry["primary_bean_alias"], "House Blend")
        self.assertEqual(entry["ratings"], {})
        self.assertEqual(entry["escalation_rate"], 0.0)

    def test_escalation_candidates_flagged_above_threshold(self):
        evidence = _evidence_with_two_beans()
        ledger_rows = (
            [{"task_type": "code", "bean_alias": "House Blend", "escalated": "True"}] * 4
            + [{"task_type": "code", "bean_alias": "House Blend", "escalated": "False"}] * 6
        )
        policy = build_policy(
            evidence, BEANS_CONFIG, ledger_rows=ledger_rows, escalation_rate_flag_threshold=0.3
        )
        self.assertIn("code", policy["escalation_candidates"])
        self.assertEqual(policy["task_types"]["code"]["escalation_rate"], 0.4)

    def test_escalation_rate_at_or_below_threshold_not_flagged(self):
        evidence = _evidence_with_two_beans()
        ledger_rows = (
            [{"task_type": "code", "bean_alias": "House Blend", "escalated": "True"}] * 3
            + [{"task_type": "code", "bean_alias": "House Blend", "escalated": "False"}] * 7
        )
        policy = build_policy(
            evidence, BEANS_CONFIG, ledger_rows=ledger_rows, escalation_rate_flag_threshold=0.3
        )
        self.assertNotIn("code", policy["escalation_candidates"])

    def test_render_policy_yaml_round_trips_through_yaml_safe_load(self):
        import yaml

        evidence = _evidence_with_two_beans()
        policy = build_policy(evidence, BEANS_CONFIG, ledger_rows=[])
        text = render_policy_yaml(policy)
        parsed = yaml.safe_load(text)
        self.assertEqual(parsed["task_types"]["code"]["primary_bean_alias"], "House Blend")


if __name__ == "__main__":
    unittest.main()
