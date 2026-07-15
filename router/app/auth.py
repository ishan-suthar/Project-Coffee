"""Username/password authentication for the Coffee Core Router (Brew 43).

Simple and local, exactly as scoped in docs/design/
auth-projects-chat-management-design.md: no OAuth, no JWT, no refresh-
token rotation - a single opaque bearer token per login. Users are only
ever created via router/tools/manage_users.py (a CLI, not a signup
endpoint) - see that module.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Header, HTTPException, Request

from router.app.sessions import SessionStore, UserRecord

TOKEN_TTL_DAYS = 30


class InvalidCredentialsError(Exception):
    """Raised when a username/password pair does not match - the caller
    (main.py) turns this into a generic 401 that never reveals whether
    the username or the password was wrong."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _new_token() -> str:
    # 32 random bytes -> 64 hex characters, matching the literal "random
    # 64-char hex" requirement. secrets.token_hex is CSPRNG-backed
    # (unlike random.choice over a hex alphabet).
    return secrets.token_hex(32)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def login(store: SessionStore, username: str, password: str) -> tuple[str, UserRecord]:
    """Verifies credentials and issues a new token. Raises
    InvalidCredentialsError for either an unknown username or a wrong
    password - deliberately the same error for both, so a caller can
    never learn which one was wrong from the response alone."""

    user = store.get_user_by_username(username)
    if user is None:
        # Still runs a bcrypt comparison against a fixed dummy hash so a
        # timing difference can't reveal "no such username" faster than
        # "wrong password" - constant-time-ish, not just constant-string.
        bcrypt.checkpw(password.encode("utf-8"), bcrypt.gensalt())
        raise InvalidCredentialsError("Invalid username or password.")
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid username or password.")

    token = _new_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)).isoformat()
    store.create_token(token, user.id, expires_at)
    return token, user


def get_current_user(
    request: Request, authorization: Optional[str] = Header(default=None)
) -> UserRecord:
    """FastAPI dependency applied to every /v1/* endpoint except
    POST /v1/login. Reads the live SessionStore off request.app.state.coffee
    at call time (not a store captured at import time), so a single
    module-level function object works for both the real app and tests -
    tests override it wholesale via
    `app.dependency_overrides[get_current_user] = lambda: fake_user`
    rather than needing a real Authorization header on every one of the
    ~100 existing endpoint test call sites (docs/design/
    auth-projects-chat-management-design.md Section 3.1, Gap 3)."""

    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <token>'.")
    token = authorization[len("Bearer "):]

    store: SessionStore = request.app.state.coffee.session_store
    user = store.get_user_for_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")
    return user
