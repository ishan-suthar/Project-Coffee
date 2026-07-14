# Coffee Core Router - Event Contract

Status: Brew 41B - frozen once this file is committed
Version: 1.4

This is the authoritative SSE event contract for `POST /v1/order` and
`POST /v1/retry`. The UI and any future animation are pure consumers of
this stream and should not need to renegotiate it. Field additions after
this point should be additive-only (new optional fields), never a rename
or removal, without a version bump to this file.

Drafted and approved in `docs/design/coffee-core-router-design.md` Section
4 before implementation; this is the as-implemented version, matching
`router/app/events.py` exactly.

## Changelog

- **1.4** (Brew 41, `docs/design/memory-and-pantry-design.md` Section 4.2):
  added optional `pantry_sources` to `complete` - the distinct source
  paths of the Pantry (`knowledge/`) chunks actually injected into the
  request's context when `OrderRequest.use_pantry` was true, or `null`
  when Pantry retrieval wasn't requested or nothing matched. Additive
  only.
- **1.3** (Brew 40, `docs/design/escalation-approval-ui-design.md`
  Sections 3.2/3.4): added a new `heartbeat` event (keep-alive only,
  ignored by any consumer for state purposes) and an optional
  `decision_deadline` field on `escalation_pending` (the UTC instant a
  pending approval auto-declines). Both additive - no field renamed or
  removed.
- **1.2** (Brew 38, `docs/design/attachments-design.md` Section 6.3):
  added optional `constraint_reason` to `route_selected` - explains why
  routing deviated from the plain policy/manual pick (e.g. a vision-needing
  request escalated to a vision-capable Bean). Additive only.
- **1.1** (Brew 37, `docs/design/coffee-counter-chat-ui-design.md` Section
  9): added optional `text_delta` to `generating`. Additive only - no
  field renamed or removed. Existing consumers that ignore the new field
  are unaffected.
- **1.0** (Brew 36): initial frozen contract.

## Transport

Each event is one Server-Sent Events frame:

```
data: <json>\n\n
```

## Shared base fields

Every event includes:

| Field | Type | Meaning |
| --- | --- | --- |
| `event` | string | One of the event names below. |
| `request_id` | string (UUID4) | Stable for the lifetime of one `/v1/order` call. |
| `ts` | string (ISO-8601 UTC) | Event emission time. |

## Event sequence

```
order_received
  -> classifying
    -> route_selected
      -> generating (repeated, 0+ times)
        -> [escalation_pending -> escalating]   (optional, see below)
      -> complete
  -> error      (may replace any step)
  -> cancelled  (may replace any step, via POST /v1/cancel)
```

`escalation_pending` is followed by one of:
- `escalating` then a second round of `generating` ticks against the
  premium Bean, then `complete` with `escalated: true`; or
- `complete` directly, with `escalated: false` and `draft_quality: true`
  (declined approval, or no premium Bean is configured - see
  `router/config/beans.yaml`'s `Reserve Blend` entry).

## Events

### `order_received`

| Field | Type |
| --- | --- |
| `prompt_chars` | integer |

No prompt text is included - length only, so raw request content never
appears in the event stream by default.

```json
{"event": "order_received", "ts": "2026-07-09T20:14:03.101Z", "request_id": "b3f1c2d4-...", "prompt_chars": 812}
```

### `classifying`

No extra fields.

```json
{"event": "classifying", "ts": "2026-07-09T20:14:03.140Z", "request_id": "b3f1c2d4-..."}
```

### `route_selected`

| Field | Type |
| --- | --- |
| `bean_alias` | string - never a raw model ID |
| `task_type` | string |
| `complexity` | `"espresso_shot"` \| `"cold_brew"` |
| `est_cost_usd` | number or `null` |
| `policy_entry` | string - which `routing_policy.yaml` entry justified this route |
| `constraint_reason` | string or `null` (added in v1.2) - why routing deviated from the plain policy/manual pick, e.g. a vision-needing request escalated to a vision-capable Bean; `null` in the normal, unconstrained case |

```json
{"event": "route_selected", "ts": "2026-07-09T20:14:03.210Z", "request_id": "b3f1c2d4-...", "bean_alias": "House Blend", "task_type": "code", "complexity": "espresso_shot", "est_cost_usd": 0.0, "policy_entry": "code/house-blend", "constraint_reason": null}
```

### `generating`

| Field | Type |
| --- | --- |
| `tokens_out` | integer - cumulative, not a delta |
| `est_cost_usd` | number or `null` |
| `text_delta` | string or `null` (added in v1.1) - the incremental text chunk since the last tick, not cumulative |

Emitted after `settings.generating_tick_tokens` output tokens or
`settings.generating_tick_seconds` seconds, whichever comes first.
`text_delta` is the new content produced since the previous `generating`
event (or since `route_selected`, for the first tick) - concatenate
`text_delta` values in arrival order to reconstruct the full streamed
text; do not use `tokens_out` for reconstruction, it is a count, not text.

```json
{"event": "generating", "ts": "2026-07-09T20:14:04.500Z", "request_id": "b3f1c2d4-...", "tokens_out": 40, "est_cost_usd": 0.0, "text_delta": "A Python decorator is a function that "}
```

### `escalation_pending`

| Field | Type |
| --- | --- |
| `reason` | `"truncated"` \| `"empty"` \| `"refusal_shaped"` \| `"caller_reported"` |
| `est_cost_usd` | number |
| `premium_bean_alias` | string or `null` |
| `decision_deadline` | string (ISO-8601 UTC) or `null` (added in v1.3) |

`premium_bean_alias` is `null` when no premium Bean is configured. In that
case `complete` follows immediately with `draft_quality: true` - there is
nothing to approve, and `decision_deadline` is also `null`.

`decision_deadline` (v1.3) is this event's `ts` plus
`settings.escalation_approval_timeout_seconds` - the instant
`POST /v1/approve_escalation` stops mattering and the pause auto-declines.
A UI can render a countdown from it, and can distinguish "the user
declined" from "the wait timed out" after the fact: if `complete` arrives
with `draft_quality: true` and no `escalating` was ever seen, the pause
timed out if `now >= decision_deadline`, otherwise it was an explicit
decline - no separate event carries this distinction.

```json
{"event": "escalation_pending", "ts": "2026-07-09T20:14:06.900Z", "request_id": "b3f1c2d4-...", "reason": "truncated", "est_cost_usd": 0.42, "premium_bean_alias": "Reserve Blend", "decision_deadline": "2026-07-09T20:24:06.900Z"}
```

While a request is paused on `escalation_pending`, `POST /v1/order`'s
stream may also emit `heartbeat` frames (see below) - these do not
appear in the state-sequence diagram above because they carry no state
and must be ignored by any consumer.

A pending escalation also survives the original `/v1/order` connection
being closed (a tab close, reload, or network drop) - the pause and the
eventual decision still happen server-side. `GET
/v1/sessions/{session_id}/pending_escalation` lets a reloaded client
recover the same information this event carries for any escalation still
awaiting a decision in that session; see "Escalation recovery" below.

### `escalating`

| Field | Type |
| --- | --- |
| `bean_alias` | string |

Only emitted after either auto-escalation (estimated cost under the cap)
or an approved `POST /v1/approve_escalation`.

```json
{"event": "escalating", "ts": "2026-07-09T20:14:07.000Z", "request_id": "b3f1c2d4-...", "bean_alias": "Reserve Blend"}
```

### `complete`

| Field | Type |
| --- | --- |
| `bean_alias` | string |
| `tokens_in` | integer |
| `tokens_out` | integer |
| `cost_usd` | number or `null` |
| `latency_ms` | integer |
| `escalated` | boolean |
| `draft_quality` | boolean - true exactly when escalation was declined or unavailable |
| `pantry_sources` | string array or `null` (added in v1.4) |

```json
{"event": "complete", "ts": "2026-07-09T20:14:07.050Z", "request_id": "b3f1c2d4-...", "bean_alias": "House Blend", "tokens_in": 210, "tokens_out": 640, "cost_usd": 0.0, "latency_ms": 2940, "escalated": false, "draft_quality": false, "pantry_sources": null}
```

`pantry_sources` (v1.4) is `null` unless the originating `OrderRequest` had
`use_pantry: true` and at least one chunk matched - it is never an empty
list standing in for "asked but nothing found," always `null` in that
case. When present, it lists the distinct repo-root-relative paths (e.g.
`"knowledge/00_index.md"`) of every Pantry chunk actually prepended to
the model's context for this request - see "Pantry retrieval" below.

```json
{"event": "complete", "ts": "2026-07-15T20:14:07.050Z", "request_id": "b3f1c2d4-...", "bean_alias": "House Blend", "tokens_in": 310, "tokens_out": 640, "cost_usd": 0.0, "latency_ms": 2940, "escalated": false, "draft_quality": false, "pantry_sources": ["knowledge/00_index.md", "knowledge/project_docs/project-coffee-foundation-summary.md"]}
```

### `error`

| Field | Type |
| --- | --- |
| `error_type` | string |
| `message` | string - safe summary, never raw provider error bodies |
| `retryable` | boolean |

```json
{"event": "error", "ts": "2026-07-09T20:14:07.050Z", "request_id": "b3f1c2d4-...", "error_type": "provider_error", "message": "OpenRouter did not respond within the configured timeout.", "retryable": true}
```

Known `error_type` values include `provider_error`, `invalid_bean_override`
(Brew 37), and, since Brew 38, `no_vision_bean_available` - emitted when a
request needs a vision-capable Bean (an image was attached) but no Bean in
`router/config/beans.yaml` has `capabilities.vision: true` (see
`docs/design/attachments-design.md` Section 6.2 - as of Brew 38 this is
every real request with an image attached, since no vision Bean is
configured yet):

```json
{"event": "error", "ts": "2026-07-11T20:14:07.050Z", "request_id": "b3f1c2d4-...", "error_type": "no_vision_bean_available", "message": "This request needs a vision-capable Bean, but none is configured in beans.yaml.", "retryable": false}
```

### `cancelled`

Emitted when `POST /v1/cancel` is called for an in-flight `request_id`
(reason `"client_cancel_request"`) - the generation loop checks a
per-request cancellation flag each iteration and stops early. Since v1.3
(Brew 40), this also applies while paused on `escalation_pending`:
cancelling during that wait races the cancellation flag against the
pending approval and emits `cancelled` immediately, the same as
cancelling during generation - the pause does not swallow a cancel
request. A plain client disconnect (closing the browser tab, network
drop) is different: nothing is listening anymore by definition, so no
final event is emitted for that case - `sse_stream()` simply stops
draining. `reason: "client_disconnect"` is reserved in the schema for a
future server-side detection path but is not emitted today. Note that
since Brew 40 a disconnect no longer stops the underlying request itself
(see "Escalation recovery" below) - only the stream the disconnected
client was reading from.

| Field | Type |
| --- | --- |
| `reason` | `"client_disconnect"` \| `"client_cancel_request"` |

```json
{"event": "cancelled", "ts": "2026-07-10T20:14:05.000Z", "request_id": "b3f1c2d4-...", "reason": "client_cancel_request"}
```

### `heartbeat`

Added in v1.3. Carries no fields beyond the shared base. Sent whenever no
real event has been queued for `settings.sse_heartbeat_interval_seconds`,
so an otherwise-idle connection (most likely during a long
`escalation_pending` pause) isn't dropped by an intermediate proxy or
browser idle-connection timeout. **Any consumer must ignore this event
for state purposes** - it never becomes a UI's "latest event," never
advances the animated scene, and is not part of the event-sequence
diagram at the top of this document; it can appear at any point in the
stream, any number of times.

```json
{"event": "heartbeat", "ts": "2026-07-12T20:16:00.000Z", "request_id": "b3f1c2d4-..."}
```

## Escalation recovery (survives a dropped connection)

Since Brew 40, a request paused on `escalation_pending` keeps running
server-side independent of the `/v1/order` HTTP connection that started
it - closing the tab, reloading, or a network drop during the pause does
not cancel the wait or lose the eventual decision. `POST
/v1/approve_escalation` still works using the same `request_id` even
after the original stream is gone.

`GET /v1/sessions/{session_id}/pending_escalation` returns the same
information the `escalation_pending` event carried, for any request in
that session still awaiting a decision, so a reloaded client can redraw
the approval card:

```json
{"request_id": "b3f1c2d4-...", "reason": "truncated", "est_cost_usd": 0.42, "premium_bean_alias": "Reserve Blend", "started_at": "2026-07-12T20:14:06.900Z", "decision_deadline": "2026-07-12T20:24:06.900Z"}
```

Returns HTTP 404 if no escalation is currently pending for that session.
This endpoint does not resume live token streaming for the recovered
request - see `docs/design/escalation-approval-ui-design.md` Section 3.5
for the deliberate scope boundary (polling `GET
/v1/sessions/{id}/messages` for the eventual result instead).

A `POST /v1/approve_escalation` call for a `request_id` that has already
been resolved (a duplicate click, or a decision arriving after the
timeout already fired) returns HTTP 200 with
`{"status": "already_resolved", "resolution": "approved" | "declined" | "timed_out" | "cancelled"}`
instead of silently no-op'ing or a bare 404 - see Section 3.6 of the same
design doc.

## Pantry retrieval (Brew 41)

`POST /v1/order` gains an additive `use_pantry: boolean` field (default
`false`). When true, the router queries the FTS5 index at
`router/data/pantry_index.db` (built by `python router/tools/index_pantry.py`
- see `docs/design/memory-and-pantry-design.md`) for the
`settings.pantry_top_k` best-matching chunks of `knowledge/`, prepends
them to the model's context with clear source headers and an
instruction not to fabricate citations or claim coverage the material
doesn't have (Constitution Article 6.4), and reports exactly which
sources were injected via `complete.pantry_sources` (see above) - never
a model self-report of what it "used." If the index doesn't exist yet
(the indexer has never been run) or the prompt yields no FTS5 tokens
(e.g. punctuation-only), the request proceeds without retrieval and
`pantry_sources` stays `null` - `use_pantry: true` never fails the
request outright.

`GET /v1/pantry/file?path=knowledge/00_index.md` returns the raw text
content of a file for the citation-chip file viewer - read-only, and
path-traversal safe (rejects absolute paths, `..` escapes, and anything
outside `knowledge/`; 404s rather than erroring on a bad path). Returns
HTTP 404 for any path that doesn't resolve to a real file inside
`knowledge/`.

## Memory proposals (Brew 41)

Three new endpoints, all plain request/response (not SSE) - a single
bounded model call, not a multi-minute human-wait phase, so none of the
Brew 40 background-task/heartbeat machinery applies here:

- `POST /v1/sessions/{session_id}/memory_proposal` - generates a
  proposed update to exactly two files, `brew-log/active_context.md` and
  `brew-log/progress.md`, from the session's transcript using
  `settings.memory_proposal_bean_alias` (default `House Blend`). Returns
  `{"proposal_id": "...", "files": [{"path": "...", "diff": "<unified diff>", "new_content": "..."}]}`
  for each of the two files. Refuses (HTTP 422) if the model's proposal
  names any path other than those exact two files, or if either file's
  proposed content deletes more than 50% of its current lines
  (`docs/design/memory-and-pantry-design.md` Section 3.3) - the proposal
  is never shown to the UI in that case.
- `POST /v1/memory_proposals/{proposal_id}/approve` - re-validates both
  guardrails against the *current* on-disk content (not the snapshot the
  proposal was generated from), writes both files, and appends one
  `ledger/router_requests.csv` row with `task_type=memory` (no schema
  change - `task_type` is already a free-form column).
  `POST /v1/memory_proposals/{proposal_id}/discard` - drops the proposal,
  writes nothing, logs nothing.

Memory is never written without this explicit approval call - there is
no auto-approve path.

## Aliases (never raw model IDs)

`bean_alias` values are always one of the aliases in
`router/config/beans.yaml` (`House Blend`, `Second Pour`, `Guest Bean`,
`Reserve Blend`). Raw OpenRouter model IDs never appear in any event -
see `router/tests/test_events.py::test_no_raw_model_id_ever_appears_in_any_event_payload`
and `router/tests/test_main.py::RunOrderTestCase::test_no_raw_model_id_in_any_yielded_event`.
