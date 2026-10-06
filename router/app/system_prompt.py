"""Composed system prompt for /v1/order (see router/app/main.py's
_run_order_body/_run_escalation).

Two independently-gated parts, composed by build_system_message() into
ONE system message:

1. Date awareness (Brew 53) - every Bean's training cutoff predates
   "today", so without this a Bean asked "what's the date" answers from
   training data.
2. Identity (Brew 56) - without this a Bean has no idea it is running
   inside Project Coffee at all, and answers "what am I using right now?"
   with a generic description of itself.

Both are injected only on /v1/order, never on /v1/chat/completions - that
endpoint's messages are a caller-assembled `messages_override` sent
verbatim (Cursor and other clients send their own system prompts;
silently prepending to theirs risks interfering with tool-use
instructions).

Deliberately its own tiny module rather than living in main.py - the
date/timezone formatting and the identity text are unrelated to
orchestration and are easiest to unit-test in isolation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from router.app.config import Settings

# settings.system_prompt_timezone's default - resolves to the server's own
# system timezone via datetime.now().astimezone() rather than a pinned
# IANA zone. Case-insensitive so "Local"/"LOCAL" in a hand-edited
# settings.yaml still works.
LOCAL_TIMEZONE_SENTINEL = "local"

# Brew 56. Rides on EVERY /v1/order request, so every character here is
# billed on every request - kept deliberately short (344 chars) rather
# than comprehensive. The fuller manual lives in the Pantry
# (knowledge/coffee-manual.md), which costs nothing unless the user
# actually turns Use Pantry on; this block's last sentence exists to
# point a Bean at it instead of guessing.
#
# ASCII hyphens, not em dashes, matching the date sentence below - this
# text goes out over the wire to arbitrary providers.
IDENTITY_MESSAGE = (
    "You are answering as a Bean - one routed model - inside Project "
    "Coffee, a personal AI routing workstation built by Ishan Suthar. "
    "Coffee routes each request to a cost-appropriate Bean and logs its "
    "real cost to a local Ledger. A fuller manual is in Coffee's Pantry "
    "knowledge base; the user can enable the Use Pantry toggle to make "
    "it retrievable."
)


def _utc_offset_label(dt: datetime) -> str:
    """"UTC-05:00" / "UTC+05:30" / "UTC" (naive datetime, no offset) - an
    explicit numeric offset is unambiguous, unlike a bare abbreviation
    ("CST" is both US Central and China Standard Time)."""

    offset = dt.utcoffset()
    if offset is None:
        return "UTC"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def build_date_system_message(settings: Settings) -> Optional[str]:
    """Returns None when settings.system_prompt_include_date is False - the
    caller (main.py's _with_system_message) treats None as "inject
    nothing". Date-only granularity (never a finer timestamp) is
    deliberate: this message is the first thing in every /v1/order
    request, so if prompt caching is ever added, a value that changes
    every second would defeat any cache on this prefix; a value that
    changes once a day does not."""

    if not settings.system_prompt_include_date:
        return None

    tz_setting = (settings.system_prompt_timezone or LOCAL_TIMEZONE_SENTINEL).strip()
    if tz_setting.lower() == LOCAL_TIMEZONE_SENTINEL:
        now = datetime.now().astimezone()
        tz_label = _utc_offset_label(now)
    else:
        try:
            now = datetime.now(ZoneInfo(tz_setting))
            tz_label = f"{tz_setting} ({_utc_offset_label(now)})"
        except ZoneInfoNotFoundError:
            # An invalid/unrecognized IANA name in settings.yaml must never
            # break every /v1/order request - fall back to the server's
            # own local timezone, same as the default.
            now = datetime.now().astimezone()
            tz_label = _utc_offset_label(now)

    date_str = now.strftime("%Y-%m-%d")
    return (
        f"Today's date is {date_str} ({tz_label}). Use this as the current "
        "date - do not assume a date from your training data."
    )


def build_identity_system_message(settings: Settings) -> Optional[str]:
    """Returns None when settings.system_prompt_include_identity is False.

    Gated independently of system_prompt_include_date - the two answer
    different questions ("when is now" vs "what am I running inside") and
    a user may reasonably want either without the other."""

    if not settings.system_prompt_include_identity:
        return None
    return IDENTITY_MESSAGE


def build_system_message(settings: Settings) -> Optional[str]:
    """Composes the enabled parts into ONE system message, or None when
    every part is disabled (the caller, main.py's _with_system_message,
    treats None as "inject nothing" and returns its input untouched).

    Identity first, date second. The identity text is a fixed constant
    while the date changes daily, so leading with the stable part keeps
    the longest possible common prefix across requests - the same
    prompt-caching reasoning that made build_date_system_message()
    day-granular rather than timestamped.

    Joined with a blank line so the two read as separate statements
    inside one message rather than running together into one paragraph."""

    parts = [
        part
        for part in (
            build_identity_system_message(settings),
            build_date_system_message(settings),
        )
        if part is not None
    ]
    if not parts:
        return None
    return "\n\n".join(parts)
