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
