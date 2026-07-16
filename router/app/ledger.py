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
    # Brew 47 (docs/design/openai-compat-endpoint-design.md Section 3): the
    # full column set for both /v1/order and the new /v1/chat/completions
    # endpoint, migrated in one pass even though retry_of/retry_count/
    # is_shadow/shadow_of are not populated by real logic until a later
    # session (Section 2, deferred) - deliberately one migration, not two.
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
    # Brew 47 escalation-concatenation fix (docs/design/
    # openai-compat-endpoint-design.md "Known issue", resolved): streamed
    # /v1/chat/completions requests never actually escalate (see
    # _run_chat_completion's `stream` branch) - this column preserves the
    # measurement signal that would otherwise be lost, so ledger_summary.py
    # can still report how often escalation *would* have fired.
    "would_have_escalated",
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
    # Brew 47 (docs/design/openai-compat-endpoint-design.md Section 3).
    # client_source: "chat_ui" for /v1/order; for /v1/chat/completions, the
    # raw User-Agent header (truncated) when present, else "openai_api".
    client_source: str = ""
    # requested_model: the OpenAI-shape `model` field as the client sent it
    # (raw string, may be a Bean alias, a raw model id, or empty) - only
    # meaningful for /v1/chat/completions; always "" for /v1/order, since
    # that request shape has no analogous field (bean_alias_override IS
    # the routing decision there, not a separate "requested model" string).
    requested_model: str = ""
    # retry_of/retry_count/is_shadow/shadow_of: columns exist from this
    # migration onward but are not populated by real logic until Signal A/C
    # (Section 2) lands in a later session - every row written this session
    # gets the defaults below.
    retry_of: str = ""
    retry_count: int = 0
    # over_cap_declined: True iff this request hit decide_escalation()'s
    # escalation_pending outcome and did NOT end up escalating - a real
    # human decline/timeout on /v1/order, or a forced immediate decline on
    # /v1/chat/completions (which cannot pause for approval). Populated for
    # both endpoints starting this session.
    over_cap_declined: bool = False
    is_shadow: bool = False
    shadow_of: str = ""
    # prompt_shape facts (Section 3) - stored as three raw columns, not a
    # packed string, so slicing in analysis needs no parser. has_code_fence
    # reflects the current turn's own text; message_count/total_input_chars
    # cover everything actually sent to the model this request (history +
    # current turn, or the client's full messages array).
    has_code_fence: bool = False
    message_count: int = 0
    total_input_chars: int = 0
    # would_have_escalated: True iff decide_escalation() picked
    # auto_escalate but the request was streamed, so the premium re-run
    # was skipped to avoid corrupting the client's stream (see
    # docs/design/openai-compat-endpoint-design.md). Always False for
    # /v1/order and for non-streamed /v1/chat/completions requests, since
    # both of those actually run the escalation instead of just measuring
    # it (escalated=True there, not this flag).
    would_have_escalated: bool = False

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
            self.client_source,
            self.requested_model,
            self.retry_of,
            self.retry_count,
            self.over_cap_declined,
            self.is_shadow,
            self.shadow_of,
            self.has_code_fence,
            self.message_count,
            self.total_input_chars,
            self.would_have_escalated,
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

    def increment_retry_count(self, request_id: str) -> bool:
        """Brew 47 Section 2 (docs/design/openai-compat-endpoint-design.md):
        rewrites the matching row's retry_count field, same rewrite-the-
        whole-file mechanism update_rating() already uses. Superseded the
        original design note that retry_count would only ever be a
        write-time snapshot - making it live is worth one more full-CSV
        rewrite per detected retry, at this router's real local volume.
        Returns True if a row was updated."""

        self._migrate_if_needed()
        rows = self.read_all_rows()
        found = False
        for row in rows:
            if row["request_id"] == request_id:
                current = row.get("retry_count") or "0"
                try:
                    row["retry_count"] = str(int(current) + 1)
                except ValueError:
                    row["retry_count"] = "1"
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
