import sys
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from src.status_builder import build_coffee_status


EXPECTED_TRACKED_PATHS = (
    "brew-log/active_context.md",
    "ROADMAP.md",
    "config/house_blend.md",
    "ledger/cost_log.md",
    "roastery/tasting_notes.md",
)


class StatusBuilderTests(unittest.TestCase):
    def test_builder_uses_explicit_project_root_and_tracks_mvp_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            status = build_coffee_status(project_root)

        self.assertEqual(status.project_root, project_root)
        self.assertEqual(
            tuple(file_status.relative_path for file_status in status.tracked_files),
            EXPECTED_TRACKED_PATHS,
        )

    def test_existing_and_missing_files_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._write_file(project_root, "brew-log/active_context.md", "active")
            self._write_file(project_root, "ledger/cost_log.md", "ledger")

            status = build_coffee_status(project_root)

        active_context = self._status_for(status, "brew-log/active_context.md")
        roadmap = self._status_for(status, "ROADMAP.md")
        ledger = self._status_for(status, "ledger/cost_log.md")

        self.assertTrue(active_context.exists)
        self.assertFalse(roadmap.exists)
        self.assertTrue(ledger.exists)

    def test_previewable_files_include_at_most_twenty_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            lines = [f"line {index}" for index in range(1, 26)]
            self._write_file(
                project_root,
                "brew-log/active_context.md",
                "\n".join(lines),
            )

            status = build_coffee_status(project_root)

        active_context = self._status_for(status, "brew-log/active_context.md")

        self.assertEqual(active_context.preview_lines, tuple(lines[:20]))

    def test_ledger_and_roastery_files_do_not_expose_preview_contents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._write_file(project_root, "ledger/cost_log.md", "cost detail")
            self._write_file(
                project_root,
                "roastery/tasting_notes.md",
                "model note",
            )

            status = build_coffee_status(project_root)

        ledger = self._status_for(status, "ledger/cost_log.md")
        roastery = self._status_for(status, "roastery/tasting_notes.md")

        self.assertTrue(ledger.exists)
        self.assertIsNone(ledger.preview_lines)
        self.assertTrue(roastery.exists)
        self.assertIsNone(roastery.preview_lines)

    def test_previewable_files_can_include_short_previews(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._write_file(project_root, "ROADMAP.md", "# Roadmap\nPhase 1")
            self._write_file(
                project_root,
                "config/house_blend.md",
                "# House Blend\nRouting",
            )

            status = build_coffee_status(project_root)

        roadmap = self._status_for(status, "ROADMAP.md")
        house_blend = self._status_for(status, "config/house_blend.md")

        self.assertEqual(roadmap.preview_lines, ("# Roadmap", "Phase 1"))
        self.assertEqual(house_blend.preview_lines, ("# House Blend", "Routing"))

    @staticmethod
    def _write_file(project_root: Path, relative_path: str, content: str) -> None:
        file_path = project_root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _status_for(status, relative_path: str):
        for file_status in status.tracked_files:
            if file_status.relative_path == relative_path:
                return file_status
        raise AssertionError(f"Missing file status for {relative_path}")


if __name__ == "__main__":
    unittest.main()
