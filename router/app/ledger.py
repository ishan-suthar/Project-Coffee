"""Automatic Coffee Ledger writes for the Coffee Core Router.

Appends one row per /v1/order request to ledger/router_requests.csv - a new
file, separate from the hand-maintained ledger/cost_log.md, which stays a
narrative one-row-per-Brew Ledger (see docs/design/coffee-core-router-design.md
Section 6). No CSV header migration is needed since this is a new file, not
a rename of an existing Ledger.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parent.parent.parent / "ledger" / "router_requests.csv"

CSV_HEADER = [
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


@dataclass(frozen=True)
class LedgerRow:
    timestamp: str
    request_id: str
    task_type: str
    bean_alias: str
    raw_model_id: str
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    cost_usd: Optional[float]
    latency_ms: int
    escalated: bool
    escalation_approved: Optional[bool]  # None means "n/a" (no escalation occurred)
    rating: str = ""

    def to_csv_values(self) -> list:
        return [
            self.timestamp,
            self.request_id,
            self.task_type,
            self.bean_alias,
            self.raw_model_id,
            _unknown_if_none(self.tokens_in),
            _unknown_if_none(self.tokens_out),
            _unknown_if_none(self.cost_usd),
            self.latency_ms,
            self.escalated,
            "n/a" if self.escalation_approved is None else self.escalation_approved,
            self.rating,
        ]


def _unknown_if_none(value):
    return "unknown" if value is None else value


class RouterLedger:
    """Appends LedgerRow entries to a CSV file, creating it with a header
    row on first write if it does not already exist."""

    def __init__(self, path: Path = DEFAULT_LEDGER_PATH):
        self.path = path

    def append(self, row: LedgerRow) -> None:
        is_new_file = not self.path.is_file()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if is_new_file:
                writer.writerow(CSV_HEADER)
            writer.writerow(row.to_csv_values())

    def read_all_rows(self) -> list:
        if not self.path.is_file():
            return []
        with open(self.path, "r", newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
