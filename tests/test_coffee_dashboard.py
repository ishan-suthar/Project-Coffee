import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import coffee_dashboard


class CoffeeDashboardTests(unittest.TestCase):
    def write_file(self, root: Path, relative_path: str, text: str = "ok\n") -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def make_complete_root(self, root: Path) -> None:
        for relative_path in coffee_dashboard.CORE_FILES:
            self.write_file(root, relative_path)
        for relative_path in coffee_dashboard.TOOL_FILES:
            self.write_file(root, relative_path)
        for relative_path in coffee_dashboard.GUIDE_FILES:
            self.write_file(root, relative_path)
        self.write_file(
            root,
            "brew-log/active_context.md",
            "# Active Context\n\n"
            "## Current milestone\n\n"
            "Brew 99 - Test milestone\n\n"
            "## Next actions\n\n"
            "1. Brew 99B - next test action.\n",
        )
        self.write_file(
            root,
            "brew-log/progress.md",
            "# Progress\n\n"
            "## Current shot\n\n"
            "Brew 99A - test dashboard shot.\n",
        )
        self.write_file(
            root,
            "config/house_blend.md",
            "# House Blend\n\n"
            "## Current Blend\n\n"
            "| Route | Bean | Status | Why |\n"
            "| --- | --- | --- | --- |\n"
            "| Default Bean | bean/default | Provisional | Test row |\n",
        )

    def run_tool(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = coffee_dashboard.run(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_complete_root_reports_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            code, stdout, stderr = self.run_tool("--root", str(root))

            self.assertEqual(code, 0, stderr)
            self.assertIn("Project Coffee Dashboard", stdout)
            self.assertIn("Status: OK", stdout)
            self.assertIn("Active shot: Brew 99A - test dashboard shot.", stdout)

    def test_missing_required_files_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            (root / "AGENTS.md").unlink()

            code, stdout, stderr = self.run_tool("--root", str(root))

            self.assertEqual(code, 0, stderr)
            self.assertIn("Status: WARN", stdout)
            self.assertIn("AGENTS.md", stdout)

    def test_json_output_is_valid_and_structured(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            code, stdout, stderr = self.run_tool("--root", str(root), "--json")

            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["status"], "OK")
            self.assertIn("overview", payload["sections"])
            self.assertIn("docs", payload["sections"])

    def test_section_docs_reports_docs_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            code, stdout, stderr = self.run_tool("--root", str(root), "--section", "docs")

            self.assertEqual(code, 0, stderr)
            self.assertIn("## Docs", stdout)
            self.assertNotIn("## Tools", stdout)
            self.assertNotIn("## Roastery", stdout)

    def test_section_tools_reports_tools_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            code, stdout, stderr = self.run_tool("--root", str(root), "--section", "tools")

            self.assertEqual(code, 0, stderr)
            self.assertIn("## Tools", stdout)
            self.assertNotIn("## Docs", stdout)
            self.assertNotIn("## Roastery", stdout)

    def test_fail_on_missing_returns_nonzero_for_missing_core(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            (root / "PROJECT_COFFEE.md").unlink()

            code, stdout, stderr = self.run_tool(
                "--root",
                str(root),
                "--fail-on-missing",
            )

            self.assertEqual(code, 1)
            self.assertEqual(stderr, "")
            self.assertIn("Status: INCOMPLETE", stdout)
            self.assertIn("PROJECT_COFFEE.md", stdout)

    def test_does_not_read_ignored_local_output_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            self.write_file(
                root,
                "roastery/local_cup_outputs/sentinel.md",
                "local output text must not appear\n",
            )

            code, stdout, stderr = self.run_tool("--root", str(root))

            self.assertEqual(code, 0, stderr)
            self.assertIn("Local outputs: not inspected", stdout)
            self.assertNotIn("local output text must not appear", stdout)

    def test_missing_optional_guide_produces_warn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)
            missing = "docs/guides/pantry-search-guide.md"
            (root / missing).unlink()

            code, stdout, stderr = self.run_tool("--root", str(root))

            self.assertEqual(code, 0, stderr)
            self.assertIn("Status: WARN", stdout)
            self.assertIn(missing, stdout)

    def test_output_includes_next_action_from_active_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            code, stdout, stderr = self.run_tool("--root", str(root))

            self.assertEqual(code, 0, stderr)
            self.assertIn("Next action: Brew 99B - next test action.", stdout)

    def test_no_openrouter_key_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_complete_root(root)

            with mock.patch.dict(os.environ, {}, clear=True):
                code, stdout, stderr = self.run_tool("--root", str(root))

            self.assertEqual(code, 0, stderr)
            self.assertIn("Project Coffee Dashboard", stdout)


if __name__ == "__main__":
    unittest.main()
