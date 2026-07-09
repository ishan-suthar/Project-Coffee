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


if __name__ == "__main__":
    unittest.main()
