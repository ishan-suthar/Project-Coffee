# Coffee Core Router - Event Contract

Status: Brew 36B - frozen once this file is committed
Version: 1

This is the authoritative SSE event contract for `POST /v1/order` and
`POST /v1/retry`. The UI and any future animation are pure consumers of
this stream and should not need to renegotiate it. Field additions after
this point should be additive-only (new optional fields), never a rename
or removal, without a version bump to this file.

Drafted and approved in `docs/design/coffee-core-router-design.md` Section
4 before implementation; this is the as-implemented version, matching
`router/app/events.py` exactly.

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

```json
{"event": "route_selected", "ts": "2026-07-09T20:14:03.210Z", "request_id": "b3f1c2d4-...", "bean_alias": "House Blend", "task_type": "code", "complexity": "espresso_shot", "est_cost_usd": 0.0, "policy_entry": "code/house-blend"}
```

### `generating`

| Field | Type |
| --- | --- |
| `tokens_out` | integer - cumulative, not a delta |
| `est_cost_usd` | number or `null` |

Emitted after `settings.generating_tick_tokens` output tokens or
`settings.generating_tick_seconds` seconds, whichever comes first.

```json
{"event": "generating", "ts": "2026-07-09T20:14:04.500Z", "request_id": "b3f1c2d4-...", "tokens_out": 40, "est_cost_usd": 0.0}
```

### `escalation_pending`

| Field | Type |
| --- | --- |
| `reason` | `"truncated"` \| `"empty"` \| `"refusal_shaped"` \| `"caller_reported"` |
| `est_cost_usd` | number |
| `premium_bean_alias` | string or `null` |

`premium_bean_alias` is `null` when no premium Bean is configured. In that
case `complete` follows immediately with `draft_quality: true` - there is
nothing to approve.

```json
{"event": "escalation_pending", "ts": "2026-07-09T20:14:06.900Z", "request_id": "b3f1c2d4-...", "reason": "truncated", "est_cost_usd": 0.42, "premium_bean_alias": "Reserve Blend"}
```

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

```json
{"event": "complete", "ts": "2026-07-09T20:14:07.050Z", "request_id": "b3f1c2d4-...", "bean_alias": "House Blend", "tokens_in": 210, "tokens_out": 640, "cost_usd": 0.0, "latency_ms": 2940, "escalated": false, "draft_quality": false}
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

### `cancelled`

Reserved in the schema (`router/app/events.py:CancelledEvent`) for a future
client-initiated cancel endpoint. Not emitted by the current
implementation: once a client disconnects from an open SSE stream there is
no one left to receive a final event, so `sse_stream()` simply lets the
generator stop.

| Field | Type |
| --- | --- |
| `reason` | `"client_disconnect"` \| `"client_cancel_request"` |

## Aliases (never raw model IDs)

`bean_alias` values are always one of the aliases in
`router/config/beans.yaml` (`House Blend`, `Second Pour`, `Guest Bean`,
`Reserve Blend`). Raw OpenRouter model IDs never appear in any event -
see `router/tests/test_events.py::test_no_raw_model_id_ever_appears_in_any_event_payload`
and `router/tests/test_main.py::RunOrderTestCase::test_no_raw_model_id_in_any_yielded_event`.
