# AGENTS.md - Coffee Status Agent Instructions

These instructions apply to coding agents working inside `apps/coffee-status`.

## Project Identity

Coffee Status is a local-only status dashboard for Project Coffee. Treat it as
a small real project onboarded into the Project Coffee workflow, not as a place
for experiments with secrets, credentials, or production data.

## Operating Rules

- One Shot = One Responsibility.
- Barista writes tools.
- Human runs tools.
- Roastery measures results.
- Human reviews diffs and commits.
- Prefer the smallest correct diff.
- Do not edit application behavior without explicit approval.
- Do not inspect, print, store, or commit secrets.

## Safety Gates

Ask before:

- staging, committing, pushing, or deploying;
- installing dependencies;
- deleting or overwriting files;
- touching secrets, `.env` files, credentials, SSH keys, tokens, OAuth blobs, or
  private data;
- making network, cloud, database, firmware, or production changes.

## Default Workflow

1. Start in Decaf Mode for onboarding, unclear, or risky work.
2. Inspect only the minimum safe files.
3. Propose the smallest useful plan.
4. Wait for human approval before edits.
5. Implement one small diff.
6. Run local validation.
7. Update the local Brew Log, Roastery, and Ledger when meaningful.
8. Stop before staging or committing unless explicitly approved.

Before any commit, stage only intended files and run this from the repository
root:

```powershell
git grep --cached -n -I -E "<Project Coffee staged secret patterns>"
```

If that command prints anything, do not commit.
