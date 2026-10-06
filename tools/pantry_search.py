"""Local Markdown search for Project Coffee Pantry notes.

This tool is intentionally simple: keyword search over safe Markdown files,
with no embeddings, model calls, network calls, or external dependencies.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Iterable, Sequence, TextIO


DEFAULT_ROOT = Path("knowledge")
DEFAULT_INCLUDE = ".md"
DEFAULT_MAX_RESULTS = 10
SNIPPET_CHARS = 160

SENSITIVE_EXACT_NAMES = {
    ".aws",
    ".env",
    ".git",
    ".ssh",
    "__pycache__",
    "credentials",
    "node_modules",
    "secret",
    "secrets",
    "venv",
    ".venv",
}

SENSITIVE_NAME_MARKERS = (
    ".env",
    "credential",
    "secret",
    "token",
)

WORD_RE = re.compile(r"[A-Za-z0-9_]+")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")


@dataclass(frozen=True)
class SearchResult:
    path: str
    line: int
    heading: str
    score: int
    snippet: str

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "heading": self.heading,
            "score": self.score,
            "snippet": self.snippet,
        }


class SearchError(Exception):
    """Raised when the search cannot run safely."""


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--max-results must be an integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("--max-results must be greater than zero")
    return number


def normalize_extension(value: str) -> str:
    extension = value.strip().lower()
    if not extension:
        raise argparse.ArgumentTypeError("--include must not be empty")
    if not extension.startswith("."):
        extension = f".{extension}"
    return extension


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search local Project Coffee Markdown Pantry files.",
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Root directory to search.")
    parser.add_argument("--query", required=True, help="Search query text.")
    parser.add_argument(
        "--max-results",
        type=positive_int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Maximum results to print. Default: {DEFAULT_MAX_RESULTS}.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    parser.add_argument(
        "--include",
        type=normalize_extension,
        default=DEFAULT_INCLUDE,
        help=f"File extension to include. Default: {DEFAULT_INCLUDE}.",
    )
    return parser.parse_args(argv)


def search(
    root: str | Path,
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    include: str = DEFAULT_INCLUDE,
) -> list[SearchResult]:
    root_path = validate_root(root)
    terms = query_terms(query)
    if not terms:
        return []

    extension = normalize_extension(include)
    results: list[SearchResult] = []
    phrase = " ".join(query.strip().lower().split())

    for file_path in iter_safe_files(root_path, extension):
        results.extend(search_file(file_path, root_path, terms, phrase))

    results.sort(key=lambda result: (-result.score, result.path, result.line))
    return results[:max_results]


def validate_root(root: str | Path) -> Path:
    root_path = Path(root).expanduser()
    try:
        resolved = root_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise SearchError(f"Root does not exist: {root_path}") from exc

    if not resolved.is_dir():
        raise SearchError(f"Root is not a directory: {resolved}")
    if is_sensitive_path(resolved):
        raise SearchError(f"Refusing unsafe root path: {resolved}")
    return resolved


def query_terms(query: str) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for match in WORD_RE.finditer(query.lower()):
        term = match.group(0)
        if term not in seen:
            terms.append(term)
            seen.add(term)
    return terms


def iter_safe_files(root: Path, extension: str) -> Iterable[Path]:
    root_resolved = root.resolve()
    for current_root, dirnames, filenames in os.walk(root_resolved, topdown=True, followlinks=False):
        current_path = Path(current_root)
        safe_dirs = []
        for dirname in dirnames:
            candidate = current_path / dirname
            if is_sensitive_path(candidate):
                continue
            if candidate.is_symlink() and not is_within_root(candidate, root_resolved):
                continue
            safe_dirs.append(dirname)
        dirnames[:] = safe_dirs

        for filename in filenames:
            candidate = current_path / filename
            if is_sensitive_path(candidate):
                continue
            if candidate.suffix.lower() != extension:
                continue
            if candidate.is_symlink() and not is_within_root(candidate, root_resolved):
                continue
            if looks_binary(candidate):
                continue
            yield candidate


def search_file(path: Path, root: Path, terms: Sequence[str], phrase: str) -> list[SearchResult]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    except OSError:
        return []

    display_path = path.relative_to(root).as_posix()
    current_heading = ""
    results: list[SearchResult] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        heading_match = HEADING_RE.match(line)
        if heading_match:
            current_heading = heading_match.group(1).strip()

        score = score_line(line, current_heading, terms, phrase, is_heading=bool(heading_match))
        if score <= 0:
            continue

        results.append(
            SearchResult(
                path=display_path,
                line=line_number,
                heading=current_heading,
                score=score,
                snippet=make_snippet(line, terms, phrase),
            )
        )

    return results


def score_line(
    line: str,
    heading: str,
    terms: Sequence[str],
    phrase: str,
    *,
    is_heading: bool,
) -> int:
    line_lower = line.lower()
    heading_lower = heading.lower()
    line_hits = sum(line_lower.count(term) for term in terms)
    if line_hits == 0:
        return 0

    heading_hits = sum(heading_lower.count(term) for term in terms)
    phrase_hits = line_lower.count(phrase) if phrase else 0
    heading_phrase_hits = heading_lower.count(phrase) if phrase else 0

    score = line_hits * 10
    score += phrase_hits * 20
    score += heading_hits * 8
    score += heading_phrase_hits * 12
    if is_heading:
        score += 25
    return score


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


def is_sensitive_path(path: Path) -> bool:
    for part in path.parts:
        name = part.lower()
        if name in SENSITIVE_EXACT_NAMES:
            return True
        if any(marker in name for marker in SENSITIVE_NAME_MARKERS):
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


def print_human_results(
    query: str,
    root: Path,
    results: Sequence[SearchResult],
    stdout: TextIO,
) -> None:
    print("Project Coffee Pantry Search", file=stdout)
    print(f"Query: {query}", file=stdout)
    print(f"Root: {root}", file=stdout)
    print("", file=stdout)

    if not results:
        print("No results found", file=stdout)
        return

    for index, result in enumerate(results, start=1):
        print(f"{index}. {result.path}:{result.line} (score {result.score})", file=stdout)
        print(f"   Heading: {result.heading or '(none)'}", file=stdout)
        print(f"   Snippet: {result.snippet}", file=stdout)


def print_json_results(
    query: str,
    root: Path,
    results: Sequence[SearchResult],
    stdout: TextIO,
) -> None:
    payload = {
        "query": query,
        "root": str(root),
        "result_count": len(results),
        "results": [result.as_dict() for result in results],
    }
    print(json.dumps(payload, indent=2), file=stdout)


def run(
    argv: Sequence[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr

    try:
        args = parse_args(argv)
        root = validate_root(args.root)
        results = search(
            root=root,
            query=args.query,
            max_results=args.max_results,
            include=args.include,
        )
    except SearchError as exc:
        print(f"ERROR: {exc}", file=errors)
        return 1

    if args.json:
        print_json_results(args.query, root, results, output)
    else:
        print_human_results(args.query, root, results, output)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
