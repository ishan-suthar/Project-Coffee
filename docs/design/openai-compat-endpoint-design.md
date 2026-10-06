# OpenAI-compatible endpoint + real-usage measurement (Brew 47) - Decaf plan

Status: **All four sections implemented, tested, and demoed live. The
escalation-concatenation issue found during the Section 2+4 demo is now
resolved (see below) - resolution implemented, tested, and demoed live
in a further follow-up session.**
Sections 1 (endpoint) and 3 (Ledger) shipped first; Sections 2 (retry
detection, shadow mode) and 4 (analysis tool) completed in a follow-up
session per the original deferral. 764 tests pass via
`tools/run_all_tests.py` (same two pre-existing vision-Bean fixture
failures, unrelated to this Brew). **Not staged or committed as of this
writing.**

One correctness fix found during Section 1+3 implementation: `check_for_
failure()` (written before tool calling existed) treats any empty `text`
as the `"empty"` failure reason - but a `tool_calls`-only response (no
prose) is a well-formed success, not a failure. `_run_chat_completion`
skips the failure check entirely when `tool_calls` were produced, so a
tool-calling turn never accidentally auto-escalates or gets double-run.

**Escalation-concatenation issue, found live during the Section 2+4
demo - resolved.** Original bug: when an auto-escalation happened,
`_run_against()`'s per-chunk `yield` (Section 1 below) relayed *every*
chunk to the client regardless of which of its two calls produced it -
the cheap draft's content and the premium re-run's content both reached
the client, back to back, with nothing in between signaling a reset.
Live evidence: a request that auto-escalated returned `"Hello there
youHello there, friend!"` to the client - the truncated cheap draft
glued directly onto the premium run's own text. This was originally
framed in this doc (see "Escalation, since the approval card cannot
render here" below) as an accepted quirk "mirroring `/v1/order`'s
existing behavior" - that framing undersold it: an endpoint claiming
OpenAI compatibility cannot silently violate the guarantee that streamed
content deltas concatenate into one coherent message.

The spec-correct fix (buffer the draft internally, run the failure check
before emitting anything) would have traded away time-to-first-token on
*every* request that might escalate, to correctly serve the roughly one
in eight that actually do - a bad trade for an endpoint whose whole
point is being a transparent drop-in for coding tools like Cursor.
Resolution: escalation became **mode-dependent** instead.

- `stream=false` (`/v1/chat/completions`, `stream: false`): buffering the
  draft is free here - the response is already assembled into one JSON
  body at the edge regardless. `_run_chat_completion` now holds the
  draft's per-chunk deltas back rather than relaying them live; if
  `decide_escalation()` returns `auto_escalate`, the draft is discarded
  entirely (never reached the client) and the premium response is
  emitted as a single buffered chunk once it's the known, final answer.
  Escalation still works exactly as originally designed.
- `stream=true`: never escalates. The draft streams live exactly as
  before - the fix is *not* touching this path's latency at all. The
  failure check and `decide_escalation()` still run (for measurement),
  but on `auto_escalate` the premium re-run is skipped rather than
  executed and glued on. A new Ledger column, `would_have_escalated`,
  captures the outcome that couldn't be acted on, so the signal survives
  even though the action doesn't - `ledger_summary.py`'s existing
  escalation-rate reporting keeps working, now split implicitly by
  whether a row could act on its own escalation decision or not.
- Surfaced to the client via the **same mechanism `over_cap_declined`
  already used** - `system_fingerprint: "draft_quality"` - no second
  signaling channel invented. A streamed client that hit
  `would_have_escalated` and a client that hit a real over-cap decline
  are indistinguishable from the wire's perspective: both mean "you got
  the draft, not the ideal answer," which is the honest thing to tell
  them either way.

**The accepted trade-off**: a streamed client (Cursor, in practice) can
now receive a possibly-inadequate cheap answer instead of a guaranteed-
corrupted one. This is judged acceptable because Cursor's own regenerate
action covers the gap - and Brew 47's own retry detection (Section 2)
already measures how often that gap gets used, turning "how often did
would_have_escalated correlate with a user-initiated retry" into an
answerable question with the tools this Brew already shipped.

`EVENT_CONTRACT.md` was not touched by this fix - it documents
`/v1/order`'s named SSE event stream (`escalation_pending`/
`escalating`/`complete`), which is unaffected; `/v1/chat/completions`
was already outside that contract per Section 1's original design.

## Resolved open questions

1. **`prompt_shape` format**: separate CSV columns
   (`has_code_fence`, `message_count`, `total_input_chars`), not a packed
   string - slicing is the whole point, and a packed string just pushes a
   parser onto every consumer. Section 3 below updated accordingly.
2. **Shadow mode scope**: `/v1/chat/completions` only, never `/v1/order` -
   the chat UI already has rating buttons, a strictly better signal than a
   silent shadow pair, and doubling cost where human judgment already
   exists is waste. Shadow mode exists specifically for the blind spot
   Cursor has no rating button. (Implemented in Section 2, deferred.)
3. **`api_requests` retention**: no automatic deletion. A `--older-than 90d`
   prune CLI command will be added instead (Section 2, deferred) - run
   deliberately, documented in the README, never on a forgettable schedule.
4. **`over_cap_declined` scope**: populated for **both** endpoints. A human
   looking at a `/v1/order` approval card and declining ("keep the cheap
   cup") is the strongest quality signal in the whole system - someone read
   the draft and judged it good enough. Implemented in this session's
   Ledger work (Section 3), computed from the existing `decision`/`escalated`
   state already present in `_run_order_body`.

Three further decisions, resolved during Section 2+4 planning (bringing
the total to seven across this Brew):

5. **`retry_count` is live, not a write-time snapshot.** Section 2 below
   originally said a Ledger row's `retry_count` would never retroactively
   update once written, and `ledger_summary.py` should count `retry_of`
   pointers instead. Superseded by explicit instruction: "Populate
   `retry_of` on the retry and increment `retry_count` on the original."
   `RouterLedger.increment_retry_count()` reuses `update_rating()`'s
   rewrite-the-whole-file pattern for real. `ledger_summary.py` still
   primarily counts `retry_of` pointers (the more robust signal), but the
   `retry_count` cell itself is now genuinely live.
6. **"Never recursive" is structural, not flag-gated.** The original
   sketch threaded an `is_shadow` boolean through `_run_chat_completion`
   to gate against a shadow run scheduling another shadow run. Dropped in
   favor of a stronger guarantee: `_run_shadow()` calls
   `_stream_raw_openai_chunks()` directly, never `_run_chat_completion()`
   again, so there is no code path back into anything that could schedule
   a shadow - recursion isn't gated, it's impossible by construction.
7. **Shadow rows get a real dollar `cost_usd`; primary paid-Bean rows do
   not (flagged as a known inconsistency).** Every cost_usd this router
   has ever written for a paid Bean, anywhere, was `"unknown"` -
   `_is_free_tier()` is the only cost logic that existed before this
   Brew. Without a real number on shadow rows, `shadow_mode_daily_cost_
   cap_usd` could never trip (summing "unknown" cells always totals $0),
   so `_real_cost_usd()` (tokens × the premium Bean's real `beans.yaml`
   pricing) was added, scoped *only* to shadow Ledger rows. This is a
   defensible narrow scope, not a full fix - `tools/ledger_summary.py`'s
   counterfactual-cost math will eventually want real costs on primary
   paid-Bean rows too, and as of this Brew it still cannot have them.
   Recorded in `roastery/tasting_notes.md`'s Section 2+4 entry as a known
   gap for a future Brew, not silently left inconsistent.

One further decision, resolved while fixing the escalation-concatenation
issue found during the Section 2+4 demo (bringing the total to eight):

8. **Escalation became mode-dependent instead of buffered-always.** The
   only fix that preserves streamed correctness *and* streamed
   time-to-first-token is to never escalate on `stream=true` at all -
   buffering the draft to make escalation always safe was rejected
   because it would cost every potentially-escalating streamed request
   its live token-by-token feel to correctly serve the ~1-in-8 that
   actually escalate. `would_have_escalated` (new Ledger column) keeps
   the measurement signal alive on the path that can't act on it. See
   the Status section above for the full writeup.

## Goal (stated plainly, per the request)

Answer one question with real data: **what fraction of my coding tasks
actually needed a premium model?** Cursor/Continue.dev compatibility is the
delivery mechanism that gets real coding-task traffic through the router at
all - it is not the deliverable. Every design choice below that trades
convenience against measurement quality favors measurement, and is called
out explicitly where that trade was made.

---

## 1. The endpoint: `POST /v1/chat/completions`

### Request/response shape

New `ChatCompletionRequest` Pydantic model accepting the OpenAI shape
loosely (extra fields ignored, not rejected - real clients send fields this
router doesn't need, e.g. `top_p`, `presence_penalty`):

```python
class ChatCompletionMessage(BaseModel):
    role: str
    content: Any  # str, or OpenAI's multimodal content-part array - passed through as-is
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None          # edge case: absent/empty is valid, just means "no override"
    messages: List[ChatCompletionMessage]
    stream: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    class Config:
        extra = "ignore"
```

`temperature`/`max_tokens` are passed through to OpenRouter unchanged (not
currently plumbed anywhere in this router - new, additive params on
`stream_order()`).

### No session rows; a new durable request record instead

**Decision: do not create a `sessions` row for these requests** (matches
your stated inclination). Reasoning: there is no client-supplied session
id in the OpenAI shape - the client resends its whole `messages` array every
turn. Inventing one Coffee session per external call would either flood the
chat UI's session list with one-shot sessions (Cursor can fire many calls
per minute in agent mode), or require guessing at turn-continuity from
message-array prefixes, which is exactly the kind of unreliable heuristic
this Brew is trying to avoid building. The existing `remember_chat`
machinery (Brew 46) is also irrelevant here by construction: the client
already carries its own history in `messages`, so per Section 1 of that
Brew, this endpoint is stateless with respect to Coffee's session store -
`use the client's history as-is, do not assemble history from SQLite`.

**A durable request record is still needed** (for retry detection across
router restarts, and to store shadow-mode response pairs for later human
reading). New SQLite table in the existing `router/data/sessions.db`
(reuses the established DB/migration machinery in `sessions.py` rather than
inventing a second database file):

```sql
CREATE TABLE IF NOT EXISTS api_requests (
    request_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    client_fingerprint TEXT NOT NULL,
    last_user_message_hash TEXT NOT NULL,
    response_text TEXT,              -- filled once the primary response completes
    is_shadow INTEGER NOT NULL DEFAULT 0,
    shadow_of TEXT,                  -- request_id of the primary run, when is_shadow
    shadow_response_text TEXT,       -- filled on the primary row once its shadow run completes
    shadow_bean_alias TEXT,
    retry_of TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0
)
```

A brand-new table needs no `ALTER TABLE` migration - just added to `SCHEMA`
in `sessions.py` and picked up by `CREATE TABLE IF NOT EXISTS` on next
startup, same as every other table in that file.

`response_text` is capped at `attachment_max_stored_chars`-style truncation
(reuse the existing `truncate_inline_text` helper with a new
`shadow_response_max_stored_chars` setting, default 20000) so a runaway
generation can't bloat `sessions.db` unboundedly.

### Routing

`classify()` and `RoutingPolicy` are reused exactly as `/v1/order` uses
them today - no new routing logic. The `model` field is:

- **Exact match against a Bean alias** (`state.bean_registry.by_alias(...)`
  succeeds): treated as a manual override, same code path as
  `bean_alias_override` on `/v1/order` (`routing_policy.manual_route(...)`).
- **Anything else** (a raw OpenRouter/OpenAI model string, empty, or
  absent): ignored for routing. `classify()` + `routing_policy.select_route()`
  pick the Bean as usual.

Both the requested string and the Bean actually used are logged (new Ledger
column `requested_model`, see Section 3).

**What text does `classify()` see?** The last message's own text/content
(after multimodal-content extraction), not the full concatenated history -
identical in kind to how `/v1/order` already only classifies the current
`prompt`, never prior turns' text. This directly resolves your "40k-char
Cursor agent context" edge case: `COMPLEXITY_SIGNALS`' `long_text` signal
(`len(text) > 1500`) only ever sees the current message, so a huge *prior*
context does not by itself push a request to `cold_brew`. What a large
history *does* legitimately contribute is turn **count**, via the existing
`long_history` signal (Brew 46) - so `history_turn_count` for this endpoint
is computed as the number of complete user/assistant pairs in
`messages[:-1]` (the client-supplied prior turns), fed into `classify()`
exactly like the `remember_chat`-assembled turn count is today, reusing
`classifier_long_history_turns` (no new setting). This keeps "long context by
turn count matters, long context by raw char volume alone does not" as one
deliberate, already-precedented rule instead of a special case invented for
this endpoint.

### Streaming and translation - a new orchestration function, not a reuse of `run_order()`

**This is the plan's one real structural trade-off, stated plainly up
front:** I chose to give `/v1/chat/completions` its own orchestration
function (`_run_chat_completion`) rather than routing it through
`run_order()`/`_run_order_body()`. I reuse the free functions underneath
(`classify()`, `RoutingPolicy`, `check_for_failure()`, `decide_escalation()`,
`stream_order_fn`, `RouterLedger`/`LedgerRow`) but not the orchestration
function itself. Reasons:

1. `_run_order_body()` is heavily tested (~30 tests in
   `test_main.py::RunOrderTestCase`) and load-bearing for the primary chat
   UI. Refactoring it to grow a second personality risks regressing that
   surface for a feature (`/v1/chat/completions`) whose correctness
   requirements are different in a specific, important way (next point).
2. `_consume_stream()`'s batching (`generating` ticks every N tokens/
   seconds, to reduce the chat UI's render frequency) is actively wrong for
   this endpoint: it collapses raw provider chunks into `text_delta`
   batches and **silently drops tool-call deltas** (a chunk whose only
   content is `delta.tool_calls` has `content_delta == ""`, so
   `_consume_stream` treats it as nothing happened). An OpenAI-compatible
   endpoint needs true passthrough - one outbound chunk per inbound
   provider chunk, tool-call deltas included - which is a different
   contract than the Coffee Counter UI's SSE events, not a superset of it.
3. Session-store writes, Pantry retrieval, the escalation-approval-card
   pause, and the tick/heartbeat machinery are all UI-specific and
   genuinely do not apply here (Section 1 already established no session
   rows; escalation approval is handled differently below; Pantry's
   `use_pantry` toggle has no equivalent in the OpenAI request shape).

The cost of this choice is real duplication of the "classify, route,
stream, check failure, decide escalation, write one Ledger row" sequence
(~60-80 lines). I judged that acceptable given (1) and (2) above; if this
turns out to rot the two paths apart over time, unifying them is a
reasonable ask for a later Brew once both have real usage behind them.

**Streaming mechanics**: a new small helper,
`_stream_raw_openai_chunks(stream_order_fn, model_id, messages, *, tools, tool_choice, temperature, max_tokens)`,
calls `stream_order_fn` directly (bypassing `_consume_stream`) and yields
each raw `StreamChunk` (extended - see Section 1's Tools note below)
immediately. `_run_chat_completion` uses this both for the primary run and
for an escalation re-run against the premium Bean (same helper,
different `model_id` - no separate "`_run_chat_escalation`" needed).

**`stream=false` support**: internally, *every* call still streams from
OpenRouter (SSE) and accumulates - there is no second, non-streaming
network code path. The only difference is at the very edge: when
`body.stream` is `false`, the endpoint awaits the whole
`_run_chat_completion` generator to completion, buffering the translated
chunks into one final JSON body instead of flushing each one as SSE. This
guarantees `stream=true` and `stream=false` produce byte-identical
accumulated content/tool_calls/usage for the same request, which is also
exactly what the "both stream modes" test requirement needs.

**Response `model` field**: always the Bean alias actually used (e.g.
`"Reserve Blend"`), never the raw OpenRouter model id - consistent with the
existing invariant (`router/app/aliases.py`) that a raw model id never
leaves this router in any API-visible field. Noted trade-off, as asked: a
strict OpenAI client expects `model` to echo back a real, recognizable
model string; an alias like `"Reserve Blend"` is a valid string but not one
OpenAI/OpenRouter would ever issue, and some tools may display or log it
verbatim without validating it against a known list. Cursor and the OpenAI
Python SDK do not validate this field, so this should not break function -
only cosmetics in any UI that surfaces it.

### Escalation, since the approval card cannot render here

`decide_escalation()`'s three outcomes map onto this endpoint as follows,
with **no waiting** in any case (nothing here can pause for a human, so the
`escalation_pending` + `wait_for_approval` machinery `/v1/order` uses is
simply never invoked):

- `auto_escalate` (failure detected, under the cost cap): **mode-dependent
  as of the escalation-concatenation fix** (see the Status section above).
  `stream=false` re-runs against the premium Bean and returns only that
  response, discarding the draft - matches `/v1/order`'s unconditional
  auto-escalate behavior. `stream=true` never re-runs; the draft is
  returned as final and `would_have_escalated = True` is logged instead,
  since gluing a second live stream onto an already-flushed one is
  exactly the bug this fix closes.
- `escalation_pending` (failure detected, *over* the cost cap, premium
  available): **cannot pause**, so this endpoint treats it as an immediate
  decline - `draft_quality = True`, the already-generated draft is what
  gets returned, `over_cap_declined = True` is logged. This is the
  "surface draft_quality" case.
- `no_premium_available`: same as today, `draft_quality = True`.

**Where `draft_quality` surfaces to the client** - the three options and
the tradeoff, as asked to state explicitly:

- *A trailing note in the text*: rejected. Cursor's agent mode inserts
  streamed content directly into files/diffs; a note like "(this may be a
  draft-quality response)" would land in the user's source code. Not
  acceptable for a coding tool.
- *A response header*: rejected for a structural reason, not just
  preference - `draft_quality` is only known **after** the full generation
  and failure-check complete, but HTTP headers must be sent before the SSE
  body starts. Setting it as a header would mean buffering the entire
  response before sending the first byte, defeating real-time token
  streaming (Cursor would see nothing while the model generates).
- **Chosen: `system_fingerprint`** on the final chunk (a standard, optional
  OpenAI field most SDKs already pass through and ignore harmlessly) - set
  to `"draft_quality"` when true, omitted/`null` otherwise. It can only be
  known at the point the final chunk is emitted, which is exactly when this
  field becomes available in a real stream, so no buffering is needed. The
  honest cost: this is low-visibility - Cursor's UI will not surface it, so
  in practice you'd only see it by inspecting raw SSE frames or querying
  the Ledger's `over_cap_declined`/`draft_quality`-equivalent column. The
  Ledger is the reliable way to audit this after the fact, not the live
  response.

Every `escalation_pending`-turned-immediate-decline is logged - this is
exactly "the cases where I paid for a cheap answer that was probably
wrong."

### Tools passthrough

- `openrouter_client.stream_order()` gains `tools`/`tool_choice` params
  (included in the outbound payload only when not `None` - never send an
  empty array some providers reject) and a `messages_override` param (see
  next paragraph).
- `StreamChunk` gains `tool_calls_delta: Optional[List[Dict[str, Any]]] = None`,
  parsed from `delta.get("tool_calls")` in `_parse_sse_line` - previously
  silently dropped.
- Coffee does not interpret `tool_calls` at all - they are relayed
  unchanged in both directions (round-trip fidelity is a listed test).

**`messages_override`**: since the client already assembled a valid OpenAI
`messages` array (including any multimodal content-part arrays for
images), the cleanest, lowest-risk translation is to bypass `stream_order()`'s
own prompt/`image_data_urls`/`history_messages` assembly entirely for this
endpoint and hand it the client's `messages` list close to verbatim (each
`ChatCompletionMessage` converted to a plain dict). This directly
implements "use the client's history as-is."

**`beans.yaml` capability flag**: proposing a new `capabilities.tool_calling`
boolean, same shape as the existing `vision` flag, since (as you flagged)
Cursor's agent mode leans on tool calls and a Bean that mishandles them
will fail in ways `check_for_failure()`'s truncation/empty/refusal checks
cannot catch (a malformed or hallucinated tool call is well-formed,
non-empty, non-refusing text from those checks' point of view). Proposed
values, based on public model capability, since none of these Beans has
been verified against this router's own tool-calling path yet:

| Bean | tool_calling | Reasoning |
| --- | --- | --- |
| Reserve Blend (Claude Sonnet 4.6) | `true` | Anthropic models via OpenRouter have solid, well-documented tool-calling support. |
| Single Origin (Claude 3.5 Haiku) | `true` | Same family, same support. |
| House Blend / Second Pour / Guest Bean | `false` | Free-tier/experimental models with no verified tool-calling behavior in this router - default to `false` until real evidence says otherwise. |

**Scope limit, stated explicitly**: this Brew only adds the flag as data
and logs a warning when `tools` is present but the routed Bean's
`tool_calling` is `false` - it does **not** make routing avoid such Beans
automatically. That's a reasonable follow-up once the flag has real
evidence behind it (mirrors how the `vision` flag started).

### Auth

Identical `Authorization: Bearer <token>` scheme as every other endpoint,
via the same `Depends(get_current_user)`. `router/README.md` gets a new
section: get a token via `POST /v1/login` (curl example), paste it into
Cursor's "OpenAI API Key" field with Base URL `http://localhost:8765/v1`,
and the equivalent for Continue.dev's `config.yaml`.

---

## 2. Measurement (Signals A, B, C)

### Signal A: retry detection

**Matching rule, concretely**: a new request is flagged
`retry_of = <original.request_id>` when, within
`retry_detection_window_seconds` (default 300) of the original's
completion:

1. Same `user_id`.
2. Same `client_fingerprint` - computed as `sha256(user_id + "|" + user_agent)`
   when a `User-Agent` header is present and non-empty, else
   `sha256(user_id + "|" + "unknown")`. Falling back to a per-user (not
   per-request) fingerprint when `User-Agent` is absent widens the match
   window rather than narrowing it to zero - acceptable, since the
   time-window + exact-message-match conditions below still have to hold
   too, and a false "retry" flag is a soft, non-blocking signal, not a
   billing or routing decision.
3. The new request's **last user message**, normalized (`.strip()`), is
   byte-identical to the matched original's last user message.
4. **The original request must already have `response_text` stored** -
   i.e. it already finished. This is what tells a retry apart from
   parallelism: two requests fired concurrently with identical content
   will both still be in-flight (`response_text IS NULL`) when the second
   one arrives, so neither can match the other. A retry, by definition, is
   a human reacting to an answer they already saw - it structurally cannot
   exist before the first answer does. This resolves the "concurrent
   identical requests are parallelism, not retries" edge case without any
   extra bookkeeping.

On a match: the new row gets `retry_of = original.request_id` in both the
`api_requests` table and the Ledger; the original row's `retry_count` in
`api_requests` is incremented (the Ledger's own `retry_count` column
mirrors the value *at the time that Ledger row was written* - see Section
3's honesty note on this).

**What this signal is worth, stated in the plan as asked**: a proxy for
"the human was dissatisfied enough to try again," not a measurement of it.
A retry could also be a client-side network hiccup, a user testing
different prompts, or an accidental double-click. `ledger_summary.py`'s
report labels this rate explicitly as a weak proxy, never as "dissatisfaction
rate."

### Signal B: escalation / over-cap decline rates

Already available via the existing `escalated`/`escalation_approved`
columns plus this Brew's new `over_cap_declined` column - no new logic, just
needs `task_type` and the new `client_source` to reach the Ledger with
enough context to slice by both (already true for `task_type`; `client_source`
is new, Section 3).

### Signal C: shadow mode

Settings (all new, `settings.yaml`):

```yaml
shadow_mode_enabled: false
shadow_mode_sample_rate: 0.1
shadow_mode_daily_cost_cap_usd: 1.00
shadow_response_max_stored_chars: 20000
```

**Trigger conditions**, all of which must hold:
`shadow_mode_enabled` AND the primary request is `/v1/chat/completions`
(not `/v1/order` - shadow mode is scoped to the measurement endpoint only,
since that's the traffic this Brew is trying to characterize) AND the
primary run was **not itself a shadow run** AND the routed Bean is not
already the premium Bean (shadowing a premium request against itself is
pointless) AND `random.random() < shadow_mode_sample_rate` AND today's
summed `cost_usd` across `is_shadow=True` Ledger rows is under
`shadow_mode_daily_cost_cap_usd`.

**Never-recursive guarantee**: the shadow run's own call into
`_run_chat_completion`'s internals passes an explicit `is_shadow=True`
flag, and the trigger conditions above check for it and refuse - a shadow
run can never schedule another shadow run, by construction (one boolean
gate, not a heuristic).

**Never delays or affects the client response**: the shadow task is only
scheduled *after* the primary response has been fully sent to the client -
for `stream=true`, in a `finally` block after the last SSE chunk is
yielded; for `stream=false`, after the JSON response is built. It is never
`await`ed by the request-handling coroutine - `asyncio.create_task(...)`,
added to `state.background_tasks` (the same GC-safety pattern `run_order()`
already uses for its own background task), fire-and-forget.

**Cap enforcement**: checked (via a cheap sum-over-today's-CSV-rows query)
immediately before scheduling, not after - "over the cap, skip sampling and
log that it was skipped" is satisfied by simply never creating the task and
logging one line, never touching the request path.

**Failure isolation**: the shadow task's entire body is wrapped in
`try/except Exception`, logging a warning on failure and returning quietly
- "a shadow run failing while the primary succeeded must be silent, must be
logged," exactly as asked.

**Storage**: the shadow response text and its Bean alias are written to the
*primary* request's `api_requests` row (`shadow_response_text`,
`shadow_bean_alias`) - so a human reading a pair reads one row, not a join.
A **separate** Ledger row is also written for the shadow run itself
(`is_shadow=True`, `shadow_of=<primary request_id>`), because the shadow
run is a real, billable OpenRouter call and its real cost must be
auditable - "shadow mode doubles the cost of sampled requests" has to be
provable from the Ledger, which only works if the shadow call gets its own
row with its own real `cost_usd`.

**Never contaminates cost totals or routing evidence**: `is_shadow=True`
rows are excluded from `ledger_summary.py`'s "real" volume/cost totals
(counted only in the dedicated shadow section) and excluded from
`tools/generate_policy.py`'s evidence loading (Section 5's "what not to
do").

**No automated quality scoring in this Brew**, as instructed - storing the
pair is the deliverable.

---

## 3. Ledger

### New CSV columns (appended to `CSV_HEADER`, migrated via the existing
`RouterLedger._migrate_if_needed()` - same backup-then-rewrite pattern as
Brew 38/46, no changes needed to that mechanism itself):

| Column | Meaning | Old-row (pre-migration) value | What that value means |
| --- | --- | --- | --- |
| `client_source` | `"chat_ui"` for `/v1/order`; for `/v1/chat/completions`, the raw `User-Agent` header string (truncated to 120 chars) when present, else the literal `"openai_api"` | *(blank)* | Every row before this Brew came through `/v1/order` - `ledger_summary.py` normalizes a blank cell to `"chat_ui"` explicitly (documented, not inferred silently). |
| `requested_model` | The client's `model` field as received (raw string, may be a Bean alias, a raw model id, or empty) | *(blank)* | The concept didn't exist before this Brew - blank means "not applicable," not "unknown Bean." |
| `retry_of` | Matched original's `request_id`, or blank | *(blank)* | Retry detection didn't exist before this Brew - blank means "not tracked," not "confirmed not a retry." |
| `retry_count` | Snapshot of the original row's retry count *as of when this Ledger row was written* (see honesty note below) | `0` | Accurate - no retries were tracked, so 0 is correct, not a placeholder. |
| `over_cap_declined` | `True` iff this request hit the `escalation_pending` outcome and did **not** end up escalating (forced-decline on `/v1/chat/completions`, or a real human decline/timeout on `/v1/order`) | `False` | **Not reliable** - old rows may have had a real over-cap decline (visible today only indirectly via `escalation_approved=False`) that this column will not retroactively reflect. Flagged as a known blind spot in the analysis tool's footer, not silently treated as "no declines happened before this Brew." |
| `is_shadow` | `True` for a shadow-run's own Ledger row | `False` | Accurate - shadow mode did not exist before this Brew, so `False` is a correct default, not a placeholder. |
| `shadow_of` | Primary run's `request_id`, when `is_shadow` | *(blank)* | Accurate, for the same reason. |
| `prompt_shape` | Compact string: `f"code={has_code_fence}|msgs={message_count}|chars={total_input_chars}"` | *(blank)* | Not computed retroactively - `ledger_summary.py` treats a blank cell as an `"unknown"` shape bucket, never guesses one. |

**On `prompt_shape`'s format, since your request both said "coarse bucket"
and named three raw facts**: the CSV column stores the three *raw* facts
(`has_code_fence`, `message_count`, `total_input_chars`), computed
identically for both `/v1/order` and `/v1/chat/completions` via one shared
helper, so the two client sources are directly comparable. The *coarse
bucket* (e.g. `"short_qa"` vs. `"large_agent_context"`) is derived from
those raw facts at **analysis time** in `ledger_summary.py`, not baked into
the write path - this keeps the bucket boundaries tunable/reviewable
without another CSV migration, and is the more honest reading of "coarse
bucket for coding requests" (the raw numbers are the ground truth; the
bucket is a lens on them).

**Honesty note on `retry_count`**: because the Ledger is write-once/append-
only per request, a Ledger row's `retry_count` is a *snapshot at the moment
that row was written* - if a request gets retried three times after its own
Ledger row was already appended, that row's `retry_count` does not
retroactively update to 3 (unlike `api_requests.retry_count`, which is a
live SQLite column and *is* kept current). `ledger_summary.py`'s retry-rate
calculation is therefore computed by counting rows with a non-blank
`retry_of` pointing at another row (i.e. "how many requests were
themselves retries"), not by trusting any single row's `retry_count` cell -
stated in code comments and in the report footer.

### `generate_policy.py` change

`load_ledger_rows()` (or a thin wrapper around it) filters out
`is_shadow == "True"` rows and rows whose `client_source` is neither
`"chat_ui"` nor blank (i.e. keeps only real `/v1/order` traffic) before
computing `rating_evidence`/`escalation_rates` - the concrete implementation
of "do not feed `openai_api` requests into routing evidence in this Brew."
A matching test is added to `tests/test_generate_policy.py` (not explicitly
requested, but required for correctness - flagged here).

---

## 4. The analysis tool

**Extends `tools/ledger_summary.py`** (not a new script, as instructed) with
a new mode. One structural note worth flagging: `ledger_summary.py` today
parses the *hand-maintained Markdown* `ledger/cost_log.md`, not the
*machine-written CSV* `ledger/router_requests.csv` (that's `RouterLedger`,
written by `router/app/ledger.py` and already read by
`tools/generate_policy.py`). The question this Brew is answering (bean
distribution, escalation/retry/decline rates, counterfactual cost, sliced
by `task_type`/`client_source`) can only be answered from the CSV - it has
real per-request structured fields; the Markdown ledger is prose. So the
new mode is a genuinely separate code path inside the same file
(`--mode model-usage`, existing Markdown-summary behavior stays the
default `--mode cost-log` so nothing about current usage breaks), reading
`router_requests.csv` via `csv.DictReader` (same read pattern
`generate_policy.load_ledger_rows()` already uses).

**Report content** (plain text, sliced by `task_type` and `client_source`,
excluding `is_shadow` rows from all of the below except the dedicated
shadow section):

- Request volume and total cost, per slice.
- Bean distribution (fraction of requests per Bean, per slice) - this is
  the number that most directly answers your question.
- Escalation rate, over-cap decline rate, retry rate - the retry line is
  printed with the literal phrase "weak proxy for dissatisfaction, not a
  measurement of it," not just documented elsewhere.
- Counterfactual cost: `sum(tokens_in/out * Reserve Blend's per-1k prices)`
  for every non-shadow row in the slice, printed immediately adjacent to
  (never separated from) the escalation/decline/retry rates for that same
  slice - so the savings number is never read without its quality context
  in the same glance.
- Shadow section (only when `is_shadow` rows exist): pair count, and where
  to read them (`router/data/sessions.db`'s `api_requests` table, with the
  exact query to run - no automated diffing/scoring, per Section 2).
- A closing **"what this cannot tell you"** footer, always printed,
  listing: the fraction of requests with *no* quality signal at all (no
  retry, no escalation, no shadow pair); that `over_cap_declined` is
  unreliable for pre-Brew-47 rows (Section 3); that retry rate is a proxy,
  not ground truth; that shadow mode (if disabled) means zero premium-
  quality comparison exists for any request in the period.

Tests added to `tests/test_ledger_summary.py` (the existing file, per
instruction), following its existing `TemporaryDirectory` + `build_summary`/
`run_tool` patterns.

---

## 5. What this Brew deliberately does not do

- Does not feed `openai_api`-sourced or shadow rows into
  `generate_policy.py`'s routing evidence (Section 3).
- Does not let routing avoid non-tool-calling Beans automatically (Section
  1) - the flag is data for a future decision, not new routing logic.
- Does not score or diff shadow pairs automatically (Section 2) - storage
  only.
- Does not create session rows for `/v1/chat/completions` traffic (Section
  1).

---

## 6. Edge cases, resolved

| Edge case | Resolution |
| --- | --- |
| No `model` field at all | `model: Optional[str] = None`; treated as "no override," classify+route normally, `requested_model` logged as `""`. |
| Enormous Cursor agent context (40k+ chars) | Not automatically `cold_brew` - `classify()` only ever sees the last message's text for the `long_text` signal; history contributes via turn *count* only (existing `long_history` signal), see Section 1. |
| `tools` array sent to a Bean that can't handle it | Passed through unchanged (Coffee never blocks on the new `tool_calling` flag this Brew); a warning is logged when `tools` is present and the routed Bean's flag is `false`, so it's visible in server logs even though nothing is blocked automatically. |
| Concurrent identical requests (parallelism, not retries) | Structurally excluded by Signal A's rule 4 - an in-flight original has no `response_text` yet, so nothing can match against it as a "prior, already-answered" request. |
| Shadow run fails while primary succeeds | Caught, logged as a warning, silent to the client - Section 2. |
| Daily shadow cap trips mid-request | Checked immediately before scheduling the shadow task (not after); skip + log one line, request path untouched. |
| Absent or spoofed `User-Agent` | Absent: fingerprint falls back to `user_id`-only (Signal A); `client_source` falls back to the literal `"openai_api"`. Spoofed: undetectable by construction - the report's "what this cannot tell you" footer says so plainly rather than implying `client_source` is trustworthy. |

---

## 7. Tests (new/extended files)

- `router/tests/test_openrouter_client.py`: `tools`/`tool_choice` passthrough
  (request and response), `messages_override` bypasses the prompt/history
  assembly, `tool_calls_delta` parsed from a streamed chunk.
- `router/tests/test_main.py`: new `ChatCompletionsEndpointTests` class -
  both stream modes, usage accounting, alias-as-model-override, `model`
  field always returns the Bean alias, auth rejection (401 without a
  token), no-`model`-field request, retry detection (including the
  concurrency false-positive case), `over_cap_declined`/`draft_quality`
  surfaced via `system_fingerprint`, every new Ledger column populated
  correctly for both endpoints.
- `router/tests/test_sessions.py` (or a new `test_api_requests.py` sibling,
  matching the file-per-concern pattern already used for
  `RememberChatAndAttachmentPersistenceTests`): `api_requests` table CRUD,
  shadow-pair storage, retry-count increment.
- New shadow-mode tests (likely in `test_main.py`): client latency
  unaffected (shadow task scheduled, not awaited), shadow never recursive,
  daily cap enforced and skip logged, shadow rows excluded from
  `generate_policy.py`'s evidence and from `ledger_summary.py`'s cost
  totals.
- `router/tests/test_ledger.py`: every new column's `to_csv_values()`
  output and the migration defaults table from Section 3.
- `tests/test_ledger_summary.py`: the new `--mode model-usage` report -
  volume/cost/bean-distribution slicing, escalation/decline/retry rate
  lines (including the "weak proxy" wording), counterfactual cost always
  printed adjacent to quality signals, shadow section, the "what this
  cannot tell you" footer.
- `tests/test_generate_policy.py`: `openai_api`/shadow rows excluded from
  rating evidence and escalation-rate computation.

---

## 8. Demo (per your request)

1. `curl` in raw OpenAI format against `/v1/chat/completions`.
2. The real OpenAI Python SDK (`openai.OpenAI(base_url=..., api_key=<token>)`)
   pointed at it unmodified, one call.
3. Cursor itself configured against the endpoint, one real coding task.
4. The resulting Ledger rows for all of the above, shown directly.
5. `tools/ledger_summary.py --mode model-usage` run against whatever real
   data exists at that point, output shown.

## 9. Docs

`router/README.md`: new "OpenAI-compatible endpoint" section (endpoint
table entry, Cursor setup, Continue.dev `config.yaml` snippet, how to get a
token, a short shadow-mode cost/enable note). Brew Log and Tasting Note
entries at the end, per usual.

---

## Open questions

1. **`prompt_shape` format** - raw pipe-delimited facts in the CSV column,
   coarse bucket derived at analysis time in `ledger_summary.py` (my
   reading of your "coarse bucket... has_code_fence, message_count,
   total_input_chars" wording, explained in Section 3). Confirm, or did you
   want the bucket label itself written into the CSV instead?
2. **Shadow scope** - shadow mode sampling only ever applies to
   `/v1/chat/completions` traffic, never `/v1/order` (Section 2), since
   that's the traffic this Brew is characterizing. Confirm, or should
   `/v1/order` be shadow-eligible too?
3. **`api_requests` retention** - no TTL/sweep is planned (matches this
   repo's consistent "no new background infrastructure" precedent, e.g.
   `get_user_for_token`'s comment in `auth.py`), so response text
   accumulates in `sessions.db` indefinitely, bounded only by the
   500-ish-char-capped `shadow_response_max_stored_chars` truncation.
   Acceptable for local/personal use at this router's real volume, or do
   you want a cap/sweep now?
4. **`over_cap_declined` for `/v1/order`** - Section 3 also populates this
   column for real human declines/timeouts on `/v1/order` (not just the
   forced-decline case on the new endpoint), since it's the same underlying
   phenomenon. Confirm this dual-endpoint scope is wanted, or should the
   column be `/v1/chat/completions`-only this Brew?
