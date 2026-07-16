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

    def sample_bullet_ledger(self) -> str:
        return (
            "# Cost Log\n\n"
            "## 2026-07-01 - Local validation\n\n"
            "- Model/API calls: none/local\n"
            "- Tokens: 0\n"
            "- Cost: 0\n"
            "- Evidence: Local checks only.\n\n"
            "## 2026-07-02 - OpenRouter fixture\n\n"
            "- Model/API calls: OpenRouter test call\n"
            "- Tokens: 1,234\n"
            "- Cost: $0.12\n"
            "- Notes: Fixture only; no live call.\n\n"
            "## 2026-07-03 - Unknown legacy fixture\n\n"
            "- Model/API calls: no\n"
            "- Tokens: unknown\n"
            "- Cost: unknown\n"
            "- Notes: Unknown values stay unknown.\n"
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

    def test_bullet_style_local_only_entry_counts_as_local_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_bullet_ledger())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["local_only_entries"], 2)

    def test_bullet_style_model_api_entry_counts_as_model_api_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_bullet_ledger())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["model_api_call_entries"], 1)

    def test_bullet_style_cost_parses_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_bullet_ledger())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["total_known_cost"], "0.12")

    def test_bullet_style_tokens_parse_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(
                root,
                "# Cost Log\n\n"
                "## 2026-07-01 - Token fixture\n\n"
                "- Model/API calls: none/local\n"
                "- Tokens: 1234\n"
                "- Cost: 0\n",
            )

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["total_known_tokens"], 1234)

    def test_bullet_style_comma_token_values_parse_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_bullet_ledger())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["total_known_tokens"], 1234)

    def test_bullet_style_unknown_cost_and_tokens_remain_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_bullet_ledger())

            summary = ledger_summary.build_summary(root)

            self.assertEqual(summary["totals"]["unknown_or_unparseable_cost_entries"], 1)
            self.assertEqual(summary["totals"]["unknown_or_unparseable_token_entries"], 1)


class ModelUsageReportTests(unittest.TestCase):
    """Brew 47 Section 4 (docs/design/openai-compat-endpoint-design.md):
    --mode model-usage, a genuinely separate code path reading the
    machine-written ledger/router_requests.csv, not the hand-maintained
    ledger/cost_log.md the rest of this file covers."""

    def run_tool(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = ledger_summary.run(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def write_router_ledger(self, root: Path, rows) -> Path:
        from router.app.ledger import RouterLedger

        ledger_path = root / "ledger" / "router_requests.csv"
        ledger = RouterLedger(ledger_path)
        for row in rows:
            ledger.append(row)
        return ledger_path

    def write_beans_yaml(self, root: Path, *, price_in=0.003, price_out=0.015) -> Path:
        beans_path = root / "router" / "config" / "beans.yaml"
        beans_path.parent.mkdir(parents=True, exist_ok=True)
        beans_path.write_text(
            "beans:\n"
            "  - alias: \"House Blend\"\n"
            "    role: default\n"
            "    model_id: \"vendor/house:free\"\n"
            "    price_per_1k_input_usd: 0.0\n"
            "    price_per_1k_output_usd: 0.0\n"
            "  - alias: \"Reserve Blend\"\n"
            "    role: premium\n"
            "    model_id: \"vendor/premium\"\n"
            f"    price_per_1k_input_usd: {price_in}\n"
            f"    price_per_1k_output_usd: {price_out}\n",
            encoding="utf-8",
        )
        return beans_path

    def make_row(self, **overrides):
        from router.app.ledger import LedgerRow

        defaults = dict(
            timestamp="2026-07-16T12:00:00+00:00",
            request_id="req-1",
            task_type="code",
            bean_alias="House Blend",
            raw_model_id="vendor/house:free",
            tokens_in=100,
            tokens_out=200,
            cost_usd=0.0,
            latency_ms=1000,
            escalated=False,
            escalation_approved=None,
            client_source="chat_ui",
        )
        defaults.update(overrides)
        return LedgerRow(**defaults)

    def test_no_router_ledger_file_degrades_to_zero_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("Requests: 0", stdout)

    def test_volume_and_bean_distribution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(
                root,
                [
                    self.make_row(request_id="r1", bean_alias="House Blend"),
                    self.make_row(request_id="r2", bean_alias="House Blend"),
                    self.make_row(request_id="r3", bean_alias="Reserve Blend", cost_usd=0.05),
                ],
            )
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("Requests: 3", stdout)
            self.assertIn("House Blend: 2 (66.7%)", stdout)
            self.assertIn("Reserve Blend: 1 (33.3%)", stdout)

    def test_sliced_by_task_type(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(
                root,
                [
                    self.make_row(request_id="r1", task_type="code"),
                    self.make_row(request_id="r2", task_type="explain"),
                ],
            )
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("## code", stdout)
            self.assertIn("## explain", stdout)

    def test_sliced_by_client_source_normalizes_blank_to_chat_ui(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(
                root,
                [
                    self.make_row(request_id="r1", client_source=""),
                    self.make_row(request_id="r2", client_source="Cursor/1.0"),
                ],
            )
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("## chat_ui", stdout)
            self.assertIn("## Cursor/1.0", stdout)

    def test_escalation_over_cap_and_retry_rates_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(
                root,
                [
                    self.make_row(request_id="r1", escalated=True),
                    self.make_row(request_id="r2", over_cap_declined=True),
                    self.make_row(request_id="r3", retry_of="r1"),
                    self.make_row(request_id="r4"),
                ],
            )
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("Escalation rate: 25.0%", stdout)
            self.assertIn("Over-cap decline rate: 25.0%", stdout)
            self.assertIn("Retry rate: 25.0%", stdout)

    def test_retry_rate_labeled_as_weak_proxy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(root, [self.make_row()])
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("weak proxy for dissatisfaction", stdout)
            self.assertNotIn("measurement of it\n", stdout)  # never claimed as a real measurement

    def test_counterfactual_cost_computed_from_beans_yaml_pricing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root, price_in=0.003, price_out=0.015)
            self.write_router_ledger(
                root, [self.make_row(tokens_in=1000, tokens_out=1000, cost_usd=0.0)]
            )
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            # 1000/1000 * 0.003 + 1000/1000 * 0.015 = 0.018
            self.assertIn("$0.0180", stdout)

    def test_counterfactual_cost_unavailable_without_beans_yaml(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_router_ledger(root, [self.make_row()])
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("Counterfactual cost is unavailable", stdout)

    def test_shadow_rows_excluded_from_main_stats_and_shown_in_own_section(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(
                root,
                [
                    self.make_row(request_id="r1"),
                    self.make_row(
                        request_id="r-shadow",
                        bean_alias="Reserve Blend",
                        is_shadow=True,
                        shadow_of="r1",
                        cost_usd=0.02,
                    ),
                ],
            )
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("Requests: 1", stdout)  # overall count excludes the shadow row
            self.assertIn("## Shadow mode", stdout)
            self.assertIn("1 shadow pair(s) captured", stdout)
            self.assertIn("api_requests", stdout)

    def test_no_shadow_data_path_omits_shadow_section(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(root, [self.make_row()])
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertNotIn("## Shadow mode", stdout)
            self.assertIn("No shadow-mode data exists for this period", stdout)

    def test_no_quality_signal_footer_stat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(
                root,
                [
                    self.make_row(request_id="r1"),  # no signal at all
                    self.make_row(request_id="r2", escalated=True),  # has a signal
                ],
            )
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("50.0% of real requests in this period have NO quality signal", stdout)

    def test_over_cap_declined_blind_spot_always_noted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(root, [self.make_row()])
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage")
            self.assertEqual(code, 0, stderr)
            self.assertIn("over_cap_declined is unreliable for any row written before Brew 47", stdout)

    def test_json_output_is_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(root, [self.make_row()])
            code, stdout, stderr = self.run_tool("--root", str(root), "--mode", "model-usage", "--json")
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertIn("overall", payload)
            self.assertIn("by_task_type", payload)
            self.assertIn("by_client_source", payload)

    def test_date_filtering_excludes_out_of_range_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_beans_yaml(root)
            self.write_router_ledger(
                root,
                [
                    self.make_row(request_id="r1", timestamp="2026-01-01T00:00:00+00:00"),
                    self.make_row(request_id="r2", timestamp="2026-07-16T00:00:00+00:00"),
                ],
            )
            code, stdout, stderr = self.run_tool(
                "--root", str(root), "--mode", "model-usage", "--from", "2026-07-01", "--to", "2026-07-31"
            )
            self.assertEqual(code, 0, stderr)
            self.assertIn("Requests: 1", stdout)

    def test_default_mode_is_still_cost_log_unchanged(self):
        """--mode defaults to cost-log - existing usage without --mode must
        keep behaving exactly as before this Brew."""

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_ledger(root, self.sample_table())
            code, stdout, stderr = self.run_tool("--root", str(root))
            self.assertEqual(code, 0, stderr)
            self.assertIn("Project Coffee Ledger Summary", stdout)

    def write_ledger(self, root: Path, text: str) -> Path:
        ledger = root / "ledger" / "cost_log.md"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(text, encoding="utf-8")
        return ledger

    def sample_table(self) -> str:
        return (
            "# Cost Log\n\n"
            "| Date | Task | Model / Bean | Task type | Est. tokens | Actual cost | Value notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| 2026-07-01 | Brew A | No remote Bean; local standard-library tool | Local validation | None / local-only; not metered | None / local-only; no external API cost | Tests passed. |\n"
        )


if __name__ == "__main__":
    unittest.main()
