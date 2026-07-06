# Coffee Status Project Brief

Status: Onboarded skeleton
Date: 2026-07-05

## Purpose

Coffee Status is a local-only dashboard for viewing selected Project Coffee
status files. It helps the human see current Coffee state without exposing
Ledger or Roastery contents as previews.

## Boundaries

- Local-only app.
- No secrets or private data.
- No app behavior changes during skeleton onboarding.
- No dependency changes without human approval.
- Human reviews diffs and commits manually.

## Current Shape

- App entry point: `app.py`
- Source helpers: `src/`
- Tests: `tests/`
- Dependency file: `requirements.txt`
- Framework: Streamlit
- Test runner: Python `unittest`

## First Onboarding Shot

Brew 8 / 8B adds this minimal Project Coffee skeleton so future work has local
rules, memory, evaluation notes, and cost tracking inside the project.
