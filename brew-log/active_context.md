# Active Context

## Phase

Phase 1 - Working daily AI coding environment

## Current milestone

Brew 7 - Coffee Certification Project complete.

## What matters right now

- Project Coffee Foundation v0.1 is complete through Brew 6.
- Repository cleanliness was verified before Brew 7: `git status --short` returned no output on 2026-07-05.
- Brew 7 validated the complete Coffee workflow with one small Python standard-library project.
- Brew 7 / Shot 10A added `apps/coffee-certification/`, a local dependency-free CLI/checklist with focused `unittest` coverage.
- The certification checklist covers Decaf Mode, planning, implementation, tests, Brew Log update, Roastery entry, Coffee Ledger entry, House Blend usage, diff review, human approval, and manual commit.
- House Blend was consulted for this shot. No OpenRouter Bean was invoked because local Decaf/context work plus the current Codex coding agent were sufficient; the provisional route remains Nemotron default, Cohere fallback, and Poolside secondary fallback/comparison when a remote Bean is explicitly approved.
- Brew 7 / Shot 10B completed human diff review and approved the implementation for certification.
- Brew 7 / Shot 10C records that all 11 certification steps are now satisfied.
- The implementation was manually committed at `44bce29` before Shot 10C documentation closeout.
- Brew 5 closed the Roastery MVP with three successful free Beans on the same Order and a provisional House Blend; full-output quality scoring and actual costs remain future work.
- Brew 6 completed the safety and constitution foundation.

## Next actions

1. Begin Brew 8 - first real project onboarding.
2. Before any future commit, stage only intended files and run the staged secret-pattern check:

```powershell
git grep --cached -n -I -E "sk-or-v1-|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|ghp_[A-Za-z0-9_]{20,}"
```

3. Preserve full model outputs in future Cup Tests before scoring quality.

## Blockers

No active blocker for Brew 7. Brew 8 onboarding should start with Decaf Mode and a small first project scope.

## Last updated

2026-07-05 - Brew 7 / Shot 10C Coffee Certification complete
