# Knowledge Index

Status: Pantry Lite MVP
Last updated: 2026-07-03

Use this index to choose the smallest useful context for a Project Coffee task.
Do not read every foundation document by default.

## Start Here

1. Read `brew-log/active_context.md` for current state.
2. Read `knowledge/project_docs/project-coffee-foundation-summary.md` for a
   compact project overview.
3. Open only the source documents listed below that match the current task.

## Source Table

| File path | Type | Status | Why / when to read it |
| --- | --- | --- | --- |
| `knowledge/project_docs/project-coffee-foundation-summary.md` | Summary | Current | First compact overview for most Project Coffee shots. |
| `brew-log/active_context.md` | Live status | Current | Always read for current milestone, blockers, and next actions. |
| `brew-log/progress.md` | Live progress | Current | Read when checking completed shots or deciding what happened before. |
| `ROADMAP.md` | Roadmap | Current | Read for Phase 1 checklist, shot history, and milestone direction. |
| `CHANGELOG.md` | Change history | Current | Read when summarizing user-visible project changes. |
| `AGENTS.md` | Agent rules | Current | Read before acting in the repo or when constraints are unclear. |
| `README.md` | Foundation overview | Stable | Read when the project identity or included foundation docs are unclear. |
| `VISION.md` | Identity / mission | Stable | Read for high-level purpose; avoid reading for routine implementation shots. |
| `config/house_blend.md` | Routing policy | Draft | Read only for model routing, cost, escalation, or Bean selection questions. |
| `prompts/README.md` | Prompt library | Current | Read for prompt artifact scope or copy/paste safety questions. |
| `apps/coffee-status/README.md` | App docs | Sparse | Read for Coffee Status app context before app-specific work. |

## Retrieval Guidance

- For planning shots: active context, foundation summary, roadmap.
- For implementation shots: active context, AGENTS, target files, relevant tests.
- For Coffee Status work: active context, app files, app tests, Coffee Status
  README if needed.
- For prompt work: active context, prompts README, relevant prompt template.
- For routing or cost work: active context, House Blend, Roastery or Ledger only
  when the shot explicitly allows it.

## Token-Saving Rule

If the summary answers the question, do not open the full source document. If a
source is needed, open the smallest relevant file rather than scanning folders.
