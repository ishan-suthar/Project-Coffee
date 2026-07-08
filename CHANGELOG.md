# Changelog

All notable changes to Project Coffee are recorded here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Phase 1 operational skeleton (Shot 1): Brew Log, Pantry, Roastery, Ledger, Recipes structure.
- `.gitignore` aligned with Spill Guard.
- `ROADMAP.md` as living Phase 1 roadmap.

### Added (Shot 2)

- `baristas/barista_orchestrator.md`, `espresso_fast_coder.md`, `sentinel_review.md`
- `recipes/coding/small-feature-with-tests.md`
- Cursor rules: work modes, approval gates, Spill Guard, closeout ritual
- `!ledger/token_log.md` exception in `.cursorignore` and `.cursorindexingignore`

### Added (Shot 3A)

- `config/house_blend.md` — House Blend model-routing policy
- `DECISIONS/ADR-0004-house-blend-routing.md`
- `tools/cursor_openrouter_setup.md` — Cursor + OpenRouter setup (no secrets in repo)

### Added (Brew 1 / Coffee Status MVP)

- Coffee Status app skeleton, minimal Streamlit page, project root display, safe Markdown readers, and previews for Active Context, Roadmap, and House Blend.
- Static and manual runtime verification completed; root-resolution bug found and fixed.

### Changed (Brew 1 closeout)

- Marked Coffee Status MVP complete after static and runtime verification, including the project-root fix.
- Added closeout coverage through status docs, retrospective, ledger estimate, and Roastery workflow scorecard.

### Added (Brew 2 / Prompt Library MVP)

- Added `prompts/` skeleton for local prompt artifacts.
- Added reusable Espresso Shot prompt template.
- Added first approved Espresso Shot prompt artifact.
- Completed Prompt Library verification for structure, clarity, safety, and reuse value.

### Changed (Brew 2 closeout)

- Marked Prompt Library MVP complete after adding the `prompts/` skeleton, reusable Espresso Shot template, first approved prompt artifact, and verification.
- Recorded that verification caught and fixed an untracked prompt artifact gap.
- Added closeout coverage through status docs, retrospective, ledger estimate, and Roastery workflow scorecard.

### Changed (Brew 3 / Coffee Status hardening)

- Added a plain Python Coffee Status data model, focused unit tests, and a local status builder for the MVP tracked files.
- Refactored the Streamlit app to consume the status builder/model while preserving the existing dashboard behavior.
- Runtime verified the refactored dashboard with Streamlit AppTest; Ledger and Roastery contents remain hidden.

### Added (Brew 4 / Token efficiency foundation)

- Added Pantry Lite under `knowledge/` with a context index, Project Coffee foundation summary, and usage verification.
- Added Recipes and Baristas skeletons, including a reusable Decaf planning Recipe.
- Added Barista role cards for Main Barista, Espresso Fast Coder, Mocha Python/AI, Cappuccino Research, Macchiato Embedded, Flat White Code Review, and Cortado DevOps/Infra.
- Added a Barista role selection guide and read-only role usage test to support short, focused Orders.

### Added (Brew 7 / Coffee Certification Project)

- Added `apps/coffee-certification/`, a dependency-free Python CLI/checklist for validating Coffee workflow certification steps.
- Added focused `unittest` coverage for complete, incomplete, normalized, duplicate, unexpected, and CLI behavior.
- Added Brew 7 trace entries across the Brew Log, Roastery workflow scorecards, Coffee Ledger, and Roadmap status.

### Added (Brew 11 / Template Installer)

- Added a standard-library Project Coffee template installer and onboarding doctor.
- Added focused tests for dry-run, apply, force overwrite, missing paths, summary output, and doctor mode.
- Added Template Installer Guide documentation for dry-run, apply, force, and check workflows.
- Dogfooded the installer against a scratch target and recorded local validation evidence.

### Changed (Brew 12 / Roastery full-output evidence)

- Added optional local full-output capture for Cup Tests and ignored the raw output directory.
- Recorded scored Roastery evidence from captured run `brew12-20260706-014748` without committing raw outputs.
- Updated House Blend confidence while keeping the recommendation provisional and task-limited.

### Added (Brew 13 / Pantry Search MVP)

- Added `tools/pantry_search.py`, a standard-library local Markdown search tool with `--root`, `--query`, `--max-results`, `--json`, snippets, heading context, and sensitive-path skips.
- Added focused Pantry Search tests plus the Pantry Search Guide and Pantry Intake Guide.
- Expanded the Project Coffee template Pantry index with source quality, freshness, keyword, and safety guidance.
- Dogfooded Pantry Search against Project Coffee docs and a scratch Pantry target, including human-readable output, JSON output, no-results behavior, max-results behavior, and sensitive-path skip evidence.
- Marked the Pantry Search / Local RAG foundation MVP complete and set next recommended work to Brew 14A, the Roastery multi-task benchmark pack.

### Changed (Brew 14 / Roastery multi-task benchmark)

- Added a repeatable Roastery Cup Test benchmark pack and runner support for `--order-file`, `--list-cup-tests`, and `--cup-test-dir`.
- Recorded captured-output benchmark evidence for the repo-map, tiny Python fix, docs summary, and Pantry-assisted answer Orders without committing raw outputs.
- Updated House Blend confidence: Nemotron remains provisional default across all four benchmark Orders, Cohere remains the main fallback with stricter review for grounded answers, and Poolside remains a comparison/coding/docs fallback with availability and grounding caveats.
- Marked the Roastery multi-task benchmark pack complete and set next recommended work to Brew 15A, the Roastery report generator.

### Added (Brew 15 / Roastery report generator)

- Added a standard-library Roastery report generator for draft Markdown and JSON summaries from local Cup Test manifests.
- Added tests and the Roastery Report Guide.
- Dogfooded Markdown, JSON, combined-run, capped-preview, and saved-draft report generation against existing local Cup Test outputs.
- Ignored local generated reports under `roastery/local_reports/` and kept raw outputs under `roastery/local_cup_outputs/` local-only.
- Marked the Roastery report generator complete and set next recommended work to Brew 16A, the cost/token summarizer.

### Added (Brew 16 / Coffee Dashboard)

- Added `tools/coffee_dashboard.py`, a standard-library local dashboard for Project Coffee workflow health checks.
- Added focused tests and the Coffee Dashboard Guide, linked from the docs index.
- Dogfooded human-readable output, JSON output, section filtering, strict missing-core checks, and incomplete scratch-root reporting without model or API calls.
- Recorded dashboard evidence in Roastery and Ledger, then marked the Coffee Dashboard complete and set next recommended work to Brew 17A, Coffee Doctor.

### Added (Brew 17 / Coffee Doctor)

- Added `tools/coffee_doctor.py`, a standard-library read-only health diagnosis tool for Project Coffee.
- Added focused tests and the Coffee Doctor Guide, linked from the docs index.
- Dogfooded root diagnosis, JSON output, section filtering, strict fail-on-issue behavior, and incomplete scratch-root failure behavior without model or API calls.
- Recorded the existing root Doctor warning for `docs/adr/0005-local-openrouter-coffee-core.md` as honest evidence without changing the ADR in this closeout.
- Marked Coffee Doctor complete and set next recommended work to Brew 18A, Unified Coffee CLI.

### Added (Brew 18 / Unified Coffee CLI)

- Added `tools/coffee.py`, a standard-library wrapper CLI for dashboard, doctor, Pantry Search, Roastery report, template install, and onboarding check commands.
- Added focused delegation tests and the Unified Coffee CLI Guide, linked from the docs index.
- Dogfooded help, version, dashboard, doctor, Pantry Search, onboarding check, template dry-run, Roastery report, JSON forwarding, section forwarding, and fail-flag forwarding without model or API calls.
- Marked Unified Coffee CLI complete and set next recommended work to Brew 19, Cost / Token Ledger Summarizer.

### Added (Brew 19 / Ledger Summarizer)

- Added `tools/ledger_summary.py`, a standard-library local Ledger summarizer for cost, token, local-only, model/API, unknown, and recent-entry evidence.
- Added focused tests and the Ledger Summary Guide, linked from the docs index.
- Integrated `ledger-summary` into the Unified Coffee CLI.
- Dogfooded root summaries, JSON mode, max entries, date filtering, output report mode, missing-ledger failure, invalid-date failure, scratch Ledger parsing, and Unified CLI delegation without model or API calls.
- Fixed bullet-style Ledger parsing for `Cost:`, `Tokens:`, `Model/API calls:`, `Evidence:`, and `Notes:` fields after dogfood evidence exposed a scratch parsing gap.
- Marked Ledger Summarizer complete and set next recommended work to Brew 20, Release Packaging.

### Added (Brew 20 / Release Packaging)

- Added `tools/release_check.py`, a standard-library read-only release readiness checker for repo, docs, tools, templates, safety, evidence, and tag reporting.
- Added focused tests and the Release Packaging Guide, linked from the docs index.
- Integrated `release-check` into the Unified Coffee CLI.
- Dogfooded help, root checks, JSON mode, docs/tools/safety/tags section filtering, strict fail-on-blocker behavior, incomplete scratch-root blockers, focused tests, syntax compilation, and Unified CLI delegation without model or API calls.
- Confirmed existing release tags are reported but not changed by the checker.
- Marked Release Packaging complete and set next recommended work to Brew 21, Local RAG Design Only.

### Added (Brew 21 / Local RAG Design)

- Added `docs/design/local-rag-design.md` for a local-first evidence bundle layer before embeddings, vector search, model calls, or chat UI implementation.
- Added the Local RAG Guide and linked it from the docs index.
- Defined retrieval sources, excluded sources, retrieval levels, evidence bundle format, grounding rules, query classes, safety rules, remote Bean approval model, integration plan, future UI dependency, and Brew 22 MVP scope.
- Reviewed the design against ten realistic Project Coffee questions and recorded gaps around source profiles, release-proof evidence, freshness scoring, and conflict handling.
- Marked Local RAG Design complete and set next recommended work to Brew 22, Local RAG MVP.

### Added (Brew 22 / Local RAG MVP)

- Added `tools/evidence_bundle.py`, a standard-library Local Evidence Bundle tool for safe allowlisted keyword retrieval over Project Coffee files.
- Added focused tests covering help, source listing, query retrieval, JSON, output mode, source narrowing, excluded paths, `.env` avoidance, raw-output avoidance, binary skips, zero-match behavior, and no OpenRouter key requirement.
- Integrated `evidence-bundle` into the Unified Coffee CLI.
- Updated the Local RAG guide and design docs to document MVP usage, JSON/output modes, source narrowing, safety boundaries, and non-goals.
- Dogfooded realistic Project Coffee evidence queries and scratch safety fixtures without embeddings, vector DB, model calls, external APIs, secrets, or raw Roastery output inspection.
- Marked Local RAG MVP complete and set next recommended work to Brew 23, Model Routing Policy Refinement.

### Added (Brew 23 / Model Routing Policy Refinement)

- Added `docs/design/model-routing-policy.md` to define routing modes, task classes, current Bean roles, approval gates, routing inputs/outputs, safety gates, fallback behavior, Roastery update rules, and future UI implications.
- Updated House Blend documentation and config to reference the routing policy while keeping current Bean roles provisional and evidence-based.
- Reviewed the policy against ten realistic Project Coffee scenarios and recorded gaps around context previews, explicit fallback consent, and Brew 24 fleet support.
- Marked Model Routing Policy Refinement complete and set next recommended work to Brew 24, Multi-project Fleet Support.

### Added (Brew 24 / Multi-project Fleet Support)

- Added `tools/fleet_status.py`, a standard-library local fleet registry/status tool for safe Project Coffee onboarding marker checks across registered projects.
- Added `fleet/projects.example.json`, focused Fleet Status tests, the Fleet Support Guide, docs index link, and Unified Coffee CLI `fleet-status` delegation.
- Dogfooded missing/default registry behavior, example registry parsing/listing, scratch complete/incomplete project checks, project filtering, JSON output, strict fail-on-issue behavior, tests, compile checks, and Unified Coffee CLI delegation without model or API calls.
- Marked Multi-project Fleet Support complete and set next recommended work to Brew 25, v1.0 Release Closeout.

### Added (Brew 25 / v1.0 Release Closeout)

- Added the v1.0 stronger-base closeout checklist for docs, safety, tools, evidence, release readiness, tag policy, and future UI prerequisites.
- Added the v1.0 handoff framework summarizing architecture, completed Brews, tool inventory, safety rules, House Blend, validation, onboarding, and future UI direction.
- Linked release closeout docs from the docs index and added a brief closeout note to the Project Coffee Operating Manual.
- Updated the roadmap to point from stronger-base closeout toward the future Coffee Counter UI sequence.
- Dogfooded the v1.0 stronger-base validation stack and recorded readiness as READY WITH WARNINGS; Release Check passed with no blockers, focused tests and compile checks passed, and no tag was created.
- Closed the stronger-base phase as READY WITH WARNINGS, documented optional manual tag commands, and set next recommended work to Brew 26 Coffee Counter UI Design.

### Added (Brew 26 / Coffee Counter UI Design)

- Added the Streamlit-first Coffee Counter UI design and guide.
- Defined the UI purpose, layout, screens, Brew 27 MVP scope, non-MVP boundaries, safe tool integration model, approval gates, UI states, future routing display, safety copy, proposed Brew 27 file structure, and Streamlit dependency policy.
- Reviewed ten realistic Coffee Counter workflows before implementation and recorded gaps for command wrappers, local-only Ask Coffee, warning details, no-evidence handling, and disabled remote/Git write actions.
- Marked Coffee Counter UI Design complete and set next recommended work to Brew 27, Streamlit Coffee Counter MVP.

### Added (Brew 27 / Streamlit Coffee Counter MVP)

- Added `ui/coffee_counter_app.py`, `ui/README.md`, and focused Coffee Counter UI adapter tests.
- Built the first local-only Streamlit Coffee Counter MVP with Home / Overview, Ask Coffee, Evidence Bundle, Ledger, Fleet, and Safety / Commands areas.
- Kept the command adapter allowlisted, testable without importing Streamlit, and limited to local Coffee CLI tools.
- Dogfooded tests, syntax compilation, wrapped Coffee CLI commands, adapter safety checks, Streamlit server health, and Streamlit tab/button behavior without model/API calls, OpenRouter calls, package installs, raw-output inspection, staging, or commits.
- Marked the Streamlit Coffee Counter MVP complete and set next recommended work to Brew 28, UI + Evidence Bundle Integration.

### Added (Brew 28 / UI + Evidence Bundle Integration)

- Improved Ask Coffee so it runs the local Evidence Bundle tool in JSON mode and displays structured evidence status, source paths, snippets, scores, freshness, and safety labels.
- Added deterministic local-only evidence drafts that are clearly labeled as not model-generated and include local evidence references when available.
- Improved Evidence Bundle display with Markdown output, JSON parsing, structured evidence rows, no-evidence handling, and graceful JSON parse-error handling.
- Dogfooded focused tests, syntax compilation, evidence JSON, zero-match behavior, Doctor, Release Check, Ledger Summary, Fleet Status, Streamlit server health, and Streamlit UI harness flows without model/API calls, OpenRouter calls, package installs, raw-output inspection, staging, or commits.
- Marked UI + Evidence Bundle Integration complete and set next recommended work to Brew 29, UI + Routing Approval Gates.

### Added (Brew 29 / UI + Routing Approval Gates)

- Added routing approval gates to the Coffee Counter UI with a Routing / Approval tab, request classification, route decisions, visible approval requirements, allowed/blocked context, next safe actions, and preview-only context scaffolding.
- Updated Ask Coffee so local questions show the routing decision before local evidence results.
- Kept future remote Bean behavior documented but disabled: no remote model button, no OpenRouter call control, and no API key input were added.
- Dogfooded focused tests, syntax compilation, Evidence Bundle JSON, Doctor, Release Check, Ledger Summary, Fleet Status, Streamlit routing smoke, and six Ask Coffee routing scenarios without model/API calls, raw-output inspection, staging, or commits.
- Marked UI + Routing Approval Gates complete and set next recommended work to Brew 30, UI Packaging / Polish Decision.

### Added (Brew 30 / UI Packaging and Polish Decision)

- Added `docs/design/ui-packaging-and-polish-plan.md` to decide the near-term Coffee Counter UI packaging and polish direction.
- Kept Streamlit as the working UI and documented React/Tauri as a later optional migration.
- Documented the manual Streamlit run command, future helper script option, future `requirements-ui.txt` option, polish backlog, safety constraints, migration criteria, and non-goals.
- Reviewed ten packaging/polish scenarios and found no blocking gaps.
- Marked UI Packaging / Polish Decision complete and set next recommended work to Brew 31, Streamlit Polish Pass.

### Added (Brew 31 / Streamlit Polish Pass)

- Improved Ask Coffee current-state handling with Current State Quick View for current Brew, next Shot, blocker, and "where are we" questions.
- Prioritized current-state evidence toward Brew Log, Roadmap, and Changelog files without bypassing the local Evidence Bundle flow.
- Added clearer route badge text, grouped command output sections, improved evidence item display, no-evidence suggestions, and project-root visibility.
- Added focused tests for current-state detection, priority ordering, quick-view safety, route badges, suggestions, command summaries, malformed JSON handling, adapter safety, no `shell=True`, and no OpenRouter key requirement.
- Dogfooded tests, syntax compilation, current-state and zero-match Evidence Bundle queries, Doctor, Release Check, Ledger Summary, Fleet Status, Streamlit server health, and UI harness scenarios without model/API calls, package installs, raw-output inspection, staging, or commits.
- Marked Streamlit Polish Pass complete and set next recommended work to Brew 32, Coffee Counter Project/Fleet Switching.

### Added (Brew 32 / Coffee Counter Project and Fleet Switching)

- Improved the Coffee Counter sidebar with active-root display, root validation, shallow Project Coffee marker scoring, and session-only recent roots.
- Added Project Health to the Home tab with root existence, marker score, safe local-only status, and last command status.
- Wired Ask Coffee, Current State Quick View, Evidence Bundle, Routing preview, Ledger, and Fleet to the selected active root.
- Improved Fleet tab output with active-root visibility, optional registry path argument handling, status summary cards, missing/empty registry warnings, and simple registered-project rows.
- Added focused tests for root normalization, marker scoring, root validation, session-only recent roots, active-root command arguments, Fleet registry argument safety, no `shell=True`, disallowed command rejection, and no OpenRouter key requirement.
- Dogfooded tests, syntax compilation, Fleet Status, Evidence Bundle, Doctor, Release Check, Ledger Summary, Streamlit server health, valid-root startup, invalid-root blocking, valid-root recovery, session-only recent roots, Fleet tab behavior, existing tabs, and safety controls without model/API calls, package installs, persistent config writes, raw-output inspection, staging, or commits.
- Marked Coffee Counter Project/Fleet Switching complete and set next recommended work to Brew 33, Remote Call Approval Design.

### Added (Brew 33 / Remote Call Approval Design)

- Added `docs/design/remote-call-approval-design.md` to define the future approval-gated remote Bean workflow without implementing remote calls.
- Documented approval states, context package schema, safety/redaction policy, model/provider selection policy, Ledger requirements, UI design, failure/cancel states, testing strategy, implementation roadmap, and open questions.
- Updated Coffee Counter UI docs to clarify that current approval gates remain preview-only and the UI still has no OpenRouter call, API key input, network code, or working send-to-model button.
