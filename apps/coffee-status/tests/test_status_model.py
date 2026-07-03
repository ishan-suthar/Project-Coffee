import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from src.status_model import CoffeeStatus, TrackedFileStatus


class StatusModelTests(unittest.TestCase):
    def test_coffee_status_represents_project_root(self):
        project_root = Path("Project_Coffee")

        status = CoffeeStatus(project_root=project_root)

        self.assertEqual(status.project_root, project_root)
        self.assertEqual(status.tracked_files, ())

    def test_tracked_file_represents_path_and_existence(self):
        file_status = TrackedFileStatus(
            relative_path="brew-log/active_context.md",
            exists=True,
        )

        self.assertEqual(file_status.relative_path, "brew-log/active_context.md")
        self.assertTrue(file_status.exists)
        self.assertIsNone(file_status.preview_lines)

    def test_tracked_file_represents_preview_lines(self):
        preview_lines = ("# Active Context", "", "Phase 1")

        file_status = TrackedFileStatus(
            relative_path="brew-log/active_context.md",
            exists=True,
            preview_lines=preview_lines,
        )

        self.assertEqual(file_status.preview_lines, preview_lines)

    def test_coffee_status_can_contain_multiple_tracked_files(self):
        project_root = Path("Project_Coffee")
        active_context = TrackedFileStatus(
            relative_path="brew-log/active_context.md",
            exists=True,
            preview_lines=("# Active Context",),
        )
        ledger = TrackedFileStatus(
            relative_path="ledger/cost_log.md",
            exists=False,
        )

        status = CoffeeStatus(
            project_root=project_root,
            tracked_files=(active_context, ledger),
        )

        self.assertEqual(status.tracked_files, (active_context, ledger))
        self.assertTrue(status.tracked_files[0].exists)
        self.assertFalse(status.tracked_files[1].exists)


if __name__ == "__main__":
    unittest.main()
