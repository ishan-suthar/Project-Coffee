# Coffee Core Router

## Quick start

From the repository root, with `OPENROUTER_API_KEY` already set in your
shell (see "Environment variables" below):

```powershell
.\start.ps1
```

For LAN access from another device, pass your machine's LAN IP:

```powershell
.\start.ps1 -LanIp 192.168.1.50
```

This starts both the router and the frontend (each in its own window) and
stops both cleanly on Ctrl+C. If something gets orphaned anyway, `.\stop.ps1`
force-stops whatever is listening on ports 8765/3000. See "Run" below for
the manual two-command version, and "LAN access" for what `-LanIp` sets up
under the hood.

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
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of origins the router's CORS middleware accepts, e.g. `http://localhost:3000,http://192.168.1.42:3000`. Defaults to `http://localhost:3000` (today's single-origin behavior) when unset - see "LAN access" below. |
| `NEXT_PUBLIC_ROUTER_URL` | Read by the frontend (`web/`), not the router itself - see `web/README.md`. |

## LAN access (using the app from another device)

By default, the router only accepts requests from `http://localhost:3000`
(the frontend's dev-server origin) and the frontend only talks to
`http://127.0.0.1:8765` (the router's default port, on the same machine).
To use the app from a second device on the same LAN (a phone, another
laptop), both sides need to be told about each other's real addresses -
neither `localhost` nor `127.0.0.1` mean anything from a different machine.

1. Find the router machine's LAN IP (PowerShell, on the machine running
   the router):

   ```powershell
   ipconfig | findstr /i "IPv4"
   ```

   Say this prints `192.168.1.42`.

2. Start the router allowing the frontend's real LAN origin:

   ```powershell
   $env:CORS_ALLOWED_ORIGINS = "http://localhost:3000,http://192.168.1.42:3000"
   python -m uvicorn router.app.main:app --host 0.0.0.0 --port 8765
   ```

   `--host 0.0.0.0` is required too - `uvicorn`'s own default (`127.0.0.1`)
   only accepts connections from the same machine, independent of CORS.

3. Start the frontend pointed at the router's real LAN address (see
   `web/README.md`'s "LAN access" section for the frontend-side details):

   ```powershell
   cd web
   $env:NEXT_PUBLIC_ROUTER_URL = "http://192.168.1.42:8765"
   npm run dev -- -H 0.0.0.0
   ```

4. On the other device, browse to `http://192.168.1.42:3000`.

### Windows firewall

Windows Defender Firewall blocks unsolicited inbound connections to both
ports by default the first time each is bound - a firewall prompt usually
appears when you start `uvicorn`/`next dev` with `--host 0.0.0.0`, and
allowing it there is enough. If the prompt doesn't appear (or was
previously dismissed), add the rules explicitly from an elevated
PowerShell prompt:

```powershell
New-NetFirewallRule -DisplayName "Coffee Core Router (LAN)" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow
New-NetFirewallRule -DisplayName "Coffee Counter Chat UI (LAN)" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow
```

Scope these to your LAN profile if prompted (Private network), not Public
- these rules open the ports to anything that can reach this machine on
the allowed network profile, which is appropriate for a home LAN but not
a coffee shop Wi-Fi. Remove them (`Remove-NetFirewallRule -DisplayName
"..."`) when you no longer need LAN access.

This setup has no authentication hardening beyond what already exists
(`/v1/login` + bearer tokens) - anyone who can reach both ports on your
LAN can use the app as any account they can authenticate as. Fine for a
trusted home network; do not expose these ports beyond your LAN (no
router port-forwarding, no public IP binding).

## Endpoints

All request/response bodies are JSON unless noted. `POST /v1/order` and
`POST /v1/retry` stream the SSE event contract documented in
`router/EVENT_CONTRACT.md`; every other endpoint is a plain request/response.

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/v1/order` | POST | Streams the full event contract for one prompt. Body: `{"prompt", "session_id"?, "bean_alias_override"?, "attachment_ids"?, "request_id"?, "use_pantry"?}`. |
| `/v1/chat/completions` | POST | OpenAI-compatible endpoint (Brew 47) - point Cursor, Continue.dev, Aider, or the OpenAI SDK at this router. See "OpenAI-compatible endpoint" below. |
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

## OpenAI-compatible endpoint (Brew 47)

`POST /v1/chat/completions` accepts the standard OpenAI chat-completions
shape (`model`, `messages`, `stream`, `temperature`, `max_tokens`, `tools`,
`tool_choice`) so any tool that lets you point at a custom base URL can
route through Coffee - classification, routing, escalation, and the
Ledger all apply exactly as they do for `/v1/order`. It is **stateless**
with respect to Coffee's session store: the client's `messages` array is
used as-is, no session row is created, and Brew 46's `remember_chat`
toggle does not apply here (the client already carries its own history
every turn). See `docs/design/openai-compat-endpoint-design.md` for the
full design.

A few things behave differently from a real OpenAI/OpenRouter endpoint,
worth knowing before you point a tool at this:

- The `model` field is ignored for routing unless it exactly matches a
  Bean alias (e.g. `"Reserve Blend"`) - Coffee always classifies and
  routes the request itself otherwise. The response's `model` field is
  always the Bean alias actually used, never a raw model id.
- An over-the-cost-cap escalation cannot pause for your approval here
  (there's no UI to render the approval card in) - it's declined
  immediately and the draft is returned, with `system_fingerprint` set to
  `"draft_quality"` on the final chunk. Check the Ledger's
  `over_cap_declined` column to audit these after the fact.
- `tools`/`tool_calls` are relayed to/from OpenRouter unchanged - Coffee
  never interprets them. Not every Bean has verified tool-calling support
  (`config/beans.yaml`'s `capabilities.tool_calling` flag); a warning is
  logged (not blocked) when `tools` is sent to a Bean without it.

### Getting a token

Same Bearer token as every other endpoint - log in and use the token as
the "API key":

```powershell
curl -s -X POST http://localhost:8765/v1/login `
  -H "Content-Type: application/json" `
  -d '{"username": "<your-username>", "password": "<your-password>"}'
```

The response's `token` field is what you paste below. (Users are created
via `router/tools/manage_users.py`, not a signup endpoint - see that
module.)

### Cursor

Settings -> Models -> "OpenAI API Key" -> paste the token from above.
Set the Base URL to `http://localhost:8765/v1`. Any model name works in
Cursor's model picker - it's ignored for routing unless it's a real Bean
alias (see above).

### Continue.dev

In `config.yaml`:

```yaml
models:
  - name: Coffee
    provider: openai
    model: House Blend  # or any string - ignored unless it's a real Bean alias
    apiBase: http://localhost:8765/v1
    apiKey: <the token from POST /v1/login>
```

### Retry detection (always on, no setting)

Every `/v1/chat/completions` request whose last message exactly matches a
prior *completed* request from the same user/client within
`retry_detection_window_seconds` (default 300s) is flagged as a probable
retry - the closest thing to a thumbs-down this endpoint will ever get,
since there's no rating button in Cursor. The Ledger's `retry_of` column
points at the original; the original's `retry_count` is incremented for
real. Two requests fired at the same instant with identical content are
correctly treated as parallelism, not a retry - matching only happens
against an *already-completed* original.

### Shadow mode

Off by default (`shadow_mode_enabled: false` in `config/settings.yaml`).
When on, a sampled fraction (`shadow_mode_sample_rate`, default 0.1) of
`/v1/chat/completions` requests that routed to a non-premium Bean also
run silently, in the background, against the premium Bean - after the
client already has its answer, never delaying or affecting it. This is
API-only - `/v1/order` is never shadow-sampled, since the Coffee Counter
chat UI already has rating buttons, a strictly better signal than a
silent shadow pair.

**What it costs**: a sampled request is billed twice - once for the real
answer, once for the shadow comparison. `shadow_mode_daily_cost_cap_usd`
(default $1.00) caps real daily shadow spend (computed from the Ledger's
own `cost_usd` column on `is_shadow=true` rows); once the cap is hit,
sampling is skipped for the rest of the day and logged - it never fails
a real request.

**How to enable**: set `shadow_mode_enabled: true` in
`config/settings.yaml` (or override `Settings` directly if you're running
tests/scripts) and restart the router.

**How to read the pairs**: both responses are stored, never scored or
diffed automatically - that's a deliberate later decision, not built
this Brew. Query `router/data/sessions.db` directly:

```powershell
sqlite3 router/data/sessions.db "SELECT request_id, response_text, shadow_response_text, shadow_bean_alias FROM api_requests WHERE shadow_response_text IS NOT NULL;"
```

Or run `python -m tools.ledger_summary --mode model-usage`, which prints a
shadow-mode section (pair count, total shadow spend) pointing you at the
same query whenever real shadow data exists for the period.

### Pruning old request records

`router/data/sessions.db`'s `api_requests` table (retry-matching lookups
and shadow-mode response pairs) has no automatic deletion, on purpose -
the alternative is discovering your only evidence is gone the day you
actually want to analyze it. Prune manually, deliberately:

```powershell
python router/tools/prune_api_requests.py --older-than 90d
```

`--older-than` accepts a number followed by `d` (days), `h` (hours), or
`m` (minutes) - e.g. `90d`, `24h`, `30m`. Required, no default.

### Real-usage analysis

```powershell
python -m tools.ledger_summary --mode model-usage
```

Answers "what fraction of my coding tasks actually needed a premium
model?" from real `ledger/router_requests.csv` data - request volume and
cost, Bean distribution, escalation/over-cap-decline/retry rates, and
counterfactual "if every request had gone to the premium Bean" cost,
sliced by `task_type` and `client_source`. Always ends with a "what this
cannot tell you" footer naming its own blind spots (retry rate is a weak
proxy, not a measurement; `over_cap_declined` is unreliable before Brew
47; shadow mode being off means zero premium comparison exists). The
existing `--mode cost-log` (default) behavior - the hand-maintained
`ledger/cost_log.md` summary - is unchanged.

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

## Spend caps

**These caps are the only thing standing between a LAN user and your
OpenRouter balance.** Every request that spends real money - `/v1/order`,
`/v1/chat/completions`, and memory proposal generation - is gated by three
settings in `config/settings.yaml`, checked *before* the OpenRouter call:

| Setting | Default | What it does |
| --- | --- | --- |
| `per_user_daily_cost_cap_usd` | `1.00` | Per user, rolling UTC calendar day. Sums real `cost_usd` from `ledger/router_requests.csv` for that user's rows today (shadow rows included - they're real money, attributed to whoever's request triggered them), plus a real pre-call estimate for the incoming request. Overridable per user - see below. |
| `global_daily_cost_cap_usd` | `5.00` | Same UTC-day window, summed across every user - a backstop in case a user is added faster than a cap is set for them. |
| `per_user_requests_per_minute` | `20` | A sanity limit against a runaway loop or a tight client retry cycle - not a cost control, tracked and enforced independently of the two caps above. |

A per-user override lives on the `users` table (`daily_cost_cap_usd`,
nullable - `NULL` means "use the settings.yaml default"), set via:

```powershell
python router/tools/manage_users.py set-cap <username> 2.50
python router/tools/manage_users.py set-cap <username> clear   # back to the default
```

**Why UTC, not local time**: every timestamp this router already writes
(Ledger rows, shadow-mode's own daily cap) is UTC, and a household has no
single "local" time zone once more than one member is in a different one -
local time would just move the ambiguity, not resolve it.

**The estimate**: a cap that only counts money already spent will always
allow one more request, and that request could be enormous - so the check
also prices the *incoming* request before it starts, via
`router.app.routing.estimate_cost_usd()` (the same real estimator that now
also backs `escalation_cost_cap_usd` - see below). It uses the client's own
`max_tokens` when given (Cursor usually sends one, and it's strictly better
information than a guess), else `spend_cap_assumed_output_tokens` (default
`1000`) - deliberately an overestimate, not an underestimate, since the
safe failure direction for a cap is refusing a request that would have fit,
never admitting one that doesn't. A genuinely unknown estimate (should be
impossible for an active Bean - see the startup pricing assertion below) is
refused, never treated as free.

**What each client sees on a refusal**:
- `/v1/order`: an `error` SSE event (`error_type: "spend_cap_exceeded"` or
  `"rate_limit_exceeded"`), `retryable: false` for the spend cap, `true` for
  the rate limit - this is the only error mechanism this endpoint has ever
  had, so a cap refusal follows the exact same shape as any other
  `/v1/order` failure. The chat UI renders it in the response area.
- `/v1/chat/completions`: a real HTTP `429` with an OpenAI-compatible error
  body (`error.type`/`error.code`) and a `Retry-After` header pointing at
  the UTC reset time (or a fixed 60s for the rate limit) - checked before
  either response mode commits to anything, so a denial is a plain JSON
  response even when the client asked for `stream: true`; the stream never
  starts. Cursor and the OpenAI SDK both understand a `429` as a quota
  problem.

**A second-order spend**: an auto-escalation to the premium Bean is a
*second* real OpenRouter call after the draft already succeeded. If the
escalation-stage estimate would exceed the cap, the request does not error
out - it falls back to the already-generated draft (`draft_quality: true`),
since that draft is a valid, already-paid-for answer and discarding it
would waste money already spent for nothing.

**`escalation_cost_cap_usd` is live for the first time.** The pre-call
estimator this Brew introduced also replaced the old placeholder that
`escalation_cost_cap_usd` (and the Brew 40 approval-card gate) depended on -
previously it always evaluated to `$0.00`, so every eligible failure
auto-escalated regardless of the configured cap, and the approval card
never actually fired from a real cost decision. It is real now. At typical
premium-Bean pricing a single escalation is a cent or two, so the `$0.50`
default will rarely trip in practice - real numbers from live use should
inform whether that default is still the right one, but it is unchanged in
this Brew.

**Visibility**:
- The Coffee Counter chat UI's Tips Jar area shows today's spend against
  your cap (`$0.34 of $1.00 today`), turning amber at 80% and red at the
  cap - fed by `GET /v1/usage`, never computed client-side.
- `GET /v1/usage` returns the current user's `today_spend_usd`, `cap_usd`,
  and `reset_at` (next UTC midnight).
- Every refusal is logged (`spend_cap_refused`/`spend_cap_refused_escalation`/
  `rate_limit_refused`, with the user, cap type, and the attempted
  request's estimate) - a refusal you can't see is a support call you can't
  answer.

**What this is not**: no billing, no per-user credit purchase, no monthly
quotas, no admin dashboard. This is a household of five people, not a
SaaS - the settings file plus a CLI override column is the right amount of
machinery.

## Web search

**The real cost of this feature is bigger than the per-search fee: no
free Bean supports tool calling, so turning on web search always leaves the
free tier.** House Blend, Second Pour, and Guest Bean all have
`capabilities.tool_calling: false` in `config/beans.yaml` - a web request
always routes to a paid Bean.

**How to use it**: `/v1/order` has a per-request `use_web` toggle (the chat
UI's "Use Web" checkbox, mirroring the existing "Use Pantry" toggle) - not a
session-wide setting. `/v1/chat/completions` has no `use_web` field; a
client's own `tools` array (Cursor's function-calling loop) is unrelated to
Coffee-side search, but sending any `tools` still requires a Bean that can
actually call them.

**Mechanism**: a `use_web` request sends a single
`{"type": "openrouter:web_search", "parameters": {"engine": ...}}` tool
entry. This replaced the older `plugins: [{"id": "web"}]` mechanism (an
early cost-optimization pass found that syntax is now deprecated by
OpenRouter, confirmed against its live docs) - only the `tools`-array form
exposes an `engine`, which is the whole reason this section exists.
Coffee never inspects or reinterprets the search results; they arrive as
part of the assistant turn's content, same as any other model output.
`/v1/chat/completions` never sends this tool - only `/v1/order` has the
toggle.

**Engine (`web_search_engine` in `settings.yaml`, default `"parallel"`)**:
OpenRouter bills web search per-engine, independent of which Bean makes the
call:

| Engine | Cost | Notes |
| --- | --- | --- |
| `"parallel"` (default here) | $0.001/request | Up to 10 results, then $0.001/extra result. |
| `"exa"` | $0.005/request | Up to 10 results, then $0.001/extra result. |
| `"auto"` (OpenRouter's own default when unset) | Provider-native when the Bean supports it, else Exa | On a Claude Bean this bills at Anthropic's own native web-search rate (~$0.01/request) - the accidental default before this setting existed. |

Change it with no code edit - just hand-edit `settings.yaml`.

**Bean selection**: `BeanRegistry.capable_bean(tool_calling=True)` picks the
**cheapest** available tool-calling-capable Bean by `beans.yaml` pricing,
with one named, opt-in exception (see below) - never `role="default"` (not
capable anyway) and never a fixed premium/specialist role. If the policy- or
manually-selected Bean isn't capable, routing escalates to it exactly like
the existing vision constraint does (`constraint_reason` explains why); if
no Bean is configured with `tool_calling: true` at all, the request is
refused (`no_web_search_bean_available`), never silently downgraded to a
plain, non-searching answer.

**Web-search Beans, cheapest-optimization pass**: a later cost-optimization
pass verified real OpenRouter pricing for Kimi K2 (`moonshotai/kimi-k2`,
$0.00057/$0.0023 per 1k) and DeepSeek V3.2 (`deepseek/deepseek-v3.2`,
$0.000269/$0.0004 per 1k) directly against `GET /v1/models` before adding
them - the names first proposed (`moonshotai/kimi-2`,
`deepseek/deepseek-chat-v3.2`) turned out not to exist, the same lesson a
prior pass learned the hard way with a dead Single Origin model id. DeepSeek
V3.2 is the *cheapest* capable Bean combined (~$0.000669/1k, beating Kimi
K2's ~$0.00287/1k and Single Origin's ~$0.006/1k) - but Kimi K2 is
purpose-tuned for agentic tool use, so `settings.yaml`'s
`preferred_web_search_bean_alias` (default `"Kimi K2"`) makes
`capable_bean()` return it outright, no price comparison, whenever it's a
qualifying candidate. This is a narrow, explicit, single-call-site override
(`capable_bean(prefer_alias=...)`) - every other caller (vision routing,
`/v1/chat/completions`'s own tool-calling constraint) still gets pure
cheapest-price selection, unaffected. If Kimi K2 is ever removed or made
unavailable, `capable_bean()` falls through to plain cheapest-price
selection among the rest - DeepSeek V3.2 becomes the real fallback then, not
a decorative second entry.

**Data governance note**: Kimi K2 (Moonshot AI) and DeepSeek V3.2 (DeepSeek)
are both Chinese-hosted models. Accepted for this personal-use instance only
- see the matching Tasting Note entry. Reconsider before ever routing real
work data through either.

**Classifier**: `use_web` never influences `task_type` - that would corrupt
`ledger_summary`'s task-type slicing and mislabel, say, a coding question
with search turned on. It only feeds one new `COMPLEXITY_SIGNALS` entry
(injected search results are real extra context to reason over), same
"simple and predictable, no size table" precedent as the existing
`has_attachments` signal.

**Cost**: `web_search_cost_usd` is a **breakdown** of `cost_usd`
(`resolve_cost()`'s total), never an addend, per the cost contract in
`app/ledger.py`'s module docstring - a Tips Jar or cost pill still sums
`cost_usd` alone. It's computed as `cost_usd` minus pure token cost, and
only when `cost_source == "reported"` (a real all-in total from OpenRouter
to subtract from); when the cost is `"computed"` (no reported total),
there's nothing to isolate a fee from, so this column stays genuinely
unknown rather than a guess. **Spend caps already count the search fee** -
`check_spend_cap()`/`today_spend_usd()` sum `cost_usd` alone, and a web
request's `cost_usd` is the reported total (fee included), so this needed
no code changes, only verification.

**Escalation**: `use_web` carries through an auto-escalation re-run, but
only when the premium Bean is also tool-calling capable - otherwise it's
dropped for that one re-run (logged as a warning) rather than hard-failing
an escalation that would otherwise still produce a valid, non-web answer.

**Citations**: OpenRouter's web search tool cites its sources as whole
`url_citation` annotation objects on the streamed delta - accumulated
across the response and surfaced once, deduplicated by URL, via
`complete.web_sources` (`{url, title}` only, contract v1.6). The chat UI
renders these as clickable "Web Source" chips (`WebSourceChips.tsx`,
crema-amber accent), visually distinct from Pantry's caramel citation
chips - each links out to the real source rather than opening an in-app
viewer. `null` when `use_web` was false or nothing was cited, same "never
an empty-but-claimed list" convention `pantry_sources` established. This
closed a real gap: the parser (`_parse_sse_line()`) never extracted
`delta.annotations` until this fix, so every earlier web search response's
structured citations were silently dropped even though search itself
worked - only inline markdown links the model happened to write into its
own prose were ever visible.

**What this is not**: no search-result caching, no per-request tuning
knobs (result count, freshness, allowed domains) - `settings.yaml`'s
`web_search_engine` is the one exposed knob, revisited if real usage shows
a need for more.

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
