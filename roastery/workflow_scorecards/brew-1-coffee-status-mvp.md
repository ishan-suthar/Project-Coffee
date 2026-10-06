# Brew 1 Workflow Scorecard: Coffee Status MVP

## Metadata

- Brew: Brew 1
- App: Coffee Status
- Status: MVP runtime verified
- Date: 2026-07-02
- Scope: local-only, read-only Streamlit dashboard

## Workflow Summary

The initial broad Shot 4B/4C attempt became unstable, so the project recovered by using smaller Espresso Shots. Coffee Status was rebuilt through skeleton creation, a minimal page, reader extraction, previews, static verification, runtime verification, and closeout artifacts.

## Tool/Runtime Observations

- ChatGPT was useful for shot planning and prompt design.
- Cline with OpenRouter/Nemotron encountered tool-call instability.
- Codex was useful for static verification and closeout support.
- PowerShell manual commits gave the human control.
- Streamlit manual runtime verification caught a real root-resolution issue.

## Scores

| Category | Score | Notes |
| --- | --- | --- |
| Scope control | 5 | Micro-shots kept responsibilities separate. |
| Diff size | 5 | Changes stayed small and reviewable. |
| Human reviewability | 5 | Manual commits and narrow shots kept control with the human. |
| Runtime reliability | 4 | App verified locally after root-resolution fix. |
| Tool-call reliability | 3 | Codex was steady; Cline/OpenRouter/Nemotron had instability. |
| Safety / secrets handling | 5 | App stayed local-only and did not display secrets. |
| Documentation quality | 5 | Status docs, retrospective, ledger estimate, and this scorecard were separated. |
| Commit hygiene | 5 | Manual PowerShell commits kept history explicit. |
| Overall workflow | 4 | Recovery pattern worked; agent/runtime reliability still needs improvement. |

## Evidence

- One Shot = One Responsibility worked.
- App remained local-only and read-only.
- No app secrets were displayed.
- Root-resolution bug was found through runtime verification.
- Project state docs, retrospective, and ledger estimate were updated in separate shots.

## What Improved

- Smaller shots reduced instability.
- Separate manual commits kept history clear.
- Static and runtime verification caught different classes of issues.
- Runtime-agnostic Barista approach worked: Cline could be paused and Codex could continue.

## What Still Needs Improvement

- Need stronger tool-call reliability for Cline tasks.
- Need clearer copy/paste separation between terminal commands and agent prompts.
- Need future automated tests for Coffee Status.
- Need possible future status model only after MVP closeout.

## Recommendations

- Keep One Shot = One Responsibility.
- Keep app code, docs, ledger, roastery, and closeout as separate shots.
- Prefer Codex or a stronger agentic model for command-heavy work.
- Use PowerShell manually for commits.
- Add tests in a future Brew, not during this closeout shot.
