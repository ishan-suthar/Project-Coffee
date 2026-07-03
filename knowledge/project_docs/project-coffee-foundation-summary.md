# Project Coffee Foundation Summary

Status: Pantry Lite summary
Source set: `README.md`, `VISION.md`, `ROADMAP.md`,
`brew-log/active_context.md`, `brew-log/progress.md`, `CHANGELOG.md`,
`config/house_blend.md`, `prompts/README.md`, `apps/coffee-status/README.md`
Last updated: 2026-07-03

## What Project Coffee Is

Project Coffee is a local-first, model-agnostic AI engineering operating system.
Its durable assets are memory, knowledge, recipes, evaluation discipline,
prompt artifacts, and human-controlled workflows. Models, IDEs, and gateways are
replaceable implementation details.

## Current Completed Brews

- Brew 1 / Coffee Status MVP: built a local read-only Streamlit dashboard for
  Project Coffee status files.
- Brew 2 / Prompt Library MVP: created a local prompt archive, reusable Espresso
  Shot template, and first approved prompt artifact.
- Brew 3 / Coffee Status hardening: added a plain Python status model, tests,
  local builder, app wiring, and runtime verification while preserving the MVP UI
  and keeping Ledger and Roastery contents hidden.

## Current Token-Efficiency Goal

Brew 4 focuses on reducing token waste. The immediate strategy is Pantry Lite:
short local summaries and source pointers that help future agents read only the
context needed for a shot.

## Key Local Folders

| Folder | Use |
| --- | --- |
| `brew-log/` | Live memory: active context, progress, decisions, lessons, and retrospectives. |
| `knowledge/` | Token-efficient summaries and retrieval pointers. Start here after active context. |
| `apps/coffee-status/` | Local Streamlit dashboard and tests for Coffee Status. |
| `prompts/` | Prompt templates and approved prompt artifacts. |
| `config/` | Configuration-like project policy, including House Blend routing. |
| `ledger/` | Cost and token records. Do not inspect unless the shot allows it. |
| `roastery/` | Model and workflow evaluation records. Do not inspect unless the shot allows it. |
| `recipes/` | Reusable workflows for repeated task types. |
| `DECISIONS/` | Architecture decision records. Read when changing durable policy. |

## How Agents Should Use This

1. Read `brew-log/active_context.md`.
2. Read `knowledge/00_index.md`.
3. Read this summary if the task needs general Project Coffee context.
4. Open raw source docs only when this summary or the index says they are needed.
5. Keep shots small, avoid broad folder scans, and do not read Ledger, Roastery,
   config, or app code unless the shot scope allows it.

## Notes And Caveats

- This is a retrieval aid, not a replacement for source documents.
- For exact current status, prefer `brew-log/active_context.md` and `ROADMAP.md`.
- For safety and repo rules, prefer `AGENTS.md`.
- For model routing and escalation, prefer `config/house_blend.md`.
