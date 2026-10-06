# Coffee Core Router Design

Status: Brew 36A draft - Decaf plan, no code written
Date: 2026-07-09

## 0. Reading done before this plan

Read in full before drafting: `AGENTS.md`, `PROJECT_COFFEE.md`, `ROADMAP.md`,
`COFFEE_CONSTITUTION.md`, `GOVERNANCE_AND_SAFETY.md`,
`.cursor/rules/project-coffee-approval-gates.mdc`,
`.cursor/rules/project-coffee-spill-guard.mdc`,
`config/house_blend.md`, `docs/design/model-routing-policy.md`,
`docs/design/remote-call-approval-design.md`,
`roastery/openrouter_client.py`, `roastery/tests/test_openrouter_client.py`,
`roastery/scorecard-template.md`, `roastery/cup_tests/001-004`,
`roastery/model_scorecards/`, `ledger/cost_log.md`,
`tools/coffee_context_package.py`, `tools/coffee_approval_dry_run.py`,
`ui/coffee_counter_app.py` (routing/classification section).

`evals/` is an empty placeholder (`README.md` only, per Phase 1 Track B7).
All real Roastery evidence lives in `roastery/` and `ledger/`.

This is Brew 36 per `ROADMAP.md`'s "Next step": *"OpenRouter integration
behind explicit approval, if chosen."* This plan is the "if chosen" checkpoint.
No code has been written. This document and the event contract draft in
Section 4 are the only files this shot produces.

## 1. What already exists that this builds on

Project Coffee already has real prior art for every piece of this router.
Reusing it instead of re-deriving it is itself a Coffee Principle 9
(simplicity) requirement, not just convenience:

| Need | Existing prior art | How this plan uses it |
| --- | --- | --- |
| Request classification | `ui/coffee_counter_app.py:classify_request_for_routing()` - keyword-list classifier into `request_class` | Different purpose (UI routing-mode gate vs. Bean/task_type classification), but same style: a lookup table over keyword lists, not scattered `if`s. `router/app/classifier.py` follows the same shape for a different taxonomy. |
| Complexity vocabulary | `BARISTA_CHARTER.md` "Work modes": `Espresso Shot` (small, low-risk) and `Cold Brew` (long-running, higher-risk, needs checkpoints) | The user's requested `espresso_shot` / `cold_brew` complexity values are literally Project Coffee's own existing vocabulary. No new taxonomy invented. |
| Secret/key-pattern detection | `tools/coffee_context_package.py:SUSPICIOUS_PATTERNS` (OpenRouter/OpenAI/Google/GitHub/Bearer key-like regexes) and `redact_or_label_suspicious_text()` | Reused directly for the router's startup config scan (Requirement 7), not reimplemented. |
| Approval-state vocabulary | `docs/design/remote-call-approval-design.md` Section 5 (`approval_needed_not_requested`, `context_preview_ready`, `blocked_by_safety_gate`, `user_approved`, `sending`, `ledger_recorded`, ...) | The escalation approval gate (Requirement 5) reuses this state vocabulary rather than inventing a parallel one. `escalation_pending` / `escalating` map onto this existing state machine. |
| Ledger requirements list | `docs/design/remote-call-approval-design.md` Section 9 | Cross-checked against Requirement 6's row shape; used to fill gaps the user's list didn't mention (Safety Gate result, files-excluded count). |
| Non-streaming OpenRouter client | `roastery/openrouter_client.py` | Not reused directly - it is synchronous (`urllib`) and non-streaming, built for one-shot Roastery Cup Tests. The router needs an async, streaming client (SSE `generating` ticks). Both will exist; they serve different purposes and should not be merged. |
| Bean roles with real evidence | `config/house_blend.md`, `roastery/cup_tests/001-004`, `docs/design/model-routing-policy.md` | Directly seeds `beans.yaml` and is what `generate_policy.py` computes from. |

## 2. Adaptations to the requested target structure

The user's proposed structure is workable with three additions and one open
decision, listed here so nothing is silently changed without being said.

**Kept exactly as proposed:** `router/app/main.py`, `classifier.py`,
`routing.py`, `escalation.py`, `ledger.py`, `events.py`, `aliases.py`;
`config/beans.yaml`, `config/routing_policy.yaml`, `config/settings.yaml`;
`tools/generate_policy.py`; `router/tests/`.

**Placement:** `router/` stays top-level, a sibling of `roastery/`, `ui/`,
`tools/` - not nested under `apps/`. `apps/coffee-status` and
`apps/coffee-certification` are self-contained demo projects with their own
`brew-log/`, `knowledge/`, `ledger/`, `roastery/` mini-instances (the
onboarding template shape). The router is Coffee Core infrastructure
(`ARCHITECTURE.md` Layer 3), same category as `roastery/` and `ui/`, so it
belongs at the root next to them, not inside `apps/`.

**Addition 1 - `router/app/openrouter_client.py`.** The user's file list has
no dedicated OpenRouter client module. `generating` events need
token-by-token or chunk-by-chunk streaming from OpenRouter
(`"stream": true`), which requires an async HTTP client relaying Server-Sent
Events, not the one-shot request/response shape `roastery/openrouter_client.py`
uses. Folding this into `main.py` would break single-responsibility and make
`main.py` untestable without a live server. This module owns the async
`httpx.AsyncClient` call to OpenRouter and nothing else.

**Addition 2 - `router/app/config.py`.** `routing.py`, `escalation.py`,
`ledger.py`, `aliases.py`, and `main.py` all need `beans.yaml`,
`routing_policy.yaml`, and `settings.yaml` loaded once, validated, and
shared - not five independent YAML loaders. This module owns loading and
pydantic-validating all three config files at startup, including the
Requirement 7 key-scan assertion.

**Addition 3 - `router/requirements.txt` and `router/README.md`.** Every
other component in this repo (`apps/coffee-status/requirements.txt`,
`roastery/README.md`, `ui/README.md`, `tools/README.md`) documents its
dependencies and purpose this way. `router/requirements.txt` will list
`fastapi`, `uvicorn`, `pydantic`, `httpx`, `pyyaml` - **all five are already
installed in this environment** (checked directly: fastapi 0.136.3, uvicorn
0.32.1, pydantic 2.13.4 which pins `pydantic-settings` 2.14.2, httpx 0.28.1,
PyYAML 6.0.3). This shot will not run `pip install` anything. The
requirements file documents the dependency, matching the existing
`apps/coffee-status/requirements.txt` precedent - it does not trigger a new
install.

**Open decision - `router/tests/` and the test-discovery gate.** The gate
repair earlier this session (`tools/run_all_tests.py`) hardcodes exactly
four test roots: `tests/`, `roastery/tests/`, `apps/coffee-status/tests/`,
`apps/coffee-certification/tests/`. Adding `router/tests/` without updating
that list means `router/tests/` silently never runs under
`python tools\run_all_tests.py` - reintroducing the exact class of bug that
plan just fixed. **This plan proposes adding `router/tests/` as a fifth
entry in `tools/run_all_tests.py`'s `TEST_ROOTS` list as part of the
implementation shot.** This is a one-line, additive change to a file this
session already owns; flagging it now so it is not forgotten during
implementation.

## 3. Real gaps found in current Roastery/House Blend evidence

These are not blockers to writing the plan, but they are blockers to some
of Requirement 4 and 5 working with real (not invented) data. Surfacing them
now, per Constitution Article 6.4 ("never invent references to ... test
results") and Article 1.4 ("never represent unverified output as certain
fact").

1. **No premium Bean exists anywhere in this repo.** `config/house_blend.md`
   has a "Premium escalation" row that reads: *"Human-approved premium Bean
   only ... Premium Beans require explicit human approval before use."* No
   model ID has ever been chosen, tested, or scored for that role. Every
   Bean currently in House Blend and every Bean in the four Cup Test Orders
   is a `:free` tier model. **`generate_policy.py` cannot compute a real
   premium escalation target from Roastery evidence because none exists.**
   `beans.yaml` will carry a `premium` role entry with `model_id: null` and
   `status: not_yet_selected`. `escalation.py`'s cap-exceeded path
   (`escalation_pending`) will always require human approval when no
   premium Bean is configured - which, given no premium Bean exists yet, is
   currently *every* case where the cheap-Bean failure checks trip. This is
   not a shortfall in the design; it accurately reflects that Project
   Coffee has never run a premium-tier Roastery comparison. See Section 8,
   Question 1.

2. **Roastery coverage is thin and does not cover every `task_type` the
   classifier is asked to produce.** Real, scored evidence exists for
   exactly four Cup Test Orders (`001-decaf-repo-map`,
   `002-tiny-python-fix`, `003-docs-summary`, `004-pantry-assisted-answer`),
   each run against three Beans (Nemotron, Cohere, Poolside). That maps
   reasonably to `code` (Order 002), `doc` (Order 003), and
   `explain`/`analysis` (Orders 001, 004) - but there is **no Roastery
   evidence at all for `research` or `refactor`** as the user's classifier
   task-type list requests. Per `docs/design/model-routing-policy.md`'s own
   design ("If Roastery data is too thin for a task type, the policy marks
   it 'default'"), `generate_policy.py` will mark `research` and `refactor`
   as `"default"` policy entries pointing at the House Blend default Bean,
   not fabricate scores. This matches Requirement 4's own stated fallback
   behavior exactly - it is called out here so the resulting
   `routing_policy.yaml` is not mistaken for having more evidence than it
   does.

3. **No `coffee_ledger.csv` exists anywhere in this repository.** The
   existing Ledger is `ledger/cost_log.md`, a hand-maintained Markdown table
   with columns `Date | Task | Model / Bean | Task type | Est. tokens |
   Actual cost | Value notes` - one narrative row per Brew/Shot, not one row
   per request. `ledger/token_log.md` (fixed for trackability in the prior
   gate-repair session) is a similar narrative table. Neither has a
   `request_id`, `latency`, `escalated`, or `escalation_approved` column,
   and neither is designed for high-frequency machine-appended rows. See
   Section 6 for the proposed resolution.

## 4. Event contract draft

Full contract will live in `router/EVENT_CONTRACT.md` once implemented, with
one JSON example per event. Drafted here for approval before it is treated
as frozen.

### Shared base fields

Every event includes:

- `event`: literal event-name string (see below)
- `ts`: ISO-8601 UTC timestamp
- `request_id`: UUID4 string, stable for the lifetime of one `/v1/order` call

### Event sequence (per request)

```
order_received
  -> classifying
    -> route_selected
      -> generating (repeated, 0+ times, periodic ticks)
        -> [escalation_pending -> escalating]   (optional branch, see below)
      -> complete
  -> error      (may replace any step)
  -> cancelled  (may replace any step, client-initiated)
```

### Event field reference

| Event | Extra fields | Notes |
| --- | --- | --- |
| `order_received` | `prompt_chars: int` | No prompt text in the payload - length only, to keep raw request content out of the SSE stream/Ledger event trail by default. |
| `classifying` | *(none beyond base)* | Emitted the instant classification starts; no result yet. |
| `route_selected` | `bean_alias: str`, `task_type: str`, `complexity: "espresso_shot" \| "cold_brew"`, `est_cost_usd: float \| null`, `policy_entry: str` | `bean_alias` never a raw model ID (Requirement 2). `policy_entry` names which `routing_policy.yaml` row justified the route (Requirement 4's "must log which policy entry justified each route"), e.g. `"code/nvidia-nemotron-3-ultra"` or `"research/default"`. `est_cost_usd` is `null` when the Bean has no known per-token price in `beans.yaml`. |
| `generating` | `tokens_out: int`, `est_cost_usd: float \| null` | One tick per N tokens or per T seconds (configurable in `settings.yaml`, default: every 20 tokens or 2 seconds, whichever first). Cumulative counters, not deltas. |
| `escalation_pending` | `reason: "truncated" \| "empty" \| "refusal_shaped" \| "caller_reported"`, `est_cost_usd: float`, `premium_bean_alias: str \| null` | `premium_bean_alias` is `null` when no premium Bean is configured (Section 3, Gap 1) - in that case escalation cannot proceed even with approval, and `complete` will follow with `draft_quality: true` regardless of the approval response. |
| `escalating` | `bean_alias: str` | Only emitted after either auto-escalation (under cap) or an approved `/v1/approve_escalation`. |
| `complete` | `bean_alias: str`, `tokens_in: int`, `tokens_out: int`, `cost_usd: float \| null`, `latency_ms: int`, `escalated: bool`, `draft_quality: bool` | `draft_quality: true` exactly when escalation was declined or unavailable (Requirement 5). |
| `error` | `error_type: str`, `message: str`, `retryable: bool` | `message` is a safe, human-readable summary - never raw provider error bodies that might echo request content. |
| `cancelled` | `reason: "client_disconnect" \| "client_cancel_request"` | |

### Draft JSON examples

```json
{"event": "order_received", "ts": "2026-07-09T20:14:03.101Z", "request_id": "b3f1...", "prompt_chars": 812}
```

```json
{"event": "classifying", "ts": "2026-07-09T20:14:03.140Z", "request_id": "b3f1..."}
```

```json
{"event": "route_selected", "ts": "2026-07-09T20:14:03.210Z", "request_id": "b3f1...", "bean_alias": "House Blend", "task_type": "code", "complexity": "espresso_shot", "est_cost_usd": 0.0, "policy_entry": "code/nvidia-nemotron-3-ultra"}
```

```json
{"event": "generating", "ts": "2026-07-09T20:14:04.500Z", "request_id": "b3f1...", "tokens_out": 40, "est_cost_usd": 0.0}
```

```json
{"event": "escalation_pending", "ts": "2026-07-09T20:14:06.900Z", "request_id": "b3f1...", "reason": "truncated", "est_cost_usd": 0.42, "premium_bean_alias": null}
```

```json
{"event": "complete", "ts": "2026-07-09T20:14:07.050Z", "request_id": "b3f1...", "bean_alias": "House Blend", "tokens_in": 210, "tokens_out": 640, "cost_usd": 0.0, "latency_ms": 2940, "escalated": false, "draft_quality": true}
```

```json
{"event": "error", "ts": "2026-07-09T20:14:07.050Z", "request_id": "b3f1...", "error_type": "provider_timeout", "message": "OpenRouter did not respond within the configured timeout.", "retryable": true}
```

```json
{"event": "cancelled", "ts": "2026-07-09T20:14:05.000Z", "request_id": "b3f1...", "reason": "client_disconnect"}
```

**Frozen-contract note:** per the user's instruction, once this contract is
approved and `router/EVENT_CONTRACT.md` is written, downstream consumers
(UI, future animation) should be able to rely on it without renegotiation.
Any field addition after that point should be additive-only (new optional
fields), never a rename or removal, without a version bump.

## 5. Aliases (Requirement 2)

`config/beans.yaml` maps every raw OpenRouter model ID used today to a
coffee alias. Proposed initial mapping, seeded from `config/house_blend.md`'s
current roles - **names are a taste decision, not a technical one; treat as
provisional pending approval**:

| Role | Raw model ID | Proposed alias |
| --- | --- | --- |
| Default | `nvidia/nemotron-3-ultra-550b-a55b:free` | `House Blend` |
| Fallback | `cohere/north-mini-code:free` | `Second Pour` |
| Comparison / secondary fallback | `poolside/laguna-m.1:free` | `Guest Bean` |
| Premium (not yet selected) | `null` | `Reserve Blend` (placeholder alias only, no live route) |

Enforcement: `aliases.py` is the *only* module allowed to hold the
raw-ID-to-alias table. `events.py`'s pydantic models are typed so
`bean_alias` fields only ever accept values from that table (an `Enum` or a
runtime membership check, decided during implementation). The test suite
adds a dedicated test (per Requirement 2) that serializes one instance of
every event type to JSON and asserts none of the raw model ID strings from
`beans.yaml` appear anywhere in the output - this test doubles as a
regression guard if a new Bean is added later without updating aliasing
discipline.

Raw IDs are permitted in exactly three places: `beans.yaml` itself, Ledger
rows (for audit, per Requirement 6), and the outbound OpenRouter request
body built by `router/app/openrouter_client.py`.

## 6. Ledger (Requirement 6)

**Resolution to the "no CSV exists" gap (Section 3, Gap 3):** two Ledgers,
not one, matching a distinction the repo already makes elsewhere (narrative
human Ledger vs. structured machine evidence):

1. **`ledger/router_requests.csv`** (new file) - one row automatically
   appended per `/v1/order` request. Proposed header, matching Requirement
   6's field list plus the two additions `docs/design/remote-call-approval-design.md`
   Section 9 already calls for (Safety Gate result, files-excluded count -
   adapted here to "config scan result" since the router has no
   file-context package, unlike the UI's evidence-bundle flow):

   ```
   timestamp,request_id,task_type,bean_alias,raw_model_id,tokens_in,tokens_out,cost_usd,latency_ms,escalated,escalation_approved,rating
   ```

   `escalation_approved` is `true`, `false`, or the literal string `n/a`
   (no escalation occurred) - never blank, matching this repo's existing
   "say `unknown`, don't invent" discipline (`docs/design/remote-call-approval-design.md`
   Section 9: *"If token or cost data is unavailable, Ledger must say
   `unknown`, not invent values."*). `rating` stays empty for now exactly as
   the user specified - a future Brew can add a rating capture path.

2. **`ledger/cost_log.md`** (existing file, unchanged format) - gets exactly
   one new narrative row for the Brew 36 shot itself, matching every prior
   Brew's convention (see the 35 existing rows). It does not receive one row
   per HTTP request; that would break its existing one-row-per-Brew shape
   and make it unreadable.

No CSV header migration is needed since `router_requests.csv` is a new file,
not a rename of an existing one - Requirement 6's migration-with-backup
instruction does not apply here, but is preserved as the correct procedure
if a future Brew needs to change this header.

## 7. Safety (Requirement 7)

- API key: `OPENROUTER_API_KEY` read from `os.environ` only, exactly
  matching `roastery/openrouter_client.py`'s existing pattern. Never a
  request parameter, never a config file field, never logged, never placed
  in an SSE event.
- Startup assertion: `router/app/config.py`'s startup routine runs
  `tools.coffee_context_package.redact_or_label_suspicious_text()` (reused,
  not reimplemented per Section 1) against the raw text of `beans.yaml`,
  `routing_policy.yaml`, and `settings.yaml`. If any `SUSPICIOUS_PATTERNS`
  match is found, startup fails loudly before the FastAPI app accepts any
  connection - it does not redact-and-continue, because a key-like value in
  a *config file* (not a chat request) means a real key was probably pasted
  somewhere it should never be committed.
- Outbound calls: `router/app/openrouter_client.py` hardcodes the OpenRouter
  base URL as a module-level constant (matching
  `roastery/openrouter_client.py`'s `OPENROUTER_API_URL` constant) and makes
  no other outbound host reachable from router code.
- Spill Guard file additions: `.gitignore`, `.cursorignore`, and
  `.cursorindexingignore` all need a new pattern,
  `ledger/router_requests.csv`, added to the **existing** `**/*token*` /
  general Ledger carve-out logic only if the filename accidentally matches
  an existing broad pattern. Checked directly: `router_requests.csv` does
  not match any current pattern in any of the three ignore files (no
  `key`/`token`/`password`/`secret`/`credential`/`private` substring), so
  **no ignore-file change is needed for the Ledger file itself.** The one
  ignore-file addition this shot does need: `config/routing_policy.yaml` if
  it is decided to be a build artifact rather than committed (see Section 9,
  Question 3) - otherwise no Spill Guard changes are required at all for
  Brew 36.

## 8. Open questions requiring your decision before implementation

1. **No premium Bean is configured (Section 3, Gap 1).** Ship Brew 36B with
   escalation permanently gated on "no premium Bean available" (every
   cap-exceeded failure produces `escalation_pending` with
   `premium_bean_alias: null`, and approval - even if granted - cannot
   proceed, falling through to `draft_quality: true`), or pause Brew 36 to
   run a small premium-tier Roastery comparison first and pick one? This
   plan defaults to the former (ship with escalation structurally correct
   but inert) unless you say otherwise, since it matches "small verified
   steps" better than blocking Brew 36 on a separate Roastery shot.
2. **Alias names** (Section 5) are provisional. Confirm, or supply your own.
3. **Should `config/routing_policy.yaml` be committed to git, or generated
   fresh on every startup / added to `.gitignore`?** This plan proposes
   committing it (small, human-reviewable, same treatment as
   `config/house_blend.md`) so routing decisions are auditable in git
   history and reviewable in a diff before commit like everything else in
   this repo. Say if you'd rather it be gitignored and build-generated only.
4. **`generating` tick cadence** (every 20 tokens or 2 seconds, Section 4) -
   confirm or adjust.
5. **Confirm `router/` at repo root, not under `apps/`** (Section 2).

## 9. Files this plan will touch once approved (none touched yet)

CREATE only, no existing file modified except the two additions noted:

```
router/app/__init__.py
router/app/main.py
router/app/classifier.py
router/app/routing.py
router/app/escalation.py
router/app/ledger.py
router/app/events.py
router/app/aliases.py
router/app/openrouter_client.py
router/app/config.py
router/config/beans.yaml
router/config/routing_policy.yaml   (or config/routing_policy.yaml - see Q3; leaning config/ to match beans.yaml/settings.yaml sibling placement)
router/config/settings.yaml
router/tests/__init__.py            (only if needed for import resolution; default: omit, matching apps/*/tests/ convention)
router/tests/test_classifier.py
router/tests/test_routing.py
router/tests/test_escalation.py
router/tests/test_ledger.py
router/tests/test_events.py
router/tests/test_aliases.py
router/tests/test_openrouter_client.py
router/tests/test_main.py
router/EVENT_CONTRACT.md
router/README.md
router/requirements.txt
tools/generate_policy.py
tools/run_all_tests.py              (MODIFY - add router/tests/ as a fifth TEST_ROOTS entry)
ledger/router_requests.csv          (created empty with header row on first request, or pre-seeded with header only - decide in implementation)
ledger/cost_log.md                  (MODIFY - one narrative row for Brew 36, at closeout)
```

Note the `config/beans.yaml` vs `router/config/beans.yaml` placement is
still open (folded into Question 3/5) - the user's original request showed
`config/beans.yaml` at root, which would put it alongside the unrelated
`config/house_blend.md`; keeping router-specific config under
`router/config/` keeps the blast radius of "router changes" contained to
one directory tree, consistent with how `apps/coffee-status/` keeps its own
`ledger/`, `knowledge/`, etc. self-contained rather than reaching into root
`ledger/`, `knowledge/`. Recommend `router/config/`; say if you'd rather
root `config/`.

## 10. Non-goals for Brew 36

Matching this repo's established non-goals pattern (`docs/design/remote-call-approval-design.md`
Section 2):

- No UI wiring into Coffee Counter yet - this is the backend service only.
- No premium Bean selection/testing (separate Roastery shot if pursued).
- No persistent job queue, retry-with-backoff scheduler, or multi-tenant
  auth - single-process, single-user, localhost-only for this Brew.
- No committing or pushing by this assistant - matches every prior Brew.
- No `pip install` - all five dependencies already present (Section 2).
- No changes to `roastery/openrouter_client.py` or the existing Cup Test
  runner.

## 11. Workflow from here

1. You review this plan and the event contract draft, and answer Section 8.
2. On approval, implementation proceeds in small diffs (not committed
   automatically), running `python tools\run_all_tests.py` after each
   module lands.
3. Full test suite run, all mocked (`httpx.MockTransport`), no live network
   calls anywhere in `router/tests/`.
4. Demo: you set `OPENROUTER_API_KEY` in your own shell environment (never
   pasted into a file or chat); I start the router locally
   (`uvicorn router.app.main:app`) and issue one real `/v1/order` request,
   showing you the raw SSE stream.
5. `brew-log/active_context.md` and `brew-log/progress.md` updated;
   `roastery/tasting_notes.md` gets a Tasting Note for the live demo call
   (the first real remote Bean call this Ledger/Roastery pairing has ever
   recorded end-to-end through a router rather than the Cup Test runner).
6. Summary: files changed, tests added/passing, risks, rollback.
