# Coffee Counter UI Guide

Status: Brew 26A guide
Date: 2026-07-08

This guide explains how the future Project Coffee Counter UI should work. It is
for planning and reviewing the Streamlit MVP before implementation.

## Purpose

The Coffee Counter UI is the human-facing control panel for Project Coffee. It
should make local status, evidence, safety gates, and tool output visible before
any remote model work happens.

The UI should help a human ask Coffee for a plan, inspect evidence, run safe
local checks, and decide what to do next. It should not hide the workflow or
turn Project Coffee into an automatic agent.

## Why Streamlit First

Streamlit is the first target because it lets Project Coffee prove the UI flow
with a small Python surface:

- quick local setup;
- good support for forms, tabs, sidebars, and text output;
- natural integration with existing Python CLI tools;
- enough UI for evidence bundles, status cards, and command output;
- easy rollback if the shape is wrong.

React + Tauri may be evaluated later if the UI needs desktop packaging, richer
state, lower-level control, or a more polished long-term shell.

## UI Layout

Recommended layout:

- Left sidebar: project/fleet selector, Brew status, tool navigation.
- Center panel: Ask Coffee order input, response drafts, prompts, command
  blocks, and local validation output.
- Right panel: Dashboard, Doctor, Release Check, Ledger, routing, and House
  Blend status.
- Bottom or expandable panel: evidence bundle, citations, command history,
  stdout/stderr, exit code, and approval gates.

Keep the layout practical and dense. This is a control panel, not a marketing
page.

## Screens

- Home / Overview: current Brew, next Shot, Dashboard, Doctor, Release Check,
  Fleet, and recent evidence.
- Ask Coffee: local-only Orders, plans, command drafts, and evidence-backed
  answers.
- Evidence Bundle: query local Project Coffee evidence and show citations.
- Doctor: summarize repository health and safe next actions.
- Release Check: show release readiness, blockers, warnings, and tag state.
- Fleet: show registered projects and onboarding status.
- Ledger: summarize cost/token/workflow evidence.
- Roastery: show summarized benchmark evidence, not raw local outputs.
- Settings / Safety: show roots, allowlisted tools, exclusions, and approval
  gates.

## MVP Scope

Brew 27 should implement:

- Home / Overview;
- Ask Coffee local-only;
- Evidence Bundle;
- Doctor summary;
- Fleet summary.

Brew 27 can leave Release Check, Ledger, Roastery, routing details, and settings
as links, placeholders, or read-only summaries if needed.

## Safety Boundaries

The MVP must not:

- call OpenRouter;
- call any remote model;
- call external APIs;
- commit, tag, push, or stage files;
- edit files from the UI;
- inspect raw Roastery local outputs;
- read secrets or hidden credential directories;
- install packages from inside the UI;
- run unapproved write-capable commands.

## Tool Integration Model

The UI should delegate to existing CLI tools through subprocess wrappers.

Rules:

- pass arguments as lists;
- avoid shell strings;
- never concatenate user text into a shell command;
- allowlist every command;
- show the command before execution;
- show stdout, stderr, and exit code after execution;
- preserve tool exit codes in UI status;
- fail closed when a command is not allowlisted.

Good initial commands:

```text
python tools/coffee.py dashboard --root PATH
python tools/coffee.py doctor --root PATH
python tools/coffee.py release-check --root PATH
python tools/coffee.py ledger-summary --root PATH
python tools/coffee.py evidence-bundle --root PATH --query TEXT
python tools/coffee.py fleet-status --root PATH
```

## Approval Gates

Require explicit human approval before:

- remote model calls;
- sending local evidence to a remote Bean;
- reading paths outside registered project roots;
- write-capable template install with `--apply`;
- Git operations;
- dependency installs;
- House Blend changes;
- destructive commands;
- deployment, cloud, database, firmware, or hardware-facing actions.

## UI States

The UI should make status obvious:

- clean;
- warning;
- blocker;
- local-only;
- approval required;
- command failed;
- no evidence found;
- project not registered;
- remote disabled.

## Streamlit Dependency Policy

Brew 26 installs nothing. Brew 27 may add Streamlit only after explicit
approval. The Brew 27 docs should include setup, run, validation, and rollback
commands.

## Future React / Tauri Migration Path

Move beyond Streamlit only if the MVP proves the workflow and Project Coffee
needs:

- desktop packaging;
- richer state management;
- stronger keyboard workflows;
- background local workers;
- more precise layout control;
- multi-project sessions.

A migration should preserve the same safety model and approval gates.

## Troubleshooting

- If the UI shows stale status, run Dashboard from the CLI and inspect Brew Log
  status fields.
- If a command fails, show stderr, exit code, and the exact argument list.
- If Evidence Bundle returns noisy results, narrow the query or source path.
- If Fleet Status reports no registry, use the example registry or create a
  local real registry intentionally.
- If Streamlit is missing in Brew 27, follow the documented setup step instead
  of installing packages from inside the UI.
