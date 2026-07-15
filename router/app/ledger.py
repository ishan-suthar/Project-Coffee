"""Automatic Coffee Ledger writes for the Coffee Core Router.

Appends one row per /v1/order request to ledger/router_requests.csv - a new
file, separate from the hand-maintained ledger/cost_log.md, which stays a
narrative one-row-per-Brew Ledger (see docs/design/coffee-core-router-design.md
Section 6).

Brew 38 added attachment_count/attachment_tokens_est columns. Unlike the
original file (new, no migration needed), this repository already had
committed rows under the old 12-column header (from the Brew 36/37 live
demos) - appending 14-column rows under that stale header would silently
misalign every column from that row onward. See _migrate_if_needed() and
docs/design/attachments-design.md Section 8.
"""

from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
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
    "attachment_count",
    "attachment_tokens_est",
    # Brew 46 (docs/design/conversation-memory-design.md Section 4): makes
    # "what did Remember Chat cost me" answerable from the Ledger alone.
    "remember_chat",
    "history_turns",
    "history_tokens_est",
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
    attachment_count: int = 0
    attachment_tokens_est: Optional[int] = None  # None means "unknown" (e.g. image tokens)
    remember_chat: bool = False
    history_turns: int = 0
    history_tokens_est: Optional[int] = None  # None means remember_chat was false (not a real 0)

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
            self.attachment_count,
            _unknown_if_none(self.attachment_tokens_est),
            self.remember_chat,
            self.history_turns,
            _unknown_if_none(self.history_tokens_est),
        ]


def _unknown_if_none(value):
    return "unknown" if value is None else value


class RouterLedger:
    """Appends LedgerRow entries to a CSV file, creating it with a header
    row on first write if it does not already exist, and migrating an
    existing file with a stale header (Brew 38) before the first write."""

    def __init__(self, path: Path = DEFAULT_LEDGER_PATH):
        self.path = path
        self._migrated_this_session = False

    def append(self, row: LedgerRow) -> None:
        self._migrate_if_needed()
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

    def update_rating(self, request_id: str, rating: str) -> bool:
        """Rewrite the CSV with the matching row's rating field set. CSV
        has no in-place row update, so this reads every row, updates the
        one that matches, and writes the whole file back. Fine for a
        single-process/single-user router (Brew 36 non-goal) at the
        volume a local chat UI produces. Returns True if a row was
        updated, False if request_id was not found."""

        self._migrate_if_needed()
        rows = self.read_all_rows()
        found = False
        for row in rows:
            if row["request_id"] == request_id:
                row["rating"] = rating
                found = True
                break

        if not found:
            return False

        with open(self.path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
            writer.writeheader()
            writer.writerows(rows)

        return True

    def _migrate_if_needed(self) -> Optional[Path]:
        """If the file exists with a header that does not match the
        current CSV_HEADER, back it up and rewrite it with the current
        header - missing new columns for pre-migration rows are left
        empty (csv.DictWriter's default restval=""), read back as
        "unknown" by convention, never invented as 0. Returns the backup
        path if a migration happened, None otherwise (including when
        called more than once in the same process - migration only ever
        runs once per RouterLedger instance)."""

        if self._migrated_this_session or not self.path.is_file():
            self._migrated_this_session = True
            return None

        with open(self.path, "r", newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            try:
                existing_header = next(reader)
            except StopIteration:
                existing_header = []

        self._migrated_this_session = True
        if existing_header == CSV_HEADER:
            return None

        backup_suffix = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(":", "-")
        backup_path = self.path.with_name(f"{self.path.name}.bak-{backup_suffix}")
        shutil.copy2(self.path, backup_path)

        with open(self.path, "r", newline="", encoding="utf-8") as handle:
            old_rows = list(csv.DictReader(handle))

        with open(self.path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_HEADER, restval="")
            writer.writeheader()
            writer.writerows(old_rows)

        print(
            f"[router.app.ledger] Migrated {self.path} to the current CSV header "
            f"(backup saved to {backup_path})."
        )
        return backup_path
