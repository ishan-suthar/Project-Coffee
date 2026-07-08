import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import ledger_summary


class LedgerSummaryTests(unittest.TestCase):
    def write_ledger(self, root: Path, text: str) -> Path:
        ledger = root / "ledger" / "cost_log.md"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(text, encoding="utf-8")
        return ledger

    def run_tool(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = ledger_summary.run(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def sample_table(self) -> str:
        return (
            "# Cost Log\n\n"
            "| Date | Task | Model / Bean | Task type | Est. tokens | Actual cost | Value notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| 2026-07-01 | Brew A | No remote Bean; local standard-library tool | Local validation | None / local-only; not metered | None / local-only; no external API cost | Tests passed. |\n"
            "| 2026-07-02 | Brew B | nvidia/example:free | Local Cup Test / Bean comparison | Observed: A 100 total; B 250 total | $0.00 | Model call evidence. |\n"
            "| 2026-07-03 | Brew C | ChatGPT planning | Documentation | Unknown exact tokens | Unknown exact cost | Legacy estimate. |\n"
        )

    def test_missing_ledger_exits_nonzero_with_helpful_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            code, stdout, stderr = self.run_tool("--root", temp)

            self.assertNotEqual(code, 0)
            self.assertEqual(stdout, "")
            self.assertIn("Ledger does not exist", stderr)

    def test_simple_ledger_entry_is_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["entries_parsed"], 3)
            self.assertTrue(any(entry["task"] == "Brew A" for entry in summary["entries"]))

    def test_multiple_entries_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["entries_in_range"], 3)

    def test_cost_values_are_summed_when_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(
                root,
                "# Cost Log\n\n"
                "| Date | Task | Model / Bean | Task type | Est. tokens | Actual cost | Value notes |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| 2026-07-01 | A | model/a | Test | 10 | $1.25 | ok |\n"
                "| 2026-07-02 | B | model/b | Test | 20 | $2.75 | ok |\n",
            )

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["total_known_cost"], "4.00")

    def test_token_values_are_summed_when_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["total_known_tokens"], 350)

    def test_local_only_entries_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["local_only_entries"], 1)

    def test_model_api_call_entries_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["model_api_call_entries"], 2)

    def test_invalid_date_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())

            code, _stdout, stderr = self.run_tool("--root", str(root), "--from", "07-01-2026")

            self.assertNotEqual(code, 0)
            self.assertIn("--from must use YYYY-MM-DD", stderr)

    def test_date_filtering_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())

            summary = ledger_summary.build_summary(root, from_date="2026-07-02", to_date="2026-07-02")

            self.assertEqual(summary["totals"]["entries_in_range"], 1)
            self.assertEqual(summary["entries"][0]["task"], "Brew B")

    def test_json_output_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())

            code, stdout, stderr = self.run_tool("--root", str(root), "--json")

            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertIn("totals", payload)
            self.assertIn("entries", payload)

    def test_output_writes_markdown_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())
            output = root / "summary.md"

            code, stdout, stderr = self.run_tool("--root", str(root), "--output", str(output))

            self.assertEqual(code, 0, stderr)
            self.assertIn("Project Coffee Ledger Summary", stdout)
            self.assertIn("Project Coffee Ledger Summary", output.read_text(encoding="utf-8"))

    def test_tool_does_not_require_openrouter_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())
            with mock.patch.dict(os.environ, {}, clear=True):
                code, stdout, stderr = self.run_tool("--root", str(root))

            self.assertEqual(code, 0, stderr)
            self.assertIn("Project Coffee Ledger Summary", stdout)

    def test_inconsistent_legacy_formatting_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(
                root,
                "# Cost Log\n\n"
                "## 2026-07-01 Legacy entry\n\n"
                "- Cost unknown, tokens unknown, local validation completed.\n",
            )

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["entries_parsed"], 1)
            self.assertEqual(summary["entries"][0]["date"], "2026-07-01")

    def test_invalid_output_parent_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())

            code, _stdout, stderr = self.run_tool("--root", str(root), "--output", str(root / "missing" / "summary.md"))

            self.assertNotEqual(code, 0)
            self.assertIn("Output parent does not exist", stderr)


if __name__ == "__main__":
    unittest.main()
