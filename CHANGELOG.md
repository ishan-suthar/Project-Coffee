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
