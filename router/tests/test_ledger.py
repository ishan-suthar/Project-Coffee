import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from router.app.aliases import Bean, BeanRegistry
from router.app.ledger import (
    CSV_HEADER,
    LedgerRow,
    RouterLedger,
    estimate_web_search_component_usd,
    resolve_cost,
)


def _make_row(**overrides):
    defaults = dict(
        timestamp="2026-07-09T22:00:00Z",
        request_id="req-1",
        task_type="code",
        bean_alias="House Blend",
        raw_model_id="nvidia/nemotron-3-ultra-550b-a55b:free",
        tokens_in=100,
        tokens_out=200,
        cost_usd=0.0,
        latency_ms=1500,
        escalated=False,
        escalation_approved=None,
        rating="",
    )
    defaults.update(overrides)
    return LedgerRow(**defaults)


class RouterLedgerTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.path = Path(self._tmp_dir.name) / "router_requests.csv"
        self.ledger = RouterLedger(self.path)

    def test_first_append_writes_header(self):
        self.ledger.append(_make_row())
        text = self.path.read_text(encoding="utf-8")
        first_line = text.splitlines()[0]
        self.assertEqual(first_line.split(","), CSV_HEADER)

    def test_second_append_does_not_repeat_header(self):
        self.ledger.append(_make_row(request_id="req-1"))
        self.ledger.append(_make_row(request_id="req-2"))
        lines = self.path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines.count(",".join(CSV_HEADER)), 1)
        self.assertEqual(len(lines), 3)  # header + 2 rows

    def test_read_all_rows_roundtrip(self):
        self.ledger.append(_make_row(request_id="req-1", tokens_in=50, tokens_out=75))
        rows = self.ledger.read_all_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["request_id"], "req-1")
        self.assertEqual(rows[0]["tokens_in"], "50")

    def test_unknown_values_are_written_as_unknown_not_blank(self):
        self.ledger.append(_make_row(tokens_in=None, tokens_out=None, cost_usd=None))
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["tokens_in"], "unknown")
        self.assertEqual(rows[0]["tokens_out"], "unknown")
        self.assertEqual(rows[0]["cost_usd"], "unknown")

    def test_no_escalation_records_n_a_not_blank(self):
        self.ledger.append(_make_row(escalated=False, escalation_approved=None))
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalation_approved"], "n/a")

    def test_escalation_approved_true(self):
        self.ledger.append(_make_row(escalated=True, escalation_approved=True))
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalated"], "True")
        self.assertEqual(rows[0]["escalation_approved"], "True")

    def test_escalation_declined_false(self):
        self.ledger.append(_make_row(escalated=True, escalation_approved=False))
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["escalation_approved"], "False")

    def test_raw_model_id_present_in_ledger_row(self):
        """Unlike SSE events, the Ledger is one of the three places raw
        model IDs are explicitly allowed, for audit (Requirement 2)."""

        self.ledger.append(_make_row(raw_model_id="nvidia/nemotron-3-ultra-550b-a55b:free"))
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["raw_model_id"], "nvidia/nemotron-3-ultra-550b-a55b:free")

    def test_read_all_rows_on_missing_file_returns_empty_list(self):
        missing_ledger = RouterLedger(Path(self._tmp_dir.name) / "does-not-exist.csv")
        self.assertEqual(missing_ledger.read_all_rows(), [])

    def test_rating_defaults_to_empty_string(self):
        self.ledger.append(_make_row())
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["rating"], "")

    def test_update_rating_sets_matching_row(self):
        self.ledger.append(_make_row(request_id="req-1"))
        self.ledger.append(_make_row(request_id="req-2"))

        updated = self.ledger.update_rating("req-1", "good")

        self.assertTrue(updated)
        rows = self.ledger.read_all_rows()
        by_id = {row["request_id"]: row for row in rows}
        self.assertEqual(by_id["req-1"]["rating"], "good")
        self.assertEqual(by_id["req-2"]["rating"], "")

    def test_update_rating_returns_false_when_not_found(self):
        self.ledger.append(_make_row(request_id="req-1"))
        updated = self.ledger.update_rating("nonexistent-request-id", "good")
        self.assertFalse(updated)

    def test_update_rating_preserves_other_fields(self):
        self.ledger.append(
            _make_row(request_id="req-1", tokens_in=42, cost_usd=0.05, escalated=True)
        )
        self.ledger.update_rating("req-1", "needed_fixing")
        row = self.ledger.read_all_rows()[0]
        self.assertEqual(row["tokens_in"], "42")
        self.assertEqual(row["cost_usd"], "0.05")
        self.assertEqual(row["escalated"], "True")
        self.assertEqual(row["rating"], "needed_fixing")

    def test_update_rating_preserves_header_and_row_count(self):
        for i in range(3):
            self.ledger.append(_make_row(request_id=f"req-{i}"))
        self.ledger.update_rating("req-1", "failed")

        text = self.path.read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertEqual(lines[0].split(","), CSV_HEADER)
        self.assertEqual(len(lines), 4)  # header + 3 rows

    def test_attachment_count_defaults_to_zero(self):
        self.ledger.append(_make_row())
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["attachment_count"], "0")

    def test_attachment_count_and_tokens_recorded(self):
        self.ledger.append(_make_row(attachment_count=2, attachment_tokens_est=1500))
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["attachment_count"], "2")
        self.assertEqual(rows[0]["attachment_tokens_est"], "1500")

    def test_attachment_tokens_est_none_is_unknown_not_zero(self):
        """An image attachment has no computable token estimate - must be
        recorded as "unknown", never invented as 0 (docs/design/
        attachments-design.md Section 8)."""

        self.ledger.append(_make_row(attachment_count=1, attachment_tokens_est=None))
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["attachment_tokens_est"], "unknown")

    def test_brew_47_columns_default_to_documented_values(self):
        """docs/design/openai-compat-endpoint-design.md Section 3: a new
        row that doesn't explicitly set the Brew 47 columns gets the
        documented "not tracked yet" defaults - blank strings, 0, False -
        never invented non-empty values."""

        self.ledger.append(_make_row())
        rows = self.ledger.read_all_rows()
        row = rows[0]
        self.assertEqual(row["client_source"], "")
        self.assertEqual(row["requested_model"], "")
        self.assertEqual(row["retry_of"], "")
        self.assertEqual(row["retry_count"], "0")
        self.assertEqual(row["over_cap_declined"], "False")
        self.assertEqual(row["is_shadow"], "False")
        self.assertEqual(row["shadow_of"], "")
        self.assertEqual(row["has_code_fence"], "False")
        self.assertEqual(row["message_count"], "0")
        self.assertEqual(row["total_input_chars"], "0")
        self.assertEqual(row["would_have_escalated"], "False")

    def test_brew_47_columns_recorded_when_set(self):
        self.ledger.append(
            _make_row(
                client_source="cursor/1.2.3",
                requested_model="gpt-4o",
                over_cap_declined=True,
                has_code_fence=True,
                message_count=6,
                total_input_chars=18234,
            )
        )
        rows = self.ledger.read_all_rows()
        row = rows[0]
        self.assertEqual(row["client_source"], "cursor/1.2.3")
        self.assertEqual(row["requested_model"], "gpt-4o")
        self.assertEqual(row["over_cap_declined"], "True")
        self.assertEqual(row["has_code_fence"], "True")
        self.assertEqual(row["message_count"], "6")
        self.assertEqual(row["total_input_chars"], "18234")

    def test_would_have_escalated_recorded_when_set(self):
        """Escalation-concatenation fix (docs/design/
        openai-compat-endpoint-design.md "Known issue", resolved): the
        measurement signal a streamed request can't act on."""

        self.ledger.append(_make_row(would_have_escalated=True))
        row = self.ledger.read_all_rows()[0]
        self.assertEqual(row["would_have_escalated"], "True")

    def test_increment_retry_count_bumps_matching_row(self):
        """Brew 47 Section 2: retry_count is live, not a write-time
        snapshot - the original design note was explicitly superseded."""

        self.ledger.append(_make_row(request_id="req-1"))
        self.ledger.append(_make_row(request_id="req-2"))

        updated = self.ledger.increment_retry_count("req-1")

        self.assertTrue(updated)
        rows = self.ledger.read_all_rows()
        by_id = {row["request_id"]: row for row in rows}
        self.assertEqual(by_id["req-1"]["retry_count"], "1")
        self.assertEqual(by_id["req-2"]["retry_count"], "0")

    def test_increment_retry_count_twice_reaches_two(self):
        self.ledger.append(_make_row(request_id="req-1"))
        self.ledger.increment_retry_count("req-1")
        self.ledger.increment_retry_count("req-1")
        rows = self.ledger.read_all_rows()
        self.assertEqual(rows[0]["retry_count"], "2")

    def test_increment_retry_count_returns_false_when_not_found(self):
        self.ledger.append(_make_row(request_id="req-1"))
        self.assertFalse(self.ledger.increment_retry_count("nonexistent"))

    def test_increment_retry_count_preserves_other_fields(self):
        self.ledger.append(_make_row(request_id="req-1", tokens_in=42, cost_usd=0.05))
        self.ledger.increment_retry_count("req-1")
        row = self.ledger.read_all_rows()[0]
        self.assertEqual(row["tokens_in"], "42")
        self.assertEqual(row["cost_usd"], "0.05")

    def test_prompt_shape_is_three_separate_columns_not_one_packed_string(self):
        """Explicit product decision (docs/design/
        openai-compat-endpoint-design.md, resolved open question 1):
        slicing is the point, so has_code_fence/message_count/
        total_input_chars must each be independently readable from the
        CSV without a parser."""

        self.assertIn("has_code_fence", CSV_HEADER)
        self.assertIn("message_count", CSV_HEADER)
        self.assertIn("total_input_chars", CSV_HEADER)
        self.assertNotIn("prompt_shape", CSV_HEADER)


class LedgerMigrationTests(unittest.TestCase):
    OLD_HEADER = [
        "timestamp",
        "request_id",
        "task_type",
        "bean_alias",
        "raw_model_id",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "latency_ms",
        "escalated",
        "escalation_approved",
        "rating",
    ]

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.path = Path(self._tmp_dir.name) / "router_requests.csv"

    def _write_old_format_file(self):
        with open(self.path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.OLD_HEADER)
            writer.writerow(
                [
                    "2026-07-09T20:00:00Z",
                    "req-old-1",
                    "explain",
                    "House Blend",
                    "nvidia/nemotron-3-ultra-550b-a55b:free",
                    "13",
                    "65",
                    "0.0",
                    "1733",
                    "False",
                    "n/a",
                    "",
                ]
            )

    def test_migration_backs_up_old_file(self):
        self._write_old_format_file()
        ledger = RouterLedger(self.path)

        ledger.append(_make_row(request_id="req-new-1"))

        backups = list(self.path.parent.glob(f"{self.path.name}.bak-*"))
        self.assertEqual(len(backups), 1)
        with open(backups[0], newline="", encoding="utf-8") as handle:
            backup_header = next(csv.reader(handle))
        self.assertEqual(backup_header, self.OLD_HEADER)

    def test_migration_rewrites_with_new_header(self):
        self._write_old_format_file()
        ledger = RouterLedger(self.path)

        ledger.append(_make_row(request_id="req-new-1"))

        text = self.path.read_text(encoding="utf-8")
        first_line = text.splitlines()[0]
        self.assertEqual(first_line.split(","), CSV_HEADER)

    def test_migration_preserves_old_rows_with_unknown_new_columns(self):
        self._write_old_format_file()
        ledger = RouterLedger(self.path)

        ledger.append(_make_row(request_id="req-new-1", attachment_count=1, attachment_tokens_est=42))

        rows = ledger.read_all_rows()
        old_row = next(r for r in rows if r["request_id"] == "req-old-1")
        new_row = next(r for r in rows if r["request_id"] == "req-new-1")
        # Pre-migration row never had these columns - empty/unknown, not "0".
        self.assertEqual(old_row["attachment_count"], "")
        self.assertEqual(old_row["attachment_tokens_est"], "")
        self.assertEqual(new_row["attachment_count"], "1")
        self.assertEqual(new_row["attachment_tokens_est"], "42")

    def test_migration_preserves_old_row_original_data(self):
        self._write_old_format_file()
        ledger = RouterLedger(self.path)
        ledger.append(_make_row(request_id="req-new-1"))

        rows = ledger.read_all_rows()
        old_row = next(r for r in rows if r["request_id"] == "req-old-1")
        self.assertEqual(old_row["bean_alias"], "House Blend")
        self.assertEqual(old_row["raw_model_id"], "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(old_row["tokens_out"], "65")

    def test_no_migration_when_header_already_current(self):
        """A file already on the current header must not be touched -
        no spurious backup file created."""

        ledger = RouterLedger(self.path)
        ledger.append(_make_row(request_id="req-1"))

        ledger2 = RouterLedger(self.path)
        ledger2.append(_make_row(request_id="req-2"))

        backups = list(self.path.parent.glob(f"{self.path.name}.bak-*"))
        self.assertEqual(backups, [])

    def test_migration_runs_only_once_per_ledger_instance(self):
        self._write_old_format_file()
        ledger = RouterLedger(self.path)
        ledger.append(_make_row(request_id="req-new-1"))
        ledger.append(_make_row(request_id="req-new-2"))

        backups = list(self.path.parent.glob(f"{self.path.name}.bak-*"))
        self.assertEqual(len(backups), 1)

    def test_migration_fills_brew_47_columns_blank_for_old_rows(self):
        """docs/design/openai-compat-endpoint-design.md Section 3's
        defaults table: every Brew 47 column is blank on a migrated
        pre-Brew-47 row - callers (ledger_summary.py, generate_policy.py)
        normalize blank client_source to "chat_ui" themselves, never
        infer it silently at write/migration time."""

        self._write_old_format_file()
        ledger = RouterLedger(self.path)
        ledger.append(_make_row(request_id="req-new-1", client_source="chat_ui"))

        rows = ledger.read_all_rows()
        old_row = next(r for r in rows if r["request_id"] == "req-old-1")
        for column in (
            "client_source",
            "requested_model",
            "retry_of",
            "retry_count",
            "over_cap_declined",
            "is_shadow",
            "shadow_of",
            "has_code_fence",
            "message_count",
            "total_input_chars",
            "would_have_escalated",
        ):
            self.assertEqual(old_row[column], "", column)

    def test_migration_also_triggered_by_update_rating(self):
        self._write_old_format_file()
        ledger = RouterLedger(self.path)

        updated = ledger.update_rating("req-old-1", "good")

        self.assertTrue(updated)
        text = self.path.read_text(encoding="utf-8")
        self.assertEqual(text.splitlines()[0].split(","), CSV_HEADER)


class ResolveCostTests(unittest.TestCase):
    def setUp(self):
        self.paid_bean = Bean(
            alias="Reserve Blend",
            role="premium",
            model_id="vendor/premium-model",
            vision=False,
            code=True,
            price_per_1k_input_usd=0.003,
            price_per_1k_output_usd=0.015,
            status="active",
        )
        self.free_bean = Bean(
            alias="House Blend",
            role="default",
            model_id="vendor/default-model:free",
            vision=False,
            code=True,
            price_per_1k_input_usd=0.0,
            price_per_1k_output_usd=0.0,
            status="active",
        )
        self.unpriced_bean = Bean(
            alias="Reserve Blend",
            role="premium",
            model_id=None,
            vision=False,
            code=True,
            price_per_1k_input_usd=None,
            price_per_1k_output_usd=None,
            status="not_yet_selected",
        )

    def test_prefers_reported_cost_when_usage_has_cost(self):
        cost_usd, cost_source = resolve_cost(self.paid_bean, 1000, 1000, usage={"cost": 0.021})
        self.assertEqual(cost_usd, 0.021)
        self.assertEqual(cost_source, "reported")

    def test_reported_cost_ignores_token_math_entirely(self):
        """Even a reported cost that would look "wrong" by token math must
        win - it's OpenRouter's own real bill, provider-routing quirks
        and all, not something to second-guess with beans.yaml."""

        cost_usd, cost_source = resolve_cost(self.paid_bean, 1, 1, usage={"cost": 5.0})
        self.assertEqual(cost_usd, 5.0)
        self.assertEqual(cost_source, "reported")

    def test_falls_back_to_computed_when_usage_missing(self):
        cost_usd, cost_source = resolve_cost(self.paid_bean, 1000, 1000, usage=None)
        self.assertEqual(cost_usd, 0.018)
        self.assertEqual(cost_source, "computed")

    def test_falls_back_to_computed_when_usage_has_no_cost_key(self):
        cost_usd, cost_source = resolve_cost(self.paid_bean, 1000, 1000, usage={"prompt_tokens": 1000})
        self.assertEqual(cost_usd, 0.018)
        self.assertEqual(cost_source, "computed")

    def test_free_tier_is_real_zero_computed_never_unknown(self):
        cost_usd, cost_source = resolve_cost(self.free_bean, 1000, 1000, usage=None)
        self.assertEqual(cost_usd, 0.0)
        self.assertEqual(cost_source, "computed")

    def test_unpriced_bean_returns_none_and_empty_source(self):
        cost_usd, cost_source = resolve_cost(self.unpriced_bean, 100, 100, usage=None)
        self.assertIsNone(cost_usd)
        self.assertEqual(cost_source, "")

    def test_unpriced_bean_still_prefers_reported_cost(self):
        """A reported cost needs no local pricing at all - OpenRouter told
        us the real number directly."""

        cost_usd, cost_source = resolve_cost(self.unpriced_bean, 100, 100, usage={"cost": 0.5})
        self.assertEqual(cost_usd, 0.5)
        self.assertEqual(cost_source, "reported")

    def test_non_numeric_usage_cost_falls_back_to_computed(self):
        cost_usd, cost_source = resolve_cost(self.paid_bean, 1000, 1000, usage={"cost": "not-a-number"})
        self.assertEqual(cost_usd, 0.018)
        self.assertEqual(cost_source, "computed")


class EstimateWebSearchComponentUsdTests(unittest.TestCase):
    """web-search Brew - docs/design/web-search-design.md's cost design.
    A BREAKDOWN of resolve_cost()'s total, never an addend."""

    def setUp(self):
        self.paid_bean = Bean(
            alias="Reserve Blend",
            role="premium",
            model_id="vendor/premium-model",
            vision=False,
            code=True,
            price_per_1k_input_usd=0.003,
            price_per_1k_output_usd=0.015,
            status="active",
        )

    def test_subtracts_token_cost_from_reported_total(self):
        # token cost = (1000/1000*0.003) + (1000/1000*0.015) = 0.018
        component = estimate_web_search_component_usd(
            self.paid_bean, 1000, 1000, cost_usd=0.023, cost_source="reported"
        )
        self.assertAlmostEqual(component, 0.005)

    def test_computed_source_returns_none_never_fabricated(self):
        """cost_usd IS the token math when cost_source == "computed" -
        nothing left to isolate a fee from."""

        component = estimate_web_search_component_usd(
            self.paid_bean, 1000, 1000, cost_usd=0.018, cost_source="computed"
        )
        self.assertIsNone(component)

    def test_unknown_source_returns_none(self):
        component = estimate_web_search_component_usd(
            self.paid_bean, 1000, 1000, cost_usd=None, cost_source=""
        )
        self.assertIsNone(component)

    def test_negative_drift_clamps_to_zero(self):
        """A reported total slightly under this module's own token math
        (rounding/provider drift) must never show a fabricated negative
        search fee."""

        component = estimate_web_search_component_usd(
            self.paid_bean, 1000, 1000, cost_usd=0.017, cost_source="reported"
        )
        self.assertEqual(component, 0.0)

    def test_unpriced_bean_returns_none(self):
        unpriced_bean = Bean(
            alias="Reserve Blend",
            role="premium",
            model_id=None,
            vision=False,
            code=True,
            price_per_1k_input_usd=None,
            price_per_1k_output_usd=None,
            status="not_yet_selected",
        )
        component = estimate_web_search_component_usd(
            unpriced_bean, 1000, 1000, cost_usd=0.5, cost_source="reported"
        )
        self.assertIsNone(component)


class BackfillMissingCostsTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.path = Path(self._tmp_dir.name) / "router_requests.csv"
        self.ledger = RouterLedger(self.path)
        self.registry = BeanRegistry(
            [
                Bean(
                    alias="Reserve Blend",
                    role="premium",
                    model_id="vendor/premium-model",
                    vision=False,
                    code=True,
                    price_per_1k_input_usd=0.003,
                    price_per_1k_output_usd=0.015,
                    status="active",
                ),
                Bean(
                    alias="Ghost Bean",
                    role="fallback",
                    model_id=None,
                    vision=False,
                    code=True,
                    price_per_1k_input_usd=None,
                    price_per_1k_output_usd=None,
                    status="not_yet_selected",
                ),
            ]
        )

    def test_dry_run_computes_diff_without_writing(self):
        self.ledger.append(
            _make_row(request_id="req-1", bean_alias="Reserve Blend", tokens_in=1000, tokens_out=1000, cost_usd=None)
        )
        original_text = self.path.read_text(encoding="utf-8")

        changed = self.ledger.backfill_missing_costs(self.registry, apply=False)

        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]["cost_usd"], "0.018")
        self.assertEqual(changed[0]["cost_source"], "computed")
        self.assertEqual(changed[0]["_old_cost_usd"], "unknown")
        # Nothing written to disk on a dry run.
        self.assertEqual(self.path.read_text(encoding="utf-8"), original_text)

    def test_apply_writes_backfilled_costs(self):
        self.ledger.append(
            _make_row(request_id="req-1", bean_alias="Reserve Blend", tokens_in=1000, tokens_out=1000, cost_usd=None)
        )

        changed = self.ledger.backfill_missing_costs(self.registry, apply=True)

        self.assertEqual(len(changed), 1)
        row = self.ledger.read_all_rows()[0]
        self.assertEqual(row["cost_usd"], "0.018")
        self.assertEqual(row["cost_source"], "computed")

    def test_rows_with_known_cost_source_are_skipped(self):
        self.ledger.append(
            _make_row(
                request_id="req-1",
                bean_alias="Reserve Blend",
                tokens_in=1000,
                tokens_out=1000,
                cost_usd=0.5,
                cost_source="reported",
            )
        )
        changed = self.ledger.backfill_missing_costs(self.registry, apply=True)
        self.assertEqual(changed, [])
        row = self.ledger.read_all_rows()[0]
        self.assertEqual(row["cost_usd"], "0.5")

    def test_unpriceable_bean_left_unknown(self):
        self.ledger.append(
            _make_row(request_id="req-1", bean_alias="Ghost Bean", tokens_in=100, tokens_out=100, cost_usd=None)
        )
        changed = self.ledger.backfill_missing_costs(self.registry, apply=True)
        self.assertEqual(changed, [])
        row = self.ledger.read_all_rows()[0]
        self.assertEqual(row["cost_usd"], "unknown")
        self.assertEqual(row["cost_source"], "")

    def test_unknown_bean_alias_left_unknown(self):
        self.ledger.append(
            _make_row(request_id="req-1", bean_alias="Nonexistent Bean", tokens_in=100, tokens_out=100, cost_usd=None)
        )
        changed = self.ledger.backfill_missing_costs(self.registry, apply=True)
        self.assertEqual(changed, [])

    def test_unparseable_tokens_left_unknown(self):
        self.ledger.append(
            _make_row(request_id="req-1", bean_alias="Reserve Blend", tokens_in=None, tokens_out=None, cost_usd=None)
        )
        changed = self.ledger.backfill_missing_costs(self.registry, apply=True)
        self.assertEqual(changed, [])

    def test_backfill_never_produces_reported_source(self):
        """No usage dict exists for a historical row - a backfilled cost
        can only ever be "computed", never "reported"."""

        self.ledger.append(
            _make_row(request_id="req-1", bean_alias="Reserve Blend", tokens_in=1000, tokens_out=1000, cost_usd=None)
        )
        changed = self.ledger.backfill_missing_costs(self.registry, apply=True)
        self.assertEqual(changed[0]["cost_source"], "computed")


class UserIdColumnTests(unittest.TestCase):
    """Spend-cap Brew: the new user_id Ledger column."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.path = Path(self._tmp_dir.name) / "router_requests.csv"
        self.ledger = RouterLedger(self.path)

    def test_user_id_recorded_when_set(self):
        self.ledger.append(_make_row(user_id=7))
        row = self.ledger.read_all_rows()[0]
        self.assertEqual(row["user_id"], "7")

    def test_user_id_blank_when_not_set(self):
        """None -> "" (not attributed), a distinct state from a genuinely
        unknown cost - never invented."""

        self.ledger.append(_make_row(user_id=None))
        row = self.ledger.read_all_rows()[0]
        self.assertEqual(row["user_id"], "")


class TodaySpendUsdTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.path = Path(self._tmp_dir.name) / "router_requests.csv"
        self.ledger = RouterLedger(self.path)

    def _today_row(self, **overrides):
        defaults = dict(timestamp="2026-07-17T12:00:00+00:00")
        defaults.update(overrides)
        return _make_row(**defaults)

    def test_no_rows_returns_zero_not_a_crash(self):
        total, had_unresolved = self.ledger.today_spend_usd(user_id=1)
        self.assertEqual(total, 0.0)
        self.assertFalse(had_unresolved)

    def test_sums_only_todays_rows_for_the_given_user(self):
        self.ledger.append(self._today_row(request_id="r1", user_id=1, cost_usd=0.10))
        self.ledger.append(self._today_row(request_id="r2", user_id=1, cost_usd=0.05))
        self.ledger.append(self._today_row(request_id="r3", user_id=2, cost_usd=0.20))
        self.ledger.append(
            _make_row(request_id="r4", user_id=1, cost_usd=0.50, timestamp="2020-01-01T00:00:00+00:00")
        )
        total, had_unresolved = self.ledger.today_spend_usd(user_id=1)
        self.assertAlmostEqual(total, 0.15)
        self.assertFalse(had_unresolved)

    def test_user_id_none_sums_every_users_rows_today_for_the_global_cap(self):
        self.ledger.append(self._today_row(request_id="r1", user_id=1, cost_usd=0.10))
        self.ledger.append(self._today_row(request_id="r2", user_id=2, cost_usd=0.20))
        total, _ = self.ledger.today_spend_usd(user_id=None)
        self.assertAlmostEqual(total, 0.30)

    def test_shadow_rows_count_toward_the_triggering_users_total(self):
        """Shadow rows are real money attributed to the primary request's
        user - summed identically to any other row, no special-casing."""

        self.ledger.append(
            self._today_row(request_id="r1", user_id=1, cost_usd=0.30, is_shadow=True, shadow_of="primary-1")
        )
        total, _ = self.ledger.today_spend_usd(user_id=1)
        self.assertAlmostEqual(total, 0.30)

    def test_unknown_cost_flagged_not_silently_zeroed(self):
        """A genuinely unknown cost_usd must be reported via
        had_unresolved, never silently summed as $0 - exactly the
        undercount this Ledger exists to avoid."""

        self.ledger.append(self._today_row(request_id="r1", user_id=1, cost_usd=None, cost_source=""))
        total, had_unresolved = self.ledger.today_spend_usd(user_id=1)
        self.assertEqual(total, 0.0)
        self.assertTrue(had_unresolved)

    def test_zero_cost_free_tier_never_flagged_as_unresolved(self):
        self.ledger.append(self._today_row(request_id="r1", user_id=1, cost_usd=0.0, cost_source="computed"))
        total, had_unresolved = self.ledger.today_spend_usd(user_id=1)
        self.assertEqual(total, 0.0)
        self.assertFalse(had_unresolved)


if __name__ == "__main__":
    unittest.main()
