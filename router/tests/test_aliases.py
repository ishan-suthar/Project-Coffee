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


if __name__ == "__main__":
    unittest.main()
