# Coffee Counter UI Guide

Status: Brew 30C packaging decision complete
Date: 2026-07-08

This guide explains how the Project Coffee Counter UI works today and how it
should evolve. It began as a Streamlit-first planning guide and now tracks the
implemented MVP, Evidence Bundle integration, Routing Approval Gates, and
packaging/polish direction.

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
- Routing / Approval: show route choice, approval requirement, allowed context,
  blocked context, and context preview scaffolding.
- Roastery: show summarized benchmark evidence, not raw local outputs.
- Settings / Safety: show roots, allowlisted tools, exclusions, and approval
  gates.

## Initial MVP Scope

Brew 27 implemented the initial local-only Streamlit MVP around:

- Home / Overview;
- Ask Coffee local-only;
- Evidence Bundle;
- Doctor summary;
- Fleet summary.

Brew 28 and Brew 29 then added structured Evidence Bundle display, local-only
drafting, and routing approval scaffolding.

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

## Brew 26B Review Notes

The UI design was reviewed against ten target workflows: project status, next
action, prompt drafting, warning explanation, fleet attention, remote model
approval, validation commands, commit requests, warning states, and no-evidence
results.

The design supports the workflows if Brew 27 keeps the MVP local-only and
implements:

- Home status cards for Dashboard, Doctor, Release Check, current Brew, and
  next Shot;
- Evidence Bundle query and citation display;
- Doctor details with severity, path, finding code, and safe next action;
- Fleet summary with missing-registry handling;
- Ask Coffee as local evidence plus deterministic prompt/checklist drafting;
- allowlisted command execution with argument lists, command preview, stdout,
  stderr, exit code, and failure status.

Brew 27 should keep these out of MVP:

- remote model calls;
- OpenRouter calls;
- sending context to a remote Bean;
- file editing;
- raw Roastery output inspection;
- Git staging, commits, pushes, or tags;
- background autonomous behavior.

## Brew 26C Closeout

Brew 26 Coffee Counter UI Design is complete. Use this guide and
`docs/design/coffee-counter-ui-design.md` as the source for Brew 27 Streamlit
Coffee Counter MVP planning.

Brew 27 may add Streamlit only after explicit approval and should keep the MVP
local-only.

## Brew 27A Streamlit MVP Status

Brew 27A adds the first local Streamlit Coffee Counter MVP under `ui/`. The app
wraps existing Project Coffee CLI tools through an allowlisted command adapter.
The adapter is testable without importing Streamlit.

## Setup

Install Streamlit only after approving the dependency:

```powershell
python -m pip install streamlit
```

## Run Command

From the Project Coffee root:

```powershell
python -m streamlit run ui/coffee_counter_app.py
```

## MVP Tabs

- Home / Overview: local Dashboard, Doctor, Release Check, and Fleet Status
  buttons.
- Ask Coffee: local-only evidence retrieval for a question or Order.
- Evidence Bundle: direct Evidence Bundle query form with optional JSON output.
- Ledger: Ledger Summary with configurable recent entry count.
- Fleet: Fleet Status with optional registry path.
- Safety / Commands: allowlisted commands, non-goals, and approval reminders.

## Local-only Ask Coffee Behavior

Ask Coffee in the MVP does not call a model. It sends the human's question to
the local Evidence Bundle tool and displays local evidence. Any future remote
Bean use requires a separate approval gate.

## Known Limitations

- Fresh checkouts may still need Streamlit installed after explicit human
  approval.
- The UI does not edit files.
- The UI does not stage, commit, push, or tag.
- The UI does not inspect raw Roastery outputs.
- The UI does not send evidence anywhere.
- The command adapter currently exposes only Dashboard, Doctor, Release Check,
  Ledger Summary, Evidence Bundle, and Fleet Status.

## Brew 29 Direction

- Brew 28 improved Evidence Bundle display, citations, no-evidence handling,
  and local answer drafting.
- Brew 29A adds visible routing approval gates before any future remote Bean
  can receive local context.

## Brew 28A Evidence Integration

Brew 28A improves Ask Coffee and Evidence Bundle without changing Project
Coffee's local-only UI boundary.

Ask Coffee now:

- takes a human question or Order;
- runs the local `evidence-bundle` command through the same allowlisted adapter;
- requests JSON output for structured parsing;
- shows evidence status, top source paths, headings, snippets, scores,
  freshness, and safety labels;
- creates a deterministic local evidence draft from metadata and snippets;
- labels the draft as local evidence, not model-generated;
- says when evidence is insufficient;
- shows the exact safe CLI command that was run.

Evidence Bundle now:

- keeps Markdown output visible for review;
- also runs JSON output for structured display;
- handles malformed JSON as a UI error state;
- handles zero matches as an honest no-evidence state;
- preserves stdout, stderr, and exit code visibility.

Limitations:

- The local evidence draft is not a generated answer from a Bean.
- It may be incomplete when the source evidence is thin or noisy.
- The UI still does not edit files, stage files, commit, push, tag, inspect raw
  Roastery local outputs, or send evidence to a remote model.
- Remote routing remains disabled after Brew 29A; the approval gates are
  visible scaffolding only.

## Brew 28C Closeout

Brew 28 UI + Evidence Bundle Integration is complete. Ask Coffee uses local
Evidence Bundle output, shows structured evidence, creates a deterministic
local-only draft, handles no-evidence states honestly, and keeps remote model
calls disabled.

Next recommended work after 28C was Brew 29: UI + Routing Approval Gates.
Brew 29A has now implemented the local-only routing approval scaffolding.

## Brew 29A Routing Approval Gates

Brew 29A adds routing visibility and approval-gate scaffolding without enabling
remote execution.

Routing modes shown in the UI:

- Decaf / no model;
- Local evidence only;
- Remote Bean requires approval;
- Roastery benchmark required.

Default routing mode is Local evidence only.

Routing decisions include:

- selected mode;
- whether approval is required;
- reason;
- allowed context;
- blocked context;
- next safe action.

The request classifier is intentionally conservative:

- current status questions route to local evidence only;
- docs/how-to questions route to local evidence only;
- cost/token questions route to local evidence plus Ledger;
- benchmark requests require Roastery workflow and approval;
- code changes require approval before any future remote context;
- requests to send repository context to a model require approval;
- commit/push requests stay manual-only with no UI auto-commit.

Context preview behavior:

- shows eligible local evidence snippets;
- labels the preview as not sent anywhere;
- reminds the user that secrets, `.env` files, credentials, hidden credential
  directories, raw local outputs, and broad repository dumps are excluded.

Non-goals for Brew 29A:

- no OpenRouter button;
- no API key input;
- no remote Bean calls;
- no file editing;
- no staging, commits, pushes, or tags.

Future remote execution, if ever added, should be a separate Brew with explicit
approval, context preview confirmation, Ledger evidence, and Roastery evidence.

## Brew 30A Packaging and Polish Plan

Brew 30A keeps Streamlit as the working Coffee Counter UI. React and Tauri
remain later optional migration paths after the UI workflows stabilize.

Current recommended run command from the Project Coffee root:

```powershell
python -m streamlit run ui/coffee_counter_app.py
```

Packaging plan summary:

- keep the manual Streamlit command as the supported path for now;
- consider `scripts/start_coffee_counter.ps1` later as a small local helper;
- consider `requirements-ui.txt` later if UI dependencies need a separate
  explicit install path;
- defer React/Tauri until Streamlit layout or desktop packaging needs justify
  the rewrite.

Recommended polish path:

- Brew 31: Streamlit polish pass;
- Brew 32: UI project and fleet switching;
- Brew 33: optional remote-call approval design.

The detailed plan lives in
[`../design/ui-packaging-and-polish-plan.md`](../design/ui-packaging-and-polish-plan.md).

## Brew 30C Closeout

Brew 30 closed with the decision to keep Streamlit as the working Coffee
Counter UI for now and defer React/Tauri migration. The next recommended work
is Brew 31: Streamlit Polish Pass.

Brew 31 should improve usability without changing the architecture: route
badges, status cards, better evidence ranking UX, cleaner output sections,
project root persistence, and clearer no-evidence suggestions.
