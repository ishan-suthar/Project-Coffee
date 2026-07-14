"""Pantry retrieval for the Coffee Core Router (Brew 41).

Indexes `knowledge/` into a SQLite FTS5 (BM25) index built by
`router/tools/index_pantry.py`, and provides the query/retrieval and
safe file-serving helpers `router/app/main.py` uses at request time.
See docs/design/memory-and-pantry-design.md.

Scope note (Decaf plan Section 8, Question 1, approved): indexes
literally `knowledge/` - the repository's own hand-curated pointer
index, which has only a handful of files today. Widening the indexed
root is a one-line constant change (`DEFAULT_PANTRY_ROOT`) whenever
that's wanted, not a redesign.
"""

from __future__ import annotations

import contextlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

from tools.coffee_context_package import is_unsafe_path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PANTRY_ROOT = REPO_ROOT / "knowledge"
DEFAULT_INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "pantry_index.db"

# Text-like extensions only - same allowlist philosophy as
# router/app/uploads.py's TEXT_EXTENSIONS (validate by extension, never
# attempt to index something that isn't clearly text).
INDEXABLE_EXTENSIONS = {".md", ".txt", ".py", ".yaml", ".yml", ".json"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    mtime REAL NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
    path UNINDEXED,
    chunk_index UNINDEXED,
    text
);
"""

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class PantryChunk:
    path: str  # repo-root-relative, e.g. "knowledge/00_index.md"
    chunk_index: int
    text: str


def open_index(index_path: Path = DEFAULT_INDEX_PATH) -> sqlite3.Connection:
    """Opens (creating if needed) the pantry FTS5 index. Callers are
    responsible for closing the returned connection - see `connect()`
    for the context-manager form used by request-time queries."""

    index_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(index_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


@contextlib.contextmanager
def connect(index_path: Path = DEFAULT_INDEX_PATH) -> Iterator[sqlite3.Connection]:
    conn = open_index(index_path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def is_indexable_file(path: Path) -> bool:
    """Extension allowlist plus the same Spill Guard path check the rest
    of the router already uses (tools.coffee_context_package.is_unsafe_path) -
    a file under a `secrets/`-marked path, or with an unsafe suffix, is
    never indexed regardless of its extension."""

    if path.suffix.lower() not in INDEXABLE_EXTENSIONS:
        return False
    unsafe, _reason = is_unsafe_path(str(path))
    return not unsafe


def chunk_text(text: str, *, chunk_size_chars: int, overlap_chars: int) -> List[str]:
    """Fixed-size character windows with a small overlap so a fact near a
    chunk boundary isn't lost entirely. Returns [] for empty/whitespace-
    only text - nothing to index."""

    stripped = text.strip()
    if not stripped:
        return []
    if chunk_size_chars <= 0:
        raise ValueError("chunk_size_chars must be positive")

    step = max(1, chunk_size_chars - max(0, overlap_chars))
    chunks: List[str] = []
    start = 0
    while start < len(stripped):
        chunk = stripped[start : start + chunk_size_chars]
        if chunk.strip():
            chunks.append(chunk)
        start += step
    return chunks


def build_fts_query(text: str) -> Optional[str]:
    """Sanitizes free text into a valid FTS5 MATCH expression - a raw
    prompt is not itself a safe MATCH string (unescaped quotes/punctuation
    break the query). Tokenizes to word characters, quotes each token as
    an FTS5 string literal, ORs them together. Returns None if there are
    no tokens (e.g. a punctuation-only or empty prompt) - callers should
    skip retrieval entirely in that case rather than run an invalid
    query."""

    tokens = _TOKEN_PATTERN.findall(text)
    if not tokens:
        return None
    quoted = [f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens]
    return " OR ".join(quoted)


def retrieve_chunks(
    conn: sqlite3.Connection, query_text: str, *, top_k: int
) -> List[PantryChunk]:
    fts_query = build_fts_query(query_text)
    if fts_query is None:
        return []
    rows = conn.execute(
        "SELECT path, chunk_index, text FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?",
        (fts_query, top_k),
    ).fetchall()
    return [PantryChunk(path=row["path"], chunk_index=row["chunk_index"], text=row["text"]) for row in rows]


def resolve_pantry_file_path(
    requested_path: str,
    *,
    repo_root: Path = REPO_ROOT,
    pantry_root: Path = DEFAULT_PANTRY_ROOT,
) -> Optional[Path]:
    """Path-traversal-safe resolution for the read-only file viewer
    endpoint. `requested_path` is expected repo-root-relative (the same
    form stored in `chunks.path` and returned in `pantry_sources`), e.g.
    "knowledge/00_index.md". Returns None (caller 404s) for anything
    absolute, anything that escapes `pantry_root` after resolution
    (`..`, symlink escapes), anything Spill-Guard-unsafe, or anything
    that isn't an existing file - never raises on a bad path.
    `repo_root`/`pantry_root` are overridable (not just derived from one
    another) so tests can fully sandbox both the join base and the
    containment boundary without touching the real repository."""

    if not requested_path:
        return None
    # pathlib's `/` operator silently *replaces* the left side entirely
    # when the right side is absolute (a well-known gotcha) - reject
    # absolute input up front rather than relying on resolve() alone.
    if Path(requested_path).is_absolute():
        return None

    unsafe, _reason = is_unsafe_path(requested_path)
    if unsafe:
        return None

    candidate = (repo_root / requested_path).resolve()
    resolved_root = pantry_root.resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return None

    if not candidate.is_file():
        return None
    return candidate
