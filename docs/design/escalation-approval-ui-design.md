# Escalation Approval Gate UI Design (Brew 40)

Status: Decaf plan - no code written
Date: 2026-07-12

## 0. Reading done before this plan

Read in full: `router/app/escalation.py`, `router/app/main.py` (the entire
`_run_order_body`/`_run_escalation`/`_await_approval` chain, all FastAPI
routes, `RouterState`), `router/EVENT_CONTRACT.md` (v1.2), `router/app/config.py`,
`router/config/settings.yaml`, `router/app/sessions.py`, `router/app/ledger.py`,
`web/src/store/chatStore.ts`, `web/src/lib/{chat,api,sse,events}.ts`,
`web/src/components/ResponseSection/{MessageHeader,MessageBubble}.tsx`,
`web/src/components/CounterDisplay/statusText.ts` and `sceneState.ts`.

## 1. What already exists - do not rebuild

- `router/app/escalation.py`'s `decide_escalation()`/`resolve_pending_escalation()`
  already implement the three-way outcome (`auto_escalate` /
  `escalation_pending` / `no_premium_available`) and the
  approve→escalate / decline→draft resolution. Nothing to change here
  except adding a `"cancelled"` resolution (Section 3.3).
- `router/app/main.py` already pauses correctly server-side:
  `_await_approval()` creates a `Future`, stores it in
  `state.pending_escalations[request_id]`, and `POST /v1/approve_escalation`
  resolves it. This is Requirement 1's "already built in Stage B" -
  confirmed by reading the code, not assumed.
- `router/app/main.py`'s Ledger write already records
  `escalation_approved` correctly for the approve/decline cases (`None`
  when no escalation occurred, `True`/`False` otherwise) - Requirement 3's
  "Ledger row shows `escalation_approved=false`" on decline is **already
  correct today** for a live, connected session. What's missing is making
  that still true after the connection-resilience changes below, which I
  verify with a dedicated test rather than assuming it still holds.
- `web/src/lib/api.ts` already has `approveEscalation()` and
  `cancelOrder()` - unused by any UI today. `web/src/lib/chat.ts`'s
  `reduceEventIntoMessage` already populates `message.escalation` from
  `escalation_pending`. `MessageHeader.tsx` already has a **read-only,
  post-hoc** expandable escalation marker - this stays as-is for
  *completed* turns; Requirement 1's approval card is a new,
  time-sensitive, actionable component for the *pending* turn.
- `web/src/components/CounterDisplay/sceneState.ts` already maps
  `escalation_pending` to state 5 ("Barista waits, taps foot") and
  `escalating` to state 6 - no scene changes needed.
- Requirement 5 ("Tips Jar does not tick during the pause") is **already
  true with zero code changes**: the pause emits no `generating` events,
  and `TipsJar.tsx` only reacts to `generating` events to drop a coin.
  Verified by reading `TipsJar.tsx`, not assumed - I'll still add one
  regression test since it's easy to break by accident later.

## 2. Real gaps found - surfaced now, not worked around silently

1. **The entire pending-approval wait is tied to one HTTP connection's
   lifetime.** `run_order()`'s async generator is driven directly by
   `StreamingResponse(sse_stream(events), ...)` (`main.py:719`). Starlette
   cancels the task backing a `StreamingResponse` when the client
   disconnects (closing the tab, navigating away, a network drop) - this
   is standard ASGI behavior, not a bug I'm introducing. Today, closing
   the tab during a pending escalation **kills the wait outright**: the
   `Future` in `pending_escalations` is orphaned (never resolved, never
   cleaned up until process restart), and there is nothing left to
   "recover" on reload - the whole request has silently died server-side.
   This is the central architectural gap behind Requirement 4's reload
   scenario and needs a real decision (Section 3.1), not a UI patch.
2. **No mechanism exists for the server to tell the UI "here is what's
   currently paused for this session"** after a reload - `SessionStore.add_message()`
   is only called once at the very end of `_run_order_body`, so a
   still-pending turn has no row in `sessions.db` yet for the UI to
   recover from `GET /v1/sessions/{id}/messages`.
3. **The SSE connection has no heartbeat today.** `sse_stream()` only
   ever yields real events; during a multi-minute pause it sends nothing
   at all. Requirement 4 explicitly asks for this to be fixed, so I'm not
   treating it as optional.
4. **The approval-wait timeout is a hardcoded module constant**
   (`ESCALATION_APPROVAL_TIMEOUT_SECONDS = 300.0` in `main.py`), not a
   `settings.yaml` value, and it doesn't match the requested 10-minute
   default.
5. **Nothing currently interrupts `_await_approval()` on cancel.**
   `POST /v1/cancel` sets `state.cancel_flags[request_id]`, which
   `_consume_stream()` checks during generation - but `_await_approval()`
   only awaits the approval `Future` (or its own timeout), never the
   cancel flag. Cancelling during a pause today has **no effect** until
   the wait resolves some other way. This is exactly the edge case
   Requirement 4 flags, and it's real, not hypothetical.
6. **Nothing distinguishes "declined" from "timed out" anywhere the UI
   can see.** Both resolve identically today: no `escalating` event,
   then `complete` with `draft_quality: true`. Requirement 4 asks the
   card to "note it" on timeout specifically.
7. **No plain-language mapping exists for `EscalationReason`.** The UI
   has only ever shown the raw reason string (`"truncated"`, etc.) inside
   `MessageHeader`'s read-only marker.

## 3. Proposed architecture

### 3.1 Decoupling the pending wait from the HTTP connection (the central decision)

**Recommendation: run each order as a background `asyncio.Task`, decoupled
from the HTTP connection, publishing events into a per-request
`asyncio.Queue` that `/v1/order`'s `StreamingResponse` drains.**

```
POST /v1/order
  -> creates an asyncio.Queue
  -> asyncio.create_task(_run_order_and_publish(state, queue, ...))
       (iterates run_order() exactly as today, `await queue.put(event)`
        per event, `await queue.put(None)` sentinel on completion,
        always in a finally block so a dropped connection never leaks it)
  -> StreamingResponse drains the queue (with a heartbeat timeout - 3.2)
```

This is a **minimally invasive** change: `run_order()` itself is
untouched - still a plain async generator, still directly unit-testable
exactly as today (every existing `RunOrderTestCase` test in
`test_main.py` calls `run_order()` directly and is unaffected). Only the
`/v1/order` FastAPI handler changes. If the HTTP connection drops, only
the *draining* side dies; the background task (including a pending
`_await_approval()` wait, and the eventual Ledger/SessionStore writes)
keeps running to completion untouched. This is what makes "the pipeline
survives the wait" and "reload recovers the pending card" both possible
at all - without it, there is nothing durable to recover.

**Alternative considered and rejected**: keep `run_order()` directly
driving the response and try to make the *escalation wait specifically*
survive via some other mechanism. I don't think this works - Starlette
cancels the whole request task on disconnect regardless of what it's
awaiting internally (a `Future`, an `Event`, anything) - there's no
narrower fix than decoupling execution from the connection. Flagged as
Question 1 in case you know a lighter alternative I'm missing.

### 3.2 Heartbeats (event contract v1.3)

The queue-draining loop uses `asyncio.wait_for(queue.get(), timeout=settings.sse_heartbeat_interval_seconds)`;
on a timeout it sends a `heartbeat` frame and loops again (the queue
itself is untouched). New setting `sse_heartbeat_interval_seconds: float = 15.0`
(comfortably under typical proxy/browser idle-connection timeouts).

New documented event, additive, bumping the contract to **v1.3**:

```json
{"event": "heartbeat", "ts": "...", "request_id": "b3f1c2d4-..."}
```

No extra fields. Explicitly documented as "keep-alive only - any
consumer must ignore it for state purposes; it never becomes a message's
`latestEvent`." `web/src/lib/chat.ts`'s `reduceEventIntoMessage` gains a
`case "heartbeat": return message;` (a no-op) so the scene/status text
never has to know it exists.

### 3.3 Cancel-during-pause

`_await_approval()` races the approval `Future` against
`cancel_event.wait()` via `asyncio.wait(..., return_when=FIRST_COMPLETED)`.
If the cancel wins, it returns a new `"cancelled"` outcome distinct from
`"approved"`/`"declined"`. `_run_order_body` checks for this before
calling `resolve_pending_escalation()` and yields `CancelledEvent`
immediately (matching the existing cancel semantics used during
generation) instead of falling through to a completed/draft result.
`escalation.py`'s `resolve_pending_escalation()` doesn't need to know
about `"cancelled"` at all - the caller branches before calling it.

### 3.4 Declined vs. timed out (making the distinction visible)

Rather than inventing a new event just to announce "how" the pause
resolved, `EscalationPendingEvent` gains one additive field:
`decision_deadline` (ISO-8601 UTC timestamp = pause start +
`settings.escalation_approval_timeout_seconds`). The UI can then:
- show a live countdown on the approval card (Requirement 4 implicitly
  wants users to know a timeout is coming), and
- when `complete` arrives with `draft_quality: true` and no `escalating`
  was ever seen, conclude "timed out" if `now >= decision_deadline`, else
  "declined" - a deterministic client-side computation from real
  server-provided data, not a guess.

`settings.yaml` gains `escalation_approval_timeout_seconds: float = 600.0`
(10 minutes, replacing the hardcoded 300s constant, matching your stated
default).

### 3.5 Reload recovery

New `RouterState.pending_escalation_context: Dict[str, PendingEscalationContext]`,
populated right before `_await_approval()` is called for the
`escalation_pending` outcome specifically (not `auto_escalate`, which
never pauses):

```python
@dataclass(frozen=True)
class PendingEscalationContext:
    request_id: str
    session_id: Optional[str]
    reason: FailureReason
    est_cost_usd: float
    premium_bean_alias: str
    started_at: str          # ISO-8601 UTC
    decision_deadline: str   # ISO-8601 UTC
```

New endpoint: `GET /v1/sessions/{session_id}/pending_escalation` -
returns the context if an unresolved pause exists for that session, else
404. Cleaned up in `run_order()`'s existing `finally` block, alongside
`cancel_flags.pop()`.

On session load, the frontend calls this endpoint once; if it finds a
pending escalation, it renders the approval card from that data (buttons
wired to the same `POST /v1/approve_escalation` as the live path - the
background task is still running server-side, so the decision still
takes effect for real).

**Non-goal, explicitly**: reload does **not** resume live token
streaming for that request. After the recovered card's decision is sent,
the UI shows a lightweight "waiting for the response..." indicator and
polls `GET /v1/sessions/{id}/messages` every few seconds until the
completed message appears - reusing an endpoint that already exists,
not building a second streaming/resume mechanism. If you'd rather the
reloaded tab reattach to the live event queue instead of polling, say so
- Question 2.

### 3.6 Double-click / late-approval friendliness

`PendingEscalationContext` stays in the dict after resolution until
`run_order()`'s `finally` cleans it up (i.e., it's marked resolved rather
than deleted immediately) - see amendment: the context dataclass above is
frozen for the "open" case, and a small `resolved_at`/`resolution`
companion is tracked separately in `state` so `/v1/approve_escalation`
can distinguish three cases instead of a bare 404:
- unknown `request_id` entirely -> 404 (unchanged today).
- already resolved (a second click, or a click arriving after the
  timeout already fired) -> 200 with `{"status": "already_resolved", "resolution": "approved"|"declined"|"timed_out"|"cancelled"}`,
  not a silent no-op pretending success.
- open and now resolved by this call -> 200 `{"status": "acknowledged"}` (unchanged).

## 4. Frontend

### 4.1 `EscalationApprovalCard` (new, `ResponseSection/EscalationApprovalCard.tsx`)

Rendered by `MessageBubble` when a message has an unresolved pending
escalation: `message.escalation !== null && message.isStreaming &&
message.latestEvent?.event === "escalation_pending"` for the live path,
or a `pendingEscalationRecovered` flag set from the reload-recovery fetch
for the reload path (Section 3.5). Content:
- Plain-language failure sentence from a new data-driven table
  (`escalationReasonText.ts`, matching `statusText.ts`'s own philosophy):
  `truncated` → "The response was cut off before finishing.",
  `empty` → "The model returned an empty response.",
  `refusal_shaped` → "The model appears to have declined to answer.",
  `caller_reported` → "You reported this response as needing a retry."
- Premium Bean alias, estimated cost (`$X.XXXX`).
- A live countdown to `decision_deadline` (plain `setInterval`, no new
  dependency).
- Two buttons: "Brew premium" → `api.approveEscalation(requestId, true)`,
  "Keep the cheap cup" → `api.approveEscalation(requestId, false)`. Both
  disabled immediately on click (prevents a double-click from firing two
  requests client-side; the server-side `already_resolved` handling in
  3.6 is the real safety net, this is just responsive UI).

### 4.2 `chatStore.ts`

Gains an `approveEscalation(requestId, approve)` action (thin wrapper
around `api.approveEscalation`, mirrors `rate`/`cancelActive`'s shape),
and a `recoverPendingEscalation(sessionId)` action called from
`selectSession()` that calls the new `GET .../pending_escalation`
endpoint and, if found, synthesizes an in-progress assistant
`ChatMessage` carrying the recovered `escalation` data and a
`pendingEscalationRecovered: true` marker so `MessageBubble` renders the
card without a live SSE stream backing it.

### 4.3 `events.ts` / `chat.ts`

- `RouteSelectedEvent`... unaffected. `EscalationPendingEvent` gains
  `decision_deadline: string`. New `HeartbeatEvent` interface added to
  the `RouterEvent` union, handled as a no-op in `reduceEventIntoMessage`
  (Section 3.2).
- `ChatMessage` gains one additive field: `pendingEscalationRecovered: boolean`
  (defaults `false`), only ever `true` for a card reconstructed via 3.5's
  recovery path.

## 5. Demo flag: `force_escalation`

An environment variable, **never** a `settings.yaml` field (a committed
config file must never be able to silently ship this "on"):
`COFFEE_ROUTER_FORCE_ESCALATION=1`. Checked directly via
`os.environ.get(...) == "1"` at the point `check_for_failure()` is
called in `_run_order_body` - when set, every generation is treated as a
`caller_reported` failure regardless of its real content, forcing the
escalation path on demand for a live demo. Documented in the module
docstring as test/demo-only, off by default, and asserted in a test that
it's off unless explicitly set.

## 6. Tests

- **Both button paths**: approve → `escalating` then `complete` with
  `escalated: true`; decline → `complete` directly with
  `draft_quality: true`, no `escalating`. Ledger row correct for both.
- **Timeout path**: `_await_approval` with a short injected timeout
  resolves to declined/draft-quality, Ledger `escalation_approved=false`,
  and the UI-visible distinction (`decision_deadline` in the past) is
  computable from the emitted events.
- **Cancel during pause**: cancelling mid-wait yields `CancelledEvent`,
  not a hung request or a completed one.
- **Double-click**: two rapid `POST /v1/approve_escalation` calls - first
  resolves, second gets `already_resolved`, no crash, no double-escalation.
- **Late approval**: a `POST /v1/approve_escalation` arriving after the
  timeout already fired gets `already_resolved` with `resolution: "timed_out"`,
  not a bare 404.
- **Reload recovery**: `GET /v1/sessions/{id}/pending_escalation` returns
  the right context while a background task is genuinely still paused
  (test spawns the background task the same way the real endpoint does,
  not a shortcut); resolves correctly once approved from that recovered
  state.
- **Heartbeat**: a paused request emits `heartbeat` frames at the
  configured interval, and they never touch `latestEvent`/scene state.
- **Tips Jar regression test**: no coin drop occurs across an
  `escalation_pending` → (silence) → `escalating` sequence.
- **`force_escalation` off by default**: a normal successful generation
  does not escalate unless the env var is explicitly set in that test.

## 7. Non-goals for this Brew

- Resuming live token streaming after a reload (Section 3.5) - polling
  the existing messages endpoint instead.
- A new Ledger column distinguishing declined vs. timed-out (both remain
  `escalation_approved=false`; the distinction is UI-only, computed from
  `decision_deadline`).
- Any change to `resolve_pending_escalation()`'s public two-outcome
  shape - `"cancelled"` is handled by the caller before that function is
  invoked, not added to it.
- Persisting `PendingEscalationContext` across a full router restart -
  same ephemeral-in-memory precedent as `pending_escalations` today.

## 8. Open questions requiring your decision

1. **Background-task + queue decoupling for `/v1/order`** (Section 3.1).
   *(Recommended - it's the only way I can see to make the pending wait
   outlive one HTTP connection at all.)*
2. **Reload recovery re-shows the card and lets the decision take effect,
   but does not resume live streaming - the reloaded tab polls for the
   final message instead.** *(Recommended for scope; say if you'd rather
   I build live reattachment instead.)*
3. **Heartbeat interval default 15s, approval timeout default 600s
   (10 minutes, as you specified).** *(Recommended.)*
4. **`decision_deadline` as a new additive `escalation_pending` field**
   (event contract v1.3) rather than a separate endpoint/event.
   *(Recommended - matches the v1.1/v1.2 additive-field precedent.)*
5. **`COFFEE_ROUTER_FORCE_ESCALATION` env var name** - say if you'd
   prefer a different name.

## 9. Files touched (CREATE/MODIFY)

```
router/app/escalation.py          MODIFY - "cancelled" resolution branch handling (caller-side, not resolve_pending_escalation's signature)
router/app/main.py                MODIFY - background task + queue for /v1/order, heartbeat drain loop,
                                            _await_approval cancel-race, PendingEscalationContext tracking,
                                            GET /v1/sessions/{id}/pending_escalation, already_resolved handling,
                                            force_escalation env var check
router/app/config.py              MODIFY - escalation_approval_timeout_seconds, sse_heartbeat_interval_seconds
router/config/settings.yaml       MODIFY - same two new settings
router/app/events.py              MODIFY - EscalationPendingEvent.decision_deadline, new HeartbeatEvent
router/EVENT_CONTRACT.md          MODIFY - v1.3 changelog, heartbeat event, decision_deadline field
router/tests/test_escalation.py   MODIFY - "cancelled" resolution test
router/tests/test_main.py         MODIFY - all Section 6 tests
router/tests/test_events.py       MODIFY - HeartbeatEvent/decision_deadline tests

web/src/lib/events.ts             MODIFY - HeartbeatEvent, decision_deadline field
web/src/lib/chat.ts               MODIFY - heartbeat no-op, pendingEscalationRecovered field
web/src/lib/api.ts                MODIFY - getPendingEscalation()
web/src/store/chatStore.ts        MODIFY - approveEscalation(), recoverPendingEscalation()
web/src/components/ResponseSection/
  EscalationApprovalCard.tsx      CREATE - the approval card
  EscalationApprovalCard.test.tsx CREATE
  escalationReasonText.ts         CREATE - plain-language reason table
  MessageBubble.tsx               MODIFY - render the card when pending
web/src/components/CounterDisplay/*  no changes expected (state 5/6 already mapped)
```

## 10. Workflow from here

1. You review this plan and answer Section 8's five questions.
2. On approval: router-side connection decoupling and heartbeat first
   (the riskiest, most structural change) with its own tests green,
   before any frontend work.
3. Frontend approval card and recovery flow.
4. Live demo: force a real escalation via `COFFEE_ROUTER_FORCE_ESCALATION=1`,
   demonstrate approve, decline, and - time permitting - a real reload
   during a pause.
5. Brew Log, Tasting Note, summary.
