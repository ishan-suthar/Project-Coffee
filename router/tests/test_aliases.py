import unittest

from router.app.aliases import AliasError, Bean, BeanRegistry


class BeanRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = BeanRegistry(
            [
                Bean(
                    alias="House Blend",
                    role="default",
                    model_id="vendor/default-model:free",
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
            ]
        )

    def test_from_yaml_loads_real_config(self):
        registry = BeanRegistry.from_yaml()
        aliases = registry.known_aliases()
        self.assertIn("House Blend", aliases)
        self.assertIn("Second Pour", aliases)
        self.assertIn("Guest Bean", aliases)
        self.assertIn("Reserve Blend", aliases)

    def test_alias_for_model_id_resolves(self):
        alias = self.registry.alias_for_model_id("vendor/default-model:free")
        self.assertEqual(alias, "House Blend")

    def test_alias_for_unknown_model_id_raises(self):
        with self.assertRaises(AliasError):
            self.registry.alias_for_model_id("vendor/nonexistent-model")

    def test_by_alias_unknown_raises(self):
        with self.assertRaises(AliasError):
            self.registry.by_alias("Nonexistent Alias")

    def test_model_id_for_alias(self):
        self.assertEqual(
            self.registry.model_id_for_alias("House Blend"), "vendor/default-model:free"
        )
        self.assertIsNone(self.registry.model_id_for_alias("Reserve Blend"))

    def test_premium_bean_not_available_when_model_id_is_null(self):
        premium = self.registry.by_role("premium")
        self.assertIsNotNone(premium)
        self.assertFalse(premium.is_available)

    def test_default_bean_is_available(self):
        default_bean = self.registry.by_role("default")
        self.assertTrue(default_bean.is_available)

    def test_by_role_unknown_role_returns_none(self):
        self.assertIsNone(self.registry.by_role("nonexistent-role"))

    def test_known_model_ids_excludes_null(self):
        ids = self.registry.known_model_ids()
        self.assertIn("vendor/default-model:free", ids)
        self.assertEqual(len(ids), 1)

    def test_vision_capable_beans_empty_when_none_configured(self):
        self.assertEqual(self.registry.vision_capable_beans(), [])

    def test_default_vision_bean_none_when_none_configured(self):
        self.assertIsNone(self.registry.default_vision_bean())

    def test_real_config_has_no_vision_bean_today(self):
        """Section 2, Gap 1 of docs/design/attachments-design.md: as of
        Brew 38, no Bean in the real beans.yaml has vision: true. This
        test documents that fact so it fails loudly (as a signal to
        update this test, not a bug) the day a vision Bean is added."""

        registry = BeanRegistry.from_yaml()
        self.assertEqual(registry.vision_capable_beans(), [])
        self.assertIsNone(registry.default_vision_bean())


class VisionCapableBeanTests(unittest.TestCase):
    def setUp(self):
        self.vision_default = Bean(
            alias="Vision Blend",
            role="default",
            model_id="vendor/vision-default:free",
            vision=True,
            code=True,
            price_per_1k_input_usd=0.0,
            price_per_1k_output_usd=0.0,
            status="active",
        )
        self.vision_fallback = Bean(
            alias="Vision Second",
            role="fallback",
            model_id="vendor/vision-fallback:free",
            vision=True,
            code=True,
            price_per_1k_input_usd=0.0,
            price_per_1k_output_usd=0.0,
            status="active",
        )
        self.non_vision = Bean(
            alias="Text Only",
            role="comparison",
            model_id="vendor/text-only:free",
            vision=False,
            code=True,
            price_per_1k_input_usd=0.0,
            price_per_1k_output_usd=0.0,
            status="active",
        )
        self.unavailable_vision = Bean(
            alias="Broken Vision",
            role="premium",
            model_id=None,
            vision=True,
            code=True,
            price_per_1k_input_usd=None,
            price_per_1k_output_usd=None,
            status="not_yet_selected",
        )

    def test_vision_capable_beans_excludes_non_vision(self):
        registry = BeanRegistry([self.vision_default, self.non_vision])
        result = registry.vision_capable_beans()
        self.assertEqual(result, [self.vision_default])

    def test_vision_capable_beans_excludes_unavailable(self):
        registry = BeanRegistry([self.unavailable_vision, self.non_vision])
        self.assertEqual(registry.vision_capable_beans(), [])

    def test_default_vision_bean_prefers_default_role(self):
        registry = BeanRegistry([self.vision_fallback, self.vision_default])
        self.assertEqual(registry.default_vision_bean(), self.vision_default)

    def test_default_vision_bean_falls_back_to_first_when_no_default_role(self):
        registry = BeanRegistry([self.vision_fallback, self.non_vision])
        self.assertEqual(registry.default_vision_bean(), self.vision_fallback)


if __name__ == "__main__":
    unittest.main()
