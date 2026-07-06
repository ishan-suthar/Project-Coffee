# Brew 7 Workflow Scorecard: Coffee Certification Project

## Metadata

- Brew: Brew 7
- App: Coffee Certification
- Status: Complete
- Date: 2026-07-05
- Scope: local Python standard-library CLI/checklist, tests, Brew Log, Roastery, Ledger, and Roadmap trace

## Workflow Summary

Brew 7 / Shot 10A began the first end-to-end Project Coffee workflow validation after the v0.1 foundation. The shot used Decaf/context inspection first, then implemented a small dependency-free Python project under `apps/coffee-certification/`. The app checks whether a Coffee workflow has covered the required certification steps and reports missing or unexpected steps.

The workflow covered planning, implementation, tests, Brew Log update, Roastery entry, Coffee Ledger entry, House Blend consultation, human diff review, explicit approval, and manual commit.

## Tool/Runtime Observations

- Codex handled repository inspection, implementation, tests, and local documentation updates.
- The project House Blend was consulted. No OpenRouter Bean was invoked because this shot did not need a remote Bean.
- The certification app uses only Python standard-library modules.
- No packages were installed.
- No secrets, `.env` files, credentials, tokens, SSH keys, or private key material were inspected.
- The implementation was manually committed by the human before Shot 10C closeout.

## Scores

| Category | Score | Notes |
| --- | --- | --- |
| Scope control | 5 | One small stdlib project with one responsibility: workflow certification status. |
| Diff size | 4 | Adds a new app plus required trace docs; still reviewable. |
| Human reviewability | 5 | Code is small, tests are plain `unittest`, and commit remains manual. |
| Testing usefulness | 5 | Tests cover complete, incomplete, normalized, duplicate, unexpected, and CLI behavior. |
| Documentation trace | 5 | Active context, progress, Ledger, Roastery, and Roadmap status were updated. |
| House Blend discipline | 4 | Routing policy was consulted and remote Bean use was avoided; no model comparison was needed. |
| Safety / secrets handling | 5 | Local-only, no dependency install, no secret inspection, no staging, no commit. |
| Commit hygiene | 5 | Human review and manual commit were preserved. |
| Overall workflow | 5 | All 11 Brew 7 certification steps are satisfied. |

## Evidence

- `apps/coffee-certification/src/certifier.py` defines the checklist model and report formatter.
- `apps/coffee-certification/app.py` exposes the local CLI.
- `apps/coffee-certification/tests/` contains focused `unittest` coverage.
- Verification command passed: `python -m unittest discover -s apps/coffee-certification/tests`.
- Required-step listing command passed: `python apps/coffee-certification/app.py --list-required`.
- Brew Log, Roastery, Ledger, and Roadmap entries now point to Brew 7.
- Human diff review approved the implementation in Shot 10B.
- Manual commit completed before Shot 10C closeout: `44bce29`.
- Final certification report status is `COMPLETE` when all 11 steps are supplied.

## What Improved

- Coffee now has a concrete certification surface for future workflow validation.
- The certification checklist makes the human gates visible instead of assuming completion.
- The app gives future Brews a small tool the human can run locally.
- Roadmap and active context were corrected away from stale Brew 4/Brew 5 state.

## What Still Needs Improvement

- Future certification could record the final human-run tool output immediately after commit.

## Recommendations

- Use the certification CLI at the end of future workflow validation shots.
- Keep the app stdlib-only unless a clear future need justifies a dependency.
- Continue recording unknown token/cost data honestly instead of estimating unsupported values.
