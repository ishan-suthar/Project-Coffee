# Brew 42 Release Summary - Learning Loop and Release Pass

Date: 2026-07-15
Status: Brew 42 implemented, tested, and demoed live; not yet staged or committed - pending human review.

This is a snapshot document, not a living log - it describes what exists
*as of Brew 42* and the recommended next steps. For day-to-day state, see
`brew-log/active_context.md` and `brew-log/progress.md`, which are updated
every Brew. This document itself is not.

## What exists now

### Coffee Core Router (`router/`, Brews 36-42)

A local FastAPI service (19 endpoints) that classifies a prompt, routes it
to a coffee-aliased Bean, streams generation over SSE, checks for failure,
pauses for human approval before escalating to a premium Bean, retrieves
grounded Pantry context on request, drafts and guardrails session memory
proposals, and rebuilds its own routing policy from Roastery evidence plus
real user ratings. Full endpoint table and config docs: `router/README.md`.

- **Routing** (Brew 36): classifier, coffee-alias enforcement (raw model
  IDs never leak into an event or API response), a generated
  `routing_policy.yaml`.
- **Sessions, rating, cancel** (Brew 37): SQLite-backed chat history,
  `POST /v1/rate`, `POST /v1/cancel`.
- **Attachments** (Brew 38): file/image upload, PDF/text extraction,
  vision routing (ships structurally correct but inert - no vision Bean
  exists yet).
- **Device preferences** (Brew 39): a generic key/value store backing the
  animated Coffee Counter scene's collapse state.
- **Escalation approval gate** (Brew 40, staged as `84070f9`):
  background-task/queue decoupling so a multi-minute approval pause
  survives a client disconnect, with reload recovery.
- **Session memory proposals + Pantry retrieval** (Brew 41, staged as
  `a55c07d`): guardrailed diffs to `brew-log/active_context.md`/`progress.md`
  from a session transcript (never written without explicit approval);
  FTS5 BM25 retrieval over `knowledge/` with citation chips and a
  path-traversal-safe file viewer.
- **Learning loop** (Brew 42, this release): `tools/generate_policy.py`
  now blends Roastery Cup Test evidence with real accumulated
  `POST /v1/rate` outcomes (once a `(task_type, Bean)` pair clears a
  minimum sample size, default 5) into routing policy ranking, and flags
  task types with a high real escalation rate as advisory-only candidates.
  A new `POST /v1/policy/rebuild_preview`/`rebuild_apply`/`rebuild_discard`
  trio (reusing the Brew 41 memory-proposal generate/approve/discard
  shape) lets a human preview a policy rebuild as a diff and apply it with
  no router restart - never hot-swapped without that review step.

### Coffee Counter Chat UI (`web/`, Brews 37-42)

A Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind v4 + zustand
browser client for the router. Not to be confused with "Coffee Counter"
the editor/IDE layer in `ARCHITECTURE.md` - see that document's Brew 42
disambiguation note. Structure and env vars: `web/README.md`.

- Chat interface with streaming responses, Bean override, attachments
  (drag-and-drop, paste, inline image preview).
- An animated Coffee Counter scene (Rive-backed, static-SVG/reduced-motion
  fallback tiers, 300 KB asset budget) reflecting live request state.
- The escalation approval card, with reload recovery for a still-paused
  request.
- A per-session `⋮` menu ("Close out this session") opening a memory
  proposal diff review panel.
- A "Use Pantry" toggle and citation chips with a read-only file viewer.
- A Settings panel (new in Brew 42, the first settings-shaped UI surface
  in this app) with a "Rebuild House Blend" action showing the routing
  policy diff before it takes effect.

### Verification as of Brew 42

- **579 tests** collected and passing repo-wide via `python tools/run_all_tests.py`
  (316 in `router/tests/`, 11 new in `tests/test_generate_policy.py`, the
  remainder across `tests/`, `roastery/tests/`, and both `apps/*/tests/`
  roots).
- **135 Vitest/RTL tests**, `tsc --noEmit`, `eslint`, and `next build` all
  clean in `web/`.
- Live demos this Brew: a scratch-fixture policy-rebuild mechanism proof
  (real rating-driven primary-Bean shift, proven outside the test suite
  since real data has no ratings yet); real performance numbers (asset
  budget, bundle size, first-paint/load timing, CPU idle-window
  comparison); a real two-Bean Tasting Note (House Blend vs. Second Pour)
  through the actual router pipeline on `roastery/cup_tests/002-tiny-python-fix.md`.

## Known limitations

1. **No premium or vision-capable Bean has ever been selected or
   Roastery-tested** - open since Brew 36/38, the single most-repeated
   gap across every Brew since. This blocks a live demo of the real
   (non-substituted) escalation approval flow and means vision routing
   ships structurally correct but permanently inert today.
2. **The learning loop has nothing real to act on yet.** Every rating
   cell in the real `ledger/router_requests.csv` is empty (no real
   session has ever clicked a rating button) and every real `escalated`
   flag is `False` (no real escalation has ever run, per #1). The
   ratings-weighting and escalation-rate-flagging mechanisms are proven
   correct against test fixtures and a scratch live demo, but will not
   change a single real routing decision until real ratings and/or
   escalations accumulate.
3. **`knowledge/` is still only 4 files** - a hand-curated pointer table,
   not a content corpus. Pantry retrieval's mechanism is proven correct
   against real data, but the corpus itself is thin.
4. **Every real Bean is free-tier** (`price_per_1k_*_usd: 0.0`), so a
   genuine quality-per-*dollar* metric remains impossible - the router
   uses average output tokens as the best available efficiency proxy
   instead, same as every prior Brew.
5. **No real `.riv` animation file has been dropped in** - the animated
   scene runs on its static-SVG fallback tier in every environment today.
   60fps playback timing is not independently verifiable until one
   exists.
6. **Brews 40, 41, and 42 needed workarounds to demo live** for the same
   root cause as #1 (Brew 40's substitute premium Bean) or #2 (Brew 42's
   scratch fixture) - a recurring pattern, not three unrelated issues.

## Recommended next three Brews

1. **Select and Roastery-test a real premium Bean** (and ideally a
   vision-capable one). This single decision unblocks more open items
   than anything else on this list: a real (non-substituted) escalation
   approval demo, real vision-routing verification, and - once real
   escalations start happening - genuine data for the learning loop's
   escalation-rate flagging to act on for the first time.
2. **Grow real usage signal**: encourage real `POST /v1/rate` clicks
   (or a small nudge in the UI) so the learning loop's ratings-weighting
   has real data to blend with Roastery evidence, rather than the
   Brew 42 scratch-fixture proof being the only demonstration of the
   mechanism working. A natural pairing with #1 - real premium-Bean
   escalations plus real ratings would exercise both new Brew 42
   features against real data at once.
3. **Expand the Pantry corpus** beyond `knowledge/`'s current 4 files
   (Brew 41 design doc Section 8, Question 1's deferred option) so
   retrieval demonstrates real grounded-answer value, not just a proven
   mechanism against a thin index. A good candidate: point the indexer
   at `brew-log/`, `roastery/tasting_notes.md`, and the `docs/design/`
   tree, which `knowledge/00_index.md` already references as a pointer
   table today.
