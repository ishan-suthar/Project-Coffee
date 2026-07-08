import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from ui import coffee_counter_app


class CoffeeCounterAdapterTests(unittest.TestCase):
    def test_allowlisted_command_builds_expected_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = coffee_counter_app.build_command("dashboard", root=tmp)

        self.assertTrue(Path(args[0]).name.startswith("python"))
        self.assertEqual(Path(args[1]).name, "coffee.py")
        self.assertEqual(args[2:4], ["dashboard", "--root"])

    def test_disallowed_command_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(coffee_counter_app.CommandAdapterError):
                coffee_counter_app.build_command("commit", root=tmp)

    def test_root_path_validation_works(self) -> None:
        with self.assertRaises(coffee_counter_app.CommandAdapterError):
            coffee_counter_app.build_command("dashboard", root="definitely-missing-root")

    def test_evidence_bundle_query_is_passed_as_argument_list(self) -> None:
        query = 'House Blend"; git commit'
        with tempfile.TemporaryDirectory() as tmp:
            args = coffee_counter_app.build_command(
                "evidence-bundle",
                root=tmp,
                query=query,
                max_results=3,
            )

        self.assertIn("--query", args)
        self.assertEqual(args[args.index("--query") + 1], query)
        self.assertIn("--max-results", args)
        self.assertEqual(args[args.index("--max-results") + 1], "3")

    def test_evidence_bundle_json_args_are_built_safely(self) -> None:
        query = 'Coffee Counter"; git commit'
        with tempfile.TemporaryDirectory() as tmp:
            args = coffee_counter_app.build_command(
                "evidence-bundle",
                root=tmp,
                query=query,
                max_results=4,
                json_output=True,
            )

        self.assertIn("--json", args)
        self.assertEqual(args[args.index("--query") + 1], query)

    def test_display_command_formatting_is_copy_friendly(self) -> None:
        args = [
            sys.executable,
            "tools/coffee.py",
            "evidence-bundle",
            "--query",
            'House Blend"; git commit',
        ]

        formatted = coffee_counter_app.format_display_command(args)

        self.assertIn("evidence-bundle", formatted)
        self.assertIn("--query", formatted)
        self.assertIn("House Blend", formatted)
        self.assertIn("git commit", formatted)
        self.assertNotIn("\n", formatted)

    def test_evidence_json_parser_handles_valid_bundle_json(self) -> None:
        payload = {
            "query": "current Brew",
            "total_matches": 2,
            "bundle": [
                {
                    "source_path": "brew-log/progress.md",
                    "heading": "Current shot",
                    "snippet": "Current status: Brew 28A",
                    "reason_selected": "matched body",
                    "score": 9,
                    "freshness_signal": "Brew 28",
                    "safety_classification": "local-project-note",
                    "line_start": 9,
                    "line_end": 9,
                }
            ],
            "warnings": [],
        }

        bundle = coffee_counter_app.parse_evidence_bundle_json(json.dumps(payload))

        self.assertIsNone(bundle.parse_error)
        self.assertEqual(bundle.query, "current Brew")
        self.assertEqual(bundle.total_matches, 2)
        self.assertEqual(len(bundle.items), 1)
        self.assertEqual(bundle.items[0].reference, "brew-log/progress.md:9")

    def test_evidence_json_parser_handles_malformed_json(self) -> None:
        bundle = coffee_counter_app.parse_evidence_bundle_json("{not-json")

        self.assertIsNotNone(bundle.parse_error)
        self.assertEqual(bundle.items, [])
        self.assertEqual(coffee_counter_app.evidence_state(bundle), "json-parse-error")

    def test_local_evidence_draft_includes_source_path_and_snippet(self) -> None:
        bundle = coffee_counter_app.EvidenceBundle(
            query="current Brew",
            total_matches=1,
            items=[
                coffee_counter_app.EvidenceItem(
                    source_path="brew-log/progress.md",
                    heading="Current shot",
                    snippet="Current status: Brew 28A",
                    reason_selected="matched body",
                    score=9,
                    freshness_signal="Brew 28",
                    safety_classification="local-project-note",
                    line_start=9,
                    line_end=9,
                )
            ],
            warnings=[],
        )

        draft = coffee_counter_app.build_local_evidence_draft("What is next?", bundle)

        self.assertIn("Local evidence draft, not model-generated", draft)
        self.assertIn("brew-log/progress.md:9", draft)
        self.assertIn("Current status: Brew 28A", draft)
        self.assertIn("No model call was made.", draft)

    def test_local_evidence_draft_reports_insufficient_evidence(self) -> None:
        bundle = coffee_counter_app.EvidenceBundle(
            query="nonsense",
            total_matches=0,
            items=[],
            warnings=[],
        )

        draft = coffee_counter_app.build_local_evidence_draft("Nonsense?", bundle)

        self.assertIn("Evidence is insufficient", draft)
        self.assertIn("no local evidence matched", draft)

    def test_zero_match_state_is_handled(self) -> None:
        bundle = coffee_counter_app.EvidenceBundle(
            query="nonsense",
            total_matches=0,
            items=[],
            warnings=[],
        )

        self.assertEqual(coffee_counter_app.evidence_state(bundle), "no-evidence")

    def test_current_brew_request_routes_to_local_evidence_only(self) -> None:
        decision = coffee_counter_app.build_routing_decision(
            "What is the current Brew and next Shot?",
            [],
        )

        self.assertEqual(decision.selected_mode, coffee_counter_app.ROUTE_LOCAL_EVIDENCE)
        self.assertFalse(decision.approval_required)

    def test_docs_how_to_request_routes_to_local_evidence_only(self) -> None:
        decision = coffee_counter_app.build_routing_decision(
            "How to onboard a project from the docs?",
            [],
        )

        self.assertEqual(decision.request_class, "docs_how_to")
        self.assertEqual(decision.selected_mode, coffee_counter_app.ROUTE_LOCAL_EVIDENCE)

    def test_cost_token_request_references_ledger_and_local_evidence(self) -> None:
        decision = coffee_counter_app.build_routing_decision(
            "What did tokens and cost look like?",
            [],
        )

        self.assertEqual(decision.request_class, "cost_token")
        self.assertIn("Ledger", decision.allowed_context)
        self.assertEqual(decision.selected_mode, coffee_counter_app.ROUTE_LOCAL_EVIDENCE)

    def test_benchmark_request_requires_roastery_approval(self) -> None:
        decision = coffee_counter_app.build_routing_decision(
            "Run a model benchmark with Roastery",
            [],
        )

        self.assertEqual(decision.selected_mode, coffee_counter_app.ROUTE_ROASTERY_REQUIRED)
        self.assertTrue(decision.approval_required)
        self.assertTrue(coffee_counter_app.approval_required_for_route(decision.selected_mode))

    def test_code_change_request_requires_approval_before_remote_context(self) -> None:
        decision = coffee_counter_app.build_routing_decision(
            "Fix a tiny Python bug",
            [],
        )

        self.assertEqual(decision.request_class, "code_change")
        self.assertEqual(decision.selected_mode, coffee_counter_app.ROUTE_REMOTE_APPROVAL)
        self.assertTrue(decision.approval_required)

    def test_send_repo_context_requires_approval(self) -> None:
        decision = coffee_counter_app.build_routing_decision(
            "Send this repo context to a model",
            [],
        )

        self.assertEqual(decision.request_class, "send_repo_context")
        self.assertEqual(decision.selected_mode, coffee_counter_app.ROUTE_REMOTE_APPROVAL)
        self.assertTrue(decision.approval_required)

    def test_commit_request_is_manual_only_no_auto_commit(self) -> None:
        decision = coffee_counter_app.build_routing_decision(
            "Commit this and push it",
            [],
        )

        self.assertEqual(decision.request_class, "commit_or_push")
        self.assertEqual(decision.selected_mode, coffee_counter_app.ROUTE_DECAF)
        self.assertIn("must not stage, commit, push, or tag", decision.reason)
        self.assertIn("commits manually", decision.next_safe_action)

    def test_routing_decision_includes_reason_and_next_safe_action(self) -> None:
        decision = coffee_counter_app.build_routing_decision("What should I do next?", [])

        self.assertTrue(decision.reason)
        self.assertTrue(decision.next_safe_action)
        self.assertIn("Secrets", decision.blocked_context)

    def test_context_preview_includes_source_paths_and_snippets(self) -> None:
        item = coffee_counter_app.EvidenceItem(
            source_path="brew-log/progress.md",
            heading="Current shot",
            snippet="Current status: Brew 29A",
            reason_selected="matched body",
            score=10,
            freshness_signal="Brew 29",
            safety_classification="local-project-note",
            line_start=9,
            line_end=9,
        )

        preview = coffee_counter_app.format_context_preview([item], max_items=1)

        self.assertIn("Context preview only", preview)
        self.assertIn("brew-log/progress.md:9", preview)
        self.assertIn("Current status: Brew 29A", preview)

    def test_context_preview_handles_missing_evidence_cleanly(self) -> None:
        preview = coffee_counter_app.format_context_preview([], max_items=3)

        self.assertIn("No eligible evidence snippets", preview)
        self.assertIn("Excluded:", preview)

    def test_remote_model_execution_is_not_exposed(self) -> None:
        exposed_actions = " ".join(coffee_counter_app.ALLOWED_ACTIONS)

        self.assertNotIn("openrouter", exposed_actions.lower())
        self.assertNotIn("remote", exposed_actions.lower())
        self.assertNotIn("bean", exposed_actions.lower())

    def test_subprocess_result_captures_output_and_return_code(self) -> None:
        def fake_runner(args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 7, stdout="out", stderr="err")

        with tempfile.TemporaryDirectory() as tmp:
            result = coffee_counter_app.run_coffee_command(
                "doctor",
                root=tmp,
                runner=fake_runner,
            )

        self.assertEqual(result.stdout, "out")
        self.assertEqual(result.stderr, "err")
        self.assertEqual(result.return_code, 7)

    def test_timeout_behavior_is_handled(self) -> None:
        def timeout_runner(args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(cmd=args, timeout=timeout)

        with tempfile.TemporaryDirectory() as tmp:
            result = coffee_counter_app.run_coffee_command(
                "dashboard",
                root=tmp,
                timeout=1,
                runner=timeout_runner,
            )

        self.assertTrue(result.timed_out)
        self.assertEqual(result.return_code, 124)
        self.assertIn("timed out", result.stderr)

    def test_adapter_does_not_require_streamlit_import(self) -> None:
        self.assertNotIn("st", coffee_counter_app.__dict__)
        self.assertNotIn("streamlit", coffee_counter_app.__dict__)

    def test_no_shell_true_is_used(self) -> None:
        completed = subprocess.CompletedProcess(["python"], 0, stdout="", stderr="")
        with mock.patch.object(coffee_counter_app.subprocess, "run", return_value=completed) as run_mock:
            coffee_counter_app.default_runner(["python", "--version"], timeout=5)

        self.assertIs(run_mock.call_args.kwargs["shell"], False)

    def test_command_adapter_does_not_require_openrouter_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "not-used"}):
                args = coffee_counter_app.build_command("release-check", root=tmp)

        self.assertNotIn("not-used", args)
        self.assertNotIn("OPENROUTER_API_KEY", args)

    def test_fleet_status_registry_argument_forwards_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = coffee_counter_app.build_command(
                "fleet-status",
                root=tmp,
                registry="fleet/projects.example.json",
            )

        self.assertIn("--registry", args)
        self.assertEqual(args[args.index("--registry") + 1], "fleet/projects.example.json")


if __name__ == "__main__":
    unittest.main()
