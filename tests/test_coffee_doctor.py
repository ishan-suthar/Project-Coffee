import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import coffee_doctor


class CoffeeDoctorTests(unittest.TestCase):
    def write_file(self, root: Path, relative_path: str, text: str = "ok\n") -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def make_complete_root(self, root: Path) -> None:
        for relative_path in coffee_doctor.CORE_FILES:
            self.write_file(root, relative_path)
        self.write_file(root, "docs/README.md", "# Docs\n")
        for relative_path in coffee_doctor.GUIDE_FILES:
            self.write_file(root, relative_path, f"# {relative_path}\n")
        for relative_path in coffee_doctor.TOOL_FILES:
            self.write_file(root, relative_path)
        for relative_path in coffee_doctor.ROASTERY_FILES:
            self.write_file(root, relative_path)
        self.write_file(root, "ledger/cost_log.md")
        self.write_file(root, "knowledge/00_index.md")
        for relative_path in coffee_doctor.TEMPLATE_FILES:
            self.write_file(root, relative_path)
        (root / "TEMPLATES/project-coffee").mkdir(parents=True, exist_ok=True)
        ignore_text = "roastery/local_cup_outputs/\nroastery/local_reports/\n"
        for relative_path in coffee_doctor.IGNORE_FILES:
            self.write_file(root, relative_path, ignore_text)

    def run_tool(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = coffee_doctor.run(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_complete_temp_project_coffee_like_repo_has_no_fail_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            report = coffee_doctor.build_doctor_report(
                root,
                git_ls_files_func=lambda _root, _paths: [],
            )

            self.assertEqual(report["summary"]["FAIL"], 0)
            self.assertEqual(report["status"], "OK")

    def test_missing_agents_produces_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            (root / "AGENTS.md").unlink()

            report = coffee_doctor.build_doctor_report(
                root,
                git_ls_files_func=lambda _root, _paths: [],
            )

            self.assertGreater(report["summary"]["FAIL"], 0)
            self.assertTrue(
                any(finding["path"] == "AGENTS.md" and finding["severity"] == "FAIL" for finding in report["findings"])
            )

    def test_missing_docs_guide_produces_warn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            missing = "docs/guides/pantry-search-guide.md"
            (root / missing).unlink()

            report = coffee_doctor.build_doctor_report(
                root,
                section="docs",
                git_ls_files_func=lambda _root, _paths: [],
            )

            self.assertEqual(report["summary"]["FAIL"], 0)
            self.assertGreater(report["summary"]["WARN"], 0)
            self.assertTrue(
                any(finding.get("path") == missing and finding["severity"] == "WARN" for finding in report["findings"])
            )

    def test_tracked_local_output_path_produces_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            self.write_file(root, "roastery/local_cup_outputs/raw.txt", "raw output\n")

            report = coffee_doctor.build_doctor_report(
                root,
                section="roastery",
                git_ls_files_func=lambda _root, _paths: ["roastery/local_cup_outputs/raw.txt"],
            )

            self.assertGreater(report["summary"]["FAIL"], 0)
            self.assertTrue(
                any(finding["code"] == "local-artifact-tracked" for finding in report["findings"])
            )

    def test_ignored_local_output_path_present_but_untracked_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            (root / "roastery/local_cup_outputs").mkdir(parents=True)

            report = coffee_doctor.build_doctor_report(
                root,
                section="roastery",
                git_ls_files_func=lambda _root, _paths: [],
            )

            self.assertEqual(report["summary"]["FAIL"], 0)
            self.assertTrue(
                any(finding["code"] == "local-artifact-untracked" for finding in report["findings"])
            )

    def test_literal_secret_check_command_in_docs_produces_warn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            self.write_file(
                root,
                "docs/guides/coffee-doctor-guide.md",
                "# Guide\nRun git grep --cached -n -I -E from policy.\n",
            )

            report = coffee_doctor.build_doctor_report(
                root,
                section="docs",
                git_ls_files_func=lambda _root, _paths: [],
            )

            self.assertGreater(report["summary"]["WARN"], 0)
            self.assertTrue(
                any(finding["code"] == "literal-secret-check-command" for finding in report["findings"])
            )

    def test_json_output_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            code, stdout, stderr = self.run_tool("--root", str(root), "--json")

            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertIn("root", payload)
            self.assertIn("generated_at", payload)
            self.assertIn("status", payload)
            self.assertIn("findings", payload)
            self.assertIn("summary", payload)

    def test_section_tools_only_reports_tool_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            code, stdout, stderr = self.run_tool("--root", str(root), "--section", "tools")

            self.assertEqual(code, 0, stderr)
            self.assertIn("Project Coffee Doctor", stdout)
            self.assertIn("tools/coffee_dashboard.py", stdout)
            self.assertNotIn("AGENTS.md", stdout)
            self.assertNotIn("docs/README.md", stdout)

    def test_fail_on_issue_exits_nonzero_when_fail_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            (root / "AGENTS.md").unlink()

            code, stdout, stderr = self.run_tool(
                "--root",
                str(root),
                "--fail-on-issue",
            )

            self.assertEqual(code, 1)
            self.assertEqual(stderr, "")
            self.assertIn("Status: FAIL", stdout)

    def test_tool_does_not_require_openrouter_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            with mock.patch.dict(os.environ, {}, clear=True):
                code, stdout, stderr = self.run_tool("--root", str(root), "--section", "core")

            self.assertEqual(code, 0, stderr)
            self.assertIn("Project Coffee Doctor", stdout)


if __name__ == "__main__":
    unittest.main()
