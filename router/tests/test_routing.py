import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from router.app.aliases import Bean, BeanRegistry
from router.app.routing import RoutingError, RoutingPolicy


def _make_registry():
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
                alias="Second Pour",
                role="fallback",
                model_id="vendor/fallback:free",
                vision=False,
                code=True,
                price_per_1k_input_usd=0.0,
                price_per_1k_output_usd=0.0,
                status="active",
            ),
            Bean(
                alias="Reserve Blend",
                role="premium",
                model_id=None,
                vision=False,
                code=True,
                price_per_1k_input_usd=None,
                price_per_1k_output_usd=None,
                status="not_yet_selected",
            ),
            Bean(
                alias="Retired Bean",
                role="comparison",
                model_id="vendor/retired:free",
                vision=False,
                code=True,
                price_per_1k_input_usd=0.0,
                price_per_1k_output_usd=0.0,
                status="retired",
            ),
        ]
    )


FIXTURE_POLICY = {
    "task_types": {
        "code": {
            "status": "evidence_based",
            "primary_bean_alias": "House Blend",
            "fallback_bean_alias": "Second Pour",
            "premium_bean_alias": None,
            "evidence": ["roastery/cup_tests/002-tiny-python-fix.md"],
            "reason": "test fixture",
        },
        "research": {
            "status": "default",
            "primary_bean_alias": "House Blend",
            "fallback_bean_alias": None,
            "premium_bean_alias": None,
            "evidence": [],
            "reason": "no evidence",
        },
        "flaky": {
            "status": "evidence_based",
            "primary_bean_alias": "Retired Bean",
            "fallback_bean_alias": "Second Pour",
            "premium_bean_alias": None,
            "evidence": ["fixture"],
            "reason": "primary bean has since been retired",
        },
    }
}


class RoutingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.registry = _make_registry()
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)
        self.policy = RoutingPolicy.from_yaml(path, bean_registry=self.registry)

    def test_evidence_based_route_selects_primary_bean(self):
        decision = self.policy.select_route("code")
        self.assertEqual(decision.bean_alias, "House Blend")
        self.assertEqual(decision.fallback_bean_alias, "Second Pour")
        self.assertEqual(decision.policy_status, "evidence_based")
        self.assertEqual(decision.policy_entry, "code/house-blend")

    def test_default_route_uses_house_blend(self):
        decision = self.policy.select_route("research")
        self.assertEqual(decision.bean_alias, "House Blend")
        self.assertEqual(decision.policy_status, "default")

    def test_unknown_task_type_falls_back_to_default(self):
        decision = self.policy.select_route("nonexistent-task-type")
        self.assertEqual(decision.bean_alias, "House Blend")
        self.assertEqual(decision.policy_status, "default")

    def test_retired_primary_bean_falls_back_to_house_blend(self):
        """A policy entry pointing at a since-retired Bean must never
        silently use the retired Bean anyway - it must fail over to the
        configured House Blend default (Constitution: never represent
        unverified/stale routing as certain fact)."""

        decision = self.policy.select_route("flaky")
        self.assertEqual(decision.bean_alias, "House Blend")

    def test_select_fallback_route_returns_fallback_decision(self):
        primary = self.policy.select_route("code")
        fallback = self.policy.select_fallback_route(primary)
        self.assertIsNotNone(fallback)
        self.assertEqual(fallback.bean_alias, "Second Pour")

    def test_select_fallback_route_none_when_no_fallback_configured(self):
        primary = self.policy.select_route("research")
        fallback = self.policy.select_fallback_route(primary)
        self.assertIsNone(fallback)

    def test_est_cost_usd_is_zero_for_free_tier_bean(self):
        decision = self.policy.select_route("code")
        self.assertEqual(decision.est_cost_usd, 0.0)

    def test_est_cost_usd_is_none_when_pricing_unknown(self):
        registry_without_pricing = BeanRegistry(
            [
                Bean(
                    alias="House Blend",
                    role="default",
                    model_id="vendor/default:free",
                    vision=False,
                    code=True,
                    price_per_1k_input_usd=None,
                    price_per_1k_output_usd=None,
                    status="active",
                )
            ]
        )
        policy = RoutingPolicy(FIXTURE_POLICY, registry_without_pricing)
        decision = policy.select_route("code")
        self.assertIsNone(decision.est_cost_usd)

    def test_no_default_bean_configured_raises(self):
        empty_registry = BeanRegistry([])
        policy = RoutingPolicy({"task_types": {}}, empty_registry)
        with self.assertRaises(RoutingError):
            policy.select_route("code")

    def test_real_generated_policy_loads_and_routes(self):
        """Integration check against the real generated
        router/config/routing_policy.yaml, not a fixture."""

        real_policy = RoutingPolicy.from_yaml()
        decision = real_policy.select_route("code")
        self.assertIn(decision.bean_alias, {"House Blend", "Second Pour", "Guest Bean"})
        self.assertEqual(decision.policy_status, "evidence_based")

        research_decision = real_policy.select_route("research")
        self.assertEqual(research_decision.policy_status, "default")


if __name__ == "__main__":
    unittest.main()
