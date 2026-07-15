# Learning Loop and Release Pass Design (Brew 42)

Status: Decaf plan - no code written
Date: 2026-07-14

## 0. Reading done before this plan

Read in full: `tools/generate_policy.py`, `router/app/routing.py`,
`router/app/ledger.py`, `router/app/config.py`, `router/config/settings.yaml`,
`router/config/routing_policy.yaml` (generated), `router/README.md`,
`web/README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `tools/run_all_tests.py`,
`web/scripts/checkAssetBudget.mjs`, `roastery/tasting_notes.md` (Recording
Rules + recent entries), `roastery/cup_tests/002-tiny-python-fix.md`,
`router/config/beans.yaml`, `ledger/router_requests.csv` (real data), and
`web/src/components/` directory listing. Also ran (read-only, no files
changed): `python tools/run_all_tests.py` (full repo suite) and
`node scripts/checkAssetBudget.mjs` (current asset total) to ground this
plan in real current numbers rather than assumed ones.

## 1. What already exists - do not rebuild

- `tools/generate_policy.py` already builds `router/config/routing_policy.yaml`
  from `roastery/tasting_notes.md`'s per-task Cup Test score tables
  (`parse_tasting_notes()`, `build_policy()`, `_rank_beans()`) - ranks Beans
  by avg Cup Test score (0-10), tied-broken by avg tokens. This is the
  function the ratings-weighting work extends, not replaces.
- `router/app/ledger.py`'s `LedgerRow.rating` column and
  `RouterLedger.update_rating()` (rewrite-whole-file, since CSV has no
  in-place update) already exist, wired to `POST /v1/rate` in `main.py`
  with `VALID_RATINGS = {"good", "needed_fixing", "failed"}`. Nothing new
  needed to *capture* a rating - it already happens on every real
  `POST /v1/rate` call.
- `RouterState` is a plain mutable `@dataclass` (not frozen) whose fields
  are already mutated in place by other endpoints (e.g.
  `state.memory_proposals.pop(...)`, `state.uploads[...] = ...`) - hot-
  swapping `state.routing_policy` to a freshly built `RoutingPolicy`
  instance at runtime, with no router restart, is a direct, low-risk
  consequence of this existing pattern, not a new capability to invent.
- The memory-proposal generate/approve/discard shape (Brew 41,
  `router/app/memory_proposals.py`) is a proven, tested pattern for
  "compute a proposed change, let a human review a diff, apply only on
  an explicit approve call, re-check staleness at apply time" - the
  "Rebuild House Blend" feature reuses this shape directly rather than
  inventing a new one.
- `tools/run_all_tests.py` (added in the "Gate repair" work referenced in
  `brew-log/progress.md`) already fixes the root `python -m unittest
  discover` collection bug (hyphenated `apps/coffee-status`,
  `apps/coffee-certification` directories break dotted-module discovery).
  Ran it just now: **560 tests collected across 5 roots, 0 failures**
  (308 of those in `router/tests/`). This is the real current baseline,
  not an assumption.
- `web/scripts/checkAssetBudget.mjs` already enforces and reports the
  300 KB Coffee Counter scene asset budget on `prebuild`/`pretest`. Ran
  it just now: **11.8 KB / 300 KB** (no real `.riv` file has been dropped
  in yet - unchanged since Brew 39/40).
- `roastery/cup_tests/002-tiny-python-fix.md` is a real, already-designed,
  reusable "one identical real task" prompt with existing Success
  Criteria - the two-Bean Tasting Note comparison (Requirement 8) reuses
  this verbatim rather than inventing a new task.

## 2. Real gaps found - surfaced now, not worked around silently

1. **Every rating cell in the real `ledger/router_requests.csv` is empty
   today.** `POST /v1/rate` and `update_rating()` both work correctly,
   but no real session has ever actually clicked a rating button - real
   accumulated rating data is currently zero rows for every
   `(task_type, bean_alias)` pair. With the requested minimum-sample
   threshold of 5, **the new ratings-weighting logic will not change a
   single real routing decision today** - every task_type will fall
   through to the unweighted Cup-Test-only path, exactly as now. This is
   expected and correct behavior, not a bug to work around; it is stated
   here so the live demo's "before/after diff" for Requirement 2 is
   understood in advance to show **no change** for the real repo (the
   diff mechanism itself still needs to be proven correct against a
   synthetic/scratch Ledger with enough ratings to cross the threshold).
2. **Every real Bean is free-tier (`price_per_1k_*_usd: 0.0`).** The
   existing `_rank_beans()` docstring already documents that
   "quality-per-dollar collapses to quality-per-token" for this reason
   (Brew 36 finding, still true). Requirement 1 asks for "quality-per-
   dollar" weighting; this plan keeps the existing avg-tokens tie-break
   as the token/dollar proxy and does not invent a new per-dollar metric
   that has nothing real to divide by yet - flagged as Question 1 below.
3. **No available premium Bean exists** (`Reserve Blend`'s `model_id` is
   `null`, unchanged since Brew 36). Real `escalated=True` Ledger rows
   can only happen when a real escalation runs, which requires an
   available premium Bean. **The real Ledger's `escalated` column is
   `False` in every row today**, so Requirement 3's "flag task types with
   escalation rate above a threshold" will also find nothing to flag
   against real data right now - same class of "mechanism proven,
   nothing to trigger it yet" gap as #1.
4. **`tools/generate_policy.py` has zero test coverage today** - confirmed
   by grep, not assumed. This plan adds tests for the new ratings/
   escalation-flag logic, and does not silently leave the whole module
   untested going forward.
5. **No settings/admin UI area exists in `web/` at all** - confirmed via
   directory listing (`CommandPalette`, `CounterDisplay`, `MemoryProposal`,
   `OrderBox`, `ResponseSection`, `Sidebar`, nothing settings-shaped).
   Requirement 2's "settings area" needs a new UI surface, not an
   extension of something that already exists - flagged as Question 2.
6. **`router/README.md` is Brew 36-era** - documents only 3 endpoints
   (`/v1/order`, `/v1/retry`, `/v1/approve_escalation`) and predates
   sessions, uploads, escalation approval gate, Pantry retrieval, and
   memory proposals entirely (the router now has 20 endpoints). `web/README.md`
   is still the unedited `create-next-app` boilerplate - never customized
   at all. Requirement 6 is a real rewrite of both, not a light edit.
7. **`ARCHITECTURE.md`'s "Coffee Counter" and the shipped `web/`
   "Coffee Counter Chat UI" are two different things sharing one name.**
   `ARCHITECTURE.md` (v0.1 Phase 0 Draft, dated 2026-07-02, predates
   `router/`/`web/` entirely) uses "Coffee Counter" for the *IDE/editor*
   layer (Cursor). The Next.js app built in Brews 37-41 is also called
   "Coffee Counter Chat UI" / "the animated Coffee Counter scene" -
   genuinely unrelated to the editor-layer meaning. This is a real
   naming collision, not just staleness, and the doc sweep (Requirement
   7) needs to disambiguate it explicitly rather than silently picking
   one meaning.
8. **`ROADMAP.md`'s "Current status" table and Brew history table both
   stop at Brew 36** ("Recommended next, if chosen | TBD") - six shipped
   Brews (36-41) were never recorded here, even though `brew-log/progress.md`
   stayed current for all of them. This mirrors a pattern already found
   and fixed in `brew-log/active_context.md`/`progress.md` during Brew 41
   (their top summary lines were stale at "Brew 35" while the dated
   tables underneath stayed current) - `ROADMAP.md` has the same
   two-tier staleness, just never caught until now.
9. **Next.js's Turbopack build output in this version does not print a
   per-route First Load JS size table** the way older Next.js builds did
   - confirmed by actually running `npx next build` just now. A real
   "bundle size report" (Requirement 4) needs a small supplementary step
   (summing real shipped `.next/static/chunks/*.js` bytes, excluding
   source maps) rather than assuming `next build`'s own output covers it.

## 3. Learning loop (Requirements 1-3)

### 3.1 Ratings-weighted policy generation (Requirement 1)

Extend `tools/generate_policy.py`'s `build_policy()` (not replace it) with
an optional ratings input:

1. New pure function `load_rating_evidence(ledger_rows) -> Dict[(task_type, bean_alias), RatingEvidence]`
   grouping real `ledger/router_requests.csv` rows by `(task_type, bean_alias)`,
   counting non-empty `rating` cells, and averaging a documented numeric
   mapping: **`good` = 1.0, `needed_fixing` = 0.5, `failed` = 0.0** (a
   judgment call, stated plainly here rather than buried in code - this
   is the same 0-1 "how good was this response" scale the existing
   `draft_quality` boolean already gestures at, just continuous instead
   of binary).
2. A `(task_type, bean_alias)` pair only contributes a rating signal once
   its row count reaches `settings.min_rating_sample_size` (new setting,
   **default 5**, per your instruction) - below threshold, that pair is
   treated exactly as if it had zero ratings (falls through to the
   existing Cup-Test-only ranking, unchanged).
3. `_rank_beans()` gains a `combined_score` when a rating signal clears
   the threshold: `combined_score = (cup_test_avg_score / 10) * roastery_weight + avg_rating * rating_weight`,
   where `roastery_weight + rating_weight == 1.0` (new settings,
   recommend **0.6 / 0.4** - Roastery Cup Test evidence stays the primary
   signal since it is structured/reviewed, real-world ratings are a
   corroborating signal, not a replacement, until much more accumulates -
   Question 3 below asks you to confirm or adjust this split). Below
   threshold, `combined_score` is just `cup_test_avg_score / 10` (today's
   behavior, unchanged). Tie-break stays avg-tokens ascending exactly as
   now - Gap 2 above explains why a real per-dollar metric isn't possible
   yet.
4. Each policy entry's `reason` string gains a clause when ratings
   actually influenced ranking: e.g. `"; N real rating(s) (avg X.XX)
   confirmed/shifted this ranking"` vs. the unweighted case's existing
   reason text, unchanged. This is what makes Requirement 2's diff view
   meaningful - a human reading the diff sees *why* something changed,
   not just that it changed.
5. `tools/generate_policy.py`'s CLI keeps working standalone exactly as
   documented in `router/README.md` today - a new `--ledger` flag
   (default `ledger/router_requests.csv`) and `--min-rating-sample-size`/
   `--roastery-weight` overrides, all optional with the settings.yaml-
   matching defaults baked in, so `python tools/generate_policy.py` with
   no flags behaves identically to before for anyone running it by hand.

### 3.2 "Rebuild House Blend" UI action (Requirement 2)

Reuses the Brew 41 memory-proposal generate/approve shape directly:

1. New `POST /v1/policy/rebuild_preview` - calls the extended
   `build_policy()` in-process (imported from `tools/generate_policy.py`,
   not shelled out to) against the *real* `roastery/tasting_notes.md`,
   `beans.yaml`, and `ledger/router_requests.csv`, computes a unified
   diff (stdlib `difflib`, same precedent as Brew 41's memory-proposal
   diffs - no new dependency) between the current on-disk
   `routing_policy.yaml` and the freshly computed one, and returns
   `{proposal_id, diff, new_policy_yaml, escalation_candidates}` (the
   last field is Requirement 3 - see 3.3). Stored server-side in
   `RouterState.policy_rebuild_proposals: Dict[str, PolicyRebuildProposal]`,
   same in-memory/no-TTL-sweep precedent as `memory_proposals`.
2. New `POST /v1/policy/rebuild_apply/{proposal_id}` - re-reads the
   current on-disk `routing_policy.yaml` and refuses (422) if it no
   longer matches what the proposal was diffed against (defense against
   a race, same pattern as Brew 41's approve-time guardrail re-check),
   otherwise writes the exact previously-computed `new_policy_yaml` to
   disk and hot-swaps `state.routing_policy = RoutingPolicy(new_data,
   state.bean_registry)` in place - no restart needed (Section 1). Never
   auto-applies; a preview with no matching apply call changes nothing,
   ever.
3. New `web/src/components/Settings/SettingsPanel.tsx` (new directory -
   Gap 5) - a `fixed inset-0` overlay, the fourth reuse of that pattern
   in this app (`AttachmentGallery`, `FileViewerPanel`, `MemoryProposalPanel`
   already establish it). One "Routing Policy" section: a "Rebuild House
   Blend" button calls `rebuild_preview`, renders the diff (same colored
   unified-diff `DiffView` component `MemoryProposalPanel.tsx` already
   has - extracted into a small shared component rather than duplicated),
   and shows Approve/Discard buttons that call `rebuild_apply`/do
   nothing, respectively. Opened via a new gear-icon button in the
   `Sidebar` header next to the existing collapse/expand control -
   Question 2 asks you to confirm this placement.

### 3.3 Escalation-rate flagging (Requirement 3)

- Alongside the ratings pass, `build_policy()` computes a per-task_type
  escalation rate from the same Ledger rows:
  `escalated_count / total_request_count` for that `task_type` (unrelated
  to any specific Bean - escalation is a task-type-level signal about
  whether the primary Bean keeps failing for that kind of work).
- A task_type whose rate exceeds `settings.escalation_rate_flag_threshold`
  (new setting, recommend default **0.3** - Question 4) is added to the
  rebuild-preview response's `escalation_candidates` list - **advisory
  only**. This plan does **not** add a new `routing_policy.yaml` status
  value or change what `select_route()` actually does - Gap 3 above
  means no premium Bean is even available to route to yet, so writing
  automatic "premium-first" routing behavior now would be dead code with
  nothing to verify it against. The UI renders `escalation_candidates` as
  a plain warning line above the diff ("`code` has escalated on 4/10
  (40%) of requests - consider a premium-first policy once a premium
  Bean is available"), giving a human the information without the
  system silently acting on it.

## 4. Performance and release pass (Requirements 4-8)

### 4.1 Verification and recording (Requirement 4)

Run and record, with real numbers (not restated prior-Brew numbers):

- Asset budget: `node web/scripts/checkAssetBudget.mjs` (already ran:
  11.8 KB / 300 KB as of this plan; re-run after any Brew 42 asset
  changes, though none are planned).
- First-paint timing with scene lazy-load: a real Playwright trace of
  `web/` cold-loading `/`, using the Performance API (`performance.timing`
  or `PerformanceObserver` for `first-contentful-paint`), same tooling
  class already used for the Brew 39 CPU profile (Chrome DevTools
  Protocol via Playwright - no new dependency).
- Collapsed-scene CPU profile: repeat Brew 39's `Performance.getMetrics()`
  3-second idle-window comparison (collapsed vs. expanded), explicitly
  re-verifying it's still a directional baseline (still no real `.riv`
  file), not claiming a Phase-2 number that doesn't exist yet.
- 60fps scene playback note: honestly recorded as **not independently
  verifiable yet** with only the static SVG fallback tier active (no
  real Rive animation is running today to measure frame timing against)
  - stated plainly rather than fabricating a frame-rate number for
  content that isn't animating.
- Bundle size report: a small new script (`web/scripts/reportBundleSize.mjs`,
  matching `checkAssetBudget.mjs`'s style - stdlib `fs`, no new
  dependency) summing real shipped `.next/static/chunks/*.js` byte sizes
  (excluding `.map` files), run after `next build`, printed as a table
  and recorded in the Tasting Note - Gap 6 explains why this needs a
  small script rather than reusing `next build`'s own output.

### 4.2 Full test suite from repo root (Requirement 5)

`python tools/run_all_tests.py` already does exactly this (Section 1) -
Requirement 5 is "run it again after Brew 42's changes land and print the
collected count," not new tooling. The real current baseline is **560
tests, 0 failures, 5 roots** (confirmed just now). After Brew 42's new
router tests (Section 3.1's `generate_policy.py` coverage, the two new
policy-rebuild endpoints, `min_rating_sample_size`/`escalation_rate_flag_threshold`
settings) and new Vitest tests (`SettingsPanel`, shared `DiffView`), this
number will be reported again, not assumed.

### 4.3 `router/README.md` and UI operating notes (Requirement 6)

- Rewrite `router/README.md`: full current endpoint table (20 endpoints,
  not 3), current config file list (adds `router/data/pantry_index.db`
  regeneration via `python router/tools/index_pantry.py`), env vars
  (`OPENROUTER_API_KEY`, `COFFEE_ROUTER_FORCE_ESCALATION` demo-only flag),
  and a link to `router/EVENT_CONTRACT.md`'s version history (currently
  v1.4) instead of restating it.
- Replace `web/README.md`'s unedited `create-next-app` boilerplate with
  real Project Coffee content: how to start both services together (the
  router on `:8765`, then `npm run dev` on `:3000`), the
  `NEXT_PUBLIC_ROUTER_URL` env var (`web/src/lib/api.ts`'s `ROUTER_BASE_URL`),
  which config files matter (`router/config/*.yaml`, not anything under
  `web/`), and a pointer to `router/EVENT_CONTRACT.md` for the event
  shapes the frontend consumes.

### 4.4 Doc sweep (Requirement 7)

- `ARCHITECTURE.md`: add an explicit disambiguation note where "Coffee
  Counter" first appears - the *editor* meaning (Cursor, Layer 1) is the
  original v0.1 usage and stays; a new short paragraph names the
  Next.js app built in Brews 37-41 as **"Coffee Counter Chat UI"**
  (its actual name throughout `docs/design/coffee-counter-chat-ui-design.md`
  and every Brew Log entry since) and clarifies it is a *client* of
  Layer 3 (the router), not a new architectural layer - Layer 3's
  existing "Barista orchestrator" bullet gets a one-line note that
  `router/` is its concrete implementation as of Brew 36.
- `ROADMAP.md`: update the "Current status" table (Phase, current
  shot/milestone, next step, blockers) to Brew 42's real state, and
  append Brew 36-42 rows to the Brew history table (Gap 3) using the
  same one-line-per-Brew style already used for Brews 1-35, sourced from
  `brew-log/progress.md`'s already-accurate dated rows rather than
  re-deriving them.

### 4.5 Closeout (Requirement 8)

- Final `brew-log/active_context.md`/`progress.md` update, same style as
  every prior Brew.
- A new Tasting Note entry comparing **House Blend** and **Second Pour**
  (both real, available, free-tier Beans) on the exact
  `roastery/cup_tests/002-tiny-python-fix.md` prompt, run through two
  real `POST /v1/order` calls with `bean_alias_override` (the router
  "pipeline," not the old synchronous Roastery Cup Test CLI runner) -
  scored against that Cup Test's existing Success Criteria, with real
  tokens/latency/cost recorded exactly as every other Tasting Note in
  this file already does.
- A release summary section (new, appended to `brew-log/progress.md` or
  a new `docs/releases/` entry - Question 5): what exists now (both
  router + web/ feature set as of Brew 42), known limitations (no
  premium/vision Bean ever selected - the single most-repeated gap
  across Brews 36-42, `knowledge/` still 4 files, ratings/escalation-
  flag logic proven but not yet real-data-triggered), and a recommended
  next three Brews (drawn from the "Up next"/"Next actions" lists
  `brew-log/progress.md`/`active_context.md` already carry, not invented
  fresh).

## 5. Cross-cutting additions

**Settings** (`router/config/settings.yaml` + `Settings`):
```yaml
min_rating_sample_size: 5
policy_roastery_weight: 0.6
policy_rating_weight: 0.4
escalation_rate_flag_threshold: 0.3
```

**No event contract version bump** - the two new policy endpoints are
plain request/response (matching the memory-proposal precedent), not new
SSE event types.

**Ledger**: no schema change - this work only *reads* `ledger/router_requests.csv`,
it never writes a new column or row shape.

## 6. Tests (as requested, plus the zero-coverage gap from Section 2)

- `tools/generate_policy.py` / `router/tests/test_generate_policy.py`
  (new file - Gap 4): rating-to-numeric mapping, below-threshold pairs
  unaffected, at-threshold pairs get a `combined_score`, weight-split
  math, escalation-rate computation, CLI flags override settings-style
  defaults, and a real fixture proving the exact "5 real rating rows
  flips the primary Bean for one task_type" scenario end to end.
- Policy-rebuild endpoints: preview computes a correct diff against a
  scratch `routing_policy.yaml`/Ledger fixture (never the real files -
  same `repo_root`-override testability pattern established twice in
  Brew 41 for `pantry.py`/`index_pantry.py`); apply writes and hot-swaps
  `state.routing_policy` (a live `select_route()` call after apply
  proves the swap took effect without a restart); apply refuses (422) if
  the on-disk file changed since preview (race guard, mirroring Brew
  41's memory-proposal approve-time re-check).
- Escalation-candidate flagging: a scratch Ledger fixture with a known
  escalation rate above/below the threshold produces the right
  `escalation_candidates` list.
- Frontend: `SettingsPanel` renders the diff and escalation-candidate
  warning, Approve/Discard call the right endpoints, gear-icon button
  wiring from `Sidebar`.
- `web/scripts/reportBundleSize.mjs`: a focused test (or a documented
  manual run, since this is a build-output-dependent script, same
  precedent as `checkAssetBudget.mjs` having no dedicated test today)
  proving it sums real chunk bytes and excludes `.map` files.

## 7. Non-goals for this Brew

- No automatic "premium-first" routing behavior - Requirement 3 is
  advisory flagging only (Gap 3, Section 3.3).
- No new per-dollar cost metric invented ahead of a real priced Bean
  existing (Gap 2).
- No change to how a rating is captured (`POST /v1/rate` already works) -
  only how accumulated ratings are *used* by policy generation.
- No general preferences/settings page beyond the one "Routing Policy"
  section - the existing `/v1/preferences` (Sidebar collapse state) stays
  exactly as it is, not folded into this new panel.
- No scheduled/automatic policy rebuilds - manual button click only,
  matching this repo's consistent "no new background infrastructure"
  discipline (`index_pantry.py`'s sweep-on-access precedent, again).

## 8. Open questions requiring your decision

1. **Ratings weighting split**: Roastery Cup Test evidence weighted 0.6,
   accumulated ratings weighted 0.4, once the 5-rating threshold is
   cleared (Section 3.1, step 3). *Recommend as proposed* - Cup Test
   evidence is structured/reviewed, ratings are real-world but currently
   sparse-by-construction (Gap 1), so it should corroborate, not
   dominate, until much more accumulates.
2. **"Rebuild House Blend" placement**: a new gear-icon button in the
   `Sidebar` header opening a `SettingsPanel` overlay with one "Routing
   Policy" section (Section 3.2, step 3). *Recommend as proposed* - it's
   the first settings-shaped UI surface in this app, so the placement
   itself is a real, undecided choice, not an extension of something
   that already exists.
3. **Escalation-rate flag threshold**: 30% (Section 3.3). *Recommend as
   proposed* - arbitrary but reasonable as a first cut; easy to retune
   later since it's a plain setting, not a schema change.
4. **Where the release summary (Requirement 8) lives**: appended to
   `brew-log/progress.md` (same file as every other Brew Log entry) vs.
   a new standalone `docs/releases/brew-42-release-summary.md` (this
   repo already has a `docs/releases/` directory from the v1.0 stronger-
   base closeout in Brew 25). *Recommend the standalone file* - a
   release summary is a different shape of document (a snapshot for a
   future reader deciding what to do next) than the dated append-only
   Brew Log table, and `docs/releases/` already exists for exactly this
   purpose.
5. **Bundle size script scope**: a minimal one-shot `reportBundleSize.mjs`
   printing a table (Section 4.1) vs. wiring it into `prebuild`/`pretest`
   like `checkAssetBudget.mjs` (which *fails* the build over budget,
   which a bundle size *report* shouldn't do - there's no agreed budget
   number for total JS yet). *Recommend the minimal one-shot script,
   report-only, no build-failing threshold* - matches the fact that this
   Brew is asked to *record* a number, not *enforce* one.

## 9. Files touched (CREATE/MODIFY)

```
tools/generate_policy.py                    MODIFY - ratings-weighting, escalation-rate computation, --ledger/--dry-run CLI flags
router/tests/test_generate_policy.py         CREATE - first-ever coverage for this script
router/app/main.py                           MODIFY - POST /v1/policy/rebuild_preview, POST /v1/policy/rebuild_apply/{id}
router/app/config.py                         MODIFY - 4 new settings
router/config/settings.yaml                  MODIFY - same
router/tests/test_main.py                    MODIFY - policy-rebuild endpoint tests
router/README.md                             MODIFY - full rewrite (20-endpoint table, current config/env vars)
web/README.md                                MODIFY - full rewrite (real Project Coffee content, replaces create-next-app boilerplate)
web/src/components/Settings/
  SettingsPanel.tsx                          CREATE
  SettingsPanel.test.tsx                     CREATE
  DiffView.tsx                               CREATE - extracted from MemoryProposalPanel.tsx for reuse
web/src/components/MemoryProposal/
  MemoryProposalPanel.tsx                    MODIFY - use the extracted shared DiffView
web/src/components/Sidebar/index.tsx         MODIFY - gear-icon button opening SettingsPanel
web/src/lib/api.ts                           MODIFY - rebuildPolicyPreview()/rebuildPolicyApply() calls
web/scripts/reportBundleSize.mjs             CREATE
ARCHITECTURE.md                              MODIFY - Coffee Counter Chat UI disambiguation note
ROADMAP.md                                   MODIFY - current-status table + Brew 36-42 history rows
brew-log/active_context.md                   MODIFY - Brew 42 closeout
brew-log/progress.md                         MODIFY - Brew 42 closeout rows
ledger/cost_log.md                           MODIFY - Brew 42 Ledger row
roastery/tasting_notes.md                    MODIFY - two-Bean comparison Tasting Note + performance verification note
docs/releases/brew-42-release-summary.md     CREATE (pending Question 4's answer)
```

## 10. Workflow from here

1. You review this plan and answer Section 8's five questions.
2. On approval: learning loop first (`generate_policy.py` extension +
   its own new tests green, then the two router endpoints + their tests,
   then the `SettingsPanel` frontend + its tests) - demoed against a
   *scratch* Ledger/policy fixture proving the ratings-weighting and
   escalation-flagging mechanisms actually work, since Gaps 1 and 3 mean
   the real data can't demonstrate either one changing anything yet.
3. Then the performance/release pass (Section 4): run and record real
   numbers, rewrite the two READMEs, sweep `ARCHITECTURE.md`/`ROADMAP.md`,
   run `python tools/run_all_tests.py` from the repo root and report the
   collected count.
4. Then closeout: Brew Log, the real two-Bean Tasting Note (House Blend
   vs. Second Pour on the tiny-Python-fix task, through real `/v1/order`
   calls), and the release summary.
5. I show you the full summary. Only after you review it do I propose
   (not execute) the git tag name and message.
