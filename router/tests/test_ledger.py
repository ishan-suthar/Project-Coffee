import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from router.app.ledger import CSV_HEADER, LedgerRow, RouterLedger


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


if __name__ == "__main__":
    unittest.main()
