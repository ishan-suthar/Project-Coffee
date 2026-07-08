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
