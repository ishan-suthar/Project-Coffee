# Active Context

## Phase

Phase 1 — Working daily AI coding environment

## Current milestone

Shot 3B attempted: connectivity test **BLOCKED** — OpenRouter key not available to agent shell.

## What matters right now

- House Blend default Bean (planned): `nvidia/nemotron-3-super-120b-a12b` via OpenRouter
- First Roastery scorecard created (blocked status): `roastery/model_scorecards/shot-3b-nemotron-connectivity.md`
- Ledger entries logged with pre-flight estimates only
- **Blocker:** Cursor-stored API keys are not visible to Barista terminal; Shot 3B retry needs `OPENROUTER_API_KEY` in User environment OR manual test in Cursor UI

## Next actions

1. Retry Shot 3B: set `OPENROUTER_API_KEY` in Windows User env (not repo) **or** run connectivity prompt manually with Nemotron in Cursor
2. On success: update scorecard, ledger, and ROADMAP exit criteria
3. Shot 4 — first Roastery bake-off (fast coding Bean TBD)

## Blockers

OpenRouter authentication from agent shell.

## Last updated

2026-07-02 — Shot 3B blocked (documented)
