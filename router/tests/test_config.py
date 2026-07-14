import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from router.app.config import Settings, StartupSafetyError, assert_no_key_like_strings


class SettingsTests(unittest.TestCase):
    def test_from_yaml_loads_real_config(self):
        settings = Settings.from_yaml()
        self.assertGreater(settings.escalation_cost_cap_usd, 0)
        self.assertGreater(settings.generating_tick_tokens, 0)
        self.assertFalse(settings.classifier_model_fallback_enabled)
        self.assertGreater(settings.escalation_approval_timeout_seconds, 0)
        self.assertGreater(settings.sse_heartbeat_interval_seconds, 0)
        self.assertEqual(settings.memory_proposal_bean_alias, "House Blend")
        self.assertGreater(settings.pantry_chunk_size_chars, 0)
        self.assertGreater(settings.pantry_top_k, 0)

    def test_defaults_when_field_missing(self):
        settings = Settings(**{})
        self.assertEqual(settings.escalation_cost_cap_usd, 0.50)
        self.assertEqual(settings.escalation_approval_timeout_seconds, 600.0)
        self.assertEqual(settings.sse_heartbeat_interval_seconds, 15.0)
        self.assertEqual(settings.memory_proposal_bean_alias, "House Blend")
        self.assertEqual(settings.memory_proposal_max_transcript_chars, 20_000)
        self.assertEqual(settings.pantry_chunk_size_chars, 1200)
        self.assertEqual(settings.pantry_chunk_overlap_chars, 200)
        self.assertEqual(settings.pantry_top_k, 5)


class StartupSafetyTests(unittest.TestCase):
    def test_clean_config_files_pass(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.yaml"
            path.write_text("alias: House Blend\nmodel_id: vendor/model:free\n", encoding="utf-8")
            assert_no_key_like_strings([path])  # should not raise

    def test_key_like_value_in_config_raises(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "leaky.yaml"
            path.write_text(
                "note: whoops sk-or-v1-abcdef0123456789abcd\n", encoding="utf-8"
            )
            with self.assertRaises(StartupSafetyError):
                assert_no_key_like_strings([path])

    def test_missing_file_is_skipped_not_error(self):
        missing = Path("/tmp/definitely-does-not-exist-router-config.yaml")
        assert_no_key_like_strings([missing])  # should not raise


if __name__ == "__main__":
    unittest.main()
