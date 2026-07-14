"""Incremental Pantry indexer CLI for the Coffee Core Router (Brew 41).

Walks `knowledge/` (see router/app/pantry.py:DEFAULT_PANTRY_ROOT), skips
anything Spill-Guard-unsafe or not a text-like extension, chunks each
file, and writes/updates a SQLite FTS5 (BM25) index at
router/data/pantry_index.db (Spill Guard-ignored, same as
sessions.db/preferences.db). Incremental by mtime: a file only gets
re-chunked if its on-disk mtime is newer than what's stored - unchanged
files are skipped entirely on a re-run. Run manually:

    python router/tools/index_pantry.py

No background scheduler - matches this repo's "no new infrastructure"
discipline (router/app/uploads.py's sweep-on-access precedent), and
router restarts don't need this to be automatic since the index isn't on
any request's critical startup path.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from router.app.pantry import (  # noqa: E402
    DEFAULT_INDEX_PATH,
    DEFAULT_PANTRY_ROOT,
    REPO_ROOT,
    chunk_text,
    connect,
    is_indexable_file,
)


@dataclass(frozen=True)
class IndexStats:
    files_indexed: int
    files_skipped_unchanged: int
    files_skipped_unsafe_or_binary: int
    files_removed: int
    chunks_written: int


def index_pantry(
    root: Path = DEFAULT_PANTRY_ROOT,
    index_path: Path = DEFAULT_INDEX_PATH,
    *,
    chunk_size_chars: int,
    overlap_chars: int,
    repo_root: Path = REPO_ROOT,
) -> IndexStats:
    """`repo_root` is overridable (not derived from `root`) so tests can
    index a fully sandboxed fixture tree - stored paths are always
    computed relative to `repo_root`, matching what
    resolve_pantry_file_path() (also repo_root-relative) and the
    `pantry_sources` event field expect."""

    files_indexed = 0
    files_skipped_unchanged = 0
    files_skipped_unsafe_or_binary = 0
    chunks_written = 0

    with connect(index_path) as conn:
        existing_paths: set[str] = set()
        if root.is_dir():
            for candidate in sorted(root.rglob("*")):
                if not candidate.is_file():
                    continue
                if not is_indexable_file(candidate):
                    files_skipped_unsafe_or_binary += 1
                    continue

                rel_path = candidate.resolve().relative_to(repo_root.resolve()).as_posix()
                existing_paths.add(rel_path)
                current_mtime = candidate.stat().st_mtime

                row = conn.execute(
                    "SELECT mtime FROM files WHERE path = ?", (rel_path,)
                ).fetchone()
                if row is not None and row["mtime"] >= current_mtime:
                    files_skipped_unchanged += 1
                    continue

                try:
                    text = candidate.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    # Extension allowlist should already prevent this in
                    # practice, but never let a bad file crash the whole
                    # indexing run.
                    files_skipped_unsafe_or_binary += 1
                    continue

                conn.execute("DELETE FROM chunks WHERE path = ?", (rel_path,))
                chunks = chunk_text(text, chunk_size_chars=chunk_size_chars, overlap_chars=overlap_chars)
                for chunk_index, chunk in enumerate(chunks):
                    conn.execute(
                        "INSERT INTO chunks (path, chunk_index, text) VALUES (?, ?, ?)",
                        (rel_path, chunk_index, chunk),
                    )
                chunks_written += len(chunks)

                conn.execute(
                    "INSERT INTO files (path, mtime) VALUES (?, ?) "
                    "ON CONFLICT(path) DO UPDATE SET mtime = excluded.mtime",
                    (rel_path, current_mtime),
                )
                files_indexed += 1

        # Remove entries for files that no longer exist (deleted or moved
        # since the last run) so stale citations never surface.
        stored_paths = {row["path"] for row in conn.execute("SELECT path FROM files").fetchall()}
        removed_paths = stored_paths - existing_paths
        for stale_path in removed_paths:
            conn.execute("DELETE FROM chunks WHERE path = ?", (stale_path,))
            conn.execute("DELETE FROM files WHERE path = ?", (stale_path,))

    return IndexStats(
        files_indexed=files_indexed,
        files_skipped_unchanged=files_skipped_unchanged,
        files_skipped_unsafe_or_binary=files_skipped_unsafe_or_binary,
        files_removed=len(removed_paths),
        chunks_written=chunks_written,
    )


def main() -> None:
    from router.app.config import Settings

    settings = Settings.from_yaml()
    stats = index_pantry(
        chunk_size_chars=settings.pantry_chunk_size_chars,
        overlap_chars=settings.pantry_chunk_overlap_chars,
    )
    print(
        f"[index_pantry] {stats.files_indexed} file(s) indexed, "
        f"{stats.files_skipped_unchanged} unchanged, "
        f"{stats.files_skipped_unsafe_or_binary} skipped (unsafe/non-text), "
        f"{stats.files_removed} removed, "
        f"{stats.chunks_written} chunk(s) written."
    )


if __name__ == "__main__":
    main()
