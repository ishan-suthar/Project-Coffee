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
