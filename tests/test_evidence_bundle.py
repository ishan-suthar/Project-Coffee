import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import evidence_bundle


class EvidenceBundleTests(unittest.TestCase):
    def write_file(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_binary(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def make_root(self, temp: str) -> Path:
        root = Path(temp)
        self.write_file(root / "PROJECT_COFFEE.md", "# Project Coffee\nCore rules.\n")
        self.write_file(root / "AGENTS.md", "# Agents\nBarista rules.\n")
        self.write_file(root / "ROADMAP.md", "# Roadmap\nBrew 22 next.\n")
        self.write_file(root / "CHANGELOG.md", "# Changelog\nBrew 21 complete.\n")
        self.write_file(root / "brew-log" / "active_context.md", "# Active\nCurrent Brew 22.\n")
        self.write_file(root / "brew-log" / "progress.md", "# Progress\nBrew 21 complete.\n")
        self.write_file(root / "docs" / "guides" / "local-rag-guide.md", "# Local RAG\nEvidence bundles cite files.\n")
        self.write_file(root / "docs" / "design" / "local-rag-design.md", "# Local RAG Design\nEvidence bundle format.\n")
        self.write_file(root / "knowledge" / "00_index.md", "# Pantry\nHouse Blend keywords.\n")
        self.write_file(root / "roastery" / "tasting_notes.md", "# Roastery\nNemotron scored well.\n")
        self.write_file(root / "ledger" / "cost_log.md", "# Ledger\nCost none local.\n")
        self.write_file(root / "config" / "house_blend.md", "# House Blend\nDefault Bean is Nemotron.\n")
        return root

    def run_tool(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = evidence_bundle.run(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_help_works(self) -> None:
        code, stdout, stderr = self.run_tool("--help")

        self.assertEqual(code, 0, stderr)
        self.assertIn("--query", stdout)
        self.assertIn("--list-sources", stdout)

    def test_list_sources_lists_safe_allowlisted_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)

            code, stdout, stderr = self.run_tool("--root", str(root), "--list-sources")

        self.assertEqual(code, 0, stderr)
        self.assertIn("PROJECT_COFFEE.md", stdout)
        self.assertIn("docs", stdout)
        self.assertNotIn(".env", stdout)
        self.assertNotIn("roastery/local_cup_outputs", stdout)

    def test_query_finds_matching_markdown_heading_and_snippet(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)

            report = evidence_bundle.build_bundle(root, "Local RAG")

        self.assertGreater(report["total_matches"], 0)
        first = report["bundle"][0]
        self.assertIn("local-rag", first["source_path"])
        self.assertIn("Local RAG", first["heading"])
        self.assertIn("score", first)
        self.assertIn("safety_classification", first)

    def test_json_output_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)

            code, stdout, stderr = self.run_tool("--root", str(root), "--query", "House Blend", "--json")

        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["query"], "House Blend")
        self.assertIn("bundle", payload)
        self.assertIn("sources_searched", payload)

    def test_output_writes_markdown_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            output_path = root / "bundle.md"

            code, stdout, stderr = self.run_tool(
                "--root",
                str(root),
                "--query",
                "House Blend",
                "--output",
                str(output_path),
            )

            self.assertEqual(code, 0, stderr)
            self.assertIn("Wrote evidence bundle", stdout)
            self.assertIn("Project Coffee Evidence Bundle", output_path.read_text(encoding="utf-8"))

    def test_output_with_json_writes_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            output_path = root / "bundle.json"

            code, _stdout, stderr = self.run_tool(
                "--root",
                str(root),
                "--query",
                "House Blend",
                "--json",
                "--output",
                str(output_path),
            )

            self.assertEqual(code, 0, stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["query"], "House Blend")

    def test_max_results_caps_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            self.write_file(root / "docs" / "extra.md", "# Coffee\nCoffee coffee coffee.\n")

            report = evidence_bundle.build_bundle(root, "coffee", max_results=2)

        self.assertGreaterEqual(report["total_matches"], 2)
        self.assertEqual(len(report["bundle"]), 2)

    def test_source_narrowing_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)

            report = evidence_bundle.build_bundle(root, "House Blend", requested_sources=["config/house_blend.md"])

        self.assertGreater(report["total_matches"], 0)
        self.assertTrue(all(item["source_path"] == "config/house_blend.md" for item in report["bundle"]))

    def test_invalid_source_narrowing_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            (root / "tmp").mkdir()

            code, stdout, stderr = self.run_tool("--root", str(root), "--query", "coffee", "--source", "tmp")

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Source is excluded", stderr)

    def test_excluded_directories_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            self.write_file(root / "docs" / "tmp" / "hidden.md", "# Hidden\nuniqueexcluded\n")

            report = evidence_bundle.build_bundle(root, "uniqueexcluded")

        self.assertEqual(report["total_matches"], 0)

    def test_env_file_is_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            self.write_file(root / ".env", "UNIQUE_ENV_SECRET=coffee\n")

            report = evidence_bundle.build_bundle(root, "UNIQUE_ENV_SECRET")

        self.assertEqual(report["total_matches"], 0)

    def test_roastery_local_outputs_are_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            self.write_file(root / "roastery" / "local_cup_outputs" / "raw.md", "# Raw\nrawunique\n")

            report = evidence_bundle.build_bundle(root, "rawunique")

        self.assertEqual(report["total_matches"], 0)

    def test_tmp_is_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            self.write_file(root / "tmp" / "note.md", "# Scratch\ntmpunique\n")

            report = evidence_bundle.build_bundle(root, "tmpunique")

        self.assertEqual(report["total_matches"], 0)

    def test_binary_files_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            self.write_binary(root / "docs" / "binary.md", b"\x00binaryunique")

            report = evidence_bundle.build_bundle(root, "binaryunique")

        self.assertEqual(report["total_matches"], 0)

    def test_zero_match_search_exits_zero_with_honest_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)

            code, stdout, stderr = self.run_tool("--root", str(root), "--query", "missingterm")

        self.assertEqual(code, 0, stderr)
        self.assertIn("No evidence matches found", stdout)

    def test_tool_does_not_require_openrouter_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            with mock.patch.dict(os.environ, {}, clear=True):
                code, _stdout, stderr = self.run_tool("--root", str(root), "--query", "coffee")

        self.assertEqual(code, 0, stderr)

    def test_invalid_output_parent_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)

            code, stdout, stderr = self.run_tool(
                "--root",
                str(root),
                "--query",
                "coffee",
                "--output",
                str(root / "missing" / "bundle.md"),
            )

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Output parent path does not exist", stderr)


if __name__ == "__main__":
    unittest.main()
