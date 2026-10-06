"""Device-wide UI preference storage for the Coffee Core Router (Brew 39).

Generic key/value store, not specific to any one preference - the first
consumer is the animated Coffee Counter scene's collapse state (see
docs/design/counter-scene-design.md Section 5), but this is intentionally
not named counter_collapsed anywhere in this module so future preferences
reuse it without another schema change. Device-wide rather than
session-scoped: the router is single-process/single-user (Brew 36
non-goal, unchanged), and a UI preference like "scene collapsed" is not
naturally tied to one chat session's lifetime the way messages are.

The database file is user runtime data, not source, and lives under
router/data/ alongside sessions.db - already Spill Guard-ignored
(.gitignore/.cursorignore/.cursorindexingignore) since Brew 37, so no new
ignore-file entry is needed.
"""

from __future__ import annotations

import contextlib
import sqlite3
from pathlib import Path
from typing import Dict, Iterator, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "preferences.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class PreferenceStore:
    """Thin wrapper around a SQLite file, one connection per call - same
    pattern as SessionStore (router/app/sessions.py), for the same
    single-process/single-user reason."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def get_all(self) -> Dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM preferences").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def get(self, key: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM preferences WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row is not None else None

    def set(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
