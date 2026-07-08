"""Summarize Project Coffee Ledger markdown entries.

The summarizer reads a Markdown ledger file, extracts table-style entries, and
prints local cost/token/workflow evidence. It never calls models, external
APIs, OpenRouter, or raw Roastery output directories.
"""

from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence, TextIO


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
        summary = build_summary(
            args.root,
            ledger=args.ledger,
            from_date=args.from_date,
            to_date=args.to_date,
            max_entries=args.max_entries,
        )
        markdown = render_markdown(summary)
        if args.output:
            output_path = resolve_output_path(args.output)
            output_path.write_text(markdown, encoding="utf-8")
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(markdown, end="")
        return 0
    except LedgerSummaryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
