# Project Coffee

Project Coffee is a local-first AI engineering operating system. This
repository is the working home for its memory, rules, evaluation loop, local
tools, and project-specific operating habits.

## What This Repo Is

- A model-agnostic engineering workspace.
- A place to build and test Coffee's own operating system.
- A local archive for Brew Logs, Pantry knowledge, Roastery evaluations, Ledger
  cost notes, House Blend routing, prompts, Recipes, and Barista role cards.
- Not a place for API keys, credentials, private secrets, or production data.

## Core Workflow

- One Shot = One Responsibility.
- Barista writes tools.
- Human runs tools.
- Roastery measures results.
- Human reviews diffs and commits.
- Prefer the smallest correct diff.
- Update the Brew Log after meaningful work.

## Default Safety Mode

Use Decaf Mode for non-trivial, risky, unclear, or read-only work:

- inspect only the minimum necessary files;
- do not edit files;
- do not run destructive commands;
- do not install dependencies;
- do not stage or commit;
- propose the next small shot before implementation.

## Approval Gates

Ask the human before:

- staging, committing, pushing, or deploying;
- deleting or overwriting files;
- installing dependencies;
- using credentials or touching secrets;
- making network, cloud, database, firmware, or production changes;
- sending sensitive or private context to a remote model.

Before any commit, stage only the intended files and run:

```powershell
git grep --cached -n -I -E "<Project Coffee staged secret patterns>"
```

If that command prints anything, do not commit.

## Where Things Live

| Area | Location |
| --- | --- |
| Agent starter rules | `AGENTS.md` |
| Constitution | `COFFEE_CONSTITUTION.md` |
| Governance and safety | `GOVERNANCE_AND_SAFETY.md` |
| Brew Log | `brew-log/` |
| Pantry / Knowledge | `knowledge/` and `pantry/` |
| Roastery evaluations | `roastery/` |
| Ledger | `ledger/` |
| House Blend routing | `config/house_blend.md` |
| Cursor rules | `.cursor/rules/` |
| Spill Guard ignores | `.cursorignore`, `.cursorindexingignore`, `.gitignore` |
| Prompts | `prompts/` |
| Recipes | `recipes/` |
| Barista roles | `agents/` |

## Read First

For a new Coffee task, read in this order:

1. `PROJECT_COFFEE.md`
2. `AGENTS.md`
3. `brew-log/active_context.md`
4. `knowledge/00_index.md` if context is needed
5. the smallest relevant project files for the shot

Use larger foundation docs only when the short files are insufficient.

## Secrets Rule

Never inspect, print, paste, store, or commit API keys, tokens, credentials, SSH
keys, OAuth blobs, local credential stores, `.env` files, or private production
data. If a key was exposed, assume it must be revoked and replaced outside the
repo; never paste replacement keys into chat.
