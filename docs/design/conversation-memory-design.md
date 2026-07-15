# Decaf Plan: Conversation Memory ("Remember Chat"), Attachment Persistence, and Ledger Auditability

Status: DRAFT - awaiting approval. No code changes made yet.

## Problem, confirmed by reading the code

- `_run_order_body()` (`router/app/main.py:373`) builds `outbound_text` from
  only the current prompt (plus any attachments on *this* request) via
  `_build_outbound_content()`. Prior session messages are persisted
  (`state.session_store.add_message(...)` at the end of `_run_order_body`,
  lines 657-674) and rendered by the UI (`chatStore.selectSession`), but
  never read back into the outbound payload. The router is genuinely
  single-turn today, confirmed by reading the whole request path, not
  assumed.
- `stream_order()` (`router/app/openrouter_client.py:38`) always builds
  `"messages": [{"role": "user", "content": content}]` - one message,
  no history parameter exists at all today.
- Uploaded file content (`UploadRecord.extracted_text`, images read from
  disk at send time) is held only in `RouterState.uploads` (in-memory,
  keyed by `attachment_id`) and the raw file only in
  `router/uploads/<request_id>/`, both deliberately cleaned up in
  `run_order()`'s `finally` block (`main.py:367-370`,
  `uploads.py:cleanup_request_uploads`) once the request completes -
  confirmed nothing about extracted text is written to `sessions.db`
  today.
- A real, useful **pre-existing finding**: on any `ErrorEvent` or
  `CancelledEvent` path, `_run_order_body` returns *before* reaching the
  `add_message` calls - so a failed/cancelled turn is never persisted to
  `sessions.db` at all today. This already solves the "a session whose
  only prior turn errored" edge case for free: there is nothing to
  filter, because nothing was ever stored. Stated explicitly so this
  isn't mistaken for something this Brew needs to add filtering for.
- A second finding: the module docstring at the top of
  `router/app/classifier.py` already claims "a data table (TASK_TYPE_RULES,
  COMPLEXITY_SIGNALS)" exists - but only `TASK_TYPE_RULES` is real;
  `_classify_complexity()` is plain sequential `if` statements today, no
  `COMPLEXITY_SIGNALS` table exists. This Brew's requirement to add
  history length "as a data structure change, not scattered ifs" is the
  natural moment to build the table the docstring already promises,
  not a new one-off pattern.

## 1. `remember_chat` toggle

**Schema** (`router/app/sessions.py`): add `remember_chat` to
`SESSIONS_NEW_COLUMNS` (the existing incremental-migration dict, same
`PRAGMA table_info`-guarded `ALTER TABLE` pattern Brew 43 already
established): `"remember_chat": "INTEGER NOT NULL DEFAULT 1"`. SQLite
applies a column default to every existing row on `ALTER TABLE ADD
COLUMN`, so every pre-migration session gets `TRUE` immediately -
satisfies the "session created before this migration" edge case with
no extra code.

**Reading it**: a new `SessionStore.get_session(session_id, *,
user_id=None) -> Optional[SessionRecord]` (a small new frozen dataclass:
`id`, `remember_chat`) replaces the current `session_exists()` boolean
check at the top of the `/v1/order` handler - same query cost (one
lookup), but now also returns the value `_run_order_body` needs,
instead of a bare boolean plus a second lookup. `session_exists()`
itself stays as-is (still used by every other endpoint that only needs
the boolean).

**Writing it**: `PATCH /v1/sessions/{id}` is extended, not duplicated.
`RenameSessionRequest` becomes:
```python
class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    remember_chat: Optional[bool] = None
```
The handler calls `store.rename_session(...)` when `title` is given and
a new `store.set_remember_chat(session_id, value, *, user_id=None) ->
bool` when `remember_chat` is given (independently - either, both, or
neither... though the endpoint 422s if neither is given, since a PATCH
with no fields is a client bug worth surfacing). Two focused store
methods rather than one generalized dynamic-SET-clause method, so every
existing `store.rename_session(...)` call site (tests included) keeps
working unmodified - smallest correct diff.

**`/v1/order` never accepts it from the client** - `OrderRequest` gains
no new field. `_run_order_body` receives a `remember_chat: bool`
parameter resolved once, server-side, from `store.get_session(...)`
before the background task starts, and read exactly once per request -
this is also what satisfies "toggle flipped mid-stream keeps its
original setting" for free: there is no second read.

**Frontend**: a new `RememberChatToggle.tsx` in
`ResponseSection/`, rendered at the top of `ResponseSection/index.tsx`
(only when a session is active - a not-yet-created session has no
`remember_chat` value to show). Reads the current session's
`remember_chat` from the existing `sessions` array in `chatStore`
(`GET /v1/sessions` already returns one row per session -
`SessionSummary` gains a `remember_chat: bool` field, no new endpoint
needed to *read* it). A new `chatStore.setRememberChat(sessionId,
value)` action: optimistically patches the local `sessions` array,
calls a new `api.setRememberChat()` (`PATCH /v1/sessions/{id}`), and
reverts the local value on a caught error - matching the "optimistic
plus rollback" requirement exactly.

**The cost hint** ("12 turns, ~4.2k tokens carried") reads
`history_turns`/`history_tokens_est` off the *last* assistant message's
`complete` event (Section 4 adds these fields to `CompleteEvent`/
`ChatMessage`) - shown only when `remember_chat` is true and at least
one prior assistant message exists in the session; nothing renders for
a brand-new session (no request sent yet) or when the toggle is off.

## 2. Conversation history assembly

New pure module `router/app/history.py` (matching the existing
`classifier.py`/`escalation.py` "pure function, caller injects
everything, no network/DB call inside" style):

```python
def assemble_history(
    turns: List[Turn],            # oldest-first, already paired user+assistant
    *,
    current_prompt_chars: int,
    max_messages: int,
    max_chars: int,
) -> HistoryResult:                # .messages (oldest-first dicts), .turns_included, .chars_included, .tokens_est
```

**Turn pairing** happens in `main.py` before calling `assemble_history`:
group `store.get_messages(session_id)` by `request_id`; a `Turn` is only
built from a `request_id` that has exactly one `user` row and exactly
one `assistant` row (the error/cancelled case above already guarantees
an incomplete request_id never appears at all - no extra filtering
needed for that case specifically). Rows are already oldest-first
(`get_messages`'s existing `ORDER BY created_at ASC`).

**draft_quality exclusion rule** (asked to "plan the rule and state
it"): the request says "exclude a draft_quality decline unless it was
the only response in that turn." Under the current architecture, every
`request_id` produces **at most one** assistant message row - a re-brew
(`chatStore.rebrew`) always calls `sendPrompt` fresh, which mints a new
`request_id`, not a second response under the old one. So "the only
response in that turn" is **always true** today, and this rule, as
literally stated, never actually excludes anything. I implement the
general check anyway (`is this the only assistant row for this
request_id` - trivially true today, checked for forward-compatibility
if a future feature ever persists more than one assistant response
under one request_id) rather than silently dropping the requirement -
but flagging this now so it's an informed decision, not a surprise: **no
draft_quality message is excluded from history today.** Confirm this
reading in the open questions below.

**Windowing**: `history_max_messages` (default 20) counts individual
role-tagged messages (10 turns), matching how OpenRouter/OpenAI-shaped
APIs count `messages` - not "20 turns." `history_max_chars` (default
**24000** per the request's explicit number - see Open Question 1, the
citation to `memory_proposal_max_transcript_chars` doesn't quite match:
that setting is actually `20000` in `settings.yaml` today, not 24000).

Algorithm: reserve `current_prompt_chars` first
(`remaining_chars = max(0, max_chars - current_prompt_chars)`), then
walk turns **newest to oldest**, greedily including each whole turn
while `messages_included + 2 <= max_messages` and `chars_included +
turn_chars <= remaining_chars`, stop at the first turn that doesn't
fit, then reverse back to oldest-first for the output. A turn's
`turn_chars` includes any reattached attachment text (Section 3) - a
40k-char PDF turn is sized correctly, not underestimated.

This design means **"always keep the current prompt even if it alone
exceeds the char cap" needs no special-case branch** - the current
prompt was never a candidate for trimming in the first place (only
historical turns are ever dropped), so if `current_prompt_chars >=
max_chars`, `remaining_chars` computes to `0` and zero history turns
are naturally included. A `logging.warning(...)` fires specifically
when `remaining_chars == 0` **because** the prompt alone consumed the
whole budget (distinguished from "zero history because this is turn
one," which logs nothing - that's not a warning-worthy condition).

**Bean alias never leaks into history** - each historical assistant
turn's OpenRouter message is `{"role": "assistant", "content":
turn.assistant_content}` only; `bean_alias`/`task_type`/`complexity`/
etc. are never serialized into the outbound payload, regardless of
which Bean handled that historical turn.

**Wiring into the order flow**: `stream_order()` gains an additive
`history_messages: Optional[List[Dict[str, str]]] = None` parameter,
prepended to the payload's `messages` list before the final (current)
message - additive and backward compatible, every existing call site
that doesn't pass it behaves byte-for-byte as today (the ON/OFF
byte-for-byte-equivalence test in the Tests section below is what
actually proves this, not just an assertion in prose).
`_consume_stream`/`_run_order_body` thread `history_messages` through
the same way `image_data_urls` already is.

**Logging**: one `logging.info(...)` per request with `remember_chat`,
`history_turns_included`, `history_tokens_est` (`len(chars) // 4`,
matching this codebase's existing rough-token-estimate convention used
everywhere else, e.g. `_estimate_attachment_tokens`) - satisfies "log
the number of history turns and tokens included, per request."

## 3. Attachment persistence across turns

**Storage**: a new `messages.attachments_json TEXT NULL` column
(`SESSIONS_NEW_COLUMNS`-style migration, but on `messages` - a second,
parallel `MESSAGES_NEW_COLUMNS` dict applied the same way). JSON, not a
new table: attachments are a small, bounded, read-mostly list per
message, and this repo already uses this "small structured blob in a
TEXT column" shape nowhere yet, but a full second table with a FK for
what's fundamentally still "one message's attachment list" is more
machinery than the data shape needs. Written once, alongside the
existing `add_message()` call for the **user** message only (uploads
are always on the user's turn) - `add_message()` gains an optional
`attachments_json: Optional[str] = None` parameter.

**What's actually stored, per attachment**:
- PDF/text: `{"filename", "kind", "content_type", "extracted_text":
  <truncated to attachment_max_stored_chars with a clear "...[truncated
  at N chars]" marker, same style as the existing
  `truncate_inline_text()`>}`.
- Image: `{"filename", "kind", "content_type"}` only - **no base64 data
  is ever persisted**, per the request's own stated preference (Section
  3, "include the image only on its original turn... require a
  re-upload"). Storing base64 image bytes that are, by design, never
  going to be re-sent would be pure SQLite bloat with no purpose -
  worth stating plainly since it's a real, deliberate omission, not an
  oversight.

**Re-attachment when rebuilding history**: a historical user turn's
`content` sent to OpenRouter becomes `turn.content` plus, for each
stored PDF/text attachment, the exact same inline delimiter format
`_build_outbound_content()` already uses today for the *current*
request (`--- Attached file: {filename} ---\n{text}\n--- end of
{filename} ---`) - so the model sees a historical attachment turn in
exactly the shape it would have seen it live. For a historical turn
that had an **image**, no image bytes are re-sent, but the reconstructed
turn's text gets one short appended line: `"[An image was attached to
this message but is not included in this conversation history - ask
the user to re-upload it if you need to see it again.]"` - this is new
text I'm proposing (the request didn't literally ask for it), needed so
the model doesn't get confused mid-conversation if the user references
"the image I sent earlier." Confirm in Open Question 3 below, or tell
me to drop it and let the model simply not know an image ever existed.

**Char budget accounting**: `turn_chars` (Section 2's windowing input)
is computed from the *reattached* content (prompt + delimited
attachment text), not the bare `messages.content` column - so a 40k-char
PDF turn is correctly sized/possibly trimmed, not silently
underestimated.

**Frontend hint when OFF**: `GET /v1/sessions/{id}/messages` gains a
`has_attachments: bool` per message (derived from `attachments_json IS
NOT NULL`, not the full attachment content - the endpoint doesn't need
to ship extracted text back to the browser just to answer "did this
turn have a file"). `ResponseSection` shows, next to the toggle, one
line: `"Turn on Remember chat to ask follow-ups about your
attachments."` exactly when `remember_chat` is false **and** any
message in the currently-loaded session history has `has_attachments:
true`. Hint only - never auto-enables the toggle, per the explicit
instruction.

## 4. Ledger and events

**`CompleteEvent`** (contract v1.5, additive): `history_turns:
Optional[int] = None`, `history_tokens_est: Optional[int] = None` -
both `None` when `remember_chat` was false (not `0`, so a UI can tell
"toggle is off" apart from "toggle is on but this is turn one," which
is a real `0`). `ChatMessage`/`events.ts` mirror the same two fields;
`chat.ts`'s `case "complete"` reducer also promotes them onto dedicated
`historyTurnsIncluded`/`historyTokensEst` fields on `ChatMessage`,
matching the existing pattern (`costUsd`, `latencyMs`, etc. are already
pulled out of `latestEvent` onto dedicated fields, not read from
`latestEvent` at render time).

**Ledger CSV**: `LedgerRow` gains `remember_chat: bool`,
`history_turns: int`, `history_tokens_est: Optional[int]`. `CSV_HEADER`
appends the three columns at the end. **No new migration code is
needed** - `RouterLedger._migrate_if_needed()` (the Brew 38 pattern the
request asks to match) already diffs the file's actual header against
the current `CSV_HEADER` on first write and backs up + rewrites
automatically the moment they differ; adding columns to `CSV_HEADER`
and `LedgerRow` is the entire change, the migration machinery itself
doesn't need touching. Old rows get `""` for the three new columns
(read back as `"unknown"`/blank by the existing convention), never a
fabricated `False`/`0`.

## Classifier: history length as a complexity signal

Realizes the module docstring's existing (currently false) claim that a
`COMPLEXITY_SIGNALS` table exists. `_classify_complexity()`'s current
sequential `if`s (text length, code-fence line count, attachment
presence, multi-step keywords) become:

```python
@dataclass(frozen=True)
class ComplexityContext:
    text: str
    has_code_fence: bool
    code_fence_lines: int
    attachments: Sequence[Attachment]
    history_turn_count: int  # 0 when remember_chat is off or this is turn one

@dataclass(frozen=True)
class ComplexitySignal:
    name: str
    check: Callable[[ComplexityContext], bool]

COMPLEXITY_SIGNALS: List[ComplexitySignal] = [
    ComplexitySignal("long_text", lambda c: len(c.text) > 1500),
    ComplexitySignal("large_code_fence", lambda c: c.code_fence_lines > 80),
    ComplexitySignal("has_attachments", lambda c: len(c.attachments) > 0),
    ComplexitySignal("multi_step_keywords", lambda c: any(k in c.text.lower() for k in MULTI_STEP_KEYWORDS)),
    ComplexitySignal("long_history", lambda c: c.history_turn_count >= settings.classifier_long_history_turns),
]
```

(first match wins, same short-circuit order/semantics as today's `if`
chain - not a behavior change for any existing signal, purely a
restructure, plus the one new signal). `classify()` gains an additive
`history_turn_count: int = 0` parameter; `main.py` passes the real
count only when `remember_chat` is true (0 otherwise, so history never
influences complexity when the feature is off).

New setting `classifier_long_history_turns` (proposed default `10` -
half of `history_max_messages`'s 10-turn equivalent) - Open Question 4.

## Files touched

- `router/app/sessions.py` - `remember_chat`/`attachments_json`
  migrations, `get_session()`, `set_remember_chat()`, `add_message()`
  attachment param, `get_messages()` returns `has_attachments`.
- `router/app/history.py` - new module (`assemble_history`, `Turn`,
  `HistoryResult`).
- `router/app/classifier.py` - `ComplexityContext`/`ComplexitySignal`/
  `COMPLEXITY_SIGNALS`, `classify()`'s new parameter.
- `router/app/openrouter_client.py` - `stream_order()`'s
  `history_messages` parameter.
- `router/app/events.py` - `CompleteEvent` v1.5 fields.
- `router/app/ledger.py` - `LedgerRow`/`CSV_HEADER` additions.
- `router/app/config.py` - `history_max_messages`, `history_max_chars`,
  `attachment_max_stored_chars`, `classifier_long_history_turns`
  settings.
- `router/config/settings.yaml` - the same four, documented.
- `router/app/main.py` - `_run_order_body` reads `remember_chat`,
  assembles history, passes it through; `UpdateSessionRequest`/PATCH
  handler; `_build_outbound_content` reattaches stored attachment text
  for historical turns (shared helper, not duplicated logic).
- `web/src/lib/events.ts` - `CompleteEvent` fields, `SessionSummary.
  remember_chat`, `StoredMessage.has_attachments`.
- `web/src/lib/chat.ts` - `ChatMessage.historyTurnsIncluded`/
  `historyTokensEst`.
- `web/src/lib/api.ts` - `setRememberChat()`.
- `web/src/store/chatStore.ts` - `setRememberChat()` action
  (optimistic + rollback).
- `web/src/components/ResponseSection/RememberChatToggle.tsx` - new.
- `web/src/components/ResponseSection/index.tsx` - mounts the toggle.
- `ledger/router_requests.csv` - migrated on first post-Brew write
  (backup created automatically, same as Brew 38).

## Edge cases - resolution for each (asked to handle explicitly)

- **First message in a session**: `get_messages()` returns `[]`,
  `assemble_history([], ...)` returns zero turns - no special-case code
  needed, the empty-list path already falls out of the general
  algorithm.
- **A session whose only prior turn errored**: never persisted at all
  (see "Problem" section above) - nothing to filter.
- **History from a different Bean than the current route**: fine by
  design - only `role`/`content` are ever serialized into a historical
  message, `bean_alias` never leaves `sessions.db`.
- **Concurrent requests in the same session**: each request reads
  `get_messages()` as a snapshot at the moment its own `run_order` call
  starts; no locking is added (matches this router's consistent
  "single-process/local-dev, no new background infrastructure"
  discipline, and the Send button is already disabled client-side while
  a request is in flight - this is defense-in-depth for a path that
  shouldn't happen via the UI, not a common real scenario).
- **Unknown `session_id` / belongs to another user**: already 404s
  today via the existing `session_exists`/now `get_session` check in
  the `/v1/order` handler, before `run_order` is ever called - no change
  needed, confirmed already correct.
- **Toggle flipped mid-stream**: `remember_chat` is read exactly once,
  before the background task starts - an in-flight request's behavior
  is fixed at that point regardless of later PATCH calls.
- **Session created before this migration**: `DEFAULT 1` on the
  `ALTER TABLE ADD COLUMN` gives every existing row `TRUE` immediately,
  no backfill script needed.

## Tests (per the request's list)

- History ON sends history; OFF sends **byte-for-byte** what
  `stream_order()` receives today (a real diff/equality assertion
  against a captured pre-Brew payload shape, not just "no error").
- `PATCH .../{id}` persists `remember_chat`; migration default-TRUE for
  pre-existing rows.
- History assembly ordering (oldest-first, current prompt last).
- Both windowing limits (`history_max_messages`, `history_max_chars`),
  independently and together.
- Whole-turn trimming (never splits a user/assistant pair).
- Attachment text persistence and re-attachment into a historical turn.
- Image-on-original-turn-only rule (no image bytes in any historical
  turn, ever).
- Oversized single current prompt (zero history, warning logged).
- Ledger columns for both toggle states.
- Frontend: toggle optimistic update + rollback on a failed PATCH.

**Live demo** (per the request): upload a PDF with the toggle ON, ask
about it, ask a follow-up with no re-upload confirming the model
answers from persisted text; flip OFF, ask another follow-up,
confirm the model has no memory; Ledger row shows `remember_chat=false`
and `history_tokens_est` empty/zero for that row.

## Open questions

1. **`history_max_chars` default - 24000 or 20000?** The request states
   24000 "matching the memory-proposal transcript cap already in
   settings.yaml," but that setting (`memory_proposal_max_transcript_chars`)
   is actually `20000` today, confirmed by reading `settings.yaml`, not
   24000. Recommend keeping the explicitly-stated **24000** (a
   deliberately close but distinct budget for a different feature) -
   confirm, or say if you'd rather it actually equal 20000 to match.
2. **draft_quality exclusion rule**: confirmed to be a no-op under the
   current one-assistant-row-per-`request_id` architecture (see Section
   2) - I implement the general check anyway for forward-compatibility,
   but no message is excluded by it today. Confirm this reading, or
   clarify if a different scenario was intended.
3. **Historical image-turn annotation**: recommend appending a short
   instructional line to a reattached historical turn that had an image
   ("...ask the user to re-upload it if you need to see it again"),
   proposed exact wording above - confirm, or say to leave historical
   image turns with no annotation at all (the model simply won't know
   an image was ever there).
4. **`classifier_long_history_turns` threshold**: recommend a new
   `settings.yaml` value, default `10` (half of `history_max_messages`'s
   10-turn equivalent) - confirm the value, or a different one.

Once approved, implementation proceeds directly, followed by the tests
above, the live demo, and Brew Log + Tasting Note.
