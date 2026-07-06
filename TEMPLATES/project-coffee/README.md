# Project Coffee Template Pack

Use this pack to add a minimal Project Coffee skeleton to a new project.

Copy the files in this folder into the project root, then replace the plain
prose placeholders such as "Project name goes here." with project-specific
details.

## Included Files

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Local Barista rules and safety gates. |
| `PROJECT_COFFEE.md` | Project-specific Coffee brief and workflow. |
| `.cursorignore` | Cursor context ignore rules for secrets, generated files, and caches. |
| `.cursorindexingignore` | Cursor indexing ignore rules for secrets, generated files, and caches. |
| `brew-log/projectbrief.md` | Project purpose, boundaries, and current shape. |
| `brew-log/active_context.md` | Current state, next actions, and blockers. |
| `brew-log/progress.md` | Shot history and current work. |
| `knowledge/00_index.md` | Local Pantry index. |
| `roastery/tasting_notes.md` | Workflow/model evidence notes. |
| `ledger/cost_log.md` | Cost, token, and value notes. |

## Copy Rules

- Copy only into a project you are allowed to edit.
- Do not copy secrets into these files.
- Do not add real API keys, tokens, credentials, SSH keys, OAuth blobs, or
  private data.
- Keep onboarding small and local-first.
- Stage only intended files after human review.
- Run the staged secret-pattern check from Project Coffee policy before any
  commit.
