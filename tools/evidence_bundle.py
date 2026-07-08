"""Build safe local Project Coffee evidence bundles.

This tool is the first Local RAG MVP: it retrieves short snippets from
allowlisted local text files and packages them with source, heading, freshness,
reason, score, and safety metadata. It does not call models, use embeddings,
create a vector database, or inspect excluded local output or secret paths.
"""

from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Sequence, TextIO


DEFAULT_MAX_RESULTS = 8
SNIPPET_CHARS = 260
TEXT_SUFFIXES = {".md", ".txt", ".rst"}

DEFAULT_SOURCE_SPECS = (
    "PROJECT_COFFEE.md",
    "AGENTS.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "brew-log/active_context.md",
    "brew-log/progress.md",
    "docs",
    "docs/design",
    "knowledge",
    "roastery/tasting_notes.md",
    "ledger/cost_log.md",
    "config/house_blend.md",
)

EXCLUDED_EXACT_PARTS = {
    ".env",
    ".git",
    ".ssh",
    ".aws",
    "__pycache__",
    "build",
    "dist",
    "local_cup_outputs",
    "local_reports",
    "node_modules",
    "tmp",
    "venv",
    ".venv",
}

EXCLUDED_MARKERS = (
    "credential",
    "credentials",
    "secret",
    "secrets",
    "token",
    "tokens",
)

WORD_RE = re.compile(r"[A-Za-z0-9_]+")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
BREW_RE = re.compile(r"\bBrew\s+\d+[A-Za-z]?\b", re.IGNORECASE)


class EvidenceBundleError(Exception):
    """Raised when an evidence bundle cannot be built safely."""


@dataclass(frozen=True)
class Source:
    label: str
    path: Path


@dataclass(frozen=True)
class EvidenceItem:
    source_path: str
    heading: str
    snippet: str
    reason_selected: str
    score: int
    freshness_signal: str
    safety_classification: str
    line_start: int
    line_end: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "heading": self.heading,
            "snippet": self.snippet,
            "reason_selected": self.reason_selected,
            "score": self.score,
            "freshness_signal": self.freshness_signal,
            "safety_classification": self.safety_classification,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--max-results must be an integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("--max-results must be greater than zero")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build safe local Project Coffee evidence bundles.",
    )
    parser.add_argument("--root", default=".", help="Project Coffee root. Default: current directory.")
    parser.add_argument("--query", help="Search query text. Required unless --list-sources is used.")
    parser.add_argument(
        "--max-results",
        type=positive_int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Maximum bundle items to print. Default: {DEFAULT_MAX_RESULTS}.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    parser.add_argument("--list-sources", action="store_true", help="List resolved allowlisted sources and exit.")
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Restrict retrieval to an allowlisted source. May be repeated.",
    )
    parser.add_argument("--output", help="Optional output path. Writes Markdown unless --json is passed.")
    return parser


def query_terms(query: str) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for match in WORD_RE.finditer(query.lower()):
        term = match.group(0)
        if term not in seen:
            terms.append(term)
            seen.add(term)
    return terms


def validate_root(root: str | Path) -> Path:
    root_path = Path(root).expanduser()
    try:
        resolved = root_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise EvidenceBundleError(f"Root does not exist: {root_path}") from exc
    if not resolved.is_dir():
        raise EvidenceBundleError(f"Root is not a directory: {resolved}")
    return resolved


def resolve_sources(root: Path, requested_sources: Sequence[str] | None = None) -> list[Source]:
    available_default_sources = [source for source in default_sources(root) if source.path.exists()]
    if not requested_sources:
        return available_default_sources

    allowlist_paths = [source.path for source in available_default_sources]
    resolved_sources: list[Source] = []
    seen: set[Path] = set()
    for requested in requested_sources:
        candidate = resolve_requested_source(root, requested)
        if not candidate.exists():
            raise EvidenceBundleError(f"Source does not exist: {requested}")
        if is_excluded_path(candidate, root):
            raise EvidenceBundleError(f"Source is excluded for safety: {requested}")
        if not is_within_any(candidate, allowlist_paths):
            raise EvidenceBundleError(f"Source is not allowlisted: {requested}")
        if candidate in seen:
            continue
        seen.add(candidate)
        resolved_sources.append(Source(label=display_path(candidate, root), path=candidate))
    return resolved_sources


def default_sources(root: Path) -> list[Source]:
    sources: list[Source] = []
    for spec in DEFAULT_SOURCE_SPECS:
        path = (root / spec).resolve()
        sources.append(Source(label=spec, path=path))
    return sources


def resolve_requested_source(root: Path, requested: str) -> Path:
    requested_path = Path(requested).expanduser()
    if requested_path.is_absolute():
        return requested_path.resolve()
    return (root / requested_path).resolve()


def is_within_any(path: Path, allowed_paths: Sequence[Path]) -> bool:
    resolved = path.resolve()
    for allowed in allowed_paths:
        allowed_resolved = allowed.resolve()
        if resolved == allowed_resolved:
            return True
        if allowed_resolved.is_dir():
            try:
                resolved.relative_to(allowed_resolved)
                return True
            except ValueError:
                pass
    return False


def build_bundle(
    root: str | Path,
    query: str,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    requested_sources: Sequence[str] | None = None,
) -> dict[str, Any]:
    root_path = validate_root(root)
    sources = resolve_sources(root_path, requested_sources)
    terms = query_terms(query)
    warnings: list[str] = []
    if not terms:
        warnings.append("Query did not contain searchable terms.")

    all_items: list[EvidenceItem] = []
    if terms:
        phrase = " ".join(query.strip().lower().split())
        seen_snippets: set[tuple[str, str]] = set()
        for file_path in iter_candidate_files(sources, root_path):
            for item in search_file(file_path, root_path, terms, phrase):
                dedupe_key = (item.source_path, normalize_snippet(item.snippet))
                if dedupe_key in seen_snippets:
                    continue
                seen_snippets.add(dedupe_key)
                all_items.append(item)

    all_items.sort(key=lambda item: (-item.score, item.source_path, item.line_start))
    bundle = all_items[:max_results]
    return {
        "root": str(root_path),
        "query": query,
        "generated_at": timestamp(),
        "sources_searched": [source.label for source in sources],
        "total_matches": len(all_items),
        "bundle": [item.as_dict() for item in bundle],
        "warnings": warnings,
    }


def iter_candidate_files(sources: Sequence[Source], root: Path) -> Iterable[Path]:
    yielded: set[Path] = set()
    for source in sources:
        if source.path.is_file():
            candidates = [source.path]
        else:
            candidates = list(walk_safe_files(source.path, root))
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in yielded:
                continue
            if not is_candidate_file(resolved, root):
                continue
            yielded.add(resolved)
            yield resolved


def walk_safe_files(source_dir: Path, root: Path) -> Iterable[Path]:
    for current_root, dirnames, filenames in os.walk(source_dir, topdown=True, followlinks=False):
        current_path = Path(current_root)
        safe_dirs: list[str] = []
        for dirname in dirnames:
            candidate = current_path / dirname
            if is_excluded_path(candidate, root):
                continue
            if candidate.is_symlink() and not is_within_root(candidate, root):
                continue
            safe_dirs.append(dirname)
        dirnames[:] = safe_dirs

        for filename in filenames:
            candidate = current_path / filename
            if is_candidate_file(candidate, root):
                yield candidate


def is_candidate_file(path: Path, root: Path) -> bool:
    if is_excluded_path(path, root):
        return False
    if path.is_symlink() and not is_within_root(path, root):
        return False
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    if looks_binary(path):
        return False
    return True


def search_file(path: Path, root: Path, terms: Sequence[str], phrase: str) -> list[EvidenceItem]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    except OSError:
        return []

    display = display_path(path, root)
    path_lower = display.lower()
    path_hits = sum(path_lower.count(term) for term in terms)
    current_heading = ""
    first_heading = ""
    first_content_line = ""
    first_content_line_number = 1
    items: list[EvidenceItem] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        compact_line = " ".join(line.strip().split())
        if compact_line and not first_content_line:
            first_content_line = compact_line
            first_content_line_number = line_number

        heading_match = HEADING_RE.match(line)
        if heading_match:
            current_heading = heading_match.group(1).strip()
            if not first_heading:
                first_heading = current_heading

        score = score_line(line, current_heading, terms, phrase, path_lower, is_heading=bool(heading_match))
        if score <= 0:
            continue

        items.append(
            EvidenceItem(
                source_path=display,
                heading=current_heading or first_heading,
                snippet=make_snippet(line, terms, phrase),
                reason_selected=reason_selected(line, current_heading, path_lower, terms, phrase),
                score=score,
                freshness_signal=freshness_signal(line, current_heading, display),
                safety_classification=safety_classification(display),
                line_start=line_number,
                line_end=line_number,
            )
        )

    if not items and path_hits > 0:
        snippet = make_snippet(first_content_line or display, terms, phrase)
        items.append(
            EvidenceItem(
                source_path=display,
                heading=first_heading,
                snippet=snippet,
                reason_selected="matched query terms in path",
                score=path_hits * 6,
                freshness_signal=freshness_signal(first_content_line, first_heading, display),
                safety_classification=safety_classification(display),
                line_start=first_content_line_number,
                line_end=first_content_line_number,
            )
        )
    return items


def score_line(
    line: str,
    heading: str,
    terms: Sequence[str],
    phrase: str,
    path_lower: str,
    *,
    is_heading: bool,
) -> int:
    line_lower = line.lower()
    heading_lower = heading.lower()
    body_hits = sum(line_lower.count(term) for term in terms)
    heading_hits = sum(heading_lower.count(term) for term in terms)
    path_hits = sum(path_lower.count(term) for term in terms)
    if body_hits == 0 and heading_hits == 0:
        return 0

    phrase_hits = line_lower.count(phrase) if phrase else 0
    heading_phrase_hits = heading_lower.count(phrase) if phrase else 0
    path_phrase_hits = path_lower.count(phrase) if phrase else 0

    score = body_hits * 10
    score += heading_hits * 8
    score += path_hits * 4
    score += phrase_hits * 20
    score += heading_phrase_hits * 12
    score += path_phrase_hits * 8
    if is_heading:
        score += 25
    return score


def reason_selected(
    line: str,
    heading: str,
    path_lower: str,
    terms: Sequence[str],
    phrase: str,
) -> str:
    fields: list[str] = []
    line_lower = line.lower()
    heading_lower = heading.lower()
    if any(term in line_lower for term in terms):
        fields.append("body")
    if heading and any(term in heading_lower for term in terms):
        fields.append("heading")
    if any(term in path_lower for term in terms):
        fields.append("path")
    if phrase and (phrase in line_lower or phrase in heading_lower or phrase in path_lower):
        fields.append("exact phrase")
    if not fields:
        fields.append("query term")
    matched = [term for term in terms if term in line_lower or term in heading_lower or term in path_lower]
    return f"matched {', '.join(sorted(set(fields)))} for terms: {', '.join(matched)}"


def make_snippet(line: str, terms: Sequence[str], phrase: str) -> str:
    compact = " ".join(line.strip().split())
    if len(compact) <= SNIPPET_CHARS:
        return compact

    lower = compact.lower()
    match_index = lower.find(phrase) if phrase else -1
    if match_index < 0:
        match_index = min(
            (index for term in terms if (index := lower.find(term)) >= 0),
            default=0,
        )
    half = SNIPPET_CHARS // 2
    start = max(match_index - half, 0)
    end = min(start + SNIPPET_CHARS, len(compact))
    if end - start < SNIPPET_CHARS:
        start = max(end - SNIPPET_CHARS, 0)

    snippet = compact[start:end]
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(compact):
        snippet = f"{snippet}..."
    return snippet


def freshness_signal(line: str, heading: str, source_path: str) -> str:
    for candidate in (line, heading, source_path):
        date_match = DATE_RE.search(candidate)
        if date_match:
            return f"date:{date_match.group(0)}"
        brew_match = BREW_RE.search(candidate)
        if brew_match:
            return brew_match.group(0)
    if source_path == "brew-log/active_context.md":
        return "current-status-file"
    if source_path == "brew-log/progress.md":
        return "progress-log"
    return "unknown"


def safety_classification(source_path: str) -> str:
    if source_path in {"PROJECT_COFFEE.md", "AGENTS.md"}:
        return "project-policy"
    if source_path.startswith("docs/") or source_path in {"ROADMAP.md", "CHANGELOG.md"}:
        return "public-project-doc"
    if source_path.startswith("brew-log/") or source_path.startswith("knowledge/"):
        return "local-project-note"
    if source_path.startswith(("roastery/", "ledger/", "config/")):
        return "local-only-evidence"
    return "local-project-note"


def normalize_snippet(snippet: str) -> str:
    return " ".join(snippet.lower().split())


def is_excluded_path(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    parts = [part.lower() for part in relative.parts]
    if not parts:
        return False
    for part in parts:
        if part.startswith("."):
            return True
        if part in EXCLUDED_EXACT_PARTS:
            return True
        if any(marker in part for marker in EXCLUDED_MARKERS):
            return True
    if len(parts) >= 2 and parts[0] == "roastery" and parts[1] in {"local_cup_outputs", "local_reports"}:
        return True
    return False


def is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError):
        return False
    return True


def looks_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(1024)
    except OSError:
        return True
    return b"\0" in chunk


def display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def list_sources_payload(root: str | Path, requested_sources: Sequence[str] | None = None) -> dict[str, Any]:
    root_path = validate_root(root)
    sources = resolve_sources(root_path, requested_sources)
    return {
        "root": str(root_path),
        "sources": [source.label for source in sources],
    }


def render_sources_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "Project Coffee Evidence Sources",
        f"Root: {payload['root']}",
        "",
        "Sources:",
    ]
    for source in payload["sources"]:
        lines.append(f"- {source}")
    return "\n".join(lines)


def render_bundle_markdown(report: dict[str, Any]) -> str:
    lines = [
        "Project Coffee Evidence Bundle",
        f"Root: {report['root']}",
        f"Query: {report['query']}",
        f"Generated: {report['generated_at']}",
        f"Total matches: {report['total_matches']}",
        "",
        "Sources searched:",
    ]
    for source in report["sources_searched"]:
        lines.append(f"- {source}")
    if report["warnings"]:
        lines.extend(["", "Warnings:"])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(["", "Bundle:"])
    if not report["bundle"]:
        lines.append("No evidence matches found.")
        return "\n".join(lines)

    for index, item in enumerate(report["bundle"], start=1):
        line_span = f"{item['line_start']}-{item['line_end']}"
        lines.append(f"{index}. {item['source_path']}:{line_span} (score {item['score']})")
        lines.append(f"   Heading: {item['heading'] or '(none)'}")
        lines.append(f"   Freshness: {item['freshness_signal']}")
        lines.append(f"   Safety: {item['safety_classification']}")
        lines.append(f"   Reason: {item['reason_selected']}")
        lines.append(f"   Snippet: {item['snippet']}")
    return "\n".join(lines)


def validate_output_path(path_text: str) -> Path:
    output_path = Path(path_text).expanduser()
    parent = output_path.parent if output_path.parent != Path("") else Path(".")
    if not parent.exists():
        raise EvidenceBundleError(f"Output parent path does not exist: {parent}")
    if not parent.is_dir():
        raise EvidenceBundleError(f"Output parent path is not a directory: {parent}")
    return output_path


def write_output(path_text: str, text: str) -> Path:
    output_path = validate_output_path(path_text)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def run(
    argv: Sequence[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    parser = build_parser()

    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        try:
            args = parser.parse_args(argv)
        except SystemExit as exc:
            return int(exc.code)

    if not args.list_sources and not args.query:
        print("ERROR: --query is required unless --list-sources is used.", file=errors)
        return 1

    try:
        if args.list_sources:
            payload = list_sources_payload(args.root, args.source)
            text = json.dumps(payload, indent=2) if args.json else render_sources_markdown(payload)
        else:
            report = build_bundle(
                args.root,
                args.query,
                max_results=args.max_results,
                requested_sources=args.source,
            )
            text = json.dumps(report, indent=2) if args.json else render_bundle_markdown(report)

        if args.output:
            output_path = write_output(args.output, text + "\n")
            print(f"Wrote evidence bundle: {output_path}", file=output)
        else:
            print(text, file=output)
    except EvidenceBundleError as exc:
        print(f"ERROR: {exc}", file=errors)
        return 1
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
