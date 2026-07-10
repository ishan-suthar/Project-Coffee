"""SQLite session/message storage for the Coffee Core Router.

Sessions group messages by a client-supplied `project` string (not a
rebuild of Fleet's multi-root logic - see docs/design/
coffee-counter-chat-ui-design.md Section 3.1). The database file is user
runtime data (chat history), not source, and lives under router/data/,
which is Spill Guard-ignored (see .gitignore/.cursorignore/
.cursorindexingignore).
"""

from __future__ import annotations

import contextlib
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sessions.db"

TITLE_MAX_CHARS = 80

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_seq INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    request_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    bean_alias TEXT,
    task_type TEXT,
    complexity TEXT,
    cost_usd REAL,
    latency_ms INTEGER,
    escalated INTEGER,
    draft_quality INTEGER,
    rating TEXT,
    created_at TEXT NOT NULL
);
"""


def _iso_now() -> str:
    # timespec="microseconds" forces a consistent, comparable string
    # length/format even when the microsecond component happens to be
    # exactly 0 - the default isoformat() silently omits it in that case,
    # which breaks lexical string ordering assumptions.
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _seq_now() -> int:
    # Wall-clock nanoseconds, used purely as a tiebreaker for ordering
    # writes that land in the same ISO-microsecond tick (rare but real -
    # see router/tests/test_sessions.py::test_list_sessions_ordered_newest_updated_first).
    # Unlike an in-process counter, this stays meaningfully ordered across
    # router restarts too, since it tracks wall time rather than resetting.
    return time.time_ns()


@dataclass(frozen=True)
class SessionSummary:
    id: str
    project: str
    title: str
    created_at: str
    updated_at: str
    cost_total_usd: float


@dataclass(frozen=True)
class MessageRecord:
    id: str
    session_id: str
    request_id: str
    role: str  # "user" | "assistant"
    content: str
    bean_alias: Optional[str]
    task_type: Optional[str]
    complexity: Optional[str]
    cost_usd: Optional[float]
    latency_ms: Optional[int]
    escalated: Optional[bool]
    draft_quality: Optional[bool]
    rating: Optional[str]
    created_at: str


class SessionStore:
    """Thin wrapper around a SQLite file. One connection per call, opened
    and closed per method - the router is single-process/single-user
    (Brew 36 non-goal), so no connection pool is needed."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection, commit or roll back the transaction, and
        always close the connection - `with sqlite3.connect(...) as conn`
        alone only manages the transaction, not the file handle, which
        leaves Windows unable to delete the underlying file afterward."""

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

    def create_session(self, project: str, title: str = "New session") -> str:
        session_id = str(uuid.uuid4())
        now = _iso_now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (id, project, title, created_at, updated_at, updated_seq) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, project, title[:TITLE_MAX_CHARS], now, now, _seq_now()),
            )
        return session_id

    def list_sessions(self, project: str) -> List[SessionSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.project, s.title, s.created_at, s.updated_at,
                       COALESCE(SUM(m.cost_usd), 0.0) AS cost_total_usd
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id
                WHERE s.project = ?
                GROUP BY s.id
                ORDER BY s.updated_seq DESC
                """,
                (project,),
            ).fetchall()
        return [
            SessionSummary(
                id=row["id"],
                project=row["project"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                cost_total_usd=row["cost_total_usd"],
            )
            for row in rows
        ]

    def get_messages(self, session_id: str) -> List[MessageRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        return [_row_to_message(row) for row in rows]

    def session_exists(self, session_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return row is not None

    def add_message(
        self,
        session_id: str,
        *,
        request_id: str,
        role: str,
        content: str,
        bean_alias: Optional[str] = None,
        task_type: Optional[str] = None,
        complexity: Optional[str] = None,
        cost_usd: Optional[float] = None,
        latency_ms: Optional[int] = None,
        escalated: Optional[bool] = None,
        draft_quality: Optional[bool] = None,
    ) -> str:
        message_id = str(uuid.uuid4())
        now = _iso_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    id, session_id, request_id, role, content, bean_alias,
                    task_type, complexity, cost_usd, latency_ms, escalated,
                    draft_quality, rating, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    message_id,
                    session_id,
                    request_id,
                    role,
                    content,
                    bean_alias,
                    task_type,
                    complexity,
                    cost_usd,
                    latency_ms,
                    None if escalated is None else int(escalated),
                    None if draft_quality is None else int(draft_quality),
                    now,
                ),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ?, updated_seq = ? WHERE id = ?",
                (now, _seq_now(), session_id),
            )
        return message_id

    def set_title_if_default(self, session_id: str, title: str) -> None:
        """Set a session's title from its first user message, but only if
        it still has the default placeholder title (never overwrite a
        title once set)."""

        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ? AND title = 'New session'",
                (title[:TITLE_MAX_CHARS], session_id),
            )

    def update_message_rating(self, request_id: str, rating: str) -> bool:
        """Returns True if a message row was updated, False if request_id
        was not found (caller decides whether that is an error)."""

        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE messages SET rating = ? WHERE request_id = ?", (rating, request_id)
            )
            return cursor.rowcount > 0


def _row_to_message(row: sqlite3.Row) -> MessageRecord:
    return MessageRecord(
        id=row["id"],
        session_id=row["session_id"],
        request_id=row["request_id"],
        role=row["role"],
        content=row["content"],
        bean_alias=row["bean_alias"],
        task_type=row["task_type"],
        complexity=row["complexity"],
        cost_usd=row["cost_usd"],
        latency_ms=row["latency_ms"],
        escalated=None if row["escalated"] is None else bool(row["escalated"]),
        draft_quality=None if row["draft_quality"] is None else bool(row["draft_quality"]),
        rating=row["rating"],
        created_at=row["created_at"],
    )
