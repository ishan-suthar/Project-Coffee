import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from router.app.preferences import PreferenceStore


class PreferenceStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.store = PreferenceStore(Path(self._tmp_dir.name) / "preferences.db")

    def test_get_unknown_key_returns_none(self):
        self.assertIsNone(self.store.get("counter_collapsed"))

    def test_set_then_get_round_trips(self):
        self.store.set("counter_collapsed", "true")
        self.assertEqual(self.store.get("counter_collapsed"), "true")

    def test_set_overwrites_existing_value(self):
        self.store.set("counter_collapsed", "true")
        self.store.set("counter_collapsed", "false")
        self.assertEqual(self.store.get("counter_collapsed"), "false")

    def test_get_all_returns_every_key(self):
        self.store.set("counter_collapsed", "true")
        self.store.set("some_other_pref", "42")
        self.assertEqual(
            self.store.get_all(), {"counter_collapsed": "true", "some_other_pref": "42"}
        )

    def test_get_all_on_empty_store_returns_empty_dict(self):
        self.assertEqual(self.store.get_all(), {})

    def test_store_is_generic_not_tied_to_one_key_name(self):
        """This module must stay reusable for any future preference, not
        hardcoded to the counter's collapse state - see the module
        docstring."""

        self.store.set("arbitrary_future_preference", "value")
        self.assertEqual(self.store.get("arbitrary_future_preference"), "value")

    def test_persists_across_store_instances_on_same_path(self):
        path = Path(self._tmp_dir.name) / "shared.db"
        PreferenceStore(path).set("counter_collapsed", "true")
        reopened = PreferenceStore(path)
        self.assertEqual(reopened.get("counter_collapsed"), "true")


if __name__ == "__main__":
    unittest.main()
