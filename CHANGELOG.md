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
