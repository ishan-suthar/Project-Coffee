# Project Coffee Counter UI

Status: Brew 35 complete

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
- preview a local context package and dry-run approval checklist without
  sending data anywhere;
- preview local-only routing decisions and future approval gates;
- preview eligible local evidence context without sending it anywhere;
- see command arguments, stdout, stderr, and exit codes;
- switch the active project root for local commands;
- inspect root health and session-only recent roots;
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

## Brew 32 Project and Fleet Switching

Brew 32A improves multi-project comfort while staying local-only:

- the sidebar shows the active root path;
- root validation shows whether the path exists, is a directory, and avoids
  blocked credential-like path components;
- Project Coffee marker scoring checks only known marker paths such as
  `tools/coffee.py`, `brew-log/`, `ledger/`, `roastery/`, and `docs/`;
- session-only recent roots live in Streamlit session state and reset when the
  app restarts;
- the Home tab includes a Project Health section;
- Ask Coffee, Current State Quick View, Evidence Bundle, Routing preview,
  Ledger, and Fleet all use the selected active root;
- the Fleet tab shows the active root, optional registry argument, Fleet Status
  command output, return code, registry status, project count, and simple
  registered-project rows when available.

Root choices and recent roots are not written to disk. The UI does not create
or edit Fleet registries in this shot.

Brew 32B dogfood confirmed valid-root startup, Ask Coffee with the selected
root, Evidence Bundle with the selected root, invalid-root blocking, return to
valid root, session-only recent roots, Fleet tab behavior, existing local tool
tabs, and safety controls. No product fixes were required.

## Brew 33 Remote Call Approval Design

Brew 33A adds a design document for a future approval-gated remote Bean call
workflow. It defines context preview, Safety Gate, user approval, provider/model
selection, Ledger recording, and failure/cancel states.

Brew 33B dogfooded the design against realistic future scenarios including
local questions, docs questions, code planning, whole-repo context requests,
secret-risk requests, benchmark requests, missing keys, provider failures,
Ledger write failures, user cancellation, active-root changes, and generated
code responses.

Current UI status is unchanged:

- no remote model calls;
- no OpenRouter calls;
- no external API calls;
- no API key input;
- no working send-to-model button;
- no network code;
- no Git write controls.

The current Routing / Approval tab remains preview-only.

## Brew 34 Context Package Preview

Brew 34A adds a local-only context package builder and Safety Gate. The Routing
/ Approval tab can now build a preview-only context package from the current
request, routing decision, and local Evidence Bundle results.

The preview shows:

- package status;
- active root;
- route decision;
- estimated tokens;
- evidence item count;
- included and excluded item count;
- Safety Gate status;
- warnings or block reasons;
- preview JSON.

The package is not a remote API payload. It is not sent anywhere. Provider and
model fields remain placeholders with no provider and no model selected. User
approval defaults to not approved.

The Safety Gate excludes or blocks unsafe paths and redacts suspicious
secret-like snippets without printing matched values.

Still not present:

- OpenRouter integration;
- API key input;
- model/API calls;
- network code;
- send-to-model button;
- remote execution;
- file writes;
- Git writes;
- auto-commit or auto-push.

The disabled placeholder labeled `Send disabled until future Brew` is not a
working send control. Brew 35 should use this package for dry-run approval UI
only.

Brew 34B dogfood confirmed:

- local current-state and docs packages build from Evidence Bundle items;
- explicit model-help requests route to approval-needed preview mode;
- broad whole-repo context is blocked until narrowed;
- `.env` requests are blocked without reading or printing secret values;
- suspicious token-like text is labeled/redacted without echoing matched
  values;
- selected active root is reflected in the package;
- empty-evidence packages build without crashing.

Fixes made during dogfood:

- Safety Gate now blocks broad repository context from request text.
- Safety Gate now blocks requested blocked path patterns such as `.env`.
- Routing now recognizes explicit model-help and secret-context requests.

Next work is Brew 35: dry-run approval UI around the local context package,
still without remote calls.

## Brew 35 Dry-Run Approval UI

Brew 35A adds a dry-run approval panel to the Routing / Approval tab.

The UI now shows:

- request summary;
- route decision;
- context package preview;
- Safety Gate checklist;
- included and excluded evidence summary;
- required dry-run checklist;
- dry-run Ledger preview;
- disabled future send state.

Dry-run approval is simulation only. It requires an existing context package, a
Safety Gate status that is not blocked, and every required checklist item to be
checked. If the Safety Gate blocks the package, approval controls are disabled
and the UI shows the block reasons.

The Ledger preview is not written automatically. Provider and model remain
placeholders with no provider and no model selected. Estimated cost remains
unknown / not applicable; no pricing logic is present.

No remote call exists yet. Brew 35 has no OpenRouter integration, no API key
input, no provider/model selector, no model/API call, no network code, no
working send-to-model button, no remote execution, no auto-commit, and no
auto-push.

Brew 36 is the earliest possible real OpenRouter integration, if that path is
chosen and explicitly approved later.

## Brew 35B Dogfood and Closeout

Brew 35B dogfooded the dry-run approval UI against approval-needed, local-only,
blocked secret, whole-repository, partial-checklist, complete-checklist,
cancel/reset, and active-root scenarios.

Confirmed behavior:

- approval-needed requests show context package preview, Safety Gate checklist,
  dry-run approval checklist, and Ledger preview;
- partial checklists cannot produce `dry_run_approved`;
- complete checklists can produce `dry_run_approved` for safe
  approval-needed packages;
- local-only requests stay `local_only_no_approval` and do not need dry-run
  approval;
- `.env` and whole-repository requests are blocked and cannot be dry-run
  approved;
- provider/model remain not selected;
- estimated cost remains unknown / not applicable;
- Ledger preview remains preview-only and is not written automatically;
- send remains disabled for a future Brew;
- active root is copied into each newly built package.

No OpenRouter, API key input, model call, network call, provider/model selector,
real send action, remote execution, auto-commit, or auto-push exists in Brew 35.

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
