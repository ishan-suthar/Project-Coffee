import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import fleet_status


class FleetStatusTests(unittest.TestCase):
    def make_root(self) -> tempfile.TemporaryDirectory[str]:
        return tempfile.TemporaryDirectory()

    def write_text(self, path: Path, text: str = "") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_registry(self, root: Path, projects: list[dict[str, object]], filename: str = "projects.json") -> Path:
        registry = root / "fleet" / filename
        self.write_text(registry, json.dumps({"version": 1, "projects": projects}, indent=2))
        return registry

    def make_onboarded_project(self, root: Path, name: str = "project") -> Path:
        project = root / name
        for relative_path in (
            "AGENTS.md",
            "PROJECT_COFFEE.md",
            "brew-log/active_context.md",
            "brew-log/progress.md",
            "ledger/cost_log.md",
            "roastery/tasting_notes.md",
            "knowledge/00_index.md",
        ):
            self.write_text(project / relative_path, f"# {relative_path}\n")
        return project

    def run_tool(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = fleet_status.run(list(args), stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_missing_registry_exits_zero_with_suggestion(self) -> None:
        with self.make_root() as temp:
            code, stdout, stderr = self.run_tool("--root", temp)

        self.assertEqual(code, 0, stderr)
        self.assertIn("Registry status: missing", stdout)
        self.assertIn("fleet/projects.example.json", stdout)

    def test_example_registry_parses(self) -> None:
        report = fleet_status.build_fleet_report(
            Path.cwd(),
            registry="fleet/projects.example.json",
        )

        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["summary"]["project_count"], 1)
        self.assertEqual(report["projects"][0]["id"], "project-id-goes-here")

    def test_valid_registry_lists_projects(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.write_registry(
                root,
                [
                    {
                        "id": "coffee-status",
                        "name": "Coffee Status",
                        "path": "apps/coffee-status",
                        "type": "app",
                        "status": "onboarded",
                    }
                ],
            )

            code, stdout, stderr = self.run_tool("--root", temp, "--list")

        self.assertEqual(code, 0, stderr)
        self.assertIn("coffee-status", stdout)
        self.assertIn("not-run", stdout)

    def test_json_output_is_valid(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.write_registry(
                root,
                [
                    {
                        "id": "alpha",
                        "name": "Alpha",
                        "path": "alpha",
                        "type": "app",
                        "status": "candidate",
                    }
                ],
            )
            code, stdout, stderr = self.run_tool("--root", temp, "--json")

        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["projects"][0]["id"], "alpha")
        self.assertIn("findings", payload)

    def test_project_filter_selects_one_project(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.write_registry(
                root,
                [
                    {"id": "alpha", "name": "Alpha", "path": "alpha", "type": "app", "status": "candidate"},
                    {"id": "beta", "name": "Beta", "path": "beta", "type": "app", "status": "candidate"},
                ],
            )
            report = fleet_status.build_fleet_report(temp, project_id="beta")

        self.assertEqual(report["summary"]["project_count"], 1)
        self.assertEqual(report["projects"][0]["id"], "beta")

    def test_unknown_project_fails_when_strict(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.write_registry(
                root,
                [{"id": "alpha", "name": "Alpha", "path": "alpha", "type": "app", "status": "candidate"}],
            )
            code, stdout, stderr = self.run_tool("--root", temp, "--project", "missing", "--fail-on-issue")

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertIn("project-not-found", stdout)

    def test_duplicate_ids_fail(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.write_registry(
                root,
                [
                    {"id": "same", "name": "One", "path": "one", "type": "app", "status": "candidate"},
                    {"id": "same", "name": "Two", "path": "two", "type": "app", "status": "candidate"},
                ],
            )
            report = fleet_status.build_fleet_report(temp)

        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(finding["code"] == "duplicate-project-id" for finding in report["findings"]))

    def test_invalid_json_fails(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            registry = root / "fleet" / "projects.json"
            self.write_text(registry, "{ invalid")
            code, stdout, stderr = self.run_tool("--root", temp, "--fail-on-issue")

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertIn("invalid-json", stdout)

    def test_check_identifies_complete_onboarded_project_as_ok(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.make_onboarded_project(root, "complete")
            self.write_registry(
                root,
                [
                    {
                        "id": "complete",
                        "name": "Complete",
                        "path": "complete",
                        "type": "app",
                        "status": "onboarded",
                    }
                ],
            )
            report = fleet_status.build_fleet_report(temp, check=True)

        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["projects"][0]["check_status"], "OK")
        self.assertTrue(any(finding["code"] == "project-onboarding-complete" for finding in report["findings"]))

    def test_check_identifies_missing_agents_as_fail(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            project = self.make_onboarded_project(root, "incomplete")
            (project / "AGENTS.md").unlink()
            self.write_registry(
                root,
                [
                    {
                        "id": "incomplete",
                        "name": "Incomplete",
                        "path": "incomplete",
                        "type": "app",
                        "status": "onboarded",
                    }
                ],
            )
            code, stdout, stderr = self.run_tool("--root", temp, "--check", "--fail-on-issue")

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertIn("AGENTS.md", stdout)
        self.assertIn("project-onboarding-file-missing", stdout)

    def test_hidden_or_unsafe_path_is_rejected(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.write_registry(
                root,
                [
                    {
                        "id": "unsafe",
                        "name": "Unsafe",
                        "path": ".ssh/project",
                        "type": "app",
                        "status": "candidate",
                    }
                ],
            )
            report = fleet_status.build_fleet_report(temp)

        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(finding["code"] == "unsafe-project-path" for finding in report["findings"]))

    def test_tool_does_not_read_env_file(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.make_onboarded_project(root, "safe")
            self.write_text(root / "safe" / ".env", "envsentinelvalue\n")
            self.write_registry(
                root,
                [{"id": "safe", "name": "Safe", "path": "safe", "type": "app", "status": "onboarded"}],
            )
            code, stdout, stderr = self.run_tool("--root", temp, "--check", "--json")

        self.assertEqual(code, 0, stderr)
        self.assertNotIn("envsentinelvalue", stdout)

    def test_tool_does_not_inspect_raw_local_outputs(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.make_onboarded_project(root, "safe")
            self.write_text(root / "safe" / "roastery" / "local_cup_outputs" / "raw.md", "rawsentinelvalue\n")
            self.write_registry(
                root,
                [{"id": "safe", "name": "Safe", "path": "safe", "type": "app", "status": "onboarded"}],
            )
            code, stdout, stderr = self.run_tool("--root", temp, "--check", "--json")

        self.assertEqual(code, 0, stderr)
        self.assertNotIn("rawsentinelvalue", stdout)

    def test_fail_on_issue_exits_nonzero_when_fail_exists(self) -> None:
        with self.make_root() as temp:
            root = Path(temp)
            self.write_registry(
                root,
                [{"id": "missing", "name": "Missing", "path": "missing", "type": "app", "status": "candidate"}],
            )
            code, _stdout, _stderr = self.run_tool("--root", temp, "--check", "--fail-on-issue")

        self.assertEqual(code, 1)

    def test_tool_does_not_require_openrouter_api_key(self) -> None:
        with self.make_root() as temp, mock.patch.dict(os.environ, {}, clear=True):
            code, stdout, stderr = self.run_tool("--root", temp)

        self.assertEqual(code, 0, stderr)
        self.assertIn("Project Coffee Fleet Status", stdout)


if __name__ == "__main__":
    unittest.main()
