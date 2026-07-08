# Project Coffee Counter UI

Status: Brew 31 complete

The Coffee Counter UI is a local Streamlit control panel for Project Coffee. It
wraps existing safe Project Coffee CLI tools through an allowlisted command
adapter.

## Purpose

The MVP helps you:

- view Project Coffee status;
- run Dashboard, Doctor, Release Check, Ledger Summary, Evidence Bundle, and
  Fleet Status from a local UI;
- ask Coffee for local evidence only;
- ask "What is the current Brew?" and see a Current State Quick View from
  Brew Log, Roadmap, and Changelog files;
- inspect structured Evidence Bundle items and local snippets;
- draft a simple grounded local answer without model generation;
- preview local-only routing decisions and future approval gates;
- preview eligible local evidence context without sending it anywhere;
- see command arguments, stdout, stderr, and exit codes;
- keep approval gates visible before future remote model work.

## Requirements

- Python
- Streamlit
- Project Coffee repository opened locally

The tests for the command adapter do not require Streamlit.

## Setup

Install Streamlit only after approving the dependency:

```powershell
python -m pip install streamlit
```

## Run

From the Project Coffee root:

```powershell
python -m streamlit run ui/coffee_counter_app.py
```

## Packaging Status

The supported launch path is still the manual Streamlit command above. Brew 30A
keeps Streamlit as the working Coffee Counter UI and defers React/Tauri until
the UI workflows are stable enough to justify a rewrite.

Future packaging options may include:

- a small `scripts/start_coffee_counter.ps1` helper;
- a dedicated `requirements-ui.txt`;
- a local desktop wrapper;
- React/Tauri after the Streamlit workflow proves its limits.

Current decision: keep Streamlit for now and polish the existing UI before
adding packaging helpers or considering React/Tauri migration.

## Brew 31 Polish

Brew 31 improved day-to-day usability while keeping the UI local-only:

- Current State Quick View appears for current Brew / next Shot / blocker
  questions.
- Current-state evidence is prioritized toward `brew-log/active_context.md`,
  `brew-log/progress.md`, `ROADMAP.md`, and `CHANGELOG.md`.
- Route badges make Local evidence only, Approval required, Roastery required,
  Manual-only Git, and Decaf / no model decisions easier to scan.
- Command output is grouped into command, return code, status summary, stdout,
  and stderr sections.
- Evidence rows show source/path, heading, line, snippet, match/rank, freshness,
  and safety labels when available.
- No-evidence states now show concrete suggestions.

Brew 31B dogfood confirmed current-state questions, next-action questions,
approval-required repo-context previews, zero-match evidence states, Home /
Overview command output, Ledger Summary, and safety controls. No product fixes
were required during dogfood.

No model call is made. No OpenRouter call is made. No API key input, file edit,
Git write, package install, arbitrary command execution, or remote execution
path is added.

## Brew 28 Evidence Integration

Ask Coffee now runs the local Evidence Bundle command in JSON mode and renders:

- evidence status;
- top source paths, headings, snippets, scores, freshness, and safety labels;
- the exact safe CLI command that was run;
- a deterministic local evidence draft.

The draft is labeled as local evidence only. It is not model-generated and it
does not call OpenRouter, remote Beans, or external APIs. If no evidence is
found, the UI says evidence is insufficient and asks for a narrower query or
local validation.

The Evidence Bundle tab keeps the Markdown command output visible and also
parses JSON output into a structured table/list when available. Malformed JSON,
zero matches, missing roots, and command errors are shown honestly.

## Brew 29 Routing Approval Gates

Brew 29 adds local-only routing visibility. The Routing / Approval tab shows:

- routing mode choices;
- selected routing mode;
- whether approval would be required;
- the reason for the route;
- allowed and blocked context;
- next safe action;
- a context preview from local evidence snippets.

Remote model calls remain disabled. The context preview is not sent anywhere.
Future remote Bean calls will require explicit approval, and secrets, `.env`
files, credentials, hidden credential directories, and raw local outputs remain
excluded.

## Safety Notes

- The MVP is local-only.
- It does not call OpenRouter.
- It does not call remote Beans.
- It does not call external APIs.
- It does not edit files.
- It does not inspect raw Roastery local outputs.
- It does not stage, commit, push, or create tags.
- It does not expose arbitrary shell command execution.
- It only wraps allowlisted Project Coffee CLI commands.
- It shows approval gates, but it does not execute remote routes.

## Known Limitations

- There is no start helper script yet.
- There is no separate UI requirements file yet.
- There is no desktop wrapper or production installer.
- There is no remote model execution path.
- Project root persistence and fleet project switching still need polish.

## Troubleshooting

- If Streamlit is missing, run the setup command above after approving the
  dependency.
- If a command fails, check the displayed stdout, stderr, and exit code.
- If Evidence Bundle returns no results, try a narrower query or inspect a
  specific local source.
- If a routing decision requires approval, treat it as a preview. Remote
  execution is not implemented in this MVP.
- If Fleet Status reports a missing registry, use `fleet/projects.example.json`
  or intentionally create a local `fleet/projects.json`.
- If Brew status looks stale, run `python tools/coffee.py dashboard --root .`
  and inspect the Brew Log status files.
