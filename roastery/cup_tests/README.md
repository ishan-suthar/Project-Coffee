# Roastery Cup Test Pack

Status: v0.1 benchmark pack  
Date: 2026-07-06

This folder contains repeatable Project Coffee Orders for comparing Beans
across multiple task types.

Each Cup Test is self-contained. A Bean should be able to answer from the
prompt alone, without repository access, tool calls, model calls, web access,
or private context - **except 005 and 006 below, which exist specifically to
test image attachments and real tool calls**, and are documented as
deliberate exceptions to this rule, not oversights.

## Included Orders

| File | Task type | Purpose |
| --- | --- | --- |
| `001-decaf-repo-map.md` | Planning / repo understanding | Tests safe Decaf mapping from a small project snapshot. |
| `002-tiny-python-fix.md` | Coding / debugging | Tests a small Python fix plus one focused test. |
| `003-docs-summary.md` | Documentation clarity | Tests concise user-facing summary and next steps. |
| `004-pantry-assisted-answer.md` | Grounded local knowledge answer | Tests use of provided Pantry snippets with citations. |
| `005-image-description.md` | Vision | Tests real image description with zero fabricated detail. Requires a real attached image - run via a live `/v1/order` call, not `run_cup_test.py` (text-prompt only). |
| `006-tool-calling-verification.md` | Tool calling | Verifies a Bean actually calls a supplied tool correctly, not just that the API accepts a `tools` array. Requires a real `tools` array - run via a live `/v1/chat/completions` or `/v1/order` (`use_web: true`) call, not `run_cup_test.py`. |

## Local Listing

List the pack without calling OpenRouter:

```powershell
python roastery\run_cup_test.py --list-cup-tests
```

## Running A Specific Order

Run a live Cup Test only after human approval and only when the local
`OPENROUTER_API_KEY` environment variable is configured outside the repository:

```powershell
python roastery\run_cup_test.py --order-file roastery\cup_tests\001-decaf-repo-map.md
```

Capture full outputs locally for later human review:

```powershell
python roastery\run_cup_test.py --order-file roastery\cup_tests\001-decaf-repo-map.md --save-outputs --run-id benchmark-001-example
```

Raw outputs belong under `roastery/local_cup_outputs/` and must not be
committed. Summarize scores and lessons in `roastery/tasting_notes.md` and
`ledger/cost_log.md`.

