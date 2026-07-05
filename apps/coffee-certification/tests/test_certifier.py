import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from src.certifier import (
    REQUIRED_WORKFLOW_STEPS,
    certify_workflow,
    format_markdown_report,
)


class CertifierTests(unittest.TestCase):
    def test_all_required_steps_complete_certification(self):
        result = certify_workflow(REQUIRED_WORKFLOW_STEPS)

        self.assertTrue(result.is_complete)
        self.assertEqual(result.completed_steps, REQUIRED_WORKFLOW_STEPS)
        self.assertEqual(result.missing_steps, ())
        self.assertEqual(result.unexpected_steps, ())

    def test_missing_steps_are_reported_in_required_order(self):
        result = certify_workflow(("Decaf Mode", "Planning", "Tests"))

        self.assertFalse(result.is_complete)
        self.assertEqual(
            result.missing_steps,
            (
                "Implementation",
                "Brew Log update",
                "Roastery entry",
                "Coffee Ledger entry",
                "House Blend usage",
                "Diff review",
                "Human approval",
                "Manual commit",
            ),
        )

    def test_completed_steps_are_normalized_and_deduplicated(self):
        result = certify_workflow(
            (
                " decaf-mode ",
                "DECAF MODE",
                "coffee_ledger_entry",
            )
        )

        self.assertEqual(
            result.completed_steps,
            ("Decaf Mode", "Coffee Ledger entry"),
        )

    def test_unexpected_steps_are_reported_once(self):
        result = certify_workflow(
            (
                "Decaf Mode",
                "Secret scan",
                "secret-scan",
            )
        )

        self.assertFalse(result.is_complete)
        self.assertEqual(result.unexpected_steps, ("Secret scan",))

    def test_report_marks_complete_result_as_pass(self):
        result = certify_workflow(REQUIRED_WORKFLOW_STEPS)

        report = format_markdown_report(result)

        self.assertIn("Status: PASS", report)
        self.assertIn("- None", report)


if __name__ == "__main__":
    unittest.main()
