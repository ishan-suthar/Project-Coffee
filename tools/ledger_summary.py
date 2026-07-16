"""Summarize Project Coffee Ledger markdown entries.

The summarizer reads a Markdown ledger file, extracts table-style entries, and
prints local cost/token/workflow evidence. It never calls models, external
APIs, OpenRouter, or raw Roastery output directories.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence, TextIO

import yaml


DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
NUMBER_PATTERN = re.compile(r"(?<![\w.-])~?(\d[\d,]*)(?![\w.-])")
MONEY_PATTERN = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)")
FIELD_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*)?(cost|tokens|model/api calls|model|api calls|evidence|notes)\s*:\s*(.*)$",
    re.IGNORECASE,
)

SENSITIVE_PARTS = {
    ".env",
    ".git",
    ".ssh",
    ".aws",
    "secret",
    "secrets",
    "credential",
    "credentials",
    "token",
    "tokens",
    "local_cup_outputs",
    "local_reports",
}


class LedgerSummaryError(Exception):
    """Raised when the summarizer cannot safely produce a report."""


@dataclass(frozen=True)
class LedgerEntry:
    date_text: str
    entry_date: date | None
    task: str
    model_or_bean: str
    task_type: str
    tokens_text: str
    cost_text: str
    notes: str
    source_line: int

    @property
    def combined_text(self) -> str:
        return " ".join(
            part
            for part in (
                self.task,
                self.model_or_bean,
                self.task_type,
                self.tokens_text,
                self.cost_text,
                self.notes,
            )
            if part
        )


@dataclass(frozen=True)
class EntrySummary:
    entry: LedgerEntry
    known_tokens: int | None
    known_cost: Decimal | None
    local_only: bool
    model_api_call: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.entry.date_text,
            "task": self.entry.task,
            "model_or_bean": self.entry.model_or_bean,
            "task_type": self.entry.task_type,
            "tokens": self.entry.tokens_text,
            "cost": self.entry.cost_text,
            "notes": self.entry.notes,
            "source_line": self.entry.source_line,
            "known_tokens": self.known_tokens,
            "known_cost": str(self.known_cost) if self.known_cost is not None else None,
            "local_only": self.local_only,
            "model_api_call": self.model_api_call,
        }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize local Project Coffee Ledger cost and token evidence.",
    )
    parser.add_argument("--root", default=".", help="Project root. Default: current directory.")
    parser.add_argument(
        "--ledger",
        default=None,
        help="Ledger markdown path. Default: ledger/cost_log.md under root.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    parser.add_argument("--from", dest="from_date", help="Include entries on or after YYYY-MM-DD.")
    parser.add_argument("--to", dest="to_date", help="Include entries on or before YYYY-MM-DD.")
    parser.add_argument("--max-entries", type=int, default=10, help="Maximum recent entries to print. Default: 10.")
    parser.add_argument("--output", help="Optional Markdown report output path.")
    parser.add_argument(
        "--mode",
        choices=["cost-log", "model-usage"],
        default="cost-log",
        help=(
            "Report mode. cost-log (default, unchanged) summarizes the hand-maintained "
            "ledger/cost_log.md. model-usage (Brew 47) summarizes the machine-written "
            "ledger/router_requests.csv - bean distribution, escalation/decline/retry "
            "rates, counterfactual cost, sliced by task_type and client_source."
        ),
    )
    parser.add_argument(
        "--router-ledger",
        default=None,
        help="router_requests.csv path for --mode model-usage. Default: ledger/router_requests.csv under root.",
    )
    parser.add_argument(
        "--beans",
        default=None,
        help="beans.yaml path for --mode model-usage's counterfactual-cost pricing. Default: router/config/beans.yaml under root.",
    )
    return parser.parse_args(argv)


def build_summary(
    root: str | Path,
    *,
    ledger: str | Path | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    max_entries: int = 10,
) -> dict[str, Any]:
    root_path = validate_root(root)
    ledger_path = resolve_ledger_path(root_path, ledger)
    start_date = parse_cli_date(from_date, "--from") if from_date else None
    end_date = parse_cli_date(to_date, "--to") if to_date else None
    if start_date and end_date and start_date > end_date:
        raise LedgerSummaryError("--from must be on or before --to")
    if max_entries <= 0:
        raise LedgerSummaryError("--max-entries must be greater than zero")

    entries = parse_ledger(ledger_path)
    warnings: list[str] = []
    if not entries:
        warnings.append("No ledger entries were parsed from the Markdown file.")

    filtered = filter_entries(entries, start_date=start_date, end_date=end_date)
    summarized = [summarize_entry(entry) for entry in filtered]
    totals = summarize_totals(summarized, parsed_count=len(entries))
    recent_entries = recent_entry_summaries(summarized, max_entries=max_entries)

    return {
        "root": str(root_path),
        "ledger_path": str(ledger_path),
        "generated_at": timestamp(),
        "date_range": {
            "from": start_date.isoformat() if start_date else None,
            "to": end_date.isoformat() if end_date else None,
        },
        "totals": totals,
        "entries": [entry.as_dict() for entry in recent_entries],
        "warnings": warnings,
    }


def validate_root(root: str | Path) -> Path:
    path = Path(root).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise LedgerSummaryError(f"Root does not exist: {path}") from exc
    if not resolved.is_dir():
        raise LedgerSummaryError(f"Root is not a directory: {resolved}")
    validate_safe_parts(resolved, "root")
    return resolved


def resolve_ledger_path(root: Path, ledger: str | Path | None) -> Path:
    candidate = Path(ledger) if ledger is not None else Path("ledger") / "cost_log.md"
    if not candidate.is_absolute():
        candidate = root / candidate
    validate_safe_parts(candidate, "ledger")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise LedgerSummaryError(f"Ledger does not exist: {candidate}") from exc
    if not resolved.is_file():
        raise LedgerSummaryError(f"Ledger is not a file: {resolved}")
    validate_safe_parts(resolved, "ledger")
    return resolved


def resolve_output_path(output: str | Path) -> Path:
    candidate = Path(output).expanduser()
    validate_safe_parts(candidate, "output")
    parent = candidate.parent if candidate.parent != Path("") else Path(".")
    try:
        parent_resolved = parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise LedgerSummaryError(f"Output parent does not exist: {parent}") from exc
    if not parent_resolved.is_dir():
        raise LedgerSummaryError(f"Output parent is not a directory: {parent_resolved}")
    validate_safe_parts(parent_resolved, "output parent")
    return candidate


def validate_safe_parts(path: Path, label: str) -> None:
    for part in path.parts:
        lowered = part.lower()
        if lowered in SENSITIVE_PARTS or lowered.startswith(".") and lowered not in {".", ".."}:
            raise LedgerSummaryError(f"Unsafe {label} path component: {part}")


def parse_cli_date(value: str, flag: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise LedgerSummaryError(f"{flag} must use YYYY-MM-DD") from exc


def parse_ledger(path: Path) -> list[LedgerEntry]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    entries = parse_markdown_tables(lines)
    entries.extend(parse_bullet_entries(lines))
    if entries:
        return entries
    return parse_dated_fallback(lines)


def parse_markdown_tables(lines: Sequence[str]) -> list[LedgerEntry]:
    entries: list[LedgerEntry] = []
    header: list[str] | None = None
    header_map: dict[str, int] = {}
    in_matching_table = False

    for line_number, line in enumerate(lines, start=1):
        cells = parse_table_cells(line)
        if cells is None:
            in_matching_table = False
            header = None
            header_map = {}
            continue

        if is_separator_row(cells):
            continue

        normalized = [normalize_header(cell) for cell in cells]
        if "date" in normalized and any(cell.startswith("task") for cell in normalized):
            header = cells
            header_map = {normalize_header(cell): index for index, cell in enumerate(cells)}
            in_matching_table = True
            continue

        if in_matching_table and header:
            aligned = align_cells(cells, len(header))
            entries.append(entry_from_cells(aligned, header_map, line_number))

    return entries


def parse_table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or "|" not in stripped[1:]:
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def is_separator_row(cells: Sequence[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def normalize_header(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized


def align_cells(cells: Sequence[str], expected: int) -> list[str]:
    aligned = list(cells)
    if len(aligned) < expected:
        aligned.extend([""] * (expected - len(aligned)))
    elif len(aligned) > expected:
        aligned = aligned[: expected - 1] + [" | ".join(aligned[expected - 1 :])]
    return aligned


def entry_from_cells(cells: Sequence[str], header_map: dict[str, int], line_number: int) -> LedgerEntry:
    def cell(*names: str) -> str:
        for name in names:
            index = header_map.get(name)
            if index is not None and index < len(cells):
                return cells[index].strip()
        return ""

    date_text = cell("date")
    return LedgerEntry(
        date_text=date_text,
        entry_date=parse_entry_date(date_text),
        task=cell("task"),
        model_or_bean=cell("model_bean", "model", "bean", "model_api_calls"),
        task_type=cell("task_type", "type"),
        tokens_text=cell("est_tokens", "tokens", "actual_tokens", "token_usage"),
        cost_text=cell("actual_cost", "cost"),
        notes=cell("value_notes", "notes", "evidence_notes"),
        source_line=line_number,
    )


def parse_bullet_entries(lines: Sequence[str]) -> list[LedgerEntry]:
    entries: list[LedgerEntry] = []
    current: dict[str, Any] | None = None

    for line_number, line in enumerate(lines, start=1):
        if parse_table_cells(line) is not None:
            continue

        date_match = DATE_PATTERN.search(line)
        field_match = FIELD_PATTERN.match(line)
        if date_match and not field_match:
            if current is not None:
                entries.append(entry_from_bullet_fields(current))
            current = {
                "date_text": date_match.group(1),
                "entry_date": parse_entry_date(date_match.group(1)),
                "task": clean_entry_title(line),
                "model_or_bean": "",
                "task_type": "",
                "tokens_text": "",
                "cost_text": "",
                "notes": [],
                "source_line": line_number,
            }
            continue

        if current is None:
            continue

        if field_match:
            field_name = normalize_field_name(field_match.group(1))
            value = field_match.group(2).strip()
            if field_name == "cost":
                current["cost_text"] = value
            elif field_name == "tokens":
                current["tokens_text"] = value
            elif field_name == "model_api_calls":
                current["model_or_bean"] = value
            elif field_name in {"evidence", "notes"}:
                append_note(current, value)
            continue

        stripped = line.strip()
        if stripped.startswith(("-", "*")):
            append_note(current, stripped.lstrip("-* ").strip())

    if current is not None:
        entries.append(entry_from_bullet_fields(current))
    return entries


def entry_from_bullet_fields(fields: dict[str, Any]) -> LedgerEntry:
    return LedgerEntry(
        date_text=str(fields["date_text"]),
        entry_date=fields["entry_date"],
        task=str(fields["task"]),
        model_or_bean=str(fields["model_or_bean"]),
        task_type=str(fields["task_type"]),
        tokens_text=str(fields["tokens_text"]),
        cost_text=str(fields["cost_text"]),
        notes=" ".join(fields["notes"]).strip(),
        source_line=int(fields["source_line"]),
    )


def clean_entry_title(line: str) -> str:
    return line.strip().lstrip("#-* ").strip()


def normalize_field_name(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"model/api calls", "api calls", "model"}:
        return "model_api_calls"
    return normalized.replace(" ", "_")


def append_note(fields: dict[str, Any], value: str) -> None:
    if value:
        fields["notes"].append(value)


def parse_dated_fallback(lines: Sequence[str]) -> list[LedgerEntry]:
    entries: list[LedgerEntry] = []
    for line_number, line in enumerate(lines, start=1):
        match = DATE_PATTERN.search(line)
        if not match:
            continue
        stripped = line.strip(" #-")
        entries.append(
            LedgerEntry(
                date_text=match.group(1),
                entry_date=parse_entry_date(match.group(1)),
                task=stripped,
                model_or_bean="",
                task_type="",
                tokens_text="",
                cost_text="",
                notes=stripped,
                source_line=line_number,
            )
        )
    return entries


def parse_entry_date(value: str) -> date | None:
    match = DATE_PATTERN.search(value)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def filter_entries(
    entries: Sequence[LedgerEntry],
    *,
    start_date: date | None,
    end_date: date | None,
) -> list[LedgerEntry]:
    filtered: list[LedgerEntry] = []
    for entry in entries:
        if start_date and (entry.entry_date is None or entry.entry_date < start_date):
            continue
        if end_date and (entry.entry_date is None or entry.entry_date > end_date):
            continue
        filtered.append(entry)
    return filtered


def summarize_entry(entry: LedgerEntry) -> EntrySummary:
    return EntrySummary(
        entry=entry,
        known_tokens=parse_tokens(entry.tokens_text),
        known_cost=parse_cost(entry.cost_text),
        local_only=is_local_only(entry),
        model_api_call=has_model_or_api_call(entry),
    )


def parse_tokens(value: str) -> int | None:
    lowered = value.lower()
    if not lowered.strip():
        return None
    if "none" in lowered and "local" in lowered:
        return 0
    numbers = [int(match.group(1).replace(",", "")) for match in NUMBER_PATTERN.finditer(value)]
    if not numbers:
        return None
    return sum(numbers)


def parse_cost(value: str) -> Decimal | None:
    lowered = value.lower()
    if not lowered.strip():
        return None
    if "none" in lowered and ("local" in lowered or "no external api cost" in lowered):
        return Decimal("0")
    if "unknown" in lowered and "$" not in value:
        return None
    money = MONEY_PATTERN.findall(value)
    if money:
        return sum((Decimal(item.replace(",", "")) for item in money), Decimal("0"))
    if re.search(r"\breported\s+0\b", lowered) or re.search(r"\b0\s+reported\b", lowered):
        return Decimal("0")
    if re.fullmatch(r"\s*0(?:\.0+)?\s*", value):
        return Decimal("0")
    return None


def is_local_only(entry: LedgerEntry) -> bool:
    if has_model_or_api_call(entry):
        return False
    if is_no_model_api_value(entry.model_or_bean):
        return True
    primary_text = " ".join(
        part
        for part in (
            entry.model_or_bean,
            entry.task_type,
            entry.tokens_text,
            entry.cost_text,
        )
        if part
    ).lower()
    notes = entry.notes.lower()
    markers = (
        "no remote bean",
        "local-only",
        "local standard-library",
        "no external api",
        "no models",
        "none / local",
        "local validation",
    )
    if any(marker in primary_text for marker in markers):
        return True
    return ("no models" in notes or "no external api" in notes) and "local" in notes


def has_model_or_api_call(entry: LedgerEntry) -> bool:
    if is_no_model_api_value(entry.model_or_bean):
        return False
    if entry.model_or_bean.strip():
        return True
    text = entry.combined_text.lower()
    if "no remote bean" in text or "no models" in text:
        return False
    markers = (
        "openrouter",
        "chatgpt",
        "api",
        "bean comparison",
        ":free",
        "nvidia/",
        "cohere/",
        "poolside/",
        "qwen/",
        "deepseek/",
    )
    return any(marker in text for marker in markers)


def is_no_model_api_value(value: str) -> bool:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    if not normalized:
        return False
    exact_values = {
        "none/local",
        "none / local",
        "none",
        "no",
        "local-only",
        "local only",
    }
    if normalized in exact_values:
        return True
    markers = (
        "no external api",
        "no model",
        "no models",
        "no remote bean",
        "local-only",
        "local only",
        "none/local",
        "none / local",
    )
    return any(marker in normalized for marker in markers)


def summarize_totals(entries: Sequence[EntrySummary], *, parsed_count: int) -> dict[str, Any]:
    known_cost_values = [entry.known_cost for entry in entries if entry.known_cost is not None]
    known_token_values = [entry.known_tokens for entry in entries if entry.known_tokens is not None]
    total_cost = sum(known_cost_values, Decimal("0"))
    total_tokens = sum(known_token_values)
    return {
        "entries_parsed": parsed_count,
        "entries_in_range": len(entries),
        "model_api_call_entries": sum(1 for entry in entries if entry.model_api_call),
        "local_only_entries": sum(1 for entry in entries if entry.local_only),
        "known_cost_entries": len(known_cost_values),
        "known_token_entries": len(known_token_values),
        "total_known_cost": str(total_cost),
        "total_known_tokens": total_tokens,
        "unknown_or_unparseable_cost_entries": sum(1 for entry in entries if entry.known_cost is None),
        "unknown_or_unparseable_token_entries": sum(1 for entry in entries if entry.known_tokens is None),
    }


def recent_entry_summaries(entries: Sequence[EntrySummary], *, max_entries: int) -> list[EntrySummary]:
    indexed = list(enumerate(entries))
    indexed.sort(
        key=lambda pair: (
            pair[1].entry.entry_date or date.min,
            pair[0],
        ),
        reverse=True,
    )
    return [entry for _index, entry in indexed[:max_entries]]


# --- Brew 47 Section 4: --mode model-usage -------------------------------
#
# A genuinely separate code path from everything above: this file has
# always parsed the hand-maintained Markdown ledger/cost_log.md, but the
# question this mode answers (bean distribution, escalation/decline/retry
# rates, counterfactual cost, sliced by task_type/client_source) can only
# be answered from the machine-written CSV ledger/router_requests.csv,
# which has real per-request structured fields. Reads it the same way
# tools/generate_policy.py already does (plain csv.DictReader, no import
# from router.app.* - this tool never calls models, external APIs, or
# router internals). See docs/design/openai-compat-endpoint-design.md
# Section 4.


def resolve_router_ledger_path(root: Path, router_ledger: str | Path | None) -> Path:
    candidate = Path(router_ledger) if router_ledger is not None else Path("ledger") / "router_requests.csv"
    if not candidate.is_absolute():
        candidate = root / candidate
    validate_safe_parts(candidate, "router-ledger")
    return candidate


def resolve_beans_path(root: Path, beans: str | Path | None) -> Path:
    candidate = Path(beans) if beans is not None else Path("router") / "config" / "beans.yaml"
    if not candidate.is_absolute():
        candidate = root / candidate
    validate_safe_parts(candidate, "beans")
    return candidate


def read_router_ledger_rows(path: Path) -> list[dict[str, str]]:
    """[] when the file doesn't exist yet - same graceful-degradation
    convention RouterLedger.read_all_rows() and generate_policy.
    load_ledger_rows() already use, not an error. A fresh install with
    zero requests ever made is a legitimate state for this report to
    describe (as "0 requests"), not something to crash on."""

    if not path.is_file():
        return []
    with open(path, "r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_premium_bean_pricing(path: Path) -> dict[str, Any] | None:
    """The premium Bean's real price_per_1k_input_usd/output_usd from
    beans.yaml, or None when the file/premium Bean/pricing is missing -
    the counterfactual-cost calculation and the "what this cannot tell
    you" footer both degrade gracefully on None rather than crashing or
    inventing a number."""

    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    for bean in data.get("beans", []):
        if bean.get("role") == "premium":
            price_in = bean.get("price_per_1k_input_usd")
            price_out = bean.get("price_per_1k_output_usd")
            if price_in is None or price_out is None:
                return None
            return {
                "alias": bean.get("alias", "premium"),
                "price_per_1k_input_usd": price_in,
                "price_per_1k_output_usd": price_out,
            }
    return None


def _parse_bool_cell(value: str | None) -> bool:
    return (value or "").strip().lower() == "true"


def _parse_float_cell(value: str | None) -> float | None:
    stripped = (value or "").strip()
    if not stripped or stripped.lower() == "unknown":
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def _parse_int_cell(value: str | None) -> int | None:
    stripped = (value or "").strip()
    if not stripped or stripped.lower() == "unknown":
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def normalize_client_source(value: str | None) -> str:
    """A blank client_source cell means "every row before Brew 47 came
    through /v1/order" - documented and normalized here explicitly, never
    silently treated as a different, unlabeled bucket. Matches
    tools/generate_policy.py's routing_evidence_rows() convention for the
    same column."""

    stripped = (value or "").strip()
    return stripped if stripped else "chat_ui"


def _row_in_date_range(row: dict[str, str], start_date: date | None, end_date: date | None) -> bool:
    if start_date is None and end_date is None:
        return True
    try:
        row_date = date.fromisoformat((row.get("timestamp") or "")[:10])
    except ValueError:
        return False
    if start_date and row_date < start_date:
        return False
    if end_date and row_date > end_date:
        return False
    return True


def compute_slice_stats(rows: list[dict[str, str]], *, premium_pricing: dict[str, Any] | None) -> dict[str, Any]:
    """One slice's (task_type, or client_source, or overall) volume, cost,
    Bean distribution, and quality signals - is_shadow rows must already
    be excluded from `rows` by the caller, since a shadow row is not a
    real request (Section 2)."""

    request_count = len(rows)

    known_costs = [c for c in (_parse_float_cell(r.get("cost_usd")) for r in rows) if c is not None]
    unknown_cost_count = request_count - len(known_costs)
    total_cost_usd = sum(known_costs) if known_costs else None

    bean_counts: dict[str, int] = {}
    for row in rows:
        alias = row.get("bean_alias") or "unknown"
        bean_counts[alias] = bean_counts.get(alias, 0) + 1
    bean_distribution = {
        alias: {"count": count, "fraction": (count / request_count) if request_count else 0.0}
        for alias, count in sorted(bean_counts.items(), key=lambda pair: -pair[1])
    }

    escalated_count = sum(1 for r in rows if _parse_bool_cell(r.get("escalated")))
    over_cap_count = sum(1 for r in rows if _parse_bool_cell(r.get("over_cap_declined")))
    retry_count = sum(1 for r in rows if (r.get("retry_of") or "").strip())

    counterfactual_unknown_count = 0
    counterfactual_cost_usd: float | None = None
    if premium_pricing is not None:
        known_counterfactual: list[float] = []
        for row in rows:
            tokens_in = _parse_int_cell(row.get("tokens_in"))
            tokens_out = _parse_int_cell(row.get("tokens_out"))
            if tokens_in is None or tokens_out is None:
                counterfactual_unknown_count += 1
                continue
            known_counterfactual.append(
                (tokens_in / 1000) * premium_pricing["price_per_1k_input_usd"]
                + (tokens_out / 1000) * premium_pricing["price_per_1k_output_usd"]
            )
        counterfactual_cost_usd = sum(known_counterfactual) if known_counterfactual else None
    else:
        counterfactual_unknown_count = request_count

    return {
        "request_count": request_count,
        "total_cost_usd": total_cost_usd,
        "unknown_cost_count": unknown_cost_count,
        "bean_distribution": bean_distribution,
        "escalation_rate": (escalated_count / request_count) if request_count else None,
        "over_cap_decline_rate": (over_cap_count / request_count) if request_count else None,
        "retry_rate": (retry_count / request_count) if request_count else None,
        "counterfactual_cost_usd": counterfactual_cost_usd,
        "counterfactual_unknown_count": counterfactual_unknown_count,
    }


def build_model_usage_report(
    root: str | Path,
    *,
    router_ledger: str | Path | None = None,
    beans: str | Path | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    root_path = validate_root(root)
    ledger_path = resolve_router_ledger_path(root_path, router_ledger)
    beans_path = resolve_beans_path(root_path, beans)

    start_date = parse_cli_date(from_date, "--from") if from_date else None
    end_date = parse_cli_date(to_date, "--to") if to_date else None
    if start_date and end_date and start_date > end_date:
        raise LedgerSummaryError("--from must be on or before --to")

    all_rows = read_router_ledger_rows(ledger_path)
    filtered_rows = [r for r in all_rows if _row_in_date_range(r, start_date, end_date)]

    # Brew 47 Section 5 ("what this Brew deliberately does not do") applies
    # here too, not just to generate_policy.py: a shadow row is not a real
    # request and must never contaminate volume/cost/rate stats - it gets
    # its own dedicated section below instead.
    real_rows = [r for r in filtered_rows if not _parse_bool_cell(r.get("is_shadow"))]
    shadow_rows = [r for r in filtered_rows if _parse_bool_cell(r.get("is_shadow"))]

    premium_pricing = load_premium_bean_pricing(beans_path)

    by_task_type: dict[str, list[dict[str, str]]] = {}
    by_client_source: dict[str, list[dict[str, str]]] = {}
    for row in real_rows:
        by_task_type.setdefault(row.get("task_type") or "unknown", []).append(row)
        by_client_source.setdefault(normalize_client_source(row.get("client_source")), []).append(row)

    task_type_stats = {
        key: compute_slice_stats(rows, premium_pricing=premium_pricing)
        for key, rows in sorted(by_task_type.items())
    }
    client_source_stats = {
        key: compute_slice_stats(rows, premium_pricing=premium_pricing)
        for key, rows in sorted(by_client_source.items())
    }
    overall_stats = compute_slice_stats(real_rows, premium_pricing=premium_pricing)

    # "No quality signal at all" is computable from the CSV alone - a
    # shadow row's own shadow_of cell already points back at its primary's
    # request_id, so set membership is enough; no SQLite import needed
    # (keeps this tool's existing "never touches anything but the Ledger"
    # boundary intact).
    shadowed_request_ids = {row.get("shadow_of") for row in shadow_rows if row.get("shadow_of")}
    no_signal_count = sum(
        1
        for row in real_rows
        if not (row.get("retry_of") or "").strip()
        and not _parse_bool_cell(row.get("escalated"))
        and row.get("request_id") not in shadowed_request_ids
    )
    no_signal_fraction = (no_signal_count / len(real_rows)) if real_rows else None

    shadow_summary = None
    if shadow_rows:
        shadow_known_costs = [c for c in (_parse_float_cell(r.get("cost_usd")) for r in shadow_rows) if c is not None]
        shadow_summary = {
            "pair_count": len(shadow_rows),
            "total_shadow_cost_usd": sum(shadow_known_costs) if shadow_known_costs else None,
        }

    return {
        "root": str(root_path),
        "router_ledger_path": str(ledger_path),
        "generated_at": timestamp(),
        "date_range": {
            "from": start_date.isoformat() if start_date else None,
            "to": end_date.isoformat() if end_date else None,
        },
        "premium_bean_priced": premium_pricing is not None,
        "overall": overall_stats,
        "by_task_type": task_type_stats,
        "by_client_source": client_source_stats,
        "no_quality_signal_fraction": no_signal_fraction,
        "shadow": shadow_summary,
    }


def _format_optional_cost(value: float | None) -> str:
    return "unknown" if value is None else f"${value:.4f}"


def _format_optional_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def render_model_usage_report(summary: dict[str, Any]) -> str:
    def render_slice(title: str, stats: dict[str, Any]) -> list[str]:
        block = [f"## {title}", ""]
        block.append(f"- Requests: {stats['request_count']}")
        block.append(
            f"- Total cost: {_format_optional_cost(stats['total_cost_usd'])} "
            f"({stats['unknown_cost_count']} row(s) unknown)"
        )
        if stats["bean_distribution"]:
            block.append("- Bean distribution:")
            for alias, info in stats["bean_distribution"].items():
                block.append(f"    - {alias}: {info['count']} ({info['fraction'] * 100:.1f}%)")
        else:
            block.append("- Bean distribution: no requests in this slice.")
        # Escalation/decline/retry rates and counterfactual cost are kept
        # in one grouped block, deliberately never separated - the savings
        # number is never printed without its quality context in the same
        # glance (docs/design/openai-compat-endpoint-design.md Section 4).
        block.append(
            f"- Escalation rate: {_format_optional_rate(stats['escalation_rate'])}  |  "
            f"Over-cap decline rate: {_format_optional_rate(stats['over_cap_decline_rate'])}  |  "
            f"Retry rate: {_format_optional_rate(stats['retry_rate'])} "
            "(a weak proxy for dissatisfaction - NOT a measurement of it)"
        )
        block.append(
            f"- Counterfactual cost if every request here had gone to the premium Bean: "
            f"{_format_optional_cost(stats['counterfactual_cost_usd'])} "
            f"({stats['counterfactual_unknown_count']} row(s) unknown) - read this only "
            "alongside the rates on the line above, never alone."
        )
        block.append("")
        return block

    lines = [
        "# Coffee Router Ledger - Model Usage Report",
        "",
        f"Generated: {summary['generated_at']}",
        f"Root: {summary['root']}",
        f"Router Ledger: {summary['router_ledger_path']}",
        f"Date range: {format_date_range(summary['date_range'])}",
        "",
    ]
    lines.extend(render_slice("Overall", summary["overall"]))

    lines.append("# By task_type")
    lines.append("")
    if summary["by_task_type"]:
        for key, stats in summary["by_task_type"].items():
            lines.extend(render_slice(key, stats))
    else:
        lines.extend(["No requests found for this date range.", ""])

    lines.append("# By client_source")
    lines.append("")
    if summary["by_client_source"]:
        for key, stats in summary["by_client_source"].items():
            lines.extend(render_slice(key, stats))
    else:
        lines.extend(["No requests found for this date range.", ""])

    if summary["shadow"]:
        lines.append("## Shadow mode")
        lines.append("")
        lines.append(f"- {summary['shadow']['pair_count']} shadow pair(s) captured this period.")
        lines.append(f"- Total shadow spend: {_format_optional_cost(summary['shadow']['total_shadow_cost_usd'])}")
        lines.append(
            "- Read the pairs yourself - no automated scoring or diffing exists (Section 2). "
            "Query router/data/sessions.db directly:"
        )
        lines.append(
            '    sqlite3 router/data/sessions.db "SELECT request_id, response_text, '
            'shadow_response_text, shadow_bean_alias FROM api_requests '
            'WHERE shadow_response_text IS NOT NULL;"'
        )
        lines.append("")

    lines.append("## What this cannot tell you")
    lines.append("")
    if summary["no_quality_signal_fraction"] is not None:
        lines.append(
            f"- {summary['no_quality_signal_fraction'] * 100:.1f}% of real requests in this "
            "period have NO quality signal at all - not retried, not escalated, no shadow pair."
        )
    lines.append(
        "- over_cap_declined is unreliable for any row written before Brew 47 - it does not "
        "retroactively reflect a real over-cap decline that happened before this column existed."
    )
    lines.append(
        "- Retry rate is a weak proxy for dissatisfaction, not ground truth - a retry can also "
        "be a network hiccup, a user testing a different prompt, or a double-click."
    )
    if not summary["shadow"]:
        lines.append(
            "- No shadow-mode data exists for this period (disabled, or nothing was sampled) - "
            "zero premium-quality comparison exists for any request shown above."
        )
    if not summary["premium_bean_priced"]:
        lines.append(
            "- Counterfactual cost is unavailable - no premium Bean with real pricing was found "
            "in beans.yaml."
        )

    return "\n".join(lines) + "\n"


def render_markdown(summary: dict[str, Any]) -> str:
    totals = summary["totals"]
    lines = [
        "# Project Coffee Ledger Summary",
        "",
        f"Generated: {summary['generated_at']}",
        f"Root: {summary['root']}",
        f"Ledger path: {summary['ledger_path']}",
        f"Date range: {format_date_range(summary['date_range'])}",
        "",
        "## Totals",
        "",
        f"- Total entries found: {totals['entries_in_range']} ({totals['entries_parsed']} parsed before filtering)",
        f"- Entries with model/API calls: {totals['model_api_call_entries']}",
        f"- Entries marked local-only: {totals['local_only_entries']}",
        f"- Total known cost: ${Decimal(totals['total_known_cost']):.2f}",
        f"- Total known tokens: {totals['total_known_tokens']}",
        f"- Unknown/unparseable cost entries: {totals['unknown_or_unparseable_cost_entries']}",
        f"- Unknown/unparseable token entries: {totals['unknown_or_unparseable_token_entries']}",
        "",
        "## Recent Entries",
        "",
    ]
    if summary["entries"]:
        lines.extend(
            [
                "| Date | Task | Local-only | Model/API calls | Tokens | Cost |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for entry in summary["entries"]:
            lines.append(
                "| {date} | {task} | {local_only} | {model_api_call} | {tokens} | {cost} |".format(
                    date=escape_cell(entry["date"] or "unknown"),
                    task=escape_cell(entry["task"] or "unknown"),
                    local_only="yes" if entry["local_only"] else "no",
                    model_api_call="yes" if entry["model_api_call"] else "no",
                    tokens=escape_cell(str(entry["known_tokens"]) if entry["known_tokens"] is not None else "unknown"),
                    cost=escape_cell(format_entry_cost(entry["known_cost"])),
                )
            )
    else:
        lines.append("No entries found for this date range.")

    lines.extend(["", "## Warnings", ""])
    if summary["warnings"]:
        lines.extend(f"- {warning}" for warning in summary["warnings"])
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def format_date_range(date_range: dict[str, str | None]) -> str:
    start = date_range.get("from") or "beginning"
    end = date_range.get("to") or "latest"
    return f"{start} to {end}"


def format_entry_cost(value: str | None) -> str:
    if value is None:
        return "unknown"
    return f"${Decimal(value):.2f}"


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if args.mode == "model-usage":
            summary = build_model_usage_report(
                args.root,
                router_ledger=args.router_ledger,
                beans=args.beans,
                from_date=args.from_date,
                to_date=args.to_date,
            )
            report = render_model_usage_report(summary)
        else:
            summary = build_summary(
                args.root,
                ledger=args.ledger,
                from_date=args.from_date,
                to_date=args.to_date,
                max_entries=args.max_entries,
            )
            report = render_markdown(summary)
        if args.output:
            output_path = resolve_output_path(args.output)
            output_path.write_text(report, encoding="utf-8")
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(report, end="")
        return 0
    except LedgerSummaryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
