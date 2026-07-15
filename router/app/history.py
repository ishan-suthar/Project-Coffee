"""Conversation history assembly for the Coffee Core Router (Brew 46).

See docs/design/conversation-memory-design.md. Pure functions only - no
SQLite/network access here, matching the existing classifier.py/
escalation.py style: callers (router/app/main.py) fetch
List[MessageRecord] from SessionStore and pass it in.

A "turn" is one user message paired with its one assistant reply, both
sharing the same request_id. Only complete turns are ever built - a
request that errored or was cancelled is never persisted at all (see
main.py's _run_order_body, which returns before its add_message() calls
on any ErrorEvent/CancelledEvent path), so there is nothing to filter
for a "half-turn" here.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from router.app.sessions import MessageRecord

logger = logging.getLogger(__name__)

IMAGE_HISTORY_NOTE = (
    "[An image was attached to this message but is not included in this "
    "conversation history - ask the user to re-upload it if you need to "
    "see it again.]"
)


def format_attachment_block(filename: str, text: str) -> str:
    """The one inline-attachment delimiter format used everywhere a stored
    or freshly-extracted attachment's text is inlined into a prompt -
    shared by main.py's _build_outbound_content (the current turn) and
    build_turn() below (historical turns), so a historical attachment
    turn reads in exactly the shape it would have live."""

    return f"--- Attached file: {filename} ---\n{text}\n--- end of {filename} ---"


@dataclass(frozen=True)
class Turn:
    request_id: str
    user_content: str  # prompt text, with any stored attachment content already reattached
    assistant_content: str

    @property
    def chars(self) -> int:
        return len(self.user_content) + len(self.assistant_content)


@dataclass(frozen=True)
class HistoryResult:
    messages: List[Dict[str, str]]  # oldest-first, {"role": "user"|"assistant", "content": str}
    turns_included: int
    chars_included: int
    tokens_est: int


# The remember_chat=False case - main.py uses this instead of calling
# assemble_history() at all, so "toggle is off" and "toggle is on but
# nothing fit/existed yet" stay visibly different code paths.
EMPTY_HISTORY_RESULT = HistoryResult(messages=[], turns_included=0, chars_included=0, tokens_est=0)


def _reattach_content(message: MessageRecord) -> str:
    """Rebuilds a historical user message's content exactly as the model
    would have seen it live: the stored prompt text, plus a delimited
    block per stored PDF/text attachment, plus one image note if any
    attachment on this turn was an image (never the image bytes
    themselves - see the design doc's Open Question 3 resolution)."""

    if not message.attachments_json:
        return message.content

    try:
        attachments = json.loads(message.attachments_json)
    except (json.JSONDecodeError, TypeError):
        # Defensive only - attachments_json is always written by this same
        # codebase (main.py), never user-supplied. Malformed JSON here
        # would mean a bug elsewhere, not a case to raise on and abort an
        # otherwise-valid history assembly.
        logger.warning("Malformed attachments_json for message request_id=%s", message.request_id)
        return message.content

    parts = [message.content]
    has_image = False
    for attachment in attachments:
        if attachment.get("kind") == "image":
            has_image = True
            continue
        extracted_text = attachment.get("extracted_text") or ""
        parts.append(format_attachment_block(attachment.get("filename", "attachment"), extracted_text))
    if has_image:
        parts.append(IMAGE_HISTORY_NOTE)

    return "\n\n".join(parts)


def pair_turns(messages: List[MessageRecord]) -> List[Turn]:
    """Groups oldest-first messages by request_id, keeping only groups
    with exactly one user and one assistant row. draft_quality exclusion
    (docs/design/conversation-memory-design.md Section 2, Open Question
    2): a draft_quality assistant message is excluded unless it is the
    only assistant response for its request_id - under this codebase's
    current one-assistant-row-per-request_id architecture that is always
    true, so this check never actually excludes a message today. Kept
    explicit (not silently dropped) for forward-compatibility, and
    documented rather than left to look like an oversight."""

    by_request: "Dict[str, Dict[str, List[MessageRecord]]]" = {}
    order: List[str] = []
    for message in messages:
        if message.request_id not in by_request:
            by_request[message.request_id] = {"user": [], "assistant": []}
            order.append(message.request_id)
        by_request[message.request_id][message.role].append(message)

    turns: List[Turn] = []
    for request_id in order:
        group = by_request[request_id]
        user_rows = group["user"]
        assistant_rows = group["assistant"]
        if len(user_rows) != 1 or len(assistant_rows) != 1:
            continue

        assistant_row = assistant_rows[0]
        # Always true today (see docstring above) - kept as a real check,
        # not a comment-only assumption.
        is_only_assistant_response = len(assistant_rows) == 1
        if assistant_row.draft_quality and not is_only_assistant_response:
            continue

        turns.append(
            Turn(
                request_id=request_id,
                user_content=_reattach_content(user_rows[0]),
                assistant_content=assistant_row.content,
            )
        )
    return turns


def assemble_history(
    turns: List[Turn],
    *,
    current_prompt_chars: int,
    max_messages: int,
    max_chars: int,
) -> HistoryResult:
    """turns must already be oldest-first. Reserves current_prompt_chars
    from max_chars first - the current prompt is never a trimming
    candidate, only historical turns are ever dropped - then walks
    turns newest-to-oldest, greedily including whole turns while both
    the message-count and char budgets allow it, and reverses back to
    oldest-first for the returned messages list."""

    remaining_chars = max(0, max_chars - current_prompt_chars)
    if remaining_chars == 0 and turns:
        logger.warning(
            "Current prompt alone (%d chars) meets or exceeds history_max_chars (%d) - "
            "sending with no history.",
            current_prompt_chars,
            max_chars,
        )

    included: List[Turn] = []
    messages_count = 0
    chars_count = 0
    for turn in reversed(turns):
        if messages_count + 2 > max_messages:
            break
        if chars_count + turn.chars > remaining_chars:
            break
        included.append(turn)
        messages_count += 2
        chars_count += turn.chars

    included.reverse()

    messages: List[Dict[str, str]] = []
    for turn in included:
        messages.append({"role": "user", "content": turn.user_content})
        messages.append({"role": "assistant", "content": turn.assistant_content})

    tokens_est = chars_count // 4

    logger.info(
        "History assembled: remember_chat turns_included=%d chars_included=%d tokens_est=%d",
        len(included),
        chars_count,
        tokens_est,
    )

    return HistoryResult(
        messages=messages,
        turns_included=len(included),
        chars_included=chars_count,
        tokens_est=tokens_est,
    )
