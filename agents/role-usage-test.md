# Barista Role Usage Test

Status: Read-only verification
Date: 2026-07-04

Purpose: verify that short Orders can use the role selection guide and role
cards without repeating long instructions.

## Result

`agents/role-selection-guide.md` was sufficient to select roles before reading
individual role cards. No new roles were needed.

## Tests

| Simulated Order | Selected role | Why it fits | Context to read first | Token saving | Read-only / escalation |
| --- | --- | --- | --- | --- | --- |
| "Plan a tiny typo fix in one Python file; no edits yet." | `agents/espresso-fast-coder.md` | Tiny code fix planning with clear scope. | `knowledge/00_index.md`, `brew-log/active_context.md`, named file, nearby tests. | Avoids broad repo scans and repeats only Espresso-specific rules by path. | Stay read-only until implementation is approved; escalate if scope becomes architectural. |
| "Plan a small Streamlit helper check for Coffee Status; no dependencies." | `agents/mocha-python-ai.md` | Python/Streamlit planning with local verification. | `knowledge/00_index.md`, `brew-log/active_context.md`, named app/test files. | Avoids rereading all app docs and restating dependency/data cautions. | Stay read-only; escalate before dependencies, external calls, or sensitive data. |
| "Plan a short literature map from named Pantry notes; no web search." | `agents/cappuccino-research.md` | Source-grounded research planning. | `knowledge/00_index.md`, `brew-log/active_context.md`, named Pantry summaries or source excerpts. | Reads summaries before raw papers and avoids folder-wide document sweeps. | Stay read-only; escalate for broad scope, external search, or high-stakes claims. |
| "Review this small diff for maintainability and missing tests; no edits." | `agents/flat-white-code-review.md` | Diff and test coverage review. | `knowledge/00_index.md`, `brew-log/active_context.md`, scoped diff, nearby tests/docs. | Reviews the diff first instead of opening full files or unrelated docs. | Stay read-only; escalate if findings require multi-shot fixes or specialist review. |

## Gaps

None found for read-only role selection. The guide and role cards are concise
enough for short Orders and clear enough to preserve safety boundaries.

## Reusable Short Order

```text
Barista, use agents/role-selection-guide.md.

Goal: [read-only planning/review goal]
Mode: Decaf
Scope: [specific files or source set]
Forbidden: no edits, no secrets, no commits

Select the smallest role, read Pantry first, avoid broad scans, and report the
role, reason, first context, risks, and next shot.
```
