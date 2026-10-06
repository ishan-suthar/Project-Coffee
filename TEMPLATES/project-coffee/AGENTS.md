# AGENTS.md - Project Coffee Local Instructions

Project name goes here.

These instructions apply to coding agents working inside this project.

## Project Identity

Describe what this project does in one or two sentences.

## Operating Rules

- One Shot = One Responsibility.
- Barista writes tools.
- Human runs tools.
- Roastery measures results.
- Human reviews diffs and commits.
- Prefer the smallest correct diff.
- Start unclear or risky work in Decaf Mode.
- Do not inspect, print, store, or commit secrets.

## Safety Gates

Ask before:

- staging, committing, pushing, or deploying;
- installing dependencies;
- deleting or overwriting files;
- touching `.env` files, credentials, SSH keys, tokens, OAuth blobs, or private
  data;
- making network, cloud, database, firmware, or production changes.

## Default Workflow

1. Inspect only the minimum safe files.
2. Propose the smallest useful plan.
3. Wait for approval before edits when risk or scope is unclear.
4. Implement one small diff.
5. Run local validation.
6. Update the local Brew Log, Roastery, and Ledger when meaningful.
7. Stop before staging or committing unless explicitly approved.

Before any commit, stage only intended files and run the staged secret-pattern
check from Project Coffee policy. If it prints anything, do not commit.
