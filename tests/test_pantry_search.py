import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools import pantry_search


class PantrySearchTests(unittest.TestCase):
    def write_file(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_tool(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = pantry_search.run(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_finds_simple_keyword_matches_in_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_file(root / "notes.md", "# Notes\nProject Coffee keeps context.\n")

            results = pantry_search.search(root, "coffee")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].path, "notes.md")
            self.assertIn("Coffee", results[0].snippet)

    def test_ranks_heading_matches_above_body_only_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_file(root / "heading.md", "# Pantry Search\nBody text.\n")
            self.write_file(root / "body.md", "# Other\nPantry search appears here.\n")

            results = pantry_search.search(root, "pantry search")

            self.assertGreaterEqual(len(results), 2)
            self.assertEqual(results[0].path, "heading.md")
            self.assertGreater(results[0].score, results[1].score)

    def test_handles_multiple_query_terms(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_file(root / "one.md", "# Alpha\nCoffee pantry search.\n")
            self.write_file(root / "two.md", "# Beta\nCoffee only.\n")

            results = pantry_search.search(root, "coffee pantry")

            self.assertEqual(results[0].path, "one.md")
            self.assertGreater(results[0].score, results[1].score)

    def test_returns_no_results_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_file(root / "notes.md", "# Notes\nNothing relevant.\n")

            code, stdout, stderr = self.run_tool("--root", str(root), "--query", "missing")

            self.assertEqual(code, 0, stderr)
            self.assertIn("No results found", stdout)

    def test_json_output_is_valid_and_structured(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_file(root / "notes.md", "# Notes\nSearchable coffee note.\n")

            code, stdout, stderr = self.run_tool(
                "--root",
                str(root),
                "--query",
                "coffee",
                "--json",
            )

            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["query"], "coffee")
            self.assertEqual(payload["result_count"], 1)
            self.assertEqual(payload["results"][0]["path"], "notes.md")
            self.assertIn("line", payload["results"][0])
            self.assertIn("heading", payload["results"][0])
            self.assertIn("score", payload["results"][0])
            self.assertIn("snippet", payload["results"][0])

    def test_missing_root_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "missing"

            code, stdout, stderr = self.run_tool("--root", str(root), "--query", "coffee")

            self.assertEqual(code, 1)
            self.assertEqual(stdout, "")
            self.assertIn("Root does not exist", stderr)

    def test_sensitive_looking_files_and_paths_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_file(root / "secrets" / "notes.md", "coffee secret\n")
            self.write_file(root / "token-notes.md", "coffee token\n")
            self.write_file(root / "public.md", "# Public\nNo match here.\n")

            results = pantry_search.search(root, "coffee")

            self.assertEqual(results, [])

    def test_max_results_limits_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index in range(3):
                self.write_file(root / f"note-{index}.md", f"# Note {index}\ncoffee\n")

            results = pantry_search.search(root, "coffee", max_results=2)

            self.assertEqual(len(results), 2)

    def test_snippets_include_the_matched_term(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_file(root / "long.md", "# Long\n" + ("prefix " * 60) + "coffee term\n")

            results = pantry_search.search(root, "coffee")

            self.assertEqual(len(results), 1)
            self.assertIn("coffee", results[0].snippet.lower())

    def test_symlink_escape_is_not_followed_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            outside = Path(temp) / "outside"
            root.mkdir()
            outside.mkdir()
            self.write_file(outside / "outside.md", "coffee outside\n")
            link = root / "linked-outside.md"
            try:
                link.symlink_to(outside / "outside.md")
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is not available in this environment")

            results = pantry_search.search(root, "coffee")

            self.assertEqual(results, [])

    def test_include_extension_can_be_customized(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_file(root / "notes.txt", "coffee in txt\n")

            results = pantry_search.search(root, "coffee", include=".txt")

            self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
