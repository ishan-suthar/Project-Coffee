# Roastery Cup Test Plan

Status: Planned only
Created: 2026-07-04
Shot: Brew 5 / Shot 8A

## Purpose

Run the same small, safe, local-only Order against multiple Beans so Project
Coffee can compare quality, speed, cost, supervision needed, and token
efficiency. This plan does not contain results.

## First Cup Test Order

```text
Barista, use agents/role-selection-guide.md.

Mode: Decaf read-only review.
Goal: Review agents/role-usage-test.md for clarity, token-efficiency value, and
missing safety constraints.
Scope: agents/role-usage-test.md, agents/role-selection-guide.md, and the single
role card you select if needed.
Forbidden: no edits, no secrets, no commits, no broad scans, no app code.

Report:
- selected role and why;
- files read;
- up to three findings, ordered by severity;
- any missing tests/checks or residual risk;
- whether the file is good enough as a read-only verification note.
```

## Why This Order Is Small And Fair

- It is read-only and documentation-only.
- It uses committed Project Coffee files and no secrets.
- It has the same prompt, same repo state, same expected output, and same
  constraints for each Bean.
- It exercises Brew 4 assets: Pantry-first behavior, role selection, focused
  review, and token-efficient context use.
- It is measurable without app runtime, package installs, external services, or
  code changes.

## Beans To Compare First

| Slot | Candidate Bean | Why |
| --- | --- | --- |
| A | Nemotron via OpenRouter, exact available model ID chosen at run time | Current draft default reasoning/review Bean in House Blend. |
| B | Qwen Coder or DeepSeek Coder via OpenRouter, exact available model ID chosen at run time | Cheap/fast candidate to test whether a lower-cost Bean is good enough for small reviews. |
| Optional premium | Claude or Codex-class model, only with explicit approval | Benchmark upper bound for quality and supervision needed. |

Do not treat this comparison as permanent routing policy. Update House Blend only
after enough evidence exists.

## Metrics To Collect

| Metric | What to record |
| --- | --- |
| Bean/model | Exact model display name and model ID. |
| Tool/runtime | Cursor, Codex, Cline, ChatGPT, or other runtime. |
| Barista role | Role selected by the model and whether it matches the guide. |
| Prompt/Recipe used | Order text, role guide, and any recipe/card read. |
| Speed | Wall-clock time from prompt submit to final answer. |
| Files read | Files the model/tool opened or referenced. |
| Files changed | Should be none; record any unexpected changes. |
| Tests/checks run | Should be none unless the model proposes a read-only check. |
| Test result | N/A for this read-only plan unless a check is explicitly run later. |
| Human fixes required | Corrections needed to follow instructions or improve answer. |
| Estimated cost | Tokens/cost from runtime usage view; do not invent missing values. |
| Quality score | Human 1-5 score for usefulness, correctness, and specificity. |
| Token-efficiency notes | Whether it avoided broad scans and used role/path references. |

## Manual Evidence To Capture

For each Bean run, the human should copy or record:

- exact Bean/model name and provider/model ID shown in Cursor/OpenRouter/Codex;
- runtime used and timestamp;
- wall-clock elapsed time;
- input tokens, output tokens, total tokens, and cost/credits if shown;
- files read or tool calls shown by the runtime;
- whether any file was changed unexpectedly;
- final model answer;
- any human correction, rerun, or prompt clarification needed.

## After The Actual Run

1. Save one scorecard per Bean in `roastery/model_scorecards/`.
2. Add summary rows to `roastery/tasting_notes.md`.
3. Add real usage entries to `ledger/cost_log.md`.
4. Compare Bean quality, supervision, speed, and cost.
5. Recommend whether House Blend needs more evidence or a routing adjustment.

## Guardrails

- Do not run the Cup Test from this plan shot.
- Do not call external models without explicit approval.
- Do not inspect secrets or credential files.
- Do not invent costs, tokens, latency, or quality scores.
- Keep all runs on the same commit and use the same Order.

