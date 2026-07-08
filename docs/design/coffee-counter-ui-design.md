# Coffee Counter UI Design

Status: Brew 26A design
Date: 2026-07-08

This design defines the first Project Coffee UI direction before any UI code is
implemented. The first frontend target is a Streamlit MVP. A React + Tauri
desktop app may be evaluated later only after the workflow is proven.

## Purpose

The Coffee Counter UI is a local Project Coffee control panel. It is not just a
chatbot.

It should help the human:

- see current Project Coffee status;
- write or review Coffee Orders;
- run safe local Project Coffee tools;
- inspect Dashboard, Doctor, Release Check, Ledger, Evidence Bundle, Roastery,
  Fleet, and routing status;
- draft commands for review;
- keep approval gates visible;
- preserve the rule that humans review diffs and commit.

The UI may eventually include a chat/order experience, but the control panel is
the center of the product.

## Frontend Decision

Streamlit is the first implementation target because it is:

- fast to build with Python;
- easy to run locally on Windows;
- a good fit for text-heavy tool output, forms, tabs, and status panels;
- aligned with Project Coffee's local-first toolchain;
- enough to prove the workflow before investing in a desktop shell.

React + Tauri remains a later migration option if Project Coffee needs richer
state, desktop packaging, keyboard-first workflows, background workers, or a
more durable UI architecture.

No Streamlit code or dependency is added in Brew 26. Streamlit may be added in
Brew 27 only if the dependency, setup command, and rollback path are documented.

## Main Layout

The UI should use a dense, work-focused layout:

- Left sidebar:
  - project/fleet selector;
  - current Brew status and next Shot;
  - navigation for tools and screens;
  - local-only / approval-required state.
- Center panel:
  - chat/order input;
  - Barista response drafts;
  - prompt previews;
  - generated command blocks;
  - validation summaries.
- Right panel:
  - Dashboard status;
  - Doctor status;
  - Release Check status;
  - Ledger summary;
  - routing and House Blend status.
- Bottom or expandable panel:
  - evidence bundle;
  - citations and snippets;
  - command history;
  - approval gates;
  - stdout/stderr details.

The UI should prioritize scanability over decoration. It should feel like a
control surface for repeated work.

## Primary Screens

### Home / Overview

Shows current Brew, next Shot, Dashboard status, Doctor status, Release Check
status, Fleet status, and recent evidence.

### Ask Coffee

Lets the human type an Order. Brew 27 should keep this local-only. It can draft
plans, commands, and evidence-backed answers using local tools, but it must not
call remote Beans.

### Evidence Bundle

Runs the Local Evidence Bundle tool for a query and displays path, heading,
snippet, score, freshness, safety classification, and reason selected.

### Doctor

Shows a summarized Doctor result, grouped by severity, with safe next actions.

### Release Check

Shows release readiness, blockers, warnings, and tag status.

### Fleet

Shows registered projects, missing registry state, project status, and safe
next actions.

### Ledger

Shows local cost/token/workflow evidence and recent entries.

### Roastery

Shows summarized evaluation evidence. It must not inspect raw local Cup Test
outputs by default.

### Settings / Safety

Shows local roots, allowed tools, approval gates, exclusion rules, and future
remote Bean policy.

## Brew 27 MVP Screens

Brew 27 should implement only:

- Home / Overview;
- Ask Coffee local-only;
- Evidence Bundle;
- Doctor summary;
- Fleet summary.

Everything else can remain a placeholder or link to CLI guidance.

## Not In MVP

Brew 27 must not include:

- remote model calls;
- OpenRouter calls;
- automatic Git commits;
- background autonomous agent behavior;
- editing files from the UI;
- raw Roastery output inspection;
- dependency installation from inside the UI;
- deployment or cloud features.

## Safe Tool Integration

The UI should call existing Project Coffee tools through subprocess wrappers:

- use argument lists, not shell strings;
- never concatenate user text into a shell command;
- allowlist supported commands and flags;
- show the command before execution;
- show stdout, stderr, and exit code after execution;
- capture failures without crashing the UI;
- default to read-only commands;
- keep write-capable commands disabled unless explicitly approved.

Initial allowlisted local commands:

- `python tools/coffee.py dashboard --root PATH`
- `python tools/coffee.py doctor --root PATH`
- `python tools/coffee.py release-check --root PATH`
- `python tools/coffee.py ledger-summary --root PATH`
- `python tools/coffee.py evidence-bundle --root PATH --query TEXT`
- `python tools/coffee.py fleet-status --root PATH`

Future commands can be added only when the safety and approval behavior is
documented.

## Approval Gates

The UI must require approval before:

- remote model calls;
- sending local evidence to a remote Bean;
- reading paths outside registered project roots;
- running write-capable template install with `--apply`;
- Git operations;
- dependency installs;
- House Blend changes;
- destructive commands;
- deployment, cloud, database, firmware, or hardware-facing actions.

## UI States

The UI should represent these states clearly:

- clean;
- warning;
- blocker;
- local-only;
- approval required;
- command failed;
- no evidence found;
- project not registered;
- remote disabled;
- tag not created.

## Future Routing Display

When routing is implemented, the UI should show:

- selected mode;
- selected Bean, if any;
- whether approval is required;
- why the route was chosen;
- what context would be sent;
- fallback plan;
- local evidence used.

The UI should default to Decaf or local evidence only when policy is uncertain.

## Safety Copy

Recommended UI copy:

- "Coffee can draft commands, but you review and run commits."
- "Remote Bean calls require approval."
- "Secrets and raw local outputs are excluded."
- "Local evidence is shown before remote context is sent."
- "No tag or commit is automatic."

## Brew 27 File Structure Proposal

Proposed files for the Streamlit MVP:

- `ui/coffee_counter_app.py`
- `ui/README.md`
- `tests/test_coffee_counter_ui.py`

The test file is practical only if Brew 27 adds a small command-wrapper helper
that can be tested without launching Streamlit. If the first UI is mostly view
composition, manual local validation may be enough for the first shot.

## Streamlit Dependency Policy

- Brew 26 adds no dependency.
- Brew 27 may add Streamlit only with explicit approval.
- Brew 27 should document setup, run command, validation command, and rollback.
- Streamlit should stay local-only.
- Any future React + Tauri migration requires a separate design and approval.

## Brew 27 Acceptance Criteria

Brew 27 MVP is acceptable when:

- Streamlit app opens locally;
- Home / Overview shows current Brew and next Shot;
- Dashboard summary appears;
- Doctor summary appears;
- Fleet summary appears;
- Evidence Bundle query works locally;
- Ask Coffee accepts an Order and produces local-only guidance;
- commands are run through allowlisted argument-list wrappers;
- stdout, stderr, and exit code are visible;
- no remote model/API calls are made;
- no files are edited from the UI;
- no raw Roastery outputs are inspected;
- no commits or tags are created;
- setup and run instructions are documented.

## Brew 26B Workflow Review

Date: 2026-07-08

The design was reviewed against ten realistic Coffee Counter workflows before
Streamlit implementation.

| # | Workflow | Design support | Brew 27 implication |
| --- | --- | --- | --- |
| 1 | User opens Coffee Counter for current project status | Supported by Home / Overview, Dashboard, Doctor, Release Check, current Brew, and next Shot panels | Implement status cards from existing CLI output first |
| 2 | User asks "What should I do next?" | Supported by Ask Coffee local-only plus Evidence Bundle, Brew Log, and Roadmap grounding | Use local evidence and deterministic templates; no remote Bean |
| 3 | User asks for next prompt set | Mostly supported by Ask Coffee prompt previews and command blocks | Draft prompt/checklist text only; do not edit files or commit |
| 4 | User asks "Why is this project warning?" | Supported by Doctor summary, finding details, and safe next action display | Preserve severity, finding code, path, and suggested action |
| 5 | User asks "Which projects need attention?" | Supported by Fleet screen and project/fleet selector | Handle missing `fleet/projects.json` as an informational state |
| 6 | User asks "Can Coffee send this to a model?" | Supported for future UI by routing panel, context preview, and approval gate | MVP should show remote disabled and explain approval requirements |
| 7 | User asks "Run validation." | Supported by allowlisted subprocess command model | Implement command preview, stdout, stderr, exit code, and failure state |
| 8 | User asks "Commit this." | Supported by safety copy and Git approval gate | MVP should show a commit checklist only; no Git write operation |
| 9 | Doctor or Release Check returns warning | Supported by warning state, right panel, and next safe action | Make warning status visible on Home and details screen |
| 10 | Evidence Bundle returns no matches | Supported by no evidence found UI state | Show honest no-evidence message and query refinement suggestions |

Review result: the design supports the target workflows well enough for a
Streamlit MVP, as long as Brew 27 keeps Ask Coffee local-only and implements
command execution through a small allowlisted wrapper.

## Gaps Found

- The design needs a concrete command-wrapper helper in Brew 27 so Streamlit can
  call existing CLI tools without shell strings.
- Ask Coffee needs a local-only response strategy: evidence bundle plus
  deterministic prompt/checklist templates, not an LLM.
- Warning details should preserve source path, severity, finding code, and safe
  next action.
- Evidence no-match handling should be explicit and should suggest narrower
  queries or source filters.
- Remote routing should be visible but disabled in the MVP.
- Commit requests should produce a checklist only; no staging, commit, tag, or
  push path should exist in Brew 27.
- Fleet Status needs a friendly missing-registry state because that is normal
  for a fresh Project Coffee root.

## Brew 27 Implementation Notes

Brew 27 should implement:

- Streamlit app shell with Home / Overview;
- local command-wrapper helper using argument lists;
- Dashboard summary card;
- Doctor warning summary and details;
- Fleet summary with missing-registry handling;
- Evidence Bundle query form and result display;
- Ask Coffee local-only text area that drafts next-step guidance from local
  evidence;
- command preview and result display with stdout, stderr, and exit code;
- explicit disabled state for remote model calls and Git write actions.

Brew 27 should keep out of MVP:

- remote model calls;
- OpenRouter calls;
- sending local evidence to remote Beans;
- file editing from the UI;
- raw Roastery output inspection;
- Git staging, commit, push, or tag operations;
- background agent behavior;
- React + Tauri migration work.

## Open Questions After Brew 26B

- Should Brew 27 add Streamlit as a root dependency or keep it app-local?
- Which status cards are essential for the first screen?
- Should Ask Coffee be implemented as simple deterministic templates first, or
  as a small local planner wrapper around Evidence Bundle output?
