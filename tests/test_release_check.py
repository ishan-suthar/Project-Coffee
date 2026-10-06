import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import release_check


def write_file(root: Path, relative_path: str, text: str = "ok\n") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_complete_root(root: Path) -> None:
    docs_index = "\n".join(guide.replace("docs/", "") for guide in release_check.CORE_GUIDES)
    write_file(root, "docs/README.md", docs_index)
    for guide in release_check.CORE_GUIDES:
        write_file(root, guide, "# Guide\n")
    for tool in release_check.TOOL_FILES:
        write_file(root, tool, "# tool\n")
    for template_path in release_check.TEMPLATE_PATHS:
        if template_path.endswith(".md"):
            write_file(root, template_path, "# Template\n")
        else:
            (root / template_path).mkdir(parents=True, exist_ok=True)
    for safety_file in ("AGENTS.md", "PROJECT_COFFEE.md"):
        write_file(root, safety_file, "# Safety\n")
    ignore_text = "roastery/local_cup_outputs/\nroastery/local_reports/\n"
    for ignore_file in release_check.IGNORE_FILES:
        write_file(root, ignore_file, ignore_text)
    write_file(root, "brew-log/active_context.md", "# Active\n")
    write_file(root, "brew-log/progress.md", "# Progress\n")
    write_file(root, "roastery/tasting_notes.md", "# Roastery\n")
    write_file(root, "ledger/cost_log.md", "# Ledger\n\n- Brew 19: local validation. Cost: none/local.\n")


def clean_git_status(_root: Path) -> list[str]:
    return []


def no_tags(_root: Path) -> list[str]:
    return []


def no_tracked_artifacts(_root: Path, _paths: list[str] | tuple[str, ...]) -> list[str]:
    return []


class ReleaseCheckTests(unittest.TestCase):
    def build_report(self, root: Path, section: str = "all") -> dict[str, object]:
        return release_check.build_release_report(
            root,
            section=section,
            git_status_func=clean_git_status,
            git_tag_func=no_tags,
            git_ls_files_func=no_tracked_artifacts,
        )

    def test_complete_project_like_root_has_no_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)

            report = self.build_report(root)

        self.assertEqual(report["summary"]["BLOCKER"], 0)
        self.assertIn(report["status"], {"OK", "WARN"})

    def test_missing_agents_is_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)
            (root / "AGENTS.md").unlink()

            report = self.build_report(root, section="safety")

        self.assertGreaterEqual(report["summary"]["BLOCKER"], 1)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("safety-files-missing", codes)

    def test_dirty_git_status_is_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)

            report = release_check.build_release_report(
                root,
                section="repo",
                git_status_func=lambda _root: [" M README.md"],
                git_tag_func=no_tags,
                git_ls_files_func=no_tracked_artifacts,
            )

        self.assertEqual(report["summary"]["WARN"], 1)
        self.assertEqual(report["findings"][0]["code"], "working-tree-dirty")

    def test_missing_release_guide_is_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)
            (root / "docs" / "guides" / "release-packaging-guide.md").unlink()

            report = self.build_report(root, section="docs")

        self.assertGreaterEqual(report["summary"]["WARN"], 1)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("guide-files-missing", codes)

    def test_tracked_local_output_is_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)

            report = release_check.build_release_report(
                root,
                section="safety",
                git_status_func=clean_git_status,
                git_tag_func=no_tags,
                git_ls_files_func=lambda _root, _paths: ["roastery/local_cup_outputs/raw.txt"],
            )

        self.assertGreaterEqual(report["summary"]["BLOCKER"], 1)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("local-artifact-tracked", codes)

    def test_json_output_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)
            stdout = io.StringIO()

            code = release_check.run(
                ["--root", str(root), "--json"],
                stdout=stdout,
                git_status_func=clean_git_status,
                git_tag_func=no_tags,
                git_ls_files_func=no_tracked_artifacts,
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertIn("summary", payload)
        self.assertIn("findings", payload)

    def test_section_tools_only_reports_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)
            stdout = io.StringIO()

            code = release_check.run(
                ["--root", str(root), "--section", "tools"],
                stdout=stdout,
                git_status_func=clean_git_status,
                git_tag_func=no_tags,
                git_ls_files_func=no_tracked_artifacts,
            )

        output = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("tools/coffee.py", output)
        self.assertNotIn("AGENTS.md", output)

    def test_fail_on_blocker_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)
            (root / "AGENTS.md").unlink()

            code = release_check.run(
                ["--root", str(root), "--section", "safety", "--fail-on-blocker"],
                stdout=io.StringIO(),
                git_status_func=clean_git_status,
                git_tag_func=no_tags,
                git_ls_files_func=no_tracked_artifacts,
            )

        self.assertEqual(code, 1)

    def test_missing_git_or_non_git_repo_is_graceful(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)

            report = release_check.build_release_report(
                root,
                section="all",
                git_status_func=lambda _root: None,
                git_tag_func=lambda _root: None,
                git_ls_files_func=lambda _root, _paths: None,
            )

        self.assertGreaterEqual(report["summary"]["INFO"], 1)
        self.assertEqual(report["summary"]["BLOCKER"], 0)

    def test_no_openrouter_api_key_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_complete_root(root)
            with mock.patch.dict(os.environ, {}, clear=True):
                code = release_check.run(
                    ["--root", str(root)],
                    stdout=io.StringIO(),
                    git_status_func=clean_git_status,
                    git_tag_func=no_tags,
                    git_ls_files_func=no_tracked_artifacts,
                )

        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
