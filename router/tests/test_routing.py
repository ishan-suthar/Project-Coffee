import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from router.app.aliases import Bean, BeanRegistry
from router.app.routing import NoVisionBeanError, RoutingError, RoutingPolicy


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


class ManualRouteTests(unittest.TestCase):
    def setUp(self):
        self.registry = _make_registry()
        self.policy = RoutingPolicy(FIXTURE_POLICY, self.registry)

    def test_manual_route_selects_requested_bean(self):
        decision = self.policy.manual_route("code", "Second Pour")
        self.assertEqual(decision.bean_alias, "Second Pour")
        self.assertEqual(decision.policy_entry, "manual/second-pour")
        self.assertEqual(decision.policy_status, "manual_override")

    def test_manual_route_ignores_policy_entry_for_task_type(self):
        """Even though the fixture policy's "code" entry names House
        Blend as primary, a manual override to Second Pour must win."""

        decision = self.policy.manual_route("code", "Second Pour")
        self.assertNotEqual(decision.bean_alias, "House Blend")

    def test_manual_route_unavailable_bean_raises(self):
        with self.assertRaises(RoutingError):
            self.policy.manual_route("code", "Reserve Blend")  # model_id is None

    def test_manual_route_unknown_alias_raises(self):
        from router.app.aliases import AliasError

        with self.assertRaises(AliasError):
            self.policy.manual_route("code", "Nonexistent Alias")

    def test_manual_route_has_no_fallback_or_premium(self):
        decision = self.policy.manual_route("code", "House Blend")
        self.assertIsNone(decision.fallback_bean_alias)
        self.assertIsNone(decision.premium_bean_alias)


def _make_registry_with_vision_bean():
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
                alias="Vision Blend",
                role="fallback",
                model_id="vendor/vision:free",
                vision=True,
                code=True,
                price_per_1k_input_usd=0.0,
                price_per_1k_output_usd=0.0,
                status="active",
            ),
        ]
    )


class VisionRoutingConstraintTests(unittest.TestCase):
    """docs/design/attachments-design.md Section 6.2/7 Decision 1."""

    def test_select_route_no_vision_needed_is_unconstrained(self):
        registry = _make_registry_with_vision_bean()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        decision = policy.select_route("code", needs_vision=False)
        self.assertEqual(decision.bean_alias, "House Blend")
        self.assertIsNone(decision.constraint_reason)

    def test_select_route_needs_vision_escalates_to_vision_bean(self):
        registry = _make_registry_with_vision_bean()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        decision = policy.select_route("code", needs_vision=True)
        self.assertEqual(decision.bean_alias, "Vision Blend")
        self.assertIsNotNone(decision.constraint_reason)
        self.assertIn("needs_vision", decision.constraint_reason)
        self.assertIn("House Blend", decision.constraint_reason)
        self.assertIn("Vision Blend", decision.constraint_reason)

    def test_select_route_policy_bean_already_vision_capable_is_unconstrained(self):
        vision_default = BeanRegistry(
            [
                Bean(
                    alias="Vision Blend",
                    role="default",
                    model_id="vendor/vision:free",
                    vision=True,
                    code=True,
                    price_per_1k_input_usd=0.0,
                    price_per_1k_output_usd=0.0,
                    status="active",
                )
            ]
        )
        policy = RoutingPolicy({"task_types": {}}, vision_default)
        decision = policy.select_route("code", needs_vision=True)
        self.assertEqual(decision.bean_alias, "Vision Blend")
        self.assertIsNone(decision.constraint_reason)

    def test_select_route_needs_vision_no_vision_bean_anywhere_raises(self):
        """Real state as of Brew 38 - see test_aliases.py::
        test_real_config_has_no_vision_bean_today. Must raise a distinct,
        catchable error, never silently proceed without the image."""

        registry = _make_registry()  # no vision=True Bean at all
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        with self.assertRaises(NoVisionBeanError):
            policy.select_route("code", needs_vision=True)

    def test_manual_route_needs_vision_with_vision_capable_choice_succeeds(self):
        registry = _make_registry_with_vision_bean()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        decision = policy.manual_route("code", "Vision Blend", needs_vision=True)
        self.assertEqual(decision.bean_alias, "Vision Blend")

    def test_manual_route_needs_vision_with_non_vision_choice_raises(self):
        """Manual override never silently substitutes - unlike
        select_route()'s auto-escalation, a human's explicit non-vision
        choice for a vision-needing request must fail clearly, not swap
        Beans out from under them."""

        registry = _make_registry_with_vision_bean()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        with self.assertRaises(RoutingError):
            policy.manual_route("code", "House Blend", needs_vision=True)

    def test_real_generated_policy_needs_vision_raises_today(self):
        """Integration check against the real generated
        router/config/routing_policy.yaml and real beans.yaml - no vision
        Bean is configured, so this must raise, not silently drop images."""

        real_policy = RoutingPolicy.from_yaml()
        with self.assertRaises(NoVisionBeanError):
            real_policy.select_route("explain", needs_vision=True)


if __name__ == "__main__":
    unittest.main()
