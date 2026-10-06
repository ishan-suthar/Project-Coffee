import unittest

from tools import coffee_approval_dry_run
from tools import coffee_context_package


class ApprovalDryRunTests(unittest.TestCase):
    def package(self, *, approval_required: bool = True, request_text: str = "Use a model") -> dict[str, object]:
        return coffee_context_package.build_context_package(
            request_text=request_text,
            route_decision={
                "request_class": "remote_help_request",
                "selected_mode": "Remote Bean requires approval",
                "approval_required": approval_required,
                "reason": "dry run",
            },
            active_root="C:/Project_Coffee",
            evidence_items=[
                {
                    "source_path": "brew-log/progress.md",
                    "heading": "Current shot",
                    "snippet": "Current status: Brew 35A",
                    "score": 10,
                }
            ],
            brew_shot="Brew 35 / Shot 35A",
        )

    def complete_checklist(self) -> dict[str, bool]:
        return coffee_approval_dry_run.build_approval_checklist_state(
            coffee_approval_dry_run.REQUIRED_CHECKLIST_ITEMS
        )

    def test_local_only_package_does_not_require_approval(self) -> None:
        package = self.package(approval_required=False)
        checklist = self.complete_checklist()

        state = coffee_approval_dry_run.determine_approval_state(package)

        self.assertEqual(state, coffee_approval_dry_run.APPROVAL_LOCAL_ONLY)
        self.assertFalse(coffee_approval_dry_run.can_dry_run_approve(package, checklist))

    def test_approval_needed_safe_package_can_be_dry_run_approved_after_checklist(self) -> None:
        package = self.package()
        checklist = self.complete_checklist()

        self.assertTrue(coffee_approval_dry_run.can_dry_run_approve(package, checklist))
        state = coffee_approval_dry_run.determine_approval_state(
            package,
            checklist,
            dry_run_approved=True,
        )

        self.assertEqual(state, coffee_approval_dry_run.APPROVAL_DRY_RUN_APPROVED)

    def test_blocked_safety_package_cannot_be_dry_run_approved(self) -> None:
        package = self.package(request_text="Send my whole repo to a model.")
        checklist = self.complete_checklist()

        self.assertFalse(coffee_approval_dry_run.can_dry_run_approve(package, checklist))
        self.assertEqual(
            coffee_approval_dry_run.determine_approval_state(package, checklist),
            coffee_approval_dry_run.APPROVAL_BLOCKED,
        )

    def test_missing_package_cannot_be_approved(self) -> None:
        checklist = self.complete_checklist()

        self.assertFalse(coffee_approval_dry_run.can_dry_run_approve(None, checklist))
        self.assertEqual(
            coffee_approval_dry_run.determine_approval_state(None, checklist),
            coffee_approval_dry_run.APPROVAL_NEEDED,
        )

    def test_dry_run_ledger_preview_has_provider_model_placeholders_only(self) -> None:
        package = self.package()
        preview = coffee_approval_dry_run.build_dry_run_ledger_preview(
            package,
            coffee_approval_dry_run.APPROVAL_CONTEXT_READY,
        )

        self.assertIsNone(preview["provider"])
        self.assertIsNone(preview["model"])
        self.assertEqual(preview["provider_model_status"], "not_selected")

    def test_dry_run_ledger_preview_does_not_claim_write(self) -> None:
        preview = coffee_approval_dry_run.build_dry_run_ledger_preview(
            self.package(),
            coffee_approval_dry_run.APPROVAL_CONTEXT_READY,
        )

        self.assertEqual(preview["ledger_write_status"], "preview_only_not_written")
        self.assertEqual(preview["outcome"], "dry_run_only")

    def test_estimated_cost_is_none(self) -> None:
        preview = coffee_approval_dry_run.build_dry_run_ledger_preview(
            self.package(),
            coffee_approval_dry_run.APPROVAL_CONTEXT_READY,
        )

        self.assertIsNone(preview["estimated_cost"])

    def test_send_state_remains_disabled_future_brew(self) -> None:
        preview = coffee_approval_dry_run.build_dry_run_ledger_preview(
            self.package(),
            coffee_approval_dry_run.APPROVAL_DRY_RUN_APPROVED,
        )

        self.assertEqual(preview["send_state"], coffee_approval_dry_run.APPROVAL_SEND_DISABLED)

    def test_cancelled_state_is_explicit(self) -> None:
        state = coffee_approval_dry_run.determine_approval_state(
            self.package(),
            self.complete_checklist(),
            dry_run_cancelled=True,
        )

        self.assertEqual(state, coffee_approval_dry_run.APPROVAL_DRY_RUN_CANCELLED)


if __name__ == "__main__":
    unittest.main()
