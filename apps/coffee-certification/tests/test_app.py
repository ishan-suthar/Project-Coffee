import contextlib
import io
import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import main


class AppTests(unittest.TestCase):
    def test_list_required_prints_required_steps(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["--list-required"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Decaf Mode", output.getvalue())
        self.assertIn("Manual commit", output.getvalue())

    def test_incomplete_report_returns_nonzero_status(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["--completed", "Decaf Mode"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Status: INCOMPLETE", output.getvalue())


if __name__ == "__main__":
    unittest.main()
