"""SQLite session/message/user/project storage for the Coffee Core Router.

Sessions group messages by an optional project (Brew 43 - a real
`projects` table with a foreign key, not the free-form `project` string
this file used before; see docs/design/auth-projects-chat-management-design.md
Section 4). The database file is user runtime data (chat history,
credentials), not source, and lives under router/data/, which is Spill
Guard-ignored (see .gitignore/.cursorignore/.cursorindexingignore).
"""

from __future__ import annotations

import contextlib
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, List, Optional

from router.app.uploads import truncate_inline_text

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

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Brew 47 Section 2 (docs/design/openai-compat-endpoint-design.md): a
-- durable per-request record for POST /v1/chat/completions traffic only -
-- retry-detection lookups and shadow-mode response pairs, neither of
-- which belongs in the ephemeral in-memory RouterState or the append-only
-- Ledger CSV (a Ledger row is written once and never holds full response
-- text). completed_at is distinct from created_at: retry_detection_window_
-- seconds measures time since the ORIGINAL finished, not since it started
-- (a slow original shouldn't get a wider retry window). A row for a
-- request that ultimately errored stays with response_text NULL forever -
-- never eligible as a retry match (mirrors Brew 46's "never persist a
-- failed turn"), and not cleaned up specially - only a manual
-- router/tools/prune_api_requests.py run removes anything from this table.
CREATE TABLE IF NOT EXISTS api_requests (
    request_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    client_fingerprint TEXT NOT NULL,
    last_user_message_hash TEXT NOT NULL,
    response_text TEXT,
    is_shadow INTEGER NOT NULL DEFAULT 0,
    shadow_of TEXT,
    shadow_response_text TEXT,
    shadow_bean_alias TEXT,
    retry_of TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0
);
"""

# Brew 43 (docs/design/auth-projects-chat-management-design.md Section 3.1,
# Gap 4): columns added to the pre-existing `sessions` table. SQLite's
# `CREATE TABLE IF NOT EXISTS` above never adds columns to an
# already-existing table, so these are applied via `ALTER TABLE ... ADD
# COLUMN` in `_migrate_schema()`, guarded by `PRAGMA table_info` so it is
# safe to run on every startup. The old `project` TEXT column is left in
# place, unused by any new code path - not worth the risk of a
# destructive rename/migration for a column that has only ever held the
# literal string "default" in every real row to date.
SESSIONS_NEW_COLUMNS = {
    "user_id": "INTEGER REFERENCES users(id)",
    "project_id": "INTEGER REFERENCES projects(id)",
    "deleted_at": "TEXT",
    # Brew 46 (docs/design/conversation-memory-design.md Section 1): per-
    # session, user-controlled conversation memory. DEFAULT 1 applies to
    # every existing row the moment this column is added, satisfying
    # "a session created before this migration defaults to TRUE" with no
    # separate backfill step.
    "remember_chat": "INTEGER NOT NULL DEFAULT 1",
}

# Spend-cap Brew: a per-user override for settings.per_user_daily_cost_cap_usd.
# NULL (the default for every existing user the moment this migration
# runs) means "use the settings.yaml default" - never a silent 0 or a
# guessed value. Same incremental-migration pattern as SESSIONS_NEW_COLUMNS.
USERS_NEW_COLUMNS = {
    "daily_cost_cap_usd": "REAL",
}

# Brew 46 (docs/design/conversation-memory-design.md Section 3): extracted
# attachment content (never raw image bytes - see the design doc's Open
# Question 3 resolution), persisted alongside the user message it belongs
# to so it survives past the request that uploaded it. Same incremental-
# migration pattern as SESSIONS_NEW_COLUMNS, applied to `messages` instead.
MESSAGES_NEW_COLUMNS = {
    "attachments_json": "TEXT",
}


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
    project_id: Optional[int] = None
    remember_chat: bool = True


@dataclass(frozen=True)
class SessionRecord:
    """A lighter-weight session lookup than SessionSummary - no cost-total
    JOIN/aggregation, just enough for /v1/order to resolve remember_chat
    server-side before assembling history (docs/design/
    conversation-memory-design.md Section 1)."""

    id: str
    remember_chat: bool


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
    # Brew 46: raw JSON text of persisted attachment content (None if this
    # message had no attachments) - see attachments_json() below for the
    # parsed form and has_attachments for the cheap boolean the frontend
    # needs without shipping extracted text back over the wire.
    attachments_json: Optional[str] = None

    @property
    def has_attachments(self) -> bool:
        return self.attachments_json is not None


@dataclass(frozen=True)
class ApiRequestRecord:
    """Brew 47 Section 2 - a row from `api_requests`. `response_text`/
    `shadow_response_text` are None until the corresponding generation
    completes; `retry_of`/`shadow_of` are None unless this row matched a
    prior request or was itself a shadow run."""

    request_id: str
    created_at: str
    completed_at: Optional[str]
    user_id: int
    client_fingerprint: str
    last_user_message_hash: str
    response_text: Optional[str]
    is_shadow: bool
    shadow_of: Optional[str]
    shadow_response_text: Optional[str]
    shadow_bean_alias: Optional[str]
    retry_of: Optional[str]
    retry_count: int


@dataclass(frozen=True)
class UserRecord:
    id: int
    username: str
    password_hash: str
    display_name: str
    created_at: str
    # Spend-cap Brew: per-user override for settings.per_user_daily_cost_cap_usd.
    # None means "use the settings.yaml default" - see USERS_NEW_COLUMNS.
    daily_cost_cap_usd: Optional[float] = None


@dataclass(frozen=True)
class ProjectRecord:
    id: int
    user_id: int
    name: str
    created_at: str
    updated_at: str


class UsernameTakenError(Exception):
    """Raised by create_user() when the username already exists."""


class SessionStore:
    """Thin wrapper around a SQLite file. One connection per call, opened
    and closed per method - the router is single-process/single-user-
    process (Brew 36 non-goal - "single-user" there meant single OS
    process, not single human; Brew 43 adds real multiple human users
    within that one process), so no connection pool is needed."""

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
            self._migrate_schema(conn)

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        self._migrate_table_columns(conn, "sessions", SESSIONS_NEW_COLUMNS)
        self._migrate_table_columns(conn, "messages", MESSAGES_NEW_COLUMNS)
        self._migrate_table_columns(conn, "users", USERS_NEW_COLUMNS)

    @staticmethod
    def _migrate_table_columns(conn: sqlite3.Connection, table: str, new_columns: dict) -> None:
        existing_cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col_name, col_def in new_columns.items():
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")

    # --- Sessions -----------------------------------------------------

    def create_session(
        self,
        project: str = "default",
        title: str = "New session",
        *,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> str:
        session_id = str(uuid.uuid4())
        now = _iso_now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (id, project, title, created_at, updated_at, updated_seq, user_id, project_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, project, title[:TITLE_MAX_CHARS], now, now, _seq_now(), user_id, project_id),
            )
        return session_id

    def list_sessions(
        self,
        project: Optional[str] = None,
        *,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        all_projects: bool = False,
    ) -> List[SessionSummary]:
        """project (legacy, positional-optional) filters on the old
        free-form `project` TEXT column exactly as before Brew 43 - kept
        for old direct-Python-call sites that predate the real `projects`
        table. When `project` is given, it is the *only* filter besides
        `deleted_at`/`user_id` (project_id/all_projects are ignored) -
        the two filtering systems are deliberately not mixed. New code
        should pass `project=None` (the default) and use
        project_id/all_projects instead. user_id is an optional filter -
        omitted means unscoped, matching pre-Brew-43 behavior for tests/
        fixtures that don't care about auth."""

        clauses = ["s.deleted_at IS NULL"]
        params: list = []
        if user_id is not None:
            clauses.append("s.user_id = ?")
            params.append(user_id)
        if project is not None:
            clauses.append("s.project = ?")
            params.append(project)
        elif not all_projects:
            if project_id is not None:
                clauses.append("s.project_id = ?")
                params.append(project_id)
            else:
                clauses.append("s.project_id IS NULL")
        where_sql = " AND ".join(clauses)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT s.id, s.project, s.title, s.created_at, s.updated_at, s.project_id,
                       s.remember_chat,
                       COALESCE(SUM(m.cost_usd), 0.0) AS cost_total_usd
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id
                WHERE {where_sql}
                GROUP BY s.id
                ORDER BY s.updated_seq DESC
                """,
                params,
            ).fetchall()
        return [
            SessionSummary(
                id=row["id"],
                project=row["project"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                cost_total_usd=row["cost_total_usd"],
                project_id=row["project_id"],
                remember_chat=bool(row["remember_chat"]),
            )
            for row in rows
        ]

    def get_session(self, session_id: str, *, user_id: Optional[int] = None) -> Optional[SessionRecord]:
        """Brew 46 (docs/design/conversation-memory-design.md Section 1):
        the single lookup /v1/order needs to both confirm the session
        exists/is owned by user_id (replacing session_exists() at that
        call site) and resolve remember_chat, in one query instead of
        two. Returns None for a missing, soft-deleted, or
        not-owned-by-user_id session - same "never distinguish these"
        convention as session_exists()."""

        clauses = ["id = ?", "deleted_at IS NULL"]
        params: list = [session_id]
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT id, remember_chat FROM sessions WHERE {' AND '.join(clauses)}", params
            ).fetchone()
        if row is None:
            return None
        return SessionRecord(id=row["id"], remember_chat=bool(row["remember_chat"]))

    def set_remember_chat(self, session_id: str, remember_chat: bool, *, user_id: Optional[int] = None) -> bool:
        """PATCH /v1/sessions/{id}'s remember_chat field (Section 1) -
        flipping this never deletes anything; OFF just stops history
        assembly, ON resumes with whatever is already stored. Returns
        True if a row was updated."""

        where_clauses = ["id = ?", "deleted_at IS NULL"]
        where_params: list = [session_id]
        if user_id is not None:
            where_clauses.append("user_id = ?")
            where_params.append(user_id)
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE sessions SET remember_chat = ? WHERE {' AND '.join(where_clauses)}",
                [int(remember_chat), *where_params],
            )
            return cursor.rowcount > 0

    def get_messages(self, session_id: str) -> List[MessageRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        return [_row_to_message(row) for row in rows]

    def session_exists(self, session_id: str, *, user_id: Optional[int] = None) -> bool:
        clauses = ["id = ?", "deleted_at IS NULL"]
        params: list = [session_id]
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT 1 FROM sessions WHERE {' AND '.join(clauses)}", params
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
        attachments_json: Optional[str] = None,
    ) -> str:
        message_id = str(uuid.uuid4())
        now = _iso_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    id, session_id, request_id, role, content, bean_alias,
                    task_type, complexity, cost_usd, latency_ms, escalated,
                    draft_quality, rating, created_at, attachments_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
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
                    attachments_json,
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
        title once set). Distinct from rename_session() (Brew 43), which
        is an explicit human request and always overwrites."""

        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ? AND title = 'New session'",
                (title[:TITLE_MAX_CHARS], session_id),
            )

    def rename_session(self, session_id: str, title: str, *, user_id: Optional[int] = None) -> bool:
        """Explicit human rename (Brew 43, PATCH /v1/sessions/{id}) -
        always overwrites, unlike set_title_if_default(). Returns True if
        a row was updated (exists, not soft-deleted, and owned by
        user_id when given)."""

        where_clauses = ["id = ?", "deleted_at IS NULL"]
        where_params: list = [session_id]
        if user_id is not None:
            where_clauses.append("user_id = ?")
            where_params.append(user_id)
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE sessions SET title = ? WHERE {' AND '.join(where_clauses)}",
                [title[:TITLE_MAX_CHARS], *where_params],
            )
            return cursor.rowcount > 0

    def soft_delete_session(self, session_id: str, *, user_id: Optional[int] = None) -> bool:
        """Brew 43: sets deleted_at instead of removing the row - every
        query in this class already filters `deleted_at IS NULL`, so a
        soft-deleted session becomes invisible everywhere without a
        data-loss risk. Returns True if a row was updated."""

        where_clauses = ["id = ?", "deleted_at IS NULL"]
        where_params: list = [session_id]
        if user_id is not None:
            where_clauses.append("user_id = ?")
            where_params.append(user_id)
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE sessions SET deleted_at = ? WHERE {' AND '.join(where_clauses)}",
                [_iso_now(), *where_params],
            )
            return cursor.rowcount > 0

    def update_message_rating(self, request_id: str, rating: str) -> bool:
        """Returns True if a message row was updated, False if request_id
        was not found (caller decides whether that is an error)."""

        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE messages SET rating = ? WHERE request_id = ?", (rating, request_id)
            )
            return cursor.rowcount > 0

    # --- Users and tokens (Brew 43) ------------------------------------

    def create_user(self, username: str, password_hash: str, display_name: str) -> int:
        now = _iso_now()
        with self._connect() as conn:
            try:
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash, display_name, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (username, password_hash, display_name, now),
                )
            except sqlite3.IntegrityError as exc:
                raise UsernameTakenError(f"Username {username!r} is already taken.") from exc
            return cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return _row_to_user(row) if row is not None else None

    def get_user_by_id(self, user_id: int) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_user(row) if row is not None else None

    def list_users(self) -> List[UserRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at ASC").fetchall()
        return [_row_to_user(row) for row in rows]

    def delete_user(self, username: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
            return cursor.rowcount > 0

    def set_user_daily_cost_cap(self, username: str, daily_cost_cap_usd: Optional[float]) -> bool:
        """Sets or clears (None) a per-user override for
        settings.per_user_daily_cost_cap_usd - router/tools/manage_users.py
        set-cap. Returns True if a row was updated."""

        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE users SET daily_cost_cap_usd = ? WHERE username = ?",
                (daily_cost_cap_usd, username),
            )
            return cursor.rowcount > 0

    def create_token(self, token: str, user_id: int, expires_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, _iso_now(), expires_at),
            )

    def get_user_for_token(self, token: str) -> Optional[UserRecord]:
        """Returns None for a missing OR expired token - callers never
        need to distinguish the two (both mean "not authenticated").
        Expired tokens are simply filtered at lookup time, not swept by
        a background job - matching this repo's consistent "no new
        background infrastructure" discipline."""

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.* FROM tokens t
                JOIN users u ON u.id = t.user_id
                WHERE t.token = ? AND t.expires_at > ?
                """,
                (token, _iso_now()),
            ).fetchone()
        return _row_to_user(row) if row is not None else None

    def delete_token(self, token: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
            return cursor.rowcount > 0

    # --- Projects (Brew 43) --------------------------------------------

    def create_project(self, user_id: int, name: str) -> ProjectRecord:
        now = _iso_now()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO projects (user_id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, name, now, now),
            )
            project_id = cursor.lastrowid
        return ProjectRecord(id=project_id, user_id=user_id, name=name, created_at=now, updated_at=now)

    def list_projects(self, user_id: int) -> List[ProjectRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM projects WHERE user_id = ? ORDER BY created_at ASC", (user_id,)
            ).fetchall()
        return [_row_to_project(row) for row in rows]

    def get_project(self, project_id: int, *, user_id: Optional[int] = None) -> Optional[ProjectRecord]:
        clauses = ["id = ?"]
        params: list = [project_id]
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM projects WHERE {' AND '.join(clauses)}", params
            ).fetchone()
        return _row_to_project(row) if row is not None else None

    def rename_project(self, project_id: int, name: str, *, user_id: Optional[int] = None) -> bool:
        clauses = ["id = ?"]
        params: list = [project_id]
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE projects SET name = ?, updated_at = ? WHERE {' AND '.join(clauses)}",
                [name, _iso_now(), *params],
            )
            return cursor.rowcount > 0

    def delete_project(self, project_id: int, *, user_id: Optional[int] = None) -> bool:
        """Deletes the project row and, in the same connection/transaction,
        moves its sessions to project_id NULL ("default") - never deletes
        the sessions themselves (docs/design/auth-projects-chat-management-design.md
        Section 4.1)."""

        clauses = ["id = ?"]
        params: list = [project_id]
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        with self._connect() as conn:
            cursor = conn.execute(f"SELECT id FROM projects WHERE {' AND '.join(clauses)}", params)
            if cursor.fetchone() is None:
                return False
            conn.execute("UPDATE sessions SET project_id = NULL WHERE project_id = ?", (project_id,))
            conn.execute(f"DELETE FROM projects WHERE {' AND '.join(clauses)}", params)
            return True

    # --- API requests (Brew 47) -----------------------------------------

    def create_api_request(
        self, request_id: str, *, user_id: int, client_fingerprint: str, last_user_message_hash: str
    ) -> None:
        """Inserted before generation starts, not after - a concurrent
        duplicate request arriving in the same instant must see this row
        as in-flight (response_text IS NULL), never as a prior completed
        answer to match a retry against (docs/design/
        openai-compat-endpoint-design.md Section 2, the parallelism-vs-
        retry edge case)."""

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO api_requests (request_id, created_at, user_id, client_fingerprint, "
                "last_user_message_hash) VALUES (?, ?, ?, ?, ?)",
                (request_id, _iso_now(), user_id, client_fingerprint, last_user_message_hash),
            )

    def complete_api_request(self, request_id: str, response_text: str, *, max_stored_chars: int) -> None:
        """Only called on the real success path - an errored request's
        row stays with response_text NULL forever (never persist a failed
        turn, same precedent as Brew 46's message persistence)."""

        with self._connect() as conn:
            conn.execute(
                "UPDATE api_requests SET response_text = ?, completed_at = ? WHERE request_id = ?",
                (truncate_inline_text(response_text, max_inline_text_chars=max_stored_chars), _iso_now(), request_id),
            )

    def find_retry_candidate(
        self,
        *,
        user_id: int,
        client_fingerprint: str,
        last_user_message_hash: str,
        exclude_request_id: str,
        window_seconds: float,
    ) -> Optional[str]:
        """The Signal A match rule (docs/design/
        openai-compat-endpoint-design.md Section 2): same user_id +
        client_fingerprint + last_user_message_hash, already completed
        (response_text IS NOT NULL - this is what tells a retry apart
        from parallelism, see create_api_request's docstring), within
        window_seconds of ITS completion (not its start). Most recent
        match wins. Returns None when nothing matches."""

        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat(timespec="microseconds")
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT request_id FROM api_requests
                WHERE user_id = ? AND client_fingerprint = ? AND last_user_message_hash = ?
                  AND request_id != ? AND response_text IS NOT NULL AND completed_at >= ?
                ORDER BY completed_at DESC LIMIT 1
                """,
                (user_id, client_fingerprint, last_user_message_hash, exclude_request_id, cutoff),
            ).fetchone()
        return row["request_id"] if row is not None else None

    def set_retry_of(self, request_id: str, retry_of: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE api_requests SET retry_of = ? WHERE request_id = ?", (retry_of, request_id))

    def increment_retry_count(self, request_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE api_requests SET retry_count = retry_count + 1 WHERE request_id = ?", (request_id,)
            )

    def record_shadow_result(
        self, primary_request_id: str, shadow_response_text: str, shadow_bean_alias: str, *, max_stored_chars: int
    ) -> None:
        """Written to the PRIMARY request's row, not a separate row - a
        human reading a pair reads one row, not a join (Section 2)."""

        with self._connect() as conn:
            conn.execute(
                "UPDATE api_requests SET shadow_response_text = ?, shadow_bean_alias = ? WHERE request_id = ?",
                (
                    truncate_inline_text(shadow_response_text, max_inline_text_chars=max_stored_chars),
                    shadow_bean_alias,
                    primary_request_id,
                ),
            )

    def get_api_request(self, request_id: str) -> Optional[ApiRequestRecord]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM api_requests WHERE request_id = ?", (request_id,)).fetchone()
        return _row_to_api_request(row) if row is not None else None

    def prune_api_requests_older_than(self, cutoff_iso: str) -> int:
        """Manual only, never automatic (docs/design/
        openai-compat-endpoint-design.md Section 2, resolved open question
        3) - called only from router/tools/prune_api_requests.py. Returns
        the number of rows deleted."""

        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM api_requests WHERE created_at < ?", (cutoff_iso,))
            return cursor.rowcount


def _row_to_api_request(row: sqlite3.Row) -> ApiRequestRecord:
    return ApiRequestRecord(
        request_id=row["request_id"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        user_id=row["user_id"],
        client_fingerprint=row["client_fingerprint"],
        last_user_message_hash=row["last_user_message_hash"],
        response_text=row["response_text"],
        is_shadow=bool(row["is_shadow"]),
        shadow_of=row["shadow_of"],
        shadow_response_text=row["shadow_response_text"],
        shadow_bean_alias=row["shadow_bean_alias"],
        retry_of=row["retry_of"],
        retry_count=row["retry_count"],
    )


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
        attachments_json=row["attachments_json"],
    )


def _row_to_user(row: sqlite3.Row) -> UserRecord:
    return UserRecord(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        display_name=row["display_name"],
        created_at=row["created_at"],
        daily_cost_cap_usd=row["daily_cost_cap_usd"],
    )


def _row_to_project(row: sqlite3.Row) -> ProjectRecord:
    return ProjectRecord(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
