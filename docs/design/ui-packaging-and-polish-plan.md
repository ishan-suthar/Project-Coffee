# UI Packaging and Polish Plan

Status: Brew 30A design
Date: 2026-07-08

## Purpose

This plan decides the near-term packaging and polish direction for the Coffee
Counter UI after the Streamlit MVP, Evidence Bundle integration, and Routing
Approval Gates.

The goal is to make the existing local UI easier to start, explain, test, and
use before considering a larger UI rewrite.

## Decision

Keep Streamlit as the working Coffee Counter UI for now.

React and Tauri remain a later optional migration path. Project Coffee should
not migrate yet because the important work is still workflow stabilization:
evidence display, routing approval gates, fleet switching, command ergonomics,
and safety copy. Rewriting the shell before those workflows settle would spend
energy on packaging before the product shape is proven.

## Current UI State

The Coffee Counter UI currently provides:

- Home / Overview for local Dashboard, Doctor, Release Check, and Fleet Status;
- Ask Coffee local-only evidence retrieval;
- structured Evidence Bundle display;
- deterministic local-only evidence drafts;
- Ledger Summary access;
- Fleet Status access;
- Safety / Commands visibility;
- Routing / Approval gates with preview-only context behavior.

It intentionally does not provide:

- remote model calls;
- OpenRouter calls;
- API key input;
- file editing;
- Git staging, commits, pushes, or tags;
- raw Roastery local-output inspection;
- arbitrary command execution.

## Packaging Options

### Current Manual Command

Use the existing manual command from the Project Coffee root:

```powershell
python -m streamlit run ui/coffee_counter_app.py
```

This remains the supported path during Brew 30.

### Helper Script Later

A future Brew may add:

```text
scripts/start_coffee_counter.ps1
```

The helper should be small, readable, local-only, and free of hidden side
effects. It should launch the existing Streamlit app and print clear failure
messages when Streamlit is missing.

### UI Requirements File Later

A future Brew may add:

```text
requirements-ui.txt
```

This should happen only if Project Coffee wants a separate, explicit UI
dependency path. Tests for helper functions should remain runnable without
Streamlit installed.

### Optional Local Desktop Wrapper Later

A local desktop wrapper can be considered after the Streamlit workflow is
stable. It should not change Coffee's safety model.

### React / Tauri Later

React and Tauri should wait until the UI workflow proves that Streamlit is the
limiting factor. The migration should preserve local-first execution,
allowlisted commands, approval gates, and no hidden remote calls.

## Polish Backlog

Recommended polish items:

- better current Brew retrieval ranking;
- clearer cards for Dashboard, Doctor, and Release Check outputs;
- improved evidence item display;
- route decision badges;
- UI state colors and icons;
- recent command history;
- project root persistence;
- fleet project switching;
- no-evidence suggestions;
- tests for routing and evidence helpers;
- documentation screenshots later.

## Safety Constraints

Coffee Counter packaging and polish must preserve these constraints:

- no remote model call by default;
- no API key input in the MVP;
- no auto-commit;
- no arbitrary command execution;
- no secret inspection;
- no raw Roastery local-output inspection;
- explicit human approval before any future remote Bean call;
- visible command arguments before execution;
- local-only default behavior.

## Proposed Brew 31+ Paths

### Option A: Polish First

- Brew 31: Streamlit polish pass.
- Brew 32: UI project and fleet switching.
- Brew 33: optional local remote-call approval design.

### Option B: Packaging First

- Brew 31: requirements and start script.
- Brew 32: polish.
- Brew 33: package decision.

## Recommendation

Choose Option A.

The UI is already startable with one command. The next bottleneck is usability:
status cards, clearer evidence display, routing badges, no-evidence guidance,
and fleet/project ergonomics. A helper script and requirements file are useful,
but they should follow once the UI surface is a little more comfortable.

## Future Packaging Acceptance Criteria

A future packaging implementation is acceptable when:

- there is an easy start command;
- setup is documented;
- there are no hidden side effects;
- local-only behavior remains the default;
- tests remain unaffected by Streamlit availability;
- failures are clear when Streamlit is missing;
- the helper does not run model, Git, network, or write-capable workflows.

## React / Tauri Migration Criteria

Consider React/Tauri only when one or more of these are true:

- Streamlit layout becomes limiting;
- Project Coffee needs a packaged desktop app;
- Project Coffee needs richer interactive UX;
- Project Coffee needs a multi-window or multi-project workspace;
- UI workflows are stable enough to justify a rewrite;
- the safety model can be preserved without ambiguity.

## Non-Goals

Brew 30 does not include:

- production installer work;
- remote model call implementation;
- cloud deployment;
- hosted app work;
- Langflow integration;
- React/Tauri migration;
- dependency installation;
- packaging scripts;
- API key handling.

## Next Recommended Work

Recommended near-term path:

1. Brew 30B - review and dogfood this packaging / polish plan.
2. Brew 30C - close the packaging / polish decision if the plan holds.
3. Brew 31 - Streamlit polish pass.
4. Brew 32 - UI project and fleet switching.
5. Brew 33 - optional remote-call approval design, still local-first and gated.
