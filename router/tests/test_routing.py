import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from router.app.aliases import Bean, BeanRegistry
from router.app.routing import (
    NoToolCallingBeanError,
    NoVisionBeanError,
    RoutingError,
    RoutingPolicy,
    estimate_cost_usd,
)


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

    def test_est_cost_usd_is_real_for_a_paid_bean_given_tokens(self):
        """Spend-cap Brew: the old placeholder returned None for every
        paid Bean unconditionally - this is the fix. FIXTURE_POLICY's
        "code" task_type routes to House Blend (free), so this uses a
        registry/policy built to route straight to a priced Bean."""

        registry = BeanRegistry(
            [
                Bean(
                    alias="Reserve Blend",
                    role="default",
                    model_id="vendor/premium",
                    vision=False,
                    code=True,
                    price_per_1k_input_usd=1.0,
                    price_per_1k_output_usd=2.0,
                    status="active",
                )
            ]
        )
        policy = RoutingPolicy({"task_types": {}}, registry)
        decision = policy.select_route("code", tokens_in=1000, assumed_output_tokens=500)
        # (1000/1000 * 1.0) + (500/1000 * 2.0) = 2.0
        self.assertEqual(decision.est_cost_usd, 2.0)

    def test_est_cost_usd_defaults_to_zero_tokens_when_not_given(self):
        """Callers that don't care about a real estimate (most existing
        tests) get a predictable 0.0 for a priced Bean, not a crash or a
        stale placeholder - tokens_in/assumed_output_tokens default to 0."""

        registry = BeanRegistry(
            [
                Bean(
                    alias="Reserve Blend",
                    role="default",
                    model_id="vendor/premium",
                    vision=False,
                    code=True,
                    price_per_1k_input_usd=1.0,
                    price_per_1k_output_usd=2.0,
                    status="active",
                )
            ]
        )
        policy = RoutingPolicy({"task_types": {}}, registry)
        decision = policy.select_route("code")
        self.assertEqual(decision.est_cost_usd, 0.0)

    def test_manual_route_est_cost_usd_is_real(self):
        registry = _make_registry()
        # House Blend is free-tier - use a priced Bean via a fresh registry.
        priced_registry = BeanRegistry(
            registry.all_beans()
            + [
                Bean(
                    alias="Priced Bean",
                    role="specialist",
                    model_id="vendor/priced",
                    vision=False,
                    code=True,
                    price_per_1k_input_usd=0.5,
                    price_per_1k_output_usd=1.5,
                    status="active",
                )
            ]
        )
        policy = RoutingPolicy(FIXTURE_POLICY, priced_registry)
        decision = policy.manual_route("code", "Priced Bean", tokens_in=2000, assumed_output_tokens=1000)
        # (2000/1000 * 0.5) + (1000/1000 * 1.5) = 2.5
        self.assertEqual(decision.est_cost_usd, 2.5)

    def test_select_fallback_route_est_cost_usd_is_real(self):
        registry = BeanRegistry(
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
                    model_id="vendor/priced-fallback",
                    vision=False,
                    code=True,
                    price_per_1k_input_usd=1.0,
                    price_per_1k_output_usd=1.0,
                    status="active",
                ),
            ]
        )
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        primary = policy.select_route("code")
        fallback = policy.select_fallback_route(primary, tokens_in=1000, assumed_output_tokens=1000)
        self.assertEqual(fallback.est_cost_usd, 2.0)

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


def _make_registry_with_two_tool_calling_beans():
    """House Blend (default, free, no tool_calling) plus two capable
    Beans priced so the cheaper one (Cheap Capable) is not the premium
    role - proves capable_bean() picks by price, not by role."""

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
                alias="Expensive Capable",
                role="premium",
                model_id="vendor/expensive",
                vision=False,
                code=True,
                tool_calling=True,
                price_per_1k_input_usd=0.003,
                price_per_1k_output_usd=0.015,
                status="active",
            ),
            Bean(
                alias="Cheap Capable",
                role="specialist",
                model_id="vendor/cheap",
                vision=False,
                code=True,
                tool_calling=True,
                price_per_1k_input_usd=0.001,
                price_per_1k_output_usd=0.005,
                status="active",
            ),
        ]
    )


class CapableBeanTests(unittest.TestCase):
    """BeanRegistry.capable_bean() - docs/design/web-search-design.md."""

    def test_picks_cheapest_capable_bean_not_role_default_or_premium(self):
        registry = _make_registry_with_two_tool_calling_beans()
        bean = registry.capable_bean(tool_calling=True)
        self.assertEqual(bean.alias, "Cheap Capable")

    def test_real_beans_yaml_cheapest_capable_bean_is_flat_white(self):
        """Real-config regression lock, updated for the Gemini/Gemma
        investigation Brew: Flat White (google/gemini-2.5-flash-lite,
        combined ~0.0005/1k) is now the genuinely cheapest tool-calling-
        capable Bean, cheaper than DeepSeek V3.2's ~0.000669/1k (the
        previous answer, see git history) and Kimi K2's ~0.00287/1k -
        plain cheapest-price selection (no prefer_alias) must reflect
        that. role="specialist" does NOT hold Flat White back here -
        capable_bean() has no role filter at all (confirmed by reading it
        and by this test)."""

        registry = BeanRegistry.from_yaml()
        bean = registry.capable_bean(tool_calling=True)
        self.assertEqual(bean.alias, "Flat White")

    def test_real_beans_yaml_cheapest_vision_and_tool_calling_bean_is_flat_white(self):
        """The /v1/chat/completions tools+image path and any future
        vision+tools /v1/order request both go through capable_bean(
        tool_calling=True, vision=True) - Flat White (vision: true,
        tool_calling: true, ~0.0005/1k) beats Single Origin (~0.006/1k),
        the previous answer, immediately on addition."""

        registry = BeanRegistry.from_yaml()
        bean = registry.capable_bean(tool_calling=True, vision=True)
        self.assertEqual(bean.alias, "Flat White")

    def test_real_beans_yaml_day_roast_never_wins_tool_calling_selection(self):
        """Day Roast (google/gemma-4-31b-it:free) reports tools/tool_choice
        as accepted parameters in a live GET /v1/models response, but
        tool_calling is deliberately left false in beans.yaml until a real
        Cup Test verifies it holds up (same "unverified/free-tier" caution
        as every other free Bean here) - so despite being the cheapest
        possible price (free) and vision-capable, it must never be
        selected by a tool_calling-constrained call, with or without a
        vision requirement alongside it."""

        registry = BeanRegistry.from_yaml()
        self.assertNotEqual(registry.capable_bean(tool_calling=True).alias, "Day Roast")
        self.assertNotEqual(
            registry.capable_bean(tool_calling=True, vision=True).alias, "Day Roast"
        )

    def test_real_beans_yaml_use_web_routes_to_kimi_with_real_preference(self):
        """The actual production behavior use_web routing exercises: with
        the real settings.yaml default (preferred_web_search_bean_alias=
        "Kimi K2"), the preference wins outright over both DeepSeek V3.2's
        and Flat White's lower price - prefer_alias is checked before the
        price comparison, so a merely-cheaper new Bean can never silently
        displace an explicit preference."""

        registry = BeanRegistry.from_yaml()
        bean = registry.capable_bean(tool_calling=True, prefer_alias="Kimi K2")
        self.assertEqual(bean.alias, "Kimi K2")

    def test_no_candidates_returns_none(self):
        registry = _make_registry()  # no tool_calling=True Bean at all
        self.assertIsNone(registry.capable_bean(tool_calling=True))

    def test_prefer_alias_wins_over_cheaper_candidate(self):
        """Web search cost optimization Brew: prefer_alias is an explicit
        opt-in override - "Expensive Capable" is pricier than "Cheap
        Capable" here, but must still win when preferred."""

        registry = _make_registry_with_two_tool_calling_beans()
        bean = registry.capable_bean(tool_calling=True, prefer_alias="Expensive Capable")
        self.assertEqual(bean.alias, "Expensive Capable")

    def test_prefer_alias_none_keeps_cheapest_price_behavior(self):
        """Every caller before this Brew passes nothing and must see
        unchanged behavior."""

        registry = _make_registry_with_two_tool_calling_beans()
        bean = registry.capable_bean(tool_calling=True, prefer_alias=None)
        self.assertEqual(bean.alias, "Cheap Capable")

    def test_prefer_alias_not_a_candidate_falls_through_to_cheapest(self):
        """A preferred alias that doesn't exist, isn't capable, or isn't
        available must never crash or silently return None - it just
        isn't a candidate, so cheapest-price selection proceeds among the
        real ones. This is what makes a removed/renamed preferred Bean
        degrade to its cheaper fallback instead of breaking web search."""

        registry = _make_registry_with_two_tool_calling_beans()
        bean = registry.capable_bean(tool_calling=True, prefer_alias="Nonexistent Bean")
        self.assertEqual(bean.alias, "Cheap Capable")

    def test_prefer_alias_that_lacks_the_required_capability_is_ignored(self):
        """A prefer_alias naming a real Bean that just isn't tool_calling
        (e.g. House Blend) must not be returned anyway - it's filtered out
        of the candidate pool before the preference check ever runs."""

        registry = _make_registry_with_two_tool_calling_beans()
        bean = registry.capable_bean(tool_calling=True, prefer_alias="House Blend")
        self.assertEqual(bean.alias, "Cheap Capable")

    def test_combined_vision_and_tool_calling_filter(self):
        registry = BeanRegistry(
            [
                Bean(
                    alias="Tool Only",
                    role="premium",
                    model_id="vendor/tool-only",
                    vision=False,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.001,
                    price_per_1k_output_usd=0.001,
                    status="active",
                ),
                Bean(
                    alias="Tool And Vision",
                    role="specialist",
                    model_id="vendor/tool-and-vision",
                    vision=True,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.005,
                    price_per_1k_output_usd=0.005,
                    status="active",
                ),
            ]
        )
        bean = registry.capable_bean(tool_calling=True, vision=True)
        self.assertEqual(bean.alias, "Tool And Vision")


class NeedsToolCallingConstraintTests(unittest.TestCase):
    """docs/design/web-search-design.md - mirrors VisionRoutingConstraintTests."""

    def test_select_route_preferred_tool_calling_bean_alias_wins_over_price(self):
        """Web search cost optimization Brew: select_route() threads
        preferred_tool_calling_bean_alias straight through to
        capable_bean()'s prefer_alias - "Expensive Capable" must win over
        the cheaper "Cheap Capable" when preferred."""

        registry = _make_registry_with_two_tool_calling_beans()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        decision = policy.select_route(
            "code", needs_tool_calling=True, preferred_tool_calling_bean_alias="Expensive Capable"
        )
        self.assertEqual(decision.bean_alias, "Expensive Capable")

    def test_select_route_no_preference_keeps_cheapest_price_behavior(self):
        registry = _make_registry_with_two_tool_calling_beans()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        decision = policy.select_route("code", needs_tool_calling=True)
        self.assertEqual(decision.bean_alias, "Cheap Capable")

    def test_select_route_no_web_needed_is_unconstrained(self):
        registry = _make_registry_with_two_tool_calling_beans()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        decision = policy.select_route("code", needs_tool_calling=False)
        self.assertEqual(decision.bean_alias, "House Blend")
        self.assertIsNone(decision.constraint_reason)

    def test_select_route_needs_tool_calling_escalates_to_cheapest_capable_bean(self):
        registry = _make_registry_with_two_tool_calling_beans()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        decision = policy.select_route("code", needs_tool_calling=True)
        self.assertEqual(decision.bean_alias, "Cheap Capable")
        self.assertIsNotNone(decision.constraint_reason)
        self.assertIn("needs_tool_calling", decision.constraint_reason)
        self.assertIn("House Blend", decision.constraint_reason)
        self.assertIn("Cheap Capable", decision.constraint_reason)

    def test_select_route_policy_bean_already_capable_is_unconstrained(self):
        capable_default = BeanRegistry(
            [
                Bean(
                    alias="Capable Blend",
                    role="default",
                    model_id="vendor/capable",
                    vision=False,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.001,
                    price_per_1k_output_usd=0.001,
                    status="active",
                )
            ]
        )
        policy = RoutingPolicy({"task_types": {}}, capable_default)
        decision = policy.select_route("code", needs_tool_calling=True)
        self.assertEqual(decision.bean_alias, "Capable Blend")
        self.assertIsNone(decision.constraint_reason)

    def test_select_route_preference_honoured_even_when_primary_bean_already_capable(self):
        """Regression test for the routing defect found during the
        free-Bean tool-calling verification Brew: the old
        `needs_tool_calling and not primary_bean.tool_calling` guard meant
        preferred_tool_calling_bean_alias was never even consulted once
        the primary Bean happened to already be tool_calling=True - so a
        real preference (e.g. settings.yaml's
        preferred_web_search_bean_alias="Kimi K2") would be silently
        bypassed the instant any primary/default Bean gained tool support,
        with no test catching it. House Blend here is both the primary
        Bean AND already tool_calling=True - the preferred Bean must still
        win outright."""

        registry = BeanRegistry(
            [
                Bean(
                    alias="House Blend",
                    role="default",
                    model_id="vendor/default:free",
                    vision=False,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.0,
                    price_per_1k_output_usd=0.0,
                    status="active",
                ),
                Bean(
                    alias="Preferred Search Bean",
                    role="web_search_primary",
                    model_id="vendor/preferred",
                    vision=False,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.001,
                    price_per_1k_output_usd=0.001,
                    status="active",
                ),
            ]
        )
        policy = RoutingPolicy({"task_types": {}}, registry)
        decision = policy.select_route(
            "code",
            needs_tool_calling=True,
            preferred_tool_calling_bean_alias="Preferred Search Bean",
        )
        self.assertEqual(decision.bean_alias, "Preferred Search Bean")
        self.assertIn("needs_tool_calling", decision.constraint_reason)
        self.assertIn("House Blend", decision.constraint_reason)
        self.assertIn("Preferred Search Bean", decision.constraint_reason)

    def test_select_route_preference_matching_primary_bean_stays_unconstrained(self):
        """The no-op guard: when the preferred alias IS the already-capable
        primary Bean, this must behave exactly like no preference was
        given at all - no spurious "escalated from X to X" reason, and no
        stale-preference warning (the preference resolved just fine)."""

        registry = BeanRegistry(
            [
                Bean(
                    alias="House Blend",
                    role="default",
                    model_id="vendor/default:free",
                    vision=False,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.0,
                    price_per_1k_output_usd=0.0,
                    status="active",
                ),
            ]
        )
        policy = RoutingPolicy({"task_types": {}}, registry)
        decision = policy.select_route(
            "code", needs_tool_calling=True, preferred_tool_calling_bean_alias="House Blend"
        )
        self.assertEqual(decision.bean_alias, "House Blend")
        self.assertIsNone(decision.constraint_reason)

    def test_select_route_stale_preference_falls_through_with_a_warning(self):
        """A preferred_tool_calling_bean_alias that no longer resolves to a
        qualifying Bean (renamed, removed, disabled, or lost its
        capability) must still fall through to cheapest-capable - matching
        capable_bean()'s existing documented fallthrough - but must never
        do so silently. This is what makes a broken preference visible
        instead of a permanent, undetectable behavior change."""

        registry = _make_registry_with_two_tool_calling_beans()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        with self.assertLogs("router.app.routing", level="WARNING") as log_ctx:
            decision = policy.select_route(
                "code",
                needs_tool_calling=True,
                preferred_tool_calling_bean_alias="Retired Preference",
            )
        self.assertEqual(decision.bean_alias, "Cheap Capable")
        self.assertTrue(
            any("Retired Preference" in msg and "Cheap Capable" in msg for msg in log_ctx.output)
        )

    def test_select_route_needs_tool_calling_no_capable_bean_anywhere_raises(self):
        registry = _make_registry()  # no tool_calling=True Bean at all
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        with self.assertRaises(NoToolCallingBeanError):
            policy.select_route("code", needs_tool_calling=True)

    def test_vision_and_tool_calling_constraints_combine_in_reason(self):
        """Vision-only Bean satisfies the vision escalation but not the
        tool_calling one - both constraints must fire and combine into one
        constraint_reason, landing on the one Bean with both capabilities."""

        registry = BeanRegistry(
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
                    alias="Vision Only",
                    role="fallback",
                    model_id="vendor/vision-only",
                    vision=True,
                    code=True,
                    price_per_1k_input_usd=0.0,
                    price_per_1k_output_usd=0.0,
                    status="active",
                ),
                Bean(
                    alias="Capable Vision Bean",
                    role="specialist",
                    model_id="vendor/capable-vision",
                    vision=True,
                    code=True,
                    tool_calling=True,
                    price_per_1k_input_usd=0.001,
                    price_per_1k_output_usd=0.001,
                    status="active",
                ),
            ]
        )
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        decision = policy.select_route("code", needs_vision=True, needs_tool_calling=True)
        self.assertEqual(decision.bean_alias, "Capable Vision Bean")
        self.assertIn("needs_vision", decision.constraint_reason)
        self.assertIn("needs_tool_calling", decision.constraint_reason)

    def test_manual_route_needs_tool_calling_with_capable_choice_succeeds(self):
        registry = _make_registry_with_two_tool_calling_beans()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        decision = policy.manual_route("code", "Cheap Capable", needs_tool_calling=True)
        self.assertEqual(decision.bean_alias, "Cheap Capable")

    def test_manual_route_needs_tool_calling_with_non_capable_choice_raises(self):
        """Manual override never silently substitutes - same rule as the
        vision constraint's manual-route test."""

        registry = _make_registry_with_two_tool_calling_beans()
        policy = RoutingPolicy(FIXTURE_POLICY, registry)
        with self.assertRaises(RoutingError):
            policy.manual_route("code", "House Blend", needs_tool_calling=True)


if __name__ == "__main__":
    unittest.main()
