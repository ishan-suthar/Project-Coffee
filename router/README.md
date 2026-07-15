# Coffee Core Router

Status: Brew 42 - learning loop + release pass

The Coffee Core Router is a local FastAPI service that sits between clients
(the Coffee Counter Chat UI in `web/`, or any HTTP client) and OpenRouter. It
classifies a prompt, routes it to a Bean, streams generation over Server-Sent
Events, checks for failure, pauses for human approval before escalating to a
premium Bean, retrieves grounded Pantry context on request, drafts and
guardrails session memory proposals, and rebuilds its own routing policy
from Roastery evidence plus real user ratings - all reviewable, none of it
automatic.

Design docs (read in this order for full history): `docs/design/coffee-core-router-design.md`
(Brew 36 - core service), `docs/design/coffee-counter-chat-ui-design.md`
(Brew 37 - sessions/rate/cancel), `docs/design/attachments-design.md` (Brew
38 - uploads/vision), `docs/design/counter-scene-design.md` (Brew 39 -
preferences), `docs/design/escalation-approval-ui-design.md` (Brew 40 -
background-task decoupling), `docs/design/memory-and-pantry-design.md`
(Brew 41 - Pantry retrieval + memory proposals), `docs/design/learning-loop-and-release-design.md`
(Brew 42 - ratings-weighted policy rebuild). Event contract:
`router/EVENT_CONTRACT.md` (currently v1.4 - see its changelog for the full
version history instead of restating it here).

## Requirements

`fastapi`, `uvicorn`, `pydantic`, `httpx`, `pyyaml`, `pypdf`, `charset_normalizer`
(see `requirements.txt`). All were already installed in this environment
across Brews 36-42 - no `pip install` was run for any of them.

## Run

From the Project Coffee repository root (required - `tools.coffee_context_package`
and `router.app.*` both resolve as importable packages only from there), with
`OPENROUTER_API_KEY` set in your own shell environment (never in a file,
never pasted into chat):

```powershell
python -m uvicorn router.app.main:app --port 8765
```

Then, separately, the frontend (see `web/README.md`):

```powershell
cd web
npm run dev
```

### Environment variables

| Variable | Purpose |
| --- | --- |
| `OPENROUTER_API_KEY` | Required for any real OpenRouter call. Read from the environment only - never a request field, config value, or logged/emitted anywhere. |
| `COFFEE_ROUTER_FORCE_ESCALATION` | Demo/test-only. Set to `"1"` to force every generation to look like a failure, so the escalation approval flow can be exercised without crafting a real failing prompt. Never read anywhere except `_force_escalation_enabled()` in `main.py`; never a settings.yaml field on purpose, since a committed config file could ship it "on" by accident. |
| `NEXT_PUBLIC_ROUTER_URL` | Read by the frontend (`web/`), not the router itself - see `web/README.md`. |

## Endpoints

All request/response bodies are JSON unless noted. `POST /v1/order` and
`POST /v1/retry` stream the SSE event contract documented in
`router/EVENT_CONTRACT.md`; every other endpoint is a plain request/response.

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/v1/order` | POST | Streams the full event contract for one prompt. Body: `{"prompt", "session_id"?, "bean_alias_override"?, "attachment_ids"?, "request_id"?, "use_pantry"?}`. |
| `/v1/upload` | POST | Uploads a file/image attachment (multipart form: `request_id`, `file`) for inclusion in a subsequent `/v1/order` call. |
| `/v1/retry` | POST | Caller-reports a completed request's result as a failure, re-runs the escalation decision. Body: `{"request_id"}`. |
| `/v1/approve_escalation` | POST | Resolves a paused `escalation_pending` request. Body: `{"request_id", "approve"}`. |
| `/v1/sessions/{id}/pending_escalation` | GET | Reload-recovery: the same info `escalation_pending` carried, for a client that reloaded mid-pause. 404 if nothing is pending. |
| `/v1/cancel` | POST | Cancels an in-flight request. Body: `{"request_id"}`. |
| `/v1/rate` | POST | Records a `good`/`needed_fixing`/`failed` rating for a completed request. Body: `{"request_id", "rating"}`. Feeds the learning loop (see below). |
| `/v1/beans` | GET | Lists configured Beans (alias, role, availability) - never a raw model ID. |
| `/v1/pantry/file` | GET | Read-only file viewer for a Pantry citation chip. Query: `path`. Path-traversal safe, scoped to `knowledge/` only. |
| `/v1/preferences` | GET/POST | Device-wide UI preferences (e.g. the Coffee Counter scene's collapse state). |
| `/v1/sessions` | GET/POST | Lists or creates chat sessions. |
| `/v1/sessions/{id}/messages` | GET | Full message history for a session. |
| `/v1/sessions/{id}/memory_proposal` | POST | Drafts a guardrailed proposed diff to `brew-log/active_context.md`/`progress.md` from the session transcript. Never writes anything. |
| `/v1/memory_proposals/{id}/approve` | POST | Re-checks both guardrails against current on-disk content, then writes both files and logs one `task_type="memory"` Ledger row. |
| `/v1/memory_proposals/{id}/discard` | POST | Drops the proposal. Writes and logs nothing. |
| `/v1/policy/rebuild_preview` | POST | Computes a proposed `routing_policy.yaml` rebuild (Roastery evidence blended with real accumulated ratings) and returns a diff. Never writes anything. |
| `/v1/policy/rebuild_apply/{id}` | POST | Re-checks the on-disk file hasn't changed since preview, then writes the new policy and hot-swaps it into the running router - no restart needed. |
| `/v1/policy/rebuild_discard/{id}` | POST | Drops the proposal. Writes nothing. |

## Config

- `config/beans.yaml` - raw model ID to coffee alias mapping. Hand-edited.
- `config/routing_policy.yaml` - generated by `tools/generate_policy.py`
  from `roastery/tasting_notes.md` plus real `ledger/router_requests.csv`
  ratings (Brew 42). **Do not hand-edit.** Re-run the generator after new
  Roastery evidence lands, review the diff (`--dry-run`), then commit like
  any other generated artifact - or use the Coffee Counter Chat UI's
  Settings panel ("Rebuild House Blend") to preview and apply the same
  rebuild without leaving the browser.
- `config/settings.yaml` - thresholds, escalation cap, tick cadence, Pantry/
  memory-proposal/learning-loop tunables. Hand-edited.

## Data (gitignored, regenerable)

- `data/sessions.db` - chat session/message history (SQLite).
- `data/preferences.db` - device-wide UI preferences (SQLite).
- `data/pantry_index.db` - FTS5 Pantry search index. Rebuild with:
  ```powershell
  python router/tools/index_pantry.py
  ```

## Safety

- `OPENROUTER_API_KEY` is read from the environment only - never a request
  field, config value, or logged/emitted anywhere.
- Startup asserts none of the three config files contain a key-like string
  (reuses `tools/coffee_context_package.py`'s `SUSPICIOUS_PATTERNS`), and
  refuses to start if one is found.
- Raw OpenRouter model IDs appear in exactly three places: `config/beans.yaml`,
  `ledger/router_requests.csv` (for audit), and the outbound OpenRouter
  request body. Never in an SSE event or API response field - see
  `router/tests/test_events.py` and `router/tests/test_main.py`'s
  no-raw-model-id-leak tests.
- The only outbound host is the hardcoded OpenRouter base URL in
  `router/app/openrouter_client.py`.
- `GET /v1/pantry/file` resolves and confirms containment under `knowledge/`
  before ever reading a file - `..`, absolute paths, and symlink escapes are
  all rejected with a 404.
- Memory proposals may only ever touch `brew-log/active_context.md` and
  `brew-log/progress.md` (a literal two-file allowlist, not a prefix rule),
  and are refused if they would delete more than 50% of a file's existing
  content - both checks re-run at approval time, not just at generation
  time.
- No premium Bean has been selected or tested yet (`config/beans.yaml`'s
  `Reserve Blend` entry has `model_id: null`, unchanged since Brew 36).
  Escalation is structurally correct but inert until a human selects and
  Roastery-tests one.

## Learning loop (Brew 42)

`tools/generate_policy.py` blends two evidence sources when generating
`routing_policy.yaml`:

1. **Roastery Cup Test evidence** (`roastery/tasting_notes.md`'s score
   tables) - the original, always-on signal since Brew 36.
2. **Real accumulated `POST /v1/rate` outcomes** (`ledger/router_requests.csv`)
   - a `(task_type, bean_alias)` pair only influences ranking once it has
   at least `settings.min_rating_sample_size` (default 5) real ratings.
   Below that, ranking is exactly the Cup-Test-only behavior.

Task types whose real escalation rate exceeds `settings.escalation_rate_flag_threshold`
(default 0.3) are surfaced as advisory-only candidates in the rebuild diff -
this never changes routing automatically; a human decides what to do with
that information.

## Tests

```powershell
python -m unittest discover -s router\tests
```

or, as part of the full repository suite:

```powershell
python tools\run_all_tests.py
```

All OpenRouter calls in tests are mocked via `httpx.MockTransport` /
injected fake `stream_order_fn` values. No test in `router/tests/` makes a
live network call. Tests that touch memory proposals, Pantry indexing, or
policy rebuilds always point at temp/fixture paths (`memory_proposal_repo_root`,
`pantry_index_path`, `routing_policy_path`, `tasting_notes_path` on
`RouterState`) - never the real repo files.

## Non-goals

- No persistent job queue, retry-with-backoff scheduler, or multi-tenant
  auth - single-process, single-user, localhost-only.
- No changes to `roastery/openrouter_client.py` or the Cup Test runner -
  that client stays synchronous and non-streaming, built for one-shot
  Roastery comparisons; this router's client is async and streaming, built
  for interactive requests. They serve different purposes.
- No automatic "premium-first" routing based on escalation rate - advisory
  flagging only (see Learning loop above).
- No scheduled/automatic policy rebuilds or Pantry re-indexing - both are
  manual actions (a button click or a CLI run), matching this repo's "no
  new background infrastructure" discipline.
