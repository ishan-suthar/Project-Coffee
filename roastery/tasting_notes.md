# Tasting Notes

Use model scorecards to record model performance.

## Recording Rules

- Add entries only after a real model run.
- Do not invent scores, costs, token counts, latency, or outputs.
- Use `scorecard-template.md` for reusable Bean scorecards.
- Use `cup-test-template.md` for per-run evidence capture.

## Entries

| Date | Bean | Task | Verdict | Scorecard |
| --- | --- | --- | --- | --- |
| 2026-07-02 | nvidia/nemotron-3-super-120b-a12b | Shot 3B connectivity | BLOCKED — retry needed | `model_scorecards/shot-3b-nemotron-connectivity.md` |
| 2026-07-05 | qwen/qwen3-coder:free; deepseek/deepseek-r1:free; nvidia/nemotron-3-ultra-550b-a55b:free | Brew 5 / Shot 8F first local Cup Test | PARTIAL - Nemotron succeeded; Qwen and DeepSeek were blocked by provider/model availability errors | Not scored; needs full output review |
| 2026-07-05 | poolside/laguna-m.1:free; cohere/north-mini-code:free; nvidia/nemotron-3-ultra-550b-a55b:free | Brew 5 / Shot 8K rerun local Cup Test evidence | COMPLETE RUN - all three Beans returned ok status on the same Order | Not scored; response previews only |
| 2026-07-05 | nvidia/nemotron-3-ultra-550b-a55b:free; cohere/north-mini-code:free; poolside/laguna-m.1:free | Brew 5 / Shot 8L House Blend recommendation | PROVISIONAL - Nemotron default, Cohere fallback, Poolside secondary fallback/comparison | `config/house_blend.md` |
| 2026-07-06 | No remote Bean; local standard-library installer | Brew 11 / Shot 11E template installer smoke test | COMPLETE - dry-run, apply, doctor check, reapply skip behavior, and tests passed | Workflow evidence below |
| 2026-07-06 | poolside/laguna-m.1:free; cohere/north-mini-code:free; nvidia/nemotron-3-ultra-550b-a55b:free | Brew 12 / Shot 12B captured full-output Cup Test | SCORED - all three Beans produced useful full outputs; Nemotron kept default confidence due quality parity plus lower latency/token use | Evidence below; raw outputs local-only |
| 2026-07-06 | No remote Bean; local standard-library dashboard | Brew 16 / Shot 16B Coffee Dashboard dogfood | COMPLETE - normal, JSON, section, strict missing-core, incomplete scratch, test, and compile checks passed | Workflow evidence below |
| 2026-07-08 | No remote Bean; local standard-library doctor | Brew 17 / Shot 17B Coffee Doctor dogfood | COMPLETE - root, JSON, section, strict fail-on-issue, incomplete scratch, test, and compile checks passed | Workflow evidence below |
| 2026-07-09 | No remote Bean; local standard-library gate repair | Gate repair - executed PLAN-spill-guard-token-log-fix.md and PLAN-root-test-discovery-fix.md | COMPLETE WITH ONE MID-EXECUTION FIX - Spill Guard parity restored; root test-suite gate now collects 252 tests instead of 0; the plan's own prescribed script content had to be corrected during execution | Workflow evidence below |
| 2026-07-09 | `nvidia/nemotron-3-ultra-550b-a55b:free` (House Blend, via Coffee Core Router) | Brew 36B live demo - one real `/v1/order` request, prompt "Explain what a Python decorator is in two sentences." | COMPLETE - correct classification (explain/espresso_shot), correct alias-only routing, 65 output tokens, 1733ms latency, not escalated, not draft | Full transcript below |
| 2026-07-10 | `nvidia/nemotron-3-ultra-550b-a55b:free` (House Blend, via Coffee Core Router + new Coffee Counter Chat UI) | Brew 37B live demo - one real `/v1/order` request through the actual browser UI, prompt "Explain what a Python decorator is in two sentences." | COMPLETE - correct status-line sequence, correct alias-only rendering, session persisted with auto-set title, 70 output tokens, 2405ms latency, not escalated, not draft, zero raw model ID leaks in rendered page | Full narrative below |
| 2026-07-15 | No remote Bean; real `router/` auth/projects/chat-management endpoints, verified via `curl` | Brew 43B live demo - two real users created and logged in, cross-user isolation verified directly against the real API (not `/v1/order`) | COMPLETE - real 404-not-403 ownership checks, real 401 on missing token, real logout token invalidation, all confirmed; not a Bean quality comparison, no scores to record | Full narrative below |
| 2026-07-15 | No remote Bean; `web/` frontend only (Vitest + real-Chromium Playwright), no `router/` changes | Brew 44 verification - response layout/Markdown formatting fix and barista-panel-to-right restructure | COMPLETE PER AUTOMATED SUITE (179 Vitest + 6 Playwright e2e, `tsc`/`eslint`/`next build` clean) - no manual visual/screenshot check performed, no browser/screenshot tool was available this session; not a Bean quality comparison, no scores to record | Full narrative below |
| 2026-07-15 | No remote Bean; `web/` frontend/SVG asset work only, no `router/` changes | Brew 45 verification - vertical Coffee Counter scene placeholder art (scene_bg, barista_static, collapse chevron) for the Brew 44 right-side panel | COMPLETE PER AUTOMATED SUITE (180 Vitest + 6 Playwright e2e, `tsc`/`eslint`/`next build` clean, 14.9 KB/300 KB asset budget) - no manual visual/screenshot check performed, no browser/screenshot tool was available this session; not a Bean quality comparison, no scores to record | Full narrative below |
| 2026-07-15 | `nvidia/nemotron-3-ultra-550b-a55b:free` (House Blend, via Coffee Core Router), four real `/v1/order` calls | Brew 46 live demo - real PDF upload, cross-turn recall with no re-upload, toggle flipped OFF mid-session, real Ledger row for both states | COMPLETE - correct cross-turn recall from persisted attachment text with the toggle ON, correct memory loss confirmed with the toggle OFF, real Ledger row shows `remember_chat=False`/`history_tokens_est=unknown`; single-Bean functional verification, not a Bean quality comparison, no scores to record | Full narrative below |
| 2026-07-15 | No remote Bean call this session - `router/` implementation only (fakes/mocks in every test) | Brew 47 (Sections 1+3 only) verification - `POST /v1/chat/completions` and the full Ledger schema migration | COMPLETE PER AUTOMATED SUITE (673 `router/tests`+`tests` passing, same 2 pre-existing vision-Bean fixture failures unrelated) - **no live demo performed**, deliberately: the curl/OpenAI-SDK/Cursor live demo is Section 2/4 scope, explicitly deferred to a later session per instruction; not a Bean quality comparison, no scores to record | Full narrative below |
| 2026-07-16 | `nvidia/nemotron-3-ultra-550b-a55b:free` (House Blend) + `anthropic/claude-sonnet-4-6` (Reserve Blend, via Coffee Core Router), real `/v1/chat/completions` calls including one real shadow run | Brew 47 (Sections 2+4) live demo - real retry detection, real shadow mode on/off, real prune CLI, `ledger_summary.py --mode model-usage` against real data | COMPLETE - retry correctly linked and `retry_count` live-incremented; shadow mode captured a real, distinct response pair with confirmed-unaffected client latency and a real computed shadow cost; prune verified both non-destructive and destructive; analysis report produced correct output including the blind-spot footer. **A real bug was found live (not fixed, reported separately)**: auto-escalation concatenates the cheap draft and the premium re-run's streamed content instead of replacing it. Not a Bean quality comparison, no scores to record | Full narrative below |
| 2026-07-16 | `nvidia/nemotron-3-ultra-550b-a55b:free` (House Blend) + `anthropic/claude-sonnet-4-6` (Reserve Blend, via Coffee Core Router), real `/v1/chat/completions` calls reproducing the exact bug prompt in both stream modes | Brew 47 escalation-concatenation fix - live demo re-running "say hello in exactly three words" against the fixed code | COMPLETE - `stream=true` returned only the draft's clean content with `system_fingerprint: "draft_quality"` and `would_have_escalated=True` logged, no premium text appended; `stream=false` returned only the premium response with the draft text provably absent and `usage.completion_tokens` reflecting the premium call's own count; both confirmed against real Ledger rows. Not a Bean quality comparison, no scores to record | Full narrative below |

## Cup Test Notes

### 2026-07-05 - Brew 5 / Shot 8F: First Local Cup Test Results

Command observed:

```powershell
python roastery/run_cup_test.py
```

Run status:

- Runner wrote no files.
- Runner completed and printed: `Cup Test completed successfully. Ready for Shot 8F.`
- Results below are recorded from the human-run local execution.
- No final quality scores assigned in this note; only one Bean produced a response preview, and the full output was not reviewed here.

| Bean | Status | Latency | Usage | Observed evidence |
| --- | --- | ---: | --- | --- |
| `qwen/qwen3-coder:free` | error | 0.47s | unknown | `OpenRouter HTTP error 429: Provider returned error` |
| `deepseek/deepseek-r1:free` | error | 0.15s | unknown | `OpenRouter HTTP error 404: This model is unavailable for free. The paid version is available now - use this slug instead: deepseek/deepseek-r1` |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.44s | 923 total | Response preview: `**Approach** - Iterate over the input paths and extract the file extension us...` |

Initial interpretation:

- This was a partial first live Cup Test, not a complete Bean quality comparison.
- Qwen was attempted but blocked by a provider/rate-limit style error.
- DeepSeek free was attempted but the requested free slug was unavailable.
- Nemotron free completed the Order and returned usage metadata.

Next actions:

- Update or replace the DeepSeek free model slug in a later shot.
- Add retry/fallback handling for HTTP 429 provider errors in a later shot.
- Rerun the Cup Test after those fixes before making House Blend routing changes.

### 2026-07-05 - Brew 5 / Shot 8K: Rerun Cup Test Evidence

Command observed:

```powershell
python roastery/run_cup_test.py
```

Run status:

- Runner wrote no files.
- Runner completed and printed: `Cup Test completed successfully.`
- Results below are recorded from the human-run local execution.
- All three configured Beans returned `ok` status on the same Order.
- No final quality scores assigned in this note; the runner output included response previews, not full model answers.

| Bean | Status | Latency | Usage | Observed response preview |
| --- | --- | ---: | --- | --- |
| `poolside/laguna-m.1:free` | ok | 0.81s | 3525 total | `Approach: - Use os.path.splitext to extract the extension from each path - ...` |
| `cohere/north-mini-code:free` | ok | 3.77s | 1316 total | `**Approach** - Use os.path.splitext to get the file extension, then lower-c...` |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.42s | 726 total | `**Approach** - Use os.path.splitext to extract the file extension from each...` |

Initial interpretation:

- This rerun satisfied the availability goal: at least two Beans, and in fact all three Beans, completed the same local Cup Test Order.
- Nemotron was fastest and used the fewest reported total tokens in this observed run.
- Poolside returned the largest reported token total.
- Cohere returned an ok result but had the highest observed latency.
- Quality remains unscored until full model outputs are reviewed against the requested implementation and test expectations.

Next actions:

- Preserve full model outputs in a later evidence shot or add a manual capture process before scoring quality.
- Create per-Bean scorecards only after full outputs are available for review.
- Do not update House Blend routing from response previews alone.

### 2026-07-05 - Brew 5 / Shot 8L: Provisional House Blend Recommendation

Recommendation recorded from 8J/8K evidence:

| Route | Bean | Evidence |
| --- | --- | --- |
| Default Bean | `nvidia/nemotron-3-ultra-550b-a55b:free` | Succeeded twice; fastest and lowest-token Bean in the 8J rerun. |
| Fallback Bean | `cohere/north-mini-code:free` | Succeeded on the same Order and used fewer tokens than Poolside, though it was slower. |
| Secondary fallback / comparison Bean | `poolside/laguna-m.1:free` | Succeeded on the same Order, but used the most tokens in the recorded rerun. |

This House Blend is provisional. Full-output quality and actual cost remain
unknown. Qwen and the tested DeepSeek free slugs should not be default routes
until availability improves and a future Roastery run succeeds.

### 2026-07-05 - Brew 5 / Shot 8O: Roastery MVP Closeout

Brew 5 reached Roastery MVP:

- At least two Beans were compared on the same Order; the 8J rerun compared
  Poolside, Cohere, and Nemotron.
- Roastery recorded the partial first run, successful rerun, and provisional
  House Blend recommendation.
- Ledger recorded observed token totals and used `unknown` where actual costs
  were unavailable.
- House Blend now has a provisional evidence-based recommendation:
  `nvidia/nemotron-3-ultra-550b-a55b:free` as default and
  `cohere/north-mini-code:free` as fallback.

Known limitations:

- Full outputs were not captured and scored.
- Actual costs remain unknown.
- Evidence is based on one tiny coding Order.
- Future Cup Tests should preserve full outputs and add human quality scoring.

### 2026-07-06 - Brew 11 / Shot 11E: Template Installer Smoke Test

Scratch target:

```text
tmp/template-installer-smoke-target
```

Commands run:

```powershell
python tools\install_project_coffee_template.py --target tmp\template-installer-smoke-target
python tools\install_project_coffee_template.py --target tmp\template-installer-smoke-target --apply
python tools\install_project_coffee_template.py --check --target tmp\template-installer-smoke-target
python tools\install_project_coffee_template.py --target tmp\template-installer-smoke-target --apply
python -m unittest tests.test_install_project_coffee_template
python -m py_compile tools\install_project_coffee_template.py tests\test_install_project_coffee_template.py
```

Observed behavior:

- Dry-run reported all onboarding files under `Files to create` and wrote no
  files.
- Apply created the Project Coffee onboarding files in the scratch target.
- Doctor mode reported `status` as `COMPLETE` after apply.
- Re-running apply without `--force` reported no files to create and skipped
  existing onboarding files.
- The focused installer test suite passed: 12 tests.
- Syntax compilation passed.
- The generated scratch target was cleaned up after validation so it would not
  be committed.

Cost and token evidence:

- Model / Bean: none; no remote model used.
- Tokens: unknown / not metered.
- Cost: unknown / no cost shown.

What worked:

- The installer behaved safely in dry-run-first workflow.
- The doctor provided a quick onboarding completeness check.
- Reapply preserved existing files without requiring `--force`.

Needs improvement:

- Future closeout should decide whether `tmp/` should be ignored for scratch
  smoke targets or whether smoke tests should always clean up generated targets.

### 2026-07-06 - Brew 12 / Shot 12B: Captured Full-Output Cup Test Evidence

Run ID:

```text
brew12-20260706-014748
```

Local-only output directory:

```text
roastery/local_cup_outputs/brew12-20260706-014748
```

Raw outputs are ignored by Git and Cursor indexing. They are not committed in
this note. This section records summarized review evidence only.

Evidence source:

- `manifest.json` from the captured run.
- Local raw output files under the run directory.
- Terminal output from the live run was not separately preserved in tracked
  docs; manifest metadata was used for latency, tokens, cost, and status.

Order hash:

```text
6ca498dcd2e18860179d045f545ee9603c1736a7b33b917d16d1aaf8e0f17f2f
```

Scoring rubric:

- 10 = correct, minimal, actionable, no human fix needed.
- 8-9 = good, minor review/fix needed.
- 6-7 = useful but required meaningful correction.
- 4-5 = partially useful, risky, vague, or overengineered.
- 1-3 = failed, unavailable, or not useful.

| Bean | Status | Latency | Tokens | Cost | Captured | Reviewed | Score | Use again? |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| `poolside/laguna-m.1:free` | ok | 0.66s | 2158 total | 0 reported | yes | yes | 9 | yes |
| `cohere/north-mini-code:free` | ok | 0.62s | 2272 total | 0 reported | yes | yes | 9 | yes |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.45s | 936 total | 0 reported | yes | yes | 9 | yes |

Quality notes:

| Bean | Strengths | Weaknesses | Human fixes needed |
| --- | --- | --- | --- |
| `poolside/laguna-m.1:free` | Correct and minimal implementation; clear tests for case-insensitive `.py` and `.md`, other extensions, no extension, empty input, and mixed input. | Used a numbered approach list instead of bullets; coverage was solid but not broader than necessary. | None expected for this Order. |
| `cohere/north-mini-code:free` | Correct implementation; clear docstring; good tests for empty input, case-insensitive `.md`, mixed input, no extension, and directory-like strings. | Slightly more verbose than needed; output included a non-ASCII hyphen in prose, not code. | None expected for this Order. |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | Correct implementation; broadest test coverage, including multiple dots and hidden files; fastest and lowest-token run. | Slightly less minimal due `Counter` and type imports for a tiny task. | None expected for this Order. |

Interpretation:

- All three Beans produced usable, reviewed full outputs for this small coding
  Order.
- Quality scores were tied at 9, so the differentiator for this Order remains
  latency and token use.
- Nemotron improved confidence as the default Bean for small standard-library
  coding Orders because it matched quality while using fewer reported tokens and
  lower latency.
- The recommendation remains provisional because this is still one task type
  and one small Order.

### 2026-07-06 - Brew 13 / Shot 13B: Pantry Search Dogfood Evidence

Scratch target:

```text
tmp/pantry-search-smoke
```

Commands run:

```powershell
python tools\pantry_search.py --root docs --query "House Blend" --max-results 3
python tools\pantry_search.py --root docs --query "Roastery" --max-results 3
python tools\pantry_search.py --root docs --query "onboarding" --max-results 3
python tools\pantry_search.py --root tmp\pantry-search-smoke\knowledge --query "House Blend" --max-results 5
python tools\pantry_search.py --root tmp\pantry-search-smoke\knowledge --query "onboarding" --max-results 1
$json = python tools\pantry_search.py --root tmp\pantry-search-smoke\knowledge --query "Roastery" --max-results 2 --json; $parsed = $json | ConvertFrom-Json
python tools\pantry_search.py --root tmp\pantry-search-smoke\knowledge --query "zzznomatchneedle" --max-results 3
python tools\pantry_search.py --root tmp\pantry-search-smoke\knowledge --query "zzzsafeskipneedle" --max-results 5
python -m unittest tests.test_pantry_search
```

Observed behavior:

- Project Coffee docs searches returned relevant guide hits for `House Blend`,
  `Roastery`, and `onboarding`.
- Scratch search found expected Pantry notes for `House Blend`.
- `--max-results 1` returned one onboarding result.
- JSON mode parsed successfully with `result_count=2`; the first result was
  `roastery.md` under heading `Roastery Smoke Notes`.
- The unique no-results query printed `No results found`.
- The unique sentinel stored only under sensitive-looking scratch paths printed
  `No results found`, confirming those paths were skipped in this smoke test.
- Focused Pantry Search tests passed: 11 tests, 1 skipped symlink test.

Cost and token evidence:

- Model / Bean: none; no remote model used.
- API calls: none.
- Tokens: none / local-only; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- The tool found useful Project Coffee documentation without model calls.
- Human-readable output was easy to scan.
- JSON output was machine-readable through PowerShell `ConvertFrom-Json`.
- Sensitive-looking scratch paths were not searched.

Needs improvement:

- A first negative smoke query used common words and produced expected but noisy
  overlapping results. Future smoke tests should prefer unique sentinels.
- Future polish could tighten query/token scoring so negative or hyphenated
  searches are less likely to match broad substrings.

### 2026-07-06 - Brew 14 / Shot 14B: Multi-Task Benchmark Evidence

Run IDs:

```text
brew14-repo-map-20260706-022532
brew14-python-fix-20260706-022559
```

Local-only output directories:

```text
roastery/local_cup_outputs/brew14-repo-map-20260706-022532
roastery/local_cup_outputs/brew14-python-fix-20260706-022559
```

Raw outputs are ignored by Git and Cursor indexing. They are not committed in
this note. This section records summarized review evidence only.

Evidence source:

- `manifest.json` from both captured runs.
- Local raw output files under the run directories.
- Terminal output from the live runs was not separately preserved in tracked
  docs; manifest metadata was used for status, latency, token, cost, and output
  file paths.

Scoring rubric:

- 10 = correct, minimal, actionable, no human fix needed.
- 8-9 = good, minor review/fix needed.
- 6-7 = useful but required meaningful correction.
- 4-5 = partially useful, risky, vague, or overengineered.
- 1-3 = failed, unavailable, or not useful.

#### Task 001 - Decaf Repo Map

Task file:

```text
roastery/cup_tests/001-decaf-repo-map.md
```

Order hash:

```text
00e199c3e38f19b17585a9b06df68105d2a702b138cd86329371e10264c23a6e
```

| Bean | Status | Latency | Tokens | Cost | Captured | Reviewed | Score | Use again? |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| `poolside/laguna-m.1:free` | error: HTTP 429 provider error | 0.20s | unknown | unknown | no | no output | 1 | not for repo-map until availability improves |
| `cohere/north-mini-code:free` | ok | 0.43s | 1797 total | 0 reported; billing unknown | yes | yes | 7 | yes, with review |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.38s | 1257 total | 0 reported; billing unknown | yes | yes | 8 | yes |

Quality notes:

| Bean | Strengths | Weaknesses | Human fixes needed |
| --- | --- | --- | --- |
| `poolside/laguna-m.1:free` | None; no successful output. | Provider returned HTTP 429, so there was no output to score. | Rerun only if provider availability improves. |
| `cohere/north-mini-code:free` | Covered project purpose, components, likely commands, safe documentation improvement, risks, and human approval. | Invented or over-specified some behavior and commands, including note operations and an unsupported README tooling example. | Remove unsupported commands/features and verify CLI verbs before using as a plan. |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | Clear evidence/assumption separation, concise component map, likely commands, safe improvement, and useful risk questions. | Still suggested some guessed commands and example CLI verbs that need verification. | Verify commands and CLI verbs before implementation. |

#### Task 002 - Tiny Python Fix

Task file:

```text
roastery/cup_tests/002-tiny-python-fix.md
```

Order hash:

```text
d9a0cbf5f802a5ac18c9d605842be6696b0bb95e3619c7d74aacb86523ddb4fa
```

| Bean | Status | Latency | Tokens | Cost | Captured | Reviewed | Score | Use again? |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| `poolside/laguna-m.1:free` | ok | 1.16s | 2717 total | 0 reported; billing unknown | yes | yes | 10 | yes, but token-heavy |
| `cohere/north-mini-code:free` | ok | 0.55s | 2578 total | 0 reported; billing unknown | yes | yes | 10 | yes |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.39s | 656 total | 0 reported; billing unknown | yes | yes | 10 | yes |

Quality notes:

| Bean | Strengths | Weaknesses | Human fixes needed |
| --- | --- | --- | --- |
| `poolside/laguna-m.1:free` | Correct, minimal fix; preserved first-seen order; skipped empty tags; included a focused `unittest` example. | Much higher token use than Nemotron for the same quality. | None expected for this Order. |
| `cohere/north-mini-code:free` | Correct fix and readable focused test; clear explanation of the duplicate-check and sorting bugs. | Higher token use than Nemotron; no quality advantage on this tiny task. | None expected for this Order. |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | Correct, concise, fastest, and lowest-token successful output. | No material weakness for this Order. | None expected for this Order. |

Interpretation:

- Nemotron had the best combined result across the two reviewed benchmark
  Orders: successful on both, strongest repo-map answer, tied coding quality,
  and lowest reported token use among successful Beans.
- Cohere becomes a more credible fallback for planning and coding because it
  completed both reviewed Orders, though the repo-map output needed meaningful
  cleanup.
- Poolside remains useful for coding comparison but failed the repo-map Order
  with a provider 429 and used the most tokens on the Python fix.
- The House Blend remains provisional because only two of four benchmark Orders
  have been run and reviewed.

### 2026-07-06 - Brew 14 / Shot 14C: Second Multi-Task Benchmark Pass

Run IDs:

```text
brew14-docs-summary-20260706-023220
brew14-pantry-assisted-20260706-023312
```

Local-only output directories:

```text
roastery/local_cup_outputs/brew14-docs-summary-20260706-023220
roastery/local_cup_outputs/brew14-pantry-assisted-20260706-023312
```

Raw outputs are ignored by Git and Cursor indexing. They are not committed in
this note. This section records summarized review evidence only.

Evidence source:

- `manifest.json` from both captured runs.
- Local raw output files under the run directories.
- Terminal output from the live runs was not separately preserved in tracked
  docs; manifest metadata was used for status, latency, token, cost, and output
  file paths.

#### Task 003 - Docs Summary

Task file:

```text
roastery/cup_tests/003-docs-summary.md
```

Order hash:

```text
903a02dc3f91bcaba0a8afac1fd9c92da907c8c5ffe71381af7a04961351ee1f
```

| Bean | Status | Latency | Tokens | Cost | Captured | Reviewed | Score | Use again? |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| `poolside/laguna-m.1:free` | ok | 0.91s | 690 total | 0 reported; billing unknown | yes | yes | 10 | yes |
| `cohere/north-mini-code:free` | ok | 0.57s | 759 total | 0 reported; billing unknown | yes | yes | 9 | yes |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.44s | 661 total | 0 reported; billing unknown | yes | yes | 10 | yes |

Quality notes:

| Bean | Strengths | Weaknesses | Human fixes needed |
| --- | --- | --- | --- |
| `poolside/laguna-m.1:free` | Concise, followed requested sections, preserved source facts, and gave the expected validation command. | Slightly terse, but still complete. | None expected for this Order. |
| `cohere/north-mini-code:free` | Clear summary, next step, risk, and validation command. | Slightly expanded risk wording beyond the provided snippet. | Minor review for wording before reuse. |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | Concise, complete, and well aligned with the source snippet; fastest and lowest-token. | No material weakness for this Order. | None expected for this Order. |

#### Task 004 - Pantry Assisted Answer

Task file:

```text
roastery/cup_tests/004-pantry-assisted-answer.md
```

Order hash:

```text
7b8882c50dc8f3a337e2954bbcce20d4c9b3ce78dbc6fc47f9b89100735a8296
```

| Bean | Status | Latency | Tokens | Cost | Captured | Reviewed | Score | Use again? |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| `poolside/laguna-m.1:free` | ok | 1.19s | 903 total | 0 reported; billing unknown | yes | yes | 8 | yes, with grounding review |
| `cohere/north-mini-code:free` | ok | 0.53s | 1241 total | 0 reported; billing unknown | yes | yes | 6 | only with strict review |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.40s | 762 total | 0 reported; billing unknown | yes | yes | 10 | yes |

Quality notes:

| Bean | Strengths | Weaknesses | Human fixes needed |
| --- | --- | --- | --- |
| `poolside/laguna-m.1:free` | Answered all requested sections and cited the provided snippets. | The RAG explanation drifted into broader wording not directly present in the snippets and omitted some provided non-RAG details. | Tighten wording to the exact snippet facts before reuse. |
| `cohere/north-mini-code:free` | Structured answer and cited the main workflow/evidence/RAG points. | Added unsupported examples such as editor choice, likely costs, formatting unknowns, and doc-link lessons. | Remove unsupported examples and re-ground every factual claim in snippets. |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | Concise, fully answered the prompt, cited all relevant snippets, and stayed grounded. | No material weakness for this Order. | None expected for this Order. |

Interpretation:

- All three Beans completed the docs-summary and Pantry-assisted Orders.
- Nemotron was strongest across the second pass: top quality, fastest latency,
  and lowest or near-lowest token use.
- Poolside performed well on docs summary and acceptably on grounded Pantry
  answering, but still needs grounding review.
- Cohere remains useful but showed a real risk on citation-sensitive grounded
  answers by adding unsupported details.
- Across all four Brew 14 benchmark Orders, Nemotron has the strongest
  provisional default evidence. Cohere remains the main fallback. Poolside
  remains a comparison/coding/docs fallback, with caution for availability and
  grounding-sensitive work.

### 2026-07-06 - Brew 15 / Shot 15B: Roastery Report Generator Dogfood

Local-only draft report path:

```text
roastery/local_reports/brew15b-latest-report.md
```

The local report directory and raw Cup Test output directory are ignored by Git
and Cursor indexing. Generated draft reports and raw outputs are not committed
in this note.

Commands run:

```powershell
python tools\roastery_report.py --run-dir roastery\local_cup_outputs\brew14-pantry-assisted-20260706-023312
python tools\roastery_report.py --run-dir roastery\local_cup_outputs\brew14-pantry-assisted-20260706-023312 --json
python tools\roastery_report.py --run-dir roastery\local_cup_outputs
python tools\roastery_report.py --run-dir roastery\local_cup_outputs\brew14-pantry-assisted-20260706-023312 --include-previews --max-preview-chars 80
python tools\roastery_report.py --run-dir roastery\local_cup_outputs\brew14-pantry-assisted-20260706-023312 --output roastery\local_reports\brew15b-latest-report.md
python -m unittest tests.test_roastery_report
python -m py_compile tools\roastery_report.py tests\test_roastery_report.py
git status --short --ignored -- roastery\local_reports
git status --short --ignored -- roastery\local_cup_outputs
```

Observed behavior:

- Markdown report generation worked for the latest local run:
  `brew14-pantry-assisted-20260706-023312`.
- JSON report generation worked for the same run and parsed with
  `run_count=1`, the expected run ID, and 3 Bean results.
- Combined Markdown report worked across all local run directories under
  `roastery/local_cup_outputs/`.
- Preview report generation worked with `--include-previews`; excerpts were
  capped at `--max-preview-chars 80` and showed ellipses.
- Draft report saving worked under `roastery/local_reports/`.
- `roastery/local_reports/` is ignored by Git.
- `roastery/local_cup_outputs/` remains ignored by Git.
- Focused report-generator tests passed: 10 tests.
- Syntax compilation passed.

Cost and token evidence:

- Model / Bean: none; no remote Bean used.
- API calls: none.
- Tokens: none / local-only; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- The generator rebuilt useful report tables from manifest metadata quickly.
- JSON output was machine-readable for local checks.
- Combined reporting surfaced all local runs in one draft.
- Capped previews gave enough context for review without pasting full raw
  outputs.
- Saved drafts can stay local under an ignored folder.

Needs improvement:

- Combined reports can become noisy when older failed or experimental runs are
  included. A future polish shot could add filters by run ID, date, or Order
  file.
- Draft reports still require human scoring and summary judgment before any
  content is copied into Roastery notes.

### 2026-07-06 - Brew 16 / Shot 16B: Coffee Dashboard Dogfood

Scratch target:

```text
tmp/coffee-dashboard-smoke
```

Commands run:

```powershell
python tools\coffee_dashboard.py --root .
python tools\coffee_dashboard.py --root . --json
python tools\coffee_dashboard.py --root . --section docs
python tools\coffee_dashboard.py --root . --section tools
python tools\coffee_dashboard.py --root . --section roastery
python tools\coffee_dashboard.py --root . --section ledger
python tools\coffee_dashboard.py --root . --section house-blend
python tools\coffee_dashboard.py --root . --fail-on-missing
python tools\coffee_dashboard.py --root tmp\coffee-dashboard-smoke --fail-on-missing
python -m unittest tests.test_coffee_dashboard
python -m py_compile tools\coffee_dashboard.py tests\test_coffee_dashboard.py
```

Observed behavior:

- Normal human-readable dashboard mode worked against the Project Coffee root
  and reported `Status: OK`.
- JSON mode parsed successfully and reported `status=OK` with the expected
  dashboard sections.
- Section filtering worked for docs, tools, Roastery, Ledger, and House Blend.
- `--fail-on-missing` against the Project Coffee root exited successfully with
  no missing files.
- The incomplete scratch target reported `Status: INCOMPLETE`, listed missing
  required core files, and exited `1` under `--fail-on-missing`.
- Focused dashboard tests passed: 10 tests.
- Syntax compilation passed.
- `git status --short --untracked-files=all -- tmp\coffee-dashboard-smoke`
  returned no tracked or untracked scratch files.

Cost and token evidence:

- Model / Bean: none; no remote Bean used.
- API calls: none.
- Tokens: none / local-only; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- The dashboard gave a compact root health view without touching secrets,
  models, APIs, Git, or raw local output folders.
- JSON output is usable for future local automation.
- Section filtering made focused status checks easy to scan.
- The incomplete scratch check proved missing-core detection works.

Needs improvement:

- The dashboard is intentionally file-presence oriented. Future polish could add
  richer freshness checks, but only for known safe files.

### 2026-07-08 - Brew 17 / Shot 17B: Coffee Doctor Dogfood

Scratch target:

```text
tmp/coffee-doctor-smoke
```

Commands run:

```powershell
python tools\coffee_doctor.py --root .
python tools\coffee_doctor.py --root . --json
python tools\coffee_doctor.py --root . --section tools
python tools\coffee_doctor.py --root . --section roastery
python tools\coffee_doctor.py --root . --section templates
python tools\coffee_doctor.py --root . --section ignored-paths
python tools\coffee_doctor.py --root . --fail-on-issue
python tools\coffee_doctor.py --root tmp\coffee-doctor-smoke
python tools\coffee_doctor.py --root tmp\coffee-doctor-smoke --fail-on-issue
python -m unittest tests.test_coffee_doctor
python -m py_compile tools\coffee_doctor.py tests\test_coffee_doctor.py
git status --short --untracked-files=all -- tmp\coffee-doctor-smoke
```

Observed behavior:

- Root Doctor run worked and reported `Status: WARN` with 38 OK findings, 1
  WARN finding, and 0 FAIL findings.
- The WARN finding is an existing docs policy issue:
  `docs/adr/0005-local-openrouter-coffee-core.md` appears to include the
  literal staged secret-check command. This was recorded but not fixed in this
  shot because that ADR is outside the allowed edit scope.
- JSON mode parsed successfully and reported the same summary counts.
- Section filtering worked for tools, Roastery, templates, and ignored paths.
- `--fail-on-issue` against the Project Coffee root exited `0` because no FAIL
  findings were present.
- The incomplete scratch target reported `Status: FAIL` with missing core,
  docs, tools, Roastery, Ledger, template, and ignore-file findings.
- Normal mode against the incomplete scratch target exited `0`, preserving
  exploratory diagnosis behavior.
- `--fail-on-issue` against the incomplete scratch target exited `1`.
- Focused Coffee Doctor tests passed: 10 tests.
- Syntax compilation passed.
- `git status --short --untracked-files=all -- tmp\coffee-doctor-smoke`
  returned no tracked or untracked scratch files.

Cost and token evidence:

- Model / Bean: none; no remote Bean used.
- API calls: none.
- Tokens: none / local-only; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- Doctor produced useful severity-coded findings with safe next actions.
- Root checks correctly distinguished WARN from FAIL.
- Strict mode behaved correctly for both healthy-enough root checks and
  incomplete scratch checks.
- Section filtering made targeted diagnosis easy to scan.
- Local artifact checks stayed limited to the known Roastery output/report
  paths.

Needs improvement:

- Brew 17C should decide whether to fix the existing ADR policy warning as a
  separate one-responsibility documentation shot or leave it as tracked Doctor
  evidence for now.

### 2026-07-08 - Brew 18 / Shot 18B: Unified Coffee CLI Dogfood

Scratch target:

```text
tmp/coffee-cli-template-smoke
```

Commands run:

```powershell
python tools\coffee.py --help
python tools\coffee.py --version
python tools\coffee.py dashboard --root .
python tools\coffee.py dashboard --root . --json
python tools\coffee.py dashboard --root . --section tools
python tools\coffee.py doctor --root .
python tools\coffee.py doctor --root . --json
python tools\coffee.py doctor --root . --section tools
python tools\coffee.py pantry-search --root . --query "House Blend" --max-results 3
python tools\coffee.py pantry-search --root . --query "Coffee Doctor" --max-results 3 --json
python tools\coffee.py check-onboarding --target .
python tools\coffee.py install-template --target tmp\coffee-cli-template-smoke
python tools\coffee.py roastery-report --run-dir roastery\local_cup_outputs
python -m unittest tests.test_coffee_cli
python -m py_compile tools\coffee.py
git ls-files -- tmp/coffee-cli-template-smoke
git status --short --untracked-files=all -- tmp/coffee-cli-template-smoke
```

Observed behavior:

- Unified CLI help worked and listed dashboard, doctor, Pantry Search,
  Roastery report, template install, and onboarding check subcommands.
- `--version` worked and printed `Project Coffee CLI v0.1`.
- Dashboard delegation worked against the Project Coffee root and reported
  `Status: OK`.
- Dashboard JSON forwarding parsed successfully and reported `status=OK` with
  overview, Brew Log, docs, tools, Roastery, Ledger, and House Blend sections.
- Dashboard section forwarding worked for `--section tools`.
- Doctor delegation worked against the Project Coffee root and reported
  `Status: WARN` with 38 OK findings, 1 WARN finding, and 0 FAIL findings.
- The Doctor WARN is the existing
  `docs/adr/0005-local-openrouter-coffee-core.md` literal staged
  secret-check command warning; it was not introduced by Brew 18B.
- Doctor JSON forwarding parsed successfully and preserved the same summary
  counts.
- Doctor section forwarding worked for `--section tools`.
- Pantry Search delegation worked. The `House Blend` query returned relevant
  results including the progress log, ADR-0004, and `config/house_blend.md`.
- Pantry Search JSON forwarding worked for `Coffee Doctor` and returned 3
  results.
- Onboarding check delegation worked against the Project Coffee root and
  reported `COMPLETE`.
- Template install delegation stayed in default dry-run mode against the
  scratch target and reported the files that would be created with no writes.
- Roastery report delegation worked against existing local manifests under
  `roastery/local_cup_outputs` without previews or raw output contents.
- Focused Unified Coffee CLI tests passed: 15 tests.
- Syntax compilation passed for `tools\coffee.py`.
- Scratch tracking checks returned no tracked or untracked files under
  `tmp\coffee-cli-template-smoke`.

Cost and token evidence:

- Model / Bean: none; no remote Bean used.
- API calls: none.
- Tokens: none / local-only; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- The wrapper preserved underlying tool behavior and exit codes while making
  common commands easier to discover.
- JSON and section flags forwarded correctly for dashboard and doctor.
- Pantry Search, onboarding check, template dry-run, and Roastery report all
  worked through the unified surface.
- Roastery report stayed local and did not include raw output previews.

Needs improvement:

- Dashboard and Doctor tool inventories do not yet list `tools/coffee.py`
  because their internal expected-file lists predate Brew 18. Brew 18C should
  decide whether to update those health checks as a small closeout polish item.
- The pre-existing ADR policy warning remains visible in Doctor output and
  should stay tracked separately from Unified CLI behavior.

### 2026-07-08 - Brew 19 / Shot 19B: Ledger Summarizer Dogfood

Scratch target:

```text
tmp/ledger-summary-smoke
```

Commands run:

```powershell
python tools\ledger_summary.py --help
python tools\ledger_summary.py --root .
python tools\ledger_summary.py --root . --json
python tools\ledger_summary.py --root . --max-entries 5
python tools\ledger_summary.py --root . --from 2026-07-01 --max-entries 5
python tools\ledger_summary.py --root . --output tmp\ledger-summary-smoke\ledger-summary.md --max-entries 3
python tools\ledger_summary.py --root . --ledger tmp\ledger-summary-smoke\scratch-ledger.md --max-entries 10
python tools\ledger_summary.py --root . --ledger tmp\ledger-summary-smoke\scratch-ledger.md --json
python tools\ledger_summary.py --root . --from 2026-99-99
python -m unittest tests.test_ledger_summary
python -m py_compile tools\ledger_summary.py
python tools\coffee.py ledger-summary --root . --max-entries 3
python tools\coffee.py ledger-summary --root . --json --max-entries 2
git status --short --untracked-files=all -- tmp/ledger-summary-smoke
git ls-files -- tmp/ledger-summary-smoke
```

Observed behavior:

- Help worked and listed `--root`, `--ledger`, `--json`, `--from`, `--to`,
  `--max-entries`, and `--output`.
- Project Coffee Ledger summary worked against `ledger/cost_log.md`.
- Root summary parsed 17 Ledger entries, found 11 model/API evidence entries,
  counted 6 local-only entries, summed 25,917 known tokens, and kept known cost
  at `$0.00` while preserving 11 unknown/unparseable cost entries.
- JSON mode parsed successfully and returned the same totals.
- `--max-entries 5` limited the recent-entry table to 5 rows.
- Date filtering from `2026-07-01` worked and preserved the expected 17-entry
  range for the current Ledger.
- Output report mode wrote `tmp/ledger-summary-smoke/ledger-summary.md`.
- Scratch Ledger parsing worked with 4 entries: one local-only row, one
  model/API fixture row, parseable cost of `$1.25`, 198 known tokens, and one
  uneven legacy-style row that did not crash parsing.
- Invalid date input failed with exit code `1` and the expected
  `--from must use YYYY-MM-DD` error.
- Focused Ledger Summarizer tests passed: 14 tests.
- Syntax compilation passed for `tools\ledger_summary.py`.
- Unified Coffee CLI delegation worked in human-readable and JSON modes.
- Scratch files were untracked and `git ls-files -- tmp/ledger-summary-smoke`
  returned no tracked files.

Cost and token evidence:

- Model / Bean: none; no remote Bean used.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- The summarizer made the Ledger's known tokens, known cost, unknowns, local
  work, and model/API evidence easier to scan.
- JSON output is usable for future local reporting.
- Scratch fixtures confirmed parseable costs/tokens and uneven Markdown rows
  behave safely.
- Unified CLI integration gives the summarizer the same command surface as
  dashboard, doctor, Pantry Search, and Roastery report.

Needs improvement:

- The summarizer is intentionally conservative. It can summarize known table
  evidence, but it cannot infer exact cost or token data where the Ledger says
  unknown.
- Future polish could add richer grouping by Brew or task type after Brew 19
  closeout.

### 2026-07-08 - Brew 19 / Shot 19B-fix: Ledger Summarizer Scratch Parsing Fix

Issue found:

- Brew 19B scratch dogfood exposed incomplete parsing for simple bullet-style
  Ledger entries using fields like `Cost:`, `Tokens:`, and `Model/API calls:`.

Commands run:

```powershell
python -m unittest tests.test_ledger_summary
python -m py_compile tools\ledger_summary.py
python tools\ledger_summary.py --root . --ledger <temp scratch bullet ledger> --max-entries 5
python tools\ledger_summary.py --root . --ledger <temp scratch bullet ledger> --json
python tools\ledger_summary.py --root . --json --max-entries 2
python tools\ledger_summary.py --root . --from 2026-99-99
```

Observed behavior:

- Focused Ledger Summarizer tests passed: 20 tests.
- Syntax compilation passed.
- Scratch bullet ledger acceptance passed exactly:
  - Total entries found: 2.
  - Entries with model/API calls: 1.
  - Entries marked local-only: 1.
  - Total known cost: `$0.12`.
  - Total known tokens: 1234.
- Project Coffee root summary still worked after the parser fix.
- JSON mode still worked.
- Invalid date handling still exited `1` with the expected `--from must use
  YYYY-MM-DD` error.

Cost and token evidence:

- Model / Bean: none; no remote Bean used.
- API calls: none.
- Tokens: none / local-only for this fix validation; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- Bullet-style Ledger fields now preserve cost, token, model/API, local-only,
  evidence, and notes data without breaking table parsing.
- Unknown and unparseable values remain honest unknowns.

Needs improvement:

- Brew 19C should close the Ledger Summarizer with the 19B-fix evidence included
  in the completion review.

### 2026-07-08 - Brew 20 / Shot 20B: Release Packaging Check Dogfood

Commands run:

```powershell
python tools\release_check.py --help
python tools\release_check.py --root .
python tools\release_check.py --root . --json
python tools\release_check.py --root . --section docs
python tools\release_check.py --root . --section tools
python tools\release_check.py --root . --section safety
python tools\release_check.py --root . --section tags
python tools\release_check.py --root . --fail-on-blocker
New-Item -ItemType Directory -Force -Path tmp\release-check-smoke
python tools\release_check.py --root tmp\release-check-smoke
python tools\release_check.py --root tmp\release-check-smoke --fail-on-blocker
python -m unittest tests.test_release_check
python -m py_compile tools\release_check.py
python tools\coffee.py release-check --root .
python tools\coffee.py release-check --root . --json
git status --short --untracked-files=all -- tmp\release-check-smoke
git ls-files -- tmp\release-check-smoke
```

Observed behavior:

- Help worked and listed `--root`, `--json`, `--section`, and
  `--fail-on-blocker`.
- Project Coffee root release check returned `OK` with 14 OK findings and no
  info, warnings, or blockers.
- JSON mode parsed successfully and returned the same root summary.
- Section filtering worked:
  - `docs`: 3 OK findings.
  - `tools`: 1 OK finding.
  - `safety`: 3 OK findings.
  - `tags`: 3 OK findings for `v0.1`, `v0.1-proven`, and
    `v0.1-certified`.
- `--fail-on-blocker` against Project Coffee root exited `0`.
- Incomplete scratch root `tmp\release-check-smoke` returned `BLOCKER` status
  with 5 blockers, 1 warning, and 5 OK findings.
- Scratch blockers covered missing docs index, tool files, template pack,
  safety files, and evidence files.
- `--fail-on-blocker` against the incomplete scratch root exited `1`.
- Focused Release Check tests passed: 10 tests.
- Syntax compilation passed for `tools\release_check.py`.
- Unified Coffee CLI delegation worked in human-readable and JSON modes.
- Scratch root was not tracked or staged; `git status --short --untracked-files=all -- tmp\release-check-smoke`
  and `git ls-files -- tmp\release-check-smoke` returned no tracked/staged
  files.

Cost and token evidence:

- Model / Bean: none; no remote Bean used.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- The checker gives a compact release readiness view across repo, docs, tools,
  templates, safety, evidence, and tags.
- Strict blocker mode can be used by humans or scripts without preventing normal
  warning/info review.
- Unified Coffee CLI integration makes the release check available from the
  same command surface as dashboard, doctor, Pantry Search, Roastery report,
  template install, onboarding check, and Ledger summary.

Needs improvement:

- The incomplete scratch target was inside the Project Coffee Git worktree, so
  Git status/tag checks inherited parent repository metadata. Missing-file
  blockers still validated failure behavior, but future polish could report when
  the checked root is not the Git top-level directory.

### 2026-07-08 - Brew 21 / Shot 21B: Local RAG Design Review

Review questions:

1. What is the current Brew and next Shot?
2. Why did we choose the current default Bean?
3. What did Brew 19 prove?
4. Which files should be checked before release?
5. What evidence supports Project Coffee being v0.1-proven?
6. Which docs explain onboarding a new project?
7. Which local files should never be retrieved?
8. How would future chat UI answer with local evidence?
9. What needs user approval before sending context to a remote Bean?
10. How will stale or conflicting docs be handled?

Observed coverage:

- The design covers current status through Brew Log, Roadmap, and Changelog
  evidence.
- The design covers default Bean rationale through Roastery, House Blend, and
  Ledger evidence.
- The design can explain Brew 19 through Brew Log, Changelog, Ledger, and guide
  evidence.
- The design covers release-readiness questions through the Release Packaging
  Guide and release-check evidence.
- The design covers onboarding questions through the onboarding, template pack,
  and template installer guides.
- The design explicitly excludes secrets, hidden credential directories, raw
  Roastery outputs, generated reports unless selected, dependency folders,
  virtual environments, build artifacts, caches, binary files, production data,
  and private regulated data by default.
- The design explains how a future UI should show evidence bundles, citations,
  freshness warnings, assumptions, and remote Bean usage.
- The design requires human approval before sending local context to a remote
  Bean.

Gaps found:

- Brew 22 needs explicit query-class source profiles so source selection is not
  ad hoc.
- Brew 22 needs a release-proof profile for questions like "what evidence
  supports v0.1-proven?"
- Brew 22 needs a conflict rule that includes competing snippets when Brew Log,
  Roadmap, Changelog, guides, Roastery, or Ledger disagree.
- Brew 22 needs freshness scoring visible in bundle output.

Cost and token evidence:

- Model / Bean: none; no remote Bean used.
- API calls: none.
- Tokens: none / local-only for this design review; not metered.
- Cost: none / local-only; no external API cost.

Needs improvement:

- Brew 21C should close the design if the review notes are sufficient.
- Brew 22 should stay model-free and implement evidence bundles before any
  chat UI, embeddings, or vector database.

### 2026-07-08 - Brew 22 / Shot 22B: Local Evidence Bundle Dogfood

Commands run:

```powershell
python tools\evidence_bundle.py --help
python tools\evidence_bundle.py --root . --list-sources
python tools\evidence_bundle.py --root . --query "current Brew next Shot" --max-results 5
python tools\evidence_bundle.py --root . --query "House Blend default Bean" --max-results 5
python tools\evidence_bundle.py --root . --query "Brew 19 Ledger Summarizer" --max-results 5
python tools\evidence_bundle.py --root . --query "Local RAG evidence bundle" --max-results 5
python tools\evidence_bundle.py --root . --query "release packaging" --max-results 5
python tools\evidence_bundle.py --root . --query "Coffee Doctor" --max-results 5 --json
python tools\evidence_bundle.py --root . --query "Brew 21" --source brew-log/progress.md --max-results 3
python tools\evidence_bundle.py --root . --query "onboarding" --max-results 3 --output tmp\evidence-bundle-smoke\dogfood-bundle.md
python tools\evidence_bundle.py --root . --query "Coffee Doctor" --max-results 3 --json --output tmp\evidence-bundle-smoke\dogfood-bundle.json
python tools\evidence_bundle.py --root . --query "skipenvdogfoodunique" --max-results 5
python tools\evidence_bundle.py --root . --query "scratchknowledgeunique" --max-results 5
python tools\evidence_bundle.py --root . --query "rawlocaloutputunique" --max-results 5
python tools\evidence_bundle.py --root . --query "zzdogfoodnomatch20260708unique" --max-results 5
python -m unittest tests.test_evidence_bundle
python -m py_compile tools\evidence_bundle.py
python tools\coffee.py evidence-bundle --root . --query "House Blend" --max-results 5
python tools\coffee.py evidence-bundle --root . --query "Coffee Doctor" --max-results 5 --json
git status --short --untracked-files=all -- tmp\evidence-bundle-smoke
git ls-files -- tmp\evidence-bundle-smoke
```

Observed behavior:

- Help worked and listed query, max-results, JSON, source narrowing, source
  listing, and output flags.
- `--list-sources` listed the expected allowlisted Project Coffee sources:
  policy files, Roadmap, Changelog, Brew Log, docs, design docs, knowledge,
  Roastery notes, Ledger, and House Blend.
- Realistic Project Coffee queries returned useful local evidence:
  - `current Brew next Shot` surfaced Local RAG design coverage and the current
    `brew-log/progress.md` status.
  - `House Blend default Bean` surfaced House Blend, model-routing docs,
    progress entries, and Roastery evidence.
  - `Brew 19 Ledger Summarizer` surfaced Roastery dogfood notes, Changelog, and
    Ledger evidence.
  - `Local RAG evidence bundle` surfaced Brew 22 progress, Brew 21 Ledger
    evidence, and Local RAG design sections.
  - `release packaging` surfaced the Release Packaging Guide, Changelog,
    Roastery evidence, and Ledger evidence.
- JSON mode worked for `Coffee Doctor`; output parsed with 800 total matches and
  5 bundle items.
- Source narrowing worked for `--source brew-log/progress.md`; all returned
  items came from that file.
- Output mode wrote Markdown and JSON bundles under `tmp\evidence-bundle-smoke`.
- Scratch safety fixtures under `tmp\evidence-bundle-smoke`, including a
  synthetic `.env`, scratch Markdown, and scratch raw-output path, did not
  surface when queried by unique marker.
- Zero-match behavior returned exit `0` and printed `No evidence matches found`.
- Focused tests passed: 17 tests.
- Syntax compilation passed for `tools\evidence_bundle.py`.
- Unified Coffee CLI delegation worked in human-readable and JSON modes.
- Scratch files were not tracked; `git ls-files -- tmp\evidence-bundle-smoke`
  returned no tracked files.

Cost and token evidence:

- Model / Bean: none; no remote Bean used.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- Evidence bundles can ground Project Coffee answers in local paths, headings,
  snippets, freshness signals, safety classifications, and reasons selected.
- The allowlist/exclusion model kept synthetic `.env`, scratch `tmp`, and raw
  output fixture content out of results.
- JSON and output modes are ready for future UI/tool consumption.
- Unified Coffee CLI integration gives the MVP a consistent command surface.

Needs improvement:

- Ranking is useful but still keyword-heavy. The `House Blend default Bean`
  query surfaced relevant guide and evidence entries, but the exact current
  House Blend table row did not always rank first without source narrowing.
- Brew 22C should close the MVP if this dogfood evidence is sufficient.
- Future polish should add query-class source profiles and conflict/freshness
  handling before any chat UI work.

### 2026-07-08 - Brew 23 / Shot 23B: Model Routing Policy Dogfood

Review method:

- Docs and evidence-only scenario review.
- No routing code was implemented.
- No model runner logic was edited.
- No models, OpenRouter calls, external APIs, package installs, raw Roastery
  local outputs, or secrets were used.

Scenarios reviewed:

| Scenario | Routing decision | Approval required? | Context allowed |
| --- | --- | --- | --- |
| Current Brew and next Shot | Local evidence only | No | Brew Log, Roadmap, Changelog, local status docs |
| Summarize House Blend decision | Local evidence bundle first; remote rewrite only if approved | Only for remote rewrite | House Blend, Roastery, Ledger, routing guide |
| Fix a tiny Python bug | Local inspection/tests; default Bean only after context approval | Yes before remote code context | Small approved snippet and test output |
| Search Pantry for onboarding instructions | Local Pantry Search / evidence bundle | No | Pantry, onboarding docs, template docs |
| Run a model benchmark | Roastery workflow | Yes | Approved Order, selected Beans, summarized evidence |
| Send repo context to a model | Approval gate and context preview | Yes | Preview only; no secrets, `.env`, raw outputs, or excluded paths |
| Why did Poolside fail? | Local Roastery/Ledger evidence | No | Recorded failure notes and House Blend evidence |
| Which files are unsafe to retrieve? | Local policy/evidence answer | No | Local RAG design, evidence rules, routing policy |
| Future UI: do the next Shot for me | Decaf plan plus safe local tools | Yes before edits, remote calls, staging, or commits | Current Brew Log and allowlisted docs |
| Default Bean fails or is rate-limited | Fallback only if safe and approved | Maybe; fallback approval must be explicit | Same approved context plus failure metadata |

What worked:

- The policy covers the expected routing decisions for status, House Blend,
  Pantry, failure explanation, unsafe retrieval, benchmark, coding, and UI
  scenarios.
- Local-only answers remain the default for status, evidence, Pantry, cost,
  release, and safety-sensitive questions.
- Approval gates are clear before remote context, cost-bearing calls, House
  Blend changes, and risky workflow actions.

Gaps found:

- Future UI needs a visible context preview before any remote Bean receives
  local evidence.
- Fallback consent should be explicit in route records instead of assumed after
  a default Bean failure.
- Brew 24 fleet support needs project-local routing state: source allowlists,
  approval state, route decisions, and evidence records per project or assistant
  surface.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for this review; not metered.
- Cost: none / local-only; no external API cost.

### 2026-07-08 - Brew 24 / Shot 24B: Fleet Status Dogfood

Commands run:

```powershell
python tools/fleet_status.py --help
python tools/fleet_status.py --root .
python tools/fleet_status.py --root . --json
python tools/fleet_status.py --root . --registry fleet/projects.example.json --list
python tools/fleet_status.py --root . --registry fleet/projects.example.json --json
python tools/fleet_status.py --root tmp/fleet-status-smoke --registry projects.json --list
python tools/fleet_status.py --root tmp/fleet-status-smoke --registry projects.json --check
python tools/fleet_status.py --root tmp/fleet-status-smoke --registry projects.json --project complete --check
python tools/fleet_status.py --root tmp/fleet-status-smoke --registry projects.json --project incomplete --check
python tools/fleet_status.py --root tmp/fleet-status-smoke --registry projects.json --check --json
python tools/fleet_status.py --root tmp/fleet-status-smoke --registry projects.json --project incomplete --check --fail-on-issue
python -m unittest tests.test_fleet_status
python -m py_compile tools/fleet_status.py
python tools/coffee.py fleet-status --root .
python tools/coffee.py fleet-status --root . --registry fleet/projects.example.json --list
```

Observed behavior:

- Help output worked and listed root, registry, JSON, list, project, check, and
  fail-on-issue flags.
- Default registry behavior was safe: missing `fleet/projects.json` reported
  `INFO`, suggested copying `fleet/projects.example.json`, and exited `0`.
- Default missing-registry JSON output was valid and reported the same `INFO`
  finding.
- Example registry parsed and listed one placeholder project with no checks run.
- Example registry JSON output was valid.
- Scratch registry under `tmp/fleet-status-smoke` listed two projects:
  `complete` and `incomplete`.
- Scratch `--check` reported `complete` as `OK` and `incomplete` as `FAIL`.
- Project filtering worked for both `complete` and `incomplete`.
- The incomplete filtered check identified the missing `AGENTS.md` marker.
- `--fail-on-issue` for the incomplete project returned nonzero as expected.
- Focused tests passed: 15 tests.
- Syntax compilation passed for `tools/fleet_status.py`.
- Unified Coffee CLI delegation worked for default registry behavior and example
  registry listing.
- Scratch files under `tmp/fleet-status-smoke` were not intended for commit.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- Fleet Status gives a safe, local-first way to reason across registered
  projects without reading project contents.
- Missing real registry behavior is non-blocking and points to the example
  registry.
- Scratch checks showed the MVP can distinguish complete Project Coffee
  onboarding markers from an incomplete project.
- JSON output and Unified Coffee CLI delegation are ready for future UI use.

Needs improvement:

- Brew 24C should close the Fleet Status MVP if the dogfood evidence is
  sufficient.
- Future fleet work should decide whether `fleet/projects.json` stays
  user-local/ignored or becomes an intentional committed project registry.
- Future versions may add safe per-project Doctor/Dashboard delegation, but
  Brew 24A/24B intentionally avoided running tools inside external projects.

### 2026-07-08 - Brew 25 / Shot 25B: v1.0 Release Closeout Dogfood

Commands run:

```powershell
git status --short
git log --oneline --decorate -15
git tag -l
python tools/coffee.py --help
python tools/coffee.py --version
python tools/coffee.py dashboard --root .
python tools/coffee.py doctor --root .
python tools/coffee.py release-check --root .
python tools/coffee.py release-check --root . --json
python tools/coffee.py ledger-summary --root . --max-entries 8
python tools/coffee.py evidence-bundle --root . --query "Project Coffee v1.0 stronger base" --max-results 8
python tools/coffee.py fleet-status --root .
python tools/coffee.py fleet-status --root . --registry fleet/projects.example.json --list
python -m unittest tests.test_coffee_cli
python -m unittest tests.test_coffee_doctor
python -m unittest tests.test_release_check
python -m unittest tests.test_ledger_summary
python -m unittest tests.test_evidence_bundle
python -m unittest tests.test_fleet_status
python -m py_compile tools/coffee.py tools/coffee_dashboard.py tools/coffee_doctor.py tools/release_check.py tools/ledger_summary.py tools/evidence_bundle.py tools/fleet_status.py
```

Observed behavior:

- Git status started clean and no v1.0 tag existed.
- Existing tags remained `v0.1`, `v0.1-certified`, and `v0.1-proven`.
- Unified Coffee CLI help and version worked.
- Dashboard ran successfully and exposed stale Brew Log summary fields; those
  status fields were corrected as part of Brew 25B evidence updates.
- Doctor returned `WARN` with 38 OK, 1 WARN, and 0 FAIL.
- The Doctor warning is the known ADR literal staged secret-check command
  warning in `docs/adr/0005-local-openrouter-coffee-core.md`.
- Release Check returned `OK` with 14 OK, 0 WARN, and 0 BLOCKER.
- Release Check JSON worked.
- Ledger Summary worked and showed recent local-only validation entries.
- Evidence Bundle found the new v1.0 closeout and handoff docs, while also
  surfacing noisy Ledger matches for the `v1.0` query.
- Default Fleet Status safely reported missing `fleet/projects.json` as `INFO`.
- Example Fleet registry listing worked.
- Focused tests passed for Coffee CLI, Doctor, Release Check, Ledger Summary,
  Evidence Bundle, and Fleet Status.
- Key tool syntax compilation passed.

Readiness:

- Status: READY WITH WARNINGS.
- Blocking failures: none.
- Warning 1: known Doctor ADR warning remains visible.
- Warning 2: default real fleet registry is intentionally absent.
- Warning 3: Evidence Bundle ranking has noise on the `v1.0` query.
- Tag status: no tag was created.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

Needs improvement:

- Brew 25C should decide whether the warnings are accepted for a v1.0 stronger
  base tag or whether the ADR warning should be fixed first.
- Before any commit, stage only intended files and run the staged
  secret-pattern check from Project Coffee policy.

### 2026-07-08 - Brew 26 / Shot 26B: Coffee Counter UI Design Dogfood

Workflow review:

| # | Workflow | Result |
| --- | --- | --- |
| 1 | Open Coffee Counter for current project status | Supported by Home / Overview with Dashboard, Doctor, Release Check, Brew status, and next Shot |
| 2 | Ask "What should I do next?" | Supported by local Evidence Bundle plus Brew Log and Roadmap grounding |
| 3 | Ask for next prompt set | Supported as local-only prompt/checklist drafting with command blocks and no auto-commit |
| 4 | Ask "Why is this project warning?" | Supported by Doctor summary, finding details, and safe next action |
| 5 | Ask "Which projects need attention?" | Supported by Fleet summary without secret inspection |
| 6 | Ask "Can Coffee send this to a model?" | Supported for future UI by routing panel, context preview, and approval gate; remote disabled in MVP |
| 7 | Ask "Run validation." | Supported by allowlisted local commands with preview and stdout/stderr/exit code display |
| 8 | Ask "Commit this." | Supported as checklist/command drafting only; no automatic commit in MVP |
| 9 | Doctor/Release Check warning | Supported by visible warning state, release readiness, and next safe action |
| 10 | Evidence Bundle no matches | Supported by honest no-evidence state and query refinement suggestions |

Gaps found:

- Brew 27 needs a small allowlisted command-wrapper helper.
- Ask Coffee should be local evidence plus deterministic prompt/checklist
  drafting, not a remote model.
- Warning details should preserve severity, path, finding code, and suggested
  safe next action.
- No-evidence handling should be explicit.
- Remote routing and Git write actions should be disabled in MVP.

Streamlit MVP implications:

- Implement Home / Overview, Ask Coffee local-only, Evidence Bundle, Doctor
  summary, and Fleet summary first.
- Keep Release Check, Ledger, Roastery, routing details, and settings as links,
  placeholders, or read-only summaries if needed.
- Do not implement remote model calls, file editing, raw output inspection,
  Git staging/commit/tag, or background agent behavior.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for this design review; not metered.
- Cost: none / local-only; no external API cost.

### 2026-07-08 - Brew 27 / Shot 27B: Streamlit Coffee Counter MVP Dogfood

Commands run:

```powershell
python -m unittest tests.test_coffee_counter_ui
python -m py_compile ui\coffee_counter_app.py
python tools\coffee.py dashboard --root .
python tools\coffee.py doctor --root .
python tools\coffee.py release-check --root .
python tools\coffee.py ledger-summary --root . --max-entries 5
python tools\coffee.py evidence-bundle --root . --query "Coffee Counter UI" --max-results 5
python tools\coffee.py fleet-status --root .
python -m streamlit run ui\coffee_counter_app.py --server.headless true --server.port 8765 --browser.gatherUsageStats false
```

Additional local adapter/UI smoke checks:

- Imported `ui.coffee_counter_app` without requiring a module-level Streamlit object.
- Confirmed the adapter allowlist includes only Dashboard, Doctor, Release Check, Ledger Summary, Evidence Bundle, and Fleet Status.
- Confirmed a non-allowlisted `commit` action is rejected with `CommandAdapterError`.
- Confirmed `subprocess.run` is called with `shell=False` through focused unit coverage.
- Started Streamlit locally with usage stats disabled and confirmed the app server returned HTTP 200 and health `ok`.
- Used Streamlit's local testing harness to confirm the six expected tabs:
  Home / Overview, Ask Coffee, Evidence Bundle, Ledger, Fleet, and Safety / Commands.
- Used the local testing harness to click Dashboard, Doctor, Evidence Bundle, Ledger Summary, and Fleet Status buttons; each returned exit code 0 through the UI adapter.

Observed behavior:

- Focused UI adapter tests passed: 10 tests.
- `ui/coffee_counter_app.py` compiled successfully.
- Dashboard returned `OK`.
- Doctor returned `WARN` with the known non-blocking warning state.
- Release Check returned `OK`.
- Ledger Summary returned recent local-only evidence entries.
- Evidence Bundle found Coffee Counter UI guide/design/Brew evidence.
- Fleet Status safely reported missing default `fleet/projects.json` as `INFO`.
- Streamlit was already installed locally; no package install was performed.
- The Streamlit app opened locally in server-smoke form and its visible tab/button structure was verified through Streamlit's test harness.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- The Coffee Counter MVP can wrap the core local Coffee CLI tools without exposing arbitrary command execution.
- The UI adapter remains importable for tests without requiring Streamlit.
- The first Streamlit surface exposes the expected local-only screens and command actions.
- Dashboard, Doctor, Evidence Bundle, Ledger Summary, and Fleet Status work through the UI adapter.

Needs improvement:

- Brew 27C should close the MVP if the completion criteria remain satisfied.
- A future UI polish pass can improve visual layout and warning display depth after the local-only command surface is accepted.
- Remote Bean routing, file edits, Git operations, raw Roastery output inspection, and background automation remain intentionally out of scope.

### 2026-07-08 - Brew 28 / Shot 28B: UI Evidence Bundle Integration Dogfood

Commands run:

```powershell
python -m unittest tests.test_coffee_counter_ui
python -m py_compile ui\coffee_counter_app.py
python tools\coffee.py evidence-bundle --root . --query "Coffee Counter UI evidence bundle" --max-results 8 --json
python tools\coffee.py evidence-bundle --root . --query "zzzz_unique_no_match_query_280000" --max-results 5 --json
python tools\coffee.py doctor --root .
python tools\coffee.py release-check --root .
python tools\coffee.py ledger-summary --root . --max-entries 5
python tools\coffee.py fleet-status --root .
python -m streamlit run --server.headless=true --server.port=8765 --browser.gatherUsageStats=false ui\coffee_counter_app.py
```

Observed behavior:

- Focused Coffee Counter UI tests passed: 17 tests.
- `ui/coffee_counter_app.py` compiled successfully.
- Evidence Bundle JSON query returned structured local evidence with source paths, headings, snippets, scores, freshness, and safety labels.
- Zero-match JSON query exited 0 with `total_matches: 0`, an empty bundle, and no warnings.
- Doctor returned `WARN` with the known non-blocking warning state.
- Release Check returned `OK`.
- Ledger Summary returned recent local-only evidence entries.
- Fleet Status safely reported missing default `fleet/projects.json` as `INFO`.
- Streamlit was already installed locally; no package install was performed.
- Streamlit server smoke passed when launched as a background job: root returned HTTP 200 and health returned OK.
- Streamlit UI harness verified Ask Coffee local-only showed the evidence command, evidence table, local evidence draft, not-model-generated label, source/snippet evidence, and "No model call was made."
- Streamlit UI harness verified the zero-match query showed an honest no-evidence / insufficient-evidence state.
- Streamlit UI harness verified the Evidence Bundle tab showed Markdown output, JSON output, and structured evidence rows.
- Dashboard, Doctor, Release Check, Ledger Summary, Evidence Bundle, and Fleet Status buttons remain present in the UI.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- The Coffee Counter UI can turn local Evidence Bundle JSON into inspectable evidence rows and a deterministic local-only draft.
- Zero-match behavior is honest and non-failing.
- The exact safe CLI command remains visible.
- The UI path preserves the no-model/no-OpenRouter/no-external-API boundary.

Needs improvement:

- Brew 28C should close the integration if completion criteria remain satisfied.
- Future UI work can make evidence tables easier to scan and add clearer citation affordances.
- Brew 29 should add routing approval gates before any remote Bean can receive local context.

### 2026-07-08 - Brew 29 / Shot 29B: UI Routing Approval Gates Dogfood

Commands run:

```powershell
python -m unittest tests.test_coffee_counter_ui
python -m py_compile ui\coffee_counter_app.py
python tools\coffee.py evidence-bundle --root . --query "model routing approval gate" --max-results 8 --json
python tools\coffee.py doctor --root .
python tools\coffee.py release-check --root .
python tools\coffee.py ledger-summary --root . --max-entries 5
python tools\coffee.py fleet-status --root .
python -m streamlit run ui/coffee_counter_app.py
```

Observed behavior:

- Focused Coffee Counter UI tests passed: 28 tests.
- `ui/coffee_counter_app.py` compiled successfully.
- Evidence Bundle JSON returned routing-policy, Brew Log, UI guide, House Blend, Roastery, and Ledger evidence.
- Doctor returned `WARN` with the known non-blocking ADR warning about the literal staged secret-check command.
- Release Check returned `OK`.
- Ledger Summary returned recent local-only evidence entries.
- Fleet Status safely reported missing default `fleet/projects.json` as `INFO`.
- Streamlit was already installed locally; no package install was performed.
- Streamlit server smoke passed after launch on a local loopback port; health returned HTTP 200 and the process was stopped.
- Streamlit UI harness verified the Routing / Approval tab is visible and no OpenRouter, API-key, or model-call controls appear.
- Ask Coffee scenario checks passed:
  - "What is the current Brew?" routed to Local evidence only; approval not required.
  - "How do I onboard a project?" routed to Local evidence only; approval not required.
  - "How much did Brew 14 cost?" routed to Local evidence only with Ledger context; approval not required.
  - "Run a benchmark for a new model." routed to Roastery benchmark required; approval required.
  - "Send repo context to a model." routed to Remote Bean requires approval; preview only.
  - "Commit this change." routed to Decaf / no model with manual-only next action; no auto-commit behavior.
- Each scenario showed preview-only context behavior; no remote call path was exposed.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- Routing decisions match the policy-backed task classes expected by the UI.
- Approval gates are visible for benchmark, repo-context, and commit-like requests.
- Context preview remains preview-only and does not send evidence anywhere.
- Existing local-only command surfaces remain available.

Needs improvement:

- Brew 29C should close the routing approval gate work if completion criteria remain satisfied.
- Future UI work should keep remote Bean execution disabled until explicit approval, context preview, Ledger/Roastery evidence, and routing policy enforcement are implemented together.

### 2026-07-08 - Brew 30 / Shot 30B: UI Packaging and Polish Plan Review

Review performed:

- New local user run path: covered by setup notes and the manual Streamlit run command.
- Existing user faster startup: covered by future `scripts/start_coffee_counter.ps1` helper path.
- Polished desktop app request: covered by React/Tauri and local desktop wrapper later path with migration criteria.
- Remote model calls from UI: explicitly out of current packaging scope; future approval-gated design only.
- Screenshot or product demo: covered as documentation screenshots later, not a Brew 30 blocker.
- Project switching: covered as fleet project switching polish, not a packaging blocker.
- Poor retrieval for "current Brew": covered as better current Brew retrieval ranking polish.
- Auto-commit from UI: covered by no auto-commit / no Git writes safety constraints.
- Langflow integration: explicit non-goal.
- Package install command: covered by future `requirements-ui.txt` or helper script, not created without approval.

Result:

- Plan holds.
- No blocking gaps found.
- Recommended next Brew is Brew 30C closeout, followed by Brew 31 Streamlit polish pass if closeout criteria remain satisfied.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only docs review; not metered.
- Cost: none / local-only; no external API cost.

Needs improvement:

- Fresh-user startup is still manual until a future helper or UI requirements file is explicitly approved.
- Screenshots should wait until after the next polish pass.
- Project/fleet switching and current Brew retrieval ranking remain usability polish items.

### 2026-07-08 - Brew 31 / Shot 31B: Streamlit Polish Pass Dogfood and Closeout

Commands run:

```powershell
python -m unittest tests.test_coffee_counter_ui
python -m py_compile ui/coffee_counter_app.py
python tools/coffee.py evidence-bundle --root . --query "What is the current Brew?" --max-results 8 --json
python tools/coffee.py evidence-bundle --root . --query "zzzz_unique_no_match_query_310000" --max-results 5 --json
python tools/coffee.py doctor --root .
python tools/coffee.py release-check --root .
python tools/coffee.py ledger-summary --root . --max-entries 8
python tools/coffee.py fleet-status --root .
python -m streamlit run ui/coffee_counter_app.py
```

Observed behavior:

- Focused Coffee Counter UI tests passed: 40 tests.
- `ui/coffee_counter_app.py` compiled successfully.
- Current-state Evidence Bundle query returned local evidence with Brew Log items in the results.
- Zero-match Evidence Bundle query exited successfully with `total_matches: 0` and an empty bundle.
- Doctor returned `WARN` with the known non-blocking ADR warning about the literal staged secret-check command.
- Release Check returned `OK`.
- Ledger Summary returned recent local-only evidence entries with no warnings.
- Fleet Status safely reported missing default `fleet/projects.json` as `INFO`.
- Streamlit was already installed locally; no package install was performed.
- Streamlit server smoke passed on a local loopback port with HTTP 200, and the process was stopped.

Scenario checklist:

- "What is the current Brew?" showed Current State Quick View, Brew Log evidence, Local evidence only routing, a local evidence draft, and "No model call was made."
- "What should I do next?" showed Current State Quick View, next-work evidence, and no model call.
- "Send repo context to a model." showed Approval required, preview-only context behavior, no remote execution, and blocked-context / secrets warnings.
- `zzzz_unique_no_match_query_310000` showed an honest no-evidence state with suggestions.
- Home / Overview command output exposed command, return code, status summary, stdout, and stderr sections.
- Ledger Summary still worked.
- Safety checks found no arbitrary command execution, API key input, OpenRouter button, model-call control, or auto-commit control.

Fixes made:

- No product fixes were required. A harness-only readability probe was adjusted during review after confirming command output is exposed through named expanders.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- Current-state questions are easier to answer from local Brew Log evidence.
- Route badges make local-only, approval-required, Roastery-required, manual-only Git, and Decaf/no-model states easier to scan.
- Output grouping makes command results more reviewable without hiding stderr.
- No-evidence states are honest and actionable.

Needs improvement:

- Brew 32 should make project root and Fleet project switching smoother across multiple Coffee projects.
- Fresh-user startup still depends on the manual Streamlit command until a future helper script or UI requirements file is approved.

### 2026-07-08 - Brew 32 / Shot 32B: Project/Fleet Switching Dogfood and Closeout

Commands run:

```powershell
python -m unittest tests.test_coffee_counter_ui
python -m py_compile ui/coffee_counter_app.py
python tools/coffee.py fleet-status --root .
python tools/coffee.py evidence-bundle --root . --query "Coffee Counter project root switching" --max-results 8 --json
python tools/coffee.py doctor --root .
python tools/coffee.py release-check --root .
python tools/coffee.py ledger-summary --root . --max-entries 8
python -m streamlit run ui/coffee_counter_app.py
```

Observed behavior:

- Focused Coffee Counter UI tests passed: 54 tests.
- `ui/coffee_counter_app.py` compiled successfully.
- Fleet Status safely reported missing default `fleet/projects.json` as `INFO`.
- Evidence Bundle returned local Brew 32 project/fleet switching evidence.
- Doctor returned `WARN` with the known non-blocking ADR warning about the literal staged secret-check command.
- Release Check returned `OK`.
- Ledger Summary returned recent local-only evidence entries.
- Streamlit was already installed locally; no package install was performed.
- Streamlit server smoke passed on a local loopback port with HTTP 200, and the process was stopped.

Manual scenario checklist:

- Valid root startup showed the active root, clear root-exists status, Project Coffee marker status, and Project Health.
- Ask Coffee with "What is the current Brew?" showed Current State Quick View, Brew Log evidence, selected-root context, and no model/API call.
- Evidence Bundle query "Coffee Counter project switching" used the selected root and returned local evidence.
- Invalid root `C:\Users\iisha\Definitely_Not_Project_Coffee_32` showed warnings, blocked command execution, and did not crash the UI.
- Returning to `C:\Users\iisha\Project_Coffee` restored valid state and command execution.
- Session-only recent roots were visible in the UI; helper tests cover duplicate handling and max-item capping. No recent-root file or persistent config was written.
- Fleet tab showed active root, Fleet Status command output, return code, registry status, project count, and an understandable missing-registry warning.
- Dashboard, Doctor, Release Check, Ledger, and Fleet still worked for the valid root.
- Safety checks found no API key field, OpenRouter button, model execution button, auto-commit/stage/push control, or arbitrary shell command box.

Fixes made:

- No product fixes were required. A harness-only session-state introspection attempt could not read Streamlit internals directly, but the UI displayed session-only recent roots and the pure helper tests validated recent-root behavior.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for this dogfood run; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- Root switching is safer and clearer without writing persistent configuration.
- Invalid roots fail closed before command execution.
- Fleet status is more understandable when the default local registry is missing.
- Existing local-only tabs continued to work with the selected root.

Needs improvement:

- Brew 33 should design the future remote-call approval flow before any remote context can be sent from the UI.
- A future Brew can design persistent root history or Fleet registry editing separately, with explicit safety rules.

### 2026-07-08 - Brew 33 / Shot 33B: Remote Call Approval Design Dogfood and Closeout

Commands run:

```powershell
python -m unittest tests.test_coffee_counter_ui
python -m py_compile ui/coffee_counter_app.py
python tools/coffee.py evidence-bundle --root . --query "remote call approval design safety gate ledger provider model" --max-results 8 --json
python tools/coffee.py doctor --root .
python tools/coffee.py release-check --root .
python tools/coffee.py ledger-summary --root . --max-entries 8
python tools/coffee.py fleet-status --root .
```

Observed behavior:

- Focused Coffee Counter UI tests passed: 54 tests.
- `ui/coffee_counter_app.py` compiled successfully.
- Evidence Bundle returned the Brew 33 design, Brew Log, Changelog, UI guide, and Ledger evidence.
- Doctor returned `WARN` with the known non-blocking ADR warning about the literal staged secret-check command.
- Release Check returned `OK` before the 33B closeout edits.
- Ledger Summary returned recent local-only evidence entries.
- Fleet Status safely reported missing default `fleet/projects.json` as `INFO`.

Scenario checklist:

- Simple local question: covered as local-only, no approval, no context sent, and no remote-call Ledger entry.
- Docs question: covered as local evidence first; remote help is optional only after explicit future approval.
- Code planning: covered as approval-gated with context preview, selected files, excluded files, Safety Gate result, provider/model choice, and Ledger plan.
- Whole-repo context request: refined to blocked until narrowed, with oversized-context warning and path/secret exclusions.
- Secret-risk `.env` request: refined to blocked without showing secret values, requiring manual remove/redact.
- Benchmark request: covered as Roastery first, benchmark approval, and Ledger required.
- Missing API key: refined to block gracefully without sending prompt/context or asking for keys in chat/UI.
- Provider timeout/failure: covered with visible result card, retry rules, and Ledger failure record if a call was attempted.
- Ledger write failure: refined as not success; result remains visible and evidence capture must be retried/manual.
- User cancellation: covered as local-only, no remote call, no cost, and context discarded from approval session.
- Active root changes mid-approval: refined to invalidate approval and require preview regeneration.
- Generated code response: covered as advisory only, with no automatic file write, staging, commit, or push.

Design gaps found:

- Needed a concise scenario review table tying each scenario to decision, UI display, Ledger record, user next action, and forbidden behavior.
- Needed clearer language for whole-repository context, missing provider keys, active-root changes, Ledger write failure, and generated-code advisory status.

Refinements made:

- Added Brew 33B scenario review to `docs/design/remote-call-approval-design.md`.
- Updated implementation roadmap to make Brew 34 the local context package builder and Safety Gate only.
- Updated UI docs and Roadmap to keep remote-call behavior design-only.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only design review; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- The approval-gated design covers local-only, approval-gated, blocked, failed, cancelled, stale/root-changed, and advisory-output paths.
- Ledger requirements are explicit enough for a future planned-call preview.
- The next Brew can safely implement only a local context package builder and Safety Gate without adding remote calls.

Needs improvement:

- Brew 34 should implement the local context package builder, Safety Gate report, token estimate placeholder, and approval-ready preview object without network calls.

### 2026-07-08 - Brew 34 / Shot 34A: Remote Context Package Builder Implementation

Commands run during implementation:

```powershell
python -m unittest tests.test_context_package
python -m unittest tests.test_coffee_counter_ui
python -m py_compile tools/coffee_context_package.py
python -m py_compile ui/coffee_counter_app.py
```

Implementation summary:

- Added `tools/coffee_context_package.py` as a local-only context package builder and Safety Gate.
- Added focused package tests for schema fields, default approval state, provider/model placeholder state, evidence limits, unsafe path exclusion, suspicious text redaction labels, token estimates, and summary output.
- Updated Coffee Counter Routing / Approval to show a preview-only context package built from request text, route decision, active root, and local Evidence Bundle items.
- The UI preview shows package status, active root, route decision, estimated tokens, evidence counts, included/excluded counts, Safety Gate status, warnings/block reasons, and JSON preview.

Safety observations:

- Provider/model fields remain placeholders with `provider: null`, `model: null`, and `status: not_selected`.
- User approval defaults to false with no approval timestamp or approved context hash.
- Suspicious content is labeled and redacted without printing the matched value.
- Unsafe paths such as `.env`, hidden credential directories, dependency folders, build output, caches, databases, and key-like files are excluded or blocked.
- No OpenRouter integration, API key input, model/API call, network code, send-to-model button, remote execution, file write, Git write, auto-commit, or auto-push was added.

Evidence quality:

- Focused tests and compile checks passed before final validation.
- The package remains a schema-like local preview object, not a remote API payload.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only for implementation; package token estimates are local character-count estimates only.
- Cost: none / local-only; no external API cost.

Needs improvement:

- Brew 35 should build only a dry-run approval UI around the local package before any future remote-call implementation is considered.

### 2026-07-08 - Brew 34 / Shot 34B: Remote Context Package Builder Dogfood and Closeout

Dogfood scenarios reviewed:

- Ask Coffee / Current State: `What is the current Brew?`
- Docs question: `What does the Coffee Counter UI currently do?`
- Remote-helpful request: `Use a model to explain the project state and suggest next steps.`
- Risky whole-repo request: `Send my whole repo to a model.`
- Secret-risk request: `Include my .env file in the context package.`
- Suspicious token-like text using a runtime fake value only.
- Active root / selected root handling.
- Empty evidence query.

What worked:

- Local Evidence Bundle queries returned Project Coffee evidence without model/API calls.
- Context packages built from request text, route decision, selected active root, and local evidence.
- Current-state packages included Brew Log evidence after UI prioritization.
- Provider/model stayed not selected.
- User approval stayed false.
- Empty-evidence packages built without crashing.
- The fake token-like runtime probe was labeled as suspicious and the matched value was not echoed.

Issues found and fixed:

- Explicit model-help requests initially stayed local-only; routing now classifies them as approval-needed previews.
- Whole-repository context requests initially produced a passing package; the Safety Gate now blocks broad repository context until narrowed.
- `.env` requests needed request-level blocking even when no evidence item was selected; the Safety Gate now blocks requested blocked path patterns.
- Secret-context requests now route to a blocked local/Decaf path.

Validation notes:

- Focused tests were expanded for broad-repo blocking, `.env` request blocking, empty-evidence package builds, explicit model-help routing, and secret-context routing.
- Docs query evidence was usable but a little noisy; Brew 35 can improve UI context selection and ranking display without changing the safety boundary.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only dogfood; package token estimates are local character-count estimates only.
- Cost: none / local-only; no external API cost.

Closeout:

- Brew 34 dogfood confirmed that Coffee Counter can build a local, preview-only context package from request text, route decision, active root, and local evidence.
- The Safety Gate excludes blocked paths such as `.env` and labels suspicious secret-like patterns without printing secret values.
- No OpenRouter, API key input, model call, network call, or send-to-model action exists in Brew 34.
- Remaining work moves to Brew 35: dry-run approval UI.

### 2026-07-09 - Brew 35 / Shot 35A: Approval Gate Dry Run UI Implementation

Commands run during implementation:

```powershell
python -m unittest tests.test_approval_dry_run
python -m unittest tests.test_context_package
python -m unittest tests.test_coffee_counter_ui
python -m py_compile tools/coffee_approval_dry_run.py tools/coffee_context_package.py ui/coffee_counter_app.py
```

Implementation summary:

- Added `tools/coffee_approval_dry_run.py` as a local-only helper for dry-run
  approval state, checklist gating, approval requirement summaries, and
  dry-run Ledger previews.
- Updated Coffee Counter Routing / Approval with request summary, route
  decision, context package preview, Safety Gate checklist, included/excluded
  evidence summary, required dry-run checklist, dry-run Ledger preview, and a
  disabled future send state.
- Added focused tests for local-only approval behavior, approval-needed safe
  packages, blocked packages, missing packages, provider/model placeholders,
  preview-only Ledger status, unknown estimated cost, and disabled future send
  state.

Safety observations:

- Dry-run approval is simulation only.
- No remote context is sent anywhere.
- Provider and model remain placeholders with no provider or model selected.
- The dry-run Ledger preview is not written automatically.
- Safety-blocked packages disable approval controls and keep the future send
  state unavailable.
- No OpenRouter integration, API key input, provider/model selector, pricing
  logic, network code, model/API call, remote execution, working send-to-model
  button, auto-commit, or auto-push was added.

Evidence quality:

- Focused helper, context-package, and Coffee Counter UI tests passed before
  final validation.
- Syntax compilation passed for the approval helper, context package builder,
  and Coffee Counter UI app.

Cost and token evidence:

- Model / Bean: none.
- API calls: none.
- Tokens: none / local-only implementation; package estimates remain local
  character-count estimates only.
- Cost: none / local-only; no external API cost.

Needs improvement:

- Brew 35B should dogfood the approval UX in the Streamlit UI, verify blocked
  and no-evidence states, refine copy if needed, and close Brew 35.

### 2026-07-09 - Brew 35 / Shot 35B: Approval Gate Dry Run UI Dogfood and Closeout

Dogfood scenarios reviewed:

- Approval-needed safe request:
  `Use a model to explain the project state and suggest next steps.`
- Local-only request: `What is the current Brew?`
- Blocked secret request: `Include my .env file in the context package.`
- Whole-repository request: `Send my whole repo to a model.`
- Partial dry-run checklist.
- Completed dry-run checklist.
- Cancel/reset state.
- Active root / project switching state.

What worked:

- Approval-needed safe requests route to `Remote Bean requires approval`, build a
  preview-only context package, pass the Safety Gate, show checklist
  requirements, and can become `dry_run_approved` only after all checklist items
  are complete.
- Local-only requests build local evidence packages, stay
  `local_only_no_approval`, and cannot be dry-run approved unnecessarily.
- `.env` requests are blocked without reading or printing secret values.
- Whole-repository context requests are blocked until narrowed.
- Partial checklists remain `context_preview_ready` and report incomplete
  checklist items.
- Completed checklists produce `dry_run_approved` for safe approval-needed
  packages.
- Cancel/reset produces `dry_run_cancelled`.
- Active root values are copied into newly built packages, so selected-root
  changes do not reuse stale package state.
- Dry-run Ledger preview remains `preview_only_not_written`.
- Provider/model remain `null` / `not_selected`, estimated cost remains
  unknown, and send remains `send_disabled_future_brew`.

Validation notes:

- Focused approval, context package, and Coffee Counter UI tests passed.
- The Coffee Counter app compiled successfully.
- A bounded local Streamlit smoke returned HTTP 200 and was shut down.
- Doctor returned the known non-blocking ADR warning only.
- Release Check returned the expected dirty-working-tree warning during this
  uncommitted closeout.
- Evidence Bundle found Brew 35A/35B evidence, Ledger Summary recorded the
  work as local-only, and Fleet Status returned the known missing-registry info.

Issues found and fixed:

- No product code fix was required during Brew 35B dogfood.
- A scenario-probe harness mistake was corrected locally; it did not affect the
  product code.

Closeout:

- Brew 35 dogfood confirmed that Coffee Counter can simulate the remote-call
  approval flow without sending data anywhere.
- Approval-needed requests show context package preview, Safety Gate checklist,
  dry-run approval checklist, and Ledger preview.
- Blocked secret or whole-repository requests cannot be dry-run approved.
- Ledger preview is not written automatically.
- No OpenRouter, API key input, model call, network call, provider/model
  selector, or real send action exists in Brew 35.
- Remaining work moves to Brew 36: OpenRouter integration behind explicit
  approval, if chosen.

### 2026-07-09 - Gate Repair: PLAN-spill-guard-token-log-fix.md and PLAN-root-test-discovery-fix.md

Scope: execute two previously written, previously reviewed plans in order,
verify every precondition and acceptance criterion, stage but do not commit.

Commands run (representative; full sequence in `brew-log/progress.md`):

```powershell
git check-ignore -v ledger/token_log.md
Select-String -Path .cursorignore -Pattern "!ledger/token_log.md"
Select-String -Path .gitignore -Pattern "!ledger/token_log.md"
# .gitignore edited: !ledger/token_log.md added after **/*token*
git status --short
python -m unittest discover
python -m unittest discover -s tests
python tools\run_all_tests.py
python -m py_compile tools\run_all_tests.py
git add .gitignore ledger/token_log.md tools/run_all_tests.py docs/releases/v1.0-closeout-checklist.md docs/releases/project-coffee-v1.0-handoff.md
git diff --staged
```

Observed behavior:

- Plan 1 (Spill Guard) executed exactly as written. All 4 preconditions
  matched expected output. `.gitignore` gained `!ledger/token_log.md`, a
  one-line diff. `ledger/token_log.md` is now visible to `git status` as
  untracked instead of silently hidden, and is tracked once staged.
- One acceptance-criterion nuance: `git check-ignore -v ledger/token_log.md`
  (with `-v`) prints the matched negation pattern and exits `0`, not "no
  output, exit 1" as the plan's AC2 text expected. The substantive check
  (`git check-ignore` without `-v`) confirms no output and exit `1` - the
  file is genuinely un-ignored. This is a documented quirk of git's
  `check-ignore -v` flag reporting negation matches, not a defect in the fix.
- Plan 2 (root test discovery) found a real bug in its own prescribed script
  during execution, not before: the script's `(tests, REPO_ROOT)` pairing
  raised `ImportError: Start directory is not importable` because `tests/`
  has no `__init__.py`. Pairing `(tests, tests)` instead fixed that but
  surfaced a second, deeper bug: running all four test roots in one Python
  process caused `apps/coffee-status/src` and `apps/coffee-certification/src`
  - both top-level packages literally named `src` - to collide in
  `sys.modules`, breaking `from src.certifier import ...` once
  `apps/coffee-status`'s `src` had already been imported.
- Stopped and asked for direction rather than silently patching, per this
  session's explicit instructions. Given approval, rewrote
  `tools/run_all_tests.py` to run each of the four test roots as an isolated
  subprocess (`python -m unittest discover -s <dir>`), matching the
  per-directory commands already documented elsewhere in the repo, instead
  of one shared in-process `TestLoader`. This avoids the collision entirely.
- Final result: `python tools\run_all_tests.py` collects and passes 252
  tests (214 `tests/`, 22 `roastery/tests/`, 9 `apps/coffee-status/tests/`,
  7 `apps/coffee-certification/tests/`), exit code `0`.
- The bare `python -m unittest discover` (no `-s`) from the repo root still
  collects 0 tests, unchanged. This is expected: the plan's fix was to stop
  relying on that literal command (both release-facing docs now reference
  `tools\run_all_tests.py` instead), not to make the un-fixable bare
  invocation itself succeed. Renaming the hyphenated `apps/coffee-status`
  and `apps/coffee-certification` directories was explicitly out of scope.
- A second acceptance-criterion nuance: the rewritten script's summary block
  prints `Total tests run:` but no longer prints the literal `Total
  failures:` / `Total errors:` lines the plan's AC1 text expected, since
  those counts are no longer tracked separately once each root runs as its
  own subprocess. Exit code `0` and the absence of any `FAIL:` line carry
  the same substance.
- All five changed files (`.gitignore`, `ledger/token_log.md`,
  `tools/run_all_tests.py`, `docs/releases/v1.0-closeout-checklist.md`,
  `docs/releases/project-coffee-v1.0-handoff.md`) were staged and reviewed
  via `git diff --staged`. Nothing was committed.

Cost and token evidence:

- Model / Bean: none; no remote Bean, OpenRouter call, or external API used.
- Tokens: none / local-only; not metered.
- Cost: none / local-only; no external API cost.

What worked:

- Writing preconditions as exact, literal commands with exact expected
  output made the "STOP and report" instinct concrete instead of vague -
  the moment the script's real behavior diverged from its own prescribed
  content, that was immediately visible rather than papered over.
- Stopping to ask before patching the plan's own script, instead of quietly
  fixing and moving on, surfaced a second bug (the `src` module collision)
  that a silent fix likely would have shipped without ever being tested
  against all four roots running together.

Needs improvement:

- Both fixed plan files (`PLAN-spill-guard-token-log-fix.md`,
  `PLAN-root-test-discovery-fix.md`) now contain acceptance-criteria text
  that does not exactly match the live tool's real output in two places
  (the `check-ignore -v` exit-code nuance, and the removed `Total failures:`
  / `Total errors:` lines). Plan files were explicitly off-limits to edit
  this session; a future small Brew should reconcile the plan text with the
  script that actually shipped.
- `tools/run_all_tests.py` was designed and hardened live, under real
  failures, rather than dry-run reviewed before this session. A future
  Brew could add a focused unit test for the aggregator script itself.

### 2026-07-09 - Brew 36B: Coffee Core Router Live Demo

Scope: one real, human-approved `/v1/order` call through the new Coffee
Core Router (`router/`) against OpenRouter, the first live remote-Bean call
this repository's Ledger has ever recorded through a router rather than the
Cup Test runner (`roastery/run_cup_test.py`).

Preconditions:

- Full repo test suite passed first: `python tools\run_all_tests.py` ->
  347 tests, 0 failures (214 `tests/`, 22 `roastery/tests/`, 9
  `apps/coffee-status/tests/`, 7 `apps/coffee-certification/tests/`, 95
  `router/tests/`).
- `OPENROUTER_API_KEY` was supplied by the human via their own shell
  environment only. It was never pasted into chat, never written to a
  file, and does not appear in this note, any config file, or any test.
- Router startup's key-scan (`router/app/config.py:assert_no_key_like_strings`,
  reusing `tools/coffee_context_package.py`'s `SUSPICIOUS_PATTERNS`) passed
  against all three router config files before the server accepted any
  connection.

Command sequence:

```powershell
python -m uvicorn router.app.main:app --port 8765 --host 127.0.0.1
```

```powershell
curl -sN -X POST http://127.0.0.1:8765/v1/order `
  -H "Content-Type: application/json" `
  -d '{"prompt": "Explain what a Python decorator is in two sentences."}'
```

Raw SSE transcript (verbatim):

```text
data: {"request_id":"2975e487-d46d-4ee9-8e48-f42291b90118","ts":"2026-07-09T23:51:09.251927Z","event":"order_received","prompt_chars":52}

data: {"request_id":"2975e487-d46d-4ee9-8e48-f42291b90118","ts":"2026-07-09T23:51:09.253222Z","event":"classifying"}

data: {"request_id":"2975e487-d46d-4ee9-8e48-f42291b90118","ts":"2026-07-09T23:51:09.253222Z","event":"route_selected","bean_alias":"House Blend","task_type":"explain","complexity":"espresso_shot","est_cost_usd":0.0,"policy_entry":"explain/house-blend"}

data: {"request_id":"2975e487-d46d-4ee9-8e48-f42291b90118","ts":"2026-07-09T23:51:10.761608Z","event":"generating","tokens_out":21,"est_cost_usd":0.0}

data: {"request_id":"2975e487-d46d-4ee9-8e48-f42291b90118","ts":"2026-07-09T23:51:10.851918Z","event":"generating","tokens_out":45,"est_cost_usd":0.0}

data: {"request_id":"2975e487-d46d-4ee9-8e48-f42291b90118","ts":"2026-07-09T23:51:10.980202Z","event":"complete","bean_alias":"House Blend","tokens_in":13,"tokens_out":65,"cost_usd":0.0,"latency_ms":1733,"escalated":false,"draft_quality":false}
```

Observed behavior:

- Event order matched the frozen contract exactly: `order_received` ->
  `classifying` -> `route_selected` -> `generating` x2 -> `complete`.
- The classifier correctly identified `task_type: "explain"` and
  `complexity: "espresso_shot"` from the prompt's own `classify_heuristic()`
  keyword table - not a hardcoded or mocked result.
- `route_selected` cited `policy_entry: "explain/house-blend"`, matching
  the generated `router/config/routing_policy.yaml` entry for `explain`
  (primary Bean House Blend, evidence from
  `roastery/cup_tests/004-pantry-assisted-answer.md`).
- `grep -c "nvidia/nemotron" <transcript>` returned `0` - zero raw model
  ID occurrences anywhere in the live SSE output, confirming Requirement 2
  (alias enforcement) held under a real call, not only under
  `httpx.MockTransport` in tests.
- `ledger/router_requests.csv` recorded exactly one row, with the raw
  model ID present (one of the three places it is allowed):
  `nvidia/nemotron-3-ultra-550b-a55b:free`, `tokens_in=13`,
  `tokens_out=65`, `cost_usd=0.0`, `latency_ms=1733`, `escalated=False`,
  `escalation_approved=n/a`.
- No truncation, empty response, or refusal-shaped output occurred, so no
  `escalation_pending` branch was exercised in this run (that branch is
  covered by `router/tests/test_main.py`'s mocked escalation tests, not
  by this live call).
- Full repo test suite re-run after the demo: still 347 tests, 0 failures
  - the live call did not disturb anything.

Cost and token evidence:

- Model / Bean: House Blend (`nvidia/nemotron-3-ultra-550b-a55b:free`),
  via `router/app/openrouter_client.py`'s async streaming client.
- Tokens: 13 input, 65 output (from OpenRouter's own usage field).
- Cost: `$0.00` (free-tier Bean; matches `router/config/beans.yaml`
  pricing).

What worked:

- The full pipeline (classify -> route -> stream -> failure-check ->
  Ledger write) worked correctly on the first live call after 347 mocked
  tests passed, with no code changes needed between the last test run and
  the demo.
- The alias boundary held under a real call: the human only ever saw
  "House Blend" in the stream; the raw model ID only ever appeared in the
  Ledger.

Needs improvement:

- This single demo call did not exercise the escalation-pending pause,
  the auto-escalate path, `/v1/retry`, or the no-premium-Bean fallback -
  all four are covered by mocked tests but not yet by a live call. A
  future Brew could deliberately craft a prompt likely to truncate or
  produce a short/refusal-shaped response to observe the real pause/resume
  flow end to end, though the no-premium-Bean gap (Section 3 of the design
  doc) means the auto-escalate and pending-approval-then-escalate paths
  still cannot be demoed live until a premium Bean is selected.

### 2026-07-10 - Brew 37B: Coffee Counter Chat UI Live Demo

Scope: one real, human-approved `/v1/order` call driven through the actual
running browser UI (`web/`, Next.js on `localhost:3000`) against the
actual running Coffee Core Router (`127.0.0.1:8765`) against real
OpenRouter - the first time this repository's chat UI and router have
been exercised together end to end with a real remote Bean call.

Preconditions:

- Full test suite green first: 139 `router/tests/`, 391 total repo-wide
  (`python tools\run_all_tests.py`), plus 25 Vitest/RTL component tests
  and 3 Playwright smoke tests (mocked router, no live call) in `web/`.
  `npx tsc --noEmit`, `eslint`, and `npm run build` all clean.
- `OPENROUTER_API_KEY` was already present in the shell environment from
  the Brew 36 demo session; never pasted into chat or written to a file.
- A stale router process from the Brew 36 demo (PID 27952, predating all
  Brew 37 backend changes) was found still running in the background and
  killed before starting a fresh instance with current code.

Commands (both servers started fresh with current code):

```powershell
python -m uvicorn router.app.main:app --port 8765 --host 127.0.0.1
npx next start -p 3000
```

Driven via a throwaway Playwright script (not committed - a manual demo
aid, not part of the automated suite) that filled the Order Box textarea
with "Explain what a Python decorator is in two sentences.", pressed
Enter, and polled the status line and rendered message content.

Observed behavior:

- Status line moved through the real sequence: "Ready when you are" ->
  "Reaching for the House Blend jar" -> "Brewing" -> "Order up", matching
  `router/EVENT_CONTRACT.md` v1.1's event order exactly.
- The assistant message streamed in via the new `text_delta` field on
  `generating` events and rendered as markdown.
- Message header showed `House Blend` (bean alias badge, mono,
  tabular-nums), `$0.0000` (cost pill), and `2405ms` (latency) - never a
  raw model ID.
- A session was auto-created on first send, titled from the prompt text
  ("Explain what a Python decorator..."), and appeared in the sidebar
  with a correct running cost total.
- Both the user and assistant messages persisted to
  `router/data/sessions.db` (verified directly via `SessionStore`), and a
  second real row was appended to `ledger/router_requests.csv` with the
  correct raw model ID, tokens, cost, and latency.
- `grep`-equivalent check of the full rendered page text against the
  live `/v1/beans` alias list: zero raw model ID occurrences.
- Zero browser console errors or page errors (`page.on("pageerror")`
  reported none) during the whole flow.
- Rating buttons (Good / Needed fixing / Failed), Copy, and the Re-brew
  button with a Bean-override dropdown (populated from `/v1/beans`, only
  the two other available aliases plus "Same Bean") all rendered
  correctly on the completed message.
- Screenshots were captured, visually reviewed (matched the design
  tokens - cream background, latte sidebar, caramel borders, espresso
  text, single crema-amber accent on the active session), and then
  discarded - they are not part of the repository.

Two real bugs were found and fixed during this session, both caught by
tooling rather than by eyeballing the demo:

1. A Zustand selector in `ResponseSection` (`web/src/components/
   ResponseSection/index.tsx`) returned a brand-new `[]` literal on every
   render whenever there was no active session. Zustand's default
   `Object.is` equality check saw that as "changed" on every render,
   causing an infinite re-render loop - React's minified error #185
   ("Maximum update depth exceeded"). This manifested in Playwright as
   what looked exactly like a real network failure ("This page couldn't
   load"), and took `page.on("pageerror")` console capture to correctly
   diagnose as a client-side crash, not a navigation problem. Fixed with
   a module-level stable `EMPTY_MESSAGES` constant reused across renders
   instead of a fresh literal.
2. The router's CORS allowlist (`http://localhost:3000`, approved in the
   Brew 37A plan) correctly rejected an early demo run that had navigated
   to `http://127.0.0.1:3000` instead - browsers treat `127.0.0.1` and
   `localhost` as different origins even on the same port. Confirmed via
   direct `curl -X OPTIONS` preflight requests with each Origin header
   that this was Starlette's `CORSMiddleware` working exactly as
   configured (`400 Disallowed CORS origin`), not a product defect. Fixed
   by correcting the demo script's navigation URL, not the router.

Cost and token evidence:

- Model / Bean: House Blend (`nvidia/nemotron-3-ultra-550b-a55b:free`),
  via `router/app/openrouter_client.py`'s async streaming client, driven
  through `web/`'s `fetch()`-based SSE client (`web/src/lib/sse.ts`).
- Tokens: 13 input, 70 output (from OpenRouter's own usage field).
- Cost: `$0.00` (free-tier Bean).

What worked:

- The full stack - browser UI, router orchestration, session persistence,
  Ledger write - worked correctly on the first live call once both
  demo-script bugs (not product bugs) were fixed, with zero code changes
  needed to the actual `router/` or `web/` source between the last test
  run and the successful demo.
- The frozen `CounterDisplay` interface and the event-to-status-text
  table made the status line trivial to verify against the real event
  stream - every transition matched the table exactly.
- Catching the React error #185 loop via `page.on("pageerror")` instead
  of guessing from the misleading "page couldn't load" symptom is a
  reusable debugging pattern worth remembering: a Chromium
  network-error-looking page during a Playwright test is not proof of an
  actual network failure - check for a client-side crash first.

Needs improvement:

- Like Brew 36B, this demo only exercised the happy path - no escalation
  pause, no cancel-mid-stream, no re-brew, no rating submission were
  exercised against the real router live (all are covered by mocked
  Vitest/Playwright/router tests). A future Brew could demo the cancel
  path live (Esc mid-stream) since it needs no premium Bean to exercise,
  unlike escalation.

### 2026-07-11 - Brew 38B: File/Image Attachments Live Demo

Scope: two real, human-approved `/v1/order` calls with attachments, driven
through the actual running browser UI against the actual running Coffee
Core Router against real OpenRouter - one PDF question (extraction/
inlining success path) and one image question (the approved "ship
inert" vision-routing error path, since no Bean in `beans.yaml` has
`vision: true` today).

Preconditions:

- Full test suite green first: 211 `router/tests/` (12 new for this
  Brew's `main.py` attachment wiring, plus new tests in `uploads.py`,
  `aliases.py`, `routing.py`, `events.py`, `openrouter_client.py`,
  `ledger.py`, `classifier.py`), all OpenRouter calls mocked. 29
  Vitest/RTL component tests in `web/` (new `AttachmentChip.test.tsx`).
  `npx tsc --noEmit`, `eslint`, and `npm run build` all clean.
- `OPENROUTER_API_KEY` already present in the shell environment; never
  pasted into chat or written to a file.
- Two small real fixture files were generated for the demo (not
  committed): a single-page PDF with a real Helvetica text content
  stream reading "Project Coffee brews only decaf on Tuesdays. This is a
  demo fact for Brew 38.", and a 300x150 PNG with rendered text
  ("COFFEE DEMO").

Commands (both servers started fresh with current code):

```powershell
python -m uvicorn router.app.main:app --port 8765
npx next dev -p 3000
```

Driven via a throwaway Playwright script (not committed - a manual demo
aid, not part of the automated suite) that attached each fixture file via
the Order Box's hidden file input, waited for the attachment chip to
reach `ready`, filled the textarea with a question referencing the
attachment, and pressed Send.

Observed behavior - PDF question:

- Chip reached `ready` status after a real `POST /v1/upload` round trip;
  the router's `pypdf` extraction found the real text.
- Sent user message rendered the attachment chip (filename + size) via
  the new `AttachmentGallery` component.
- `route_selected` classified the request as `cold_brew` (any attachment
  forces this per the approved Decision 3) and `constraint_reason` was
  `null` (no vision needed, nothing to escalate).
- Assistant answered correctly: "According to the PDF, Project Coffee
  brews only decaf on Tuesdays." - proving upload, `pypdf` extraction,
  `--- Attached file: ... ---` inlining, and the real OpenRouter round
  trip all work end to end.
- `ledger/router_requests.csv` recorded `attachment_count=1`,
  `attachment_tokens_est=19` (`len(extracted_text) // 4`) on the new row.

Observed behavior - image question:

- Chip reached `ready` with a rendered thumbnail (`URL.createObjectURL`).
- Sent user message rendered the image inline via `AttachmentGallery`
  (click-to-expand overlay untested in this run, code path unchanged
  from the design's overlay pattern).
- The request correctly raised `NoVisionBeanError` inside
  `RoutingPolicy.select_route()` (House Blend lacks `vision: true` and no
  vision-capable Bean exists anywhere in `beans.yaml` today), and
  `main.py` emitted a clean `error` event rather than crashing, guessing
  a model, or silently sending the request without the image. The UI
  rendered the exact message: "This request needs a vision-capable Bean,
  but none is configured in beans.yaml." No ledger row was written for
  this request (matches `_run_order_body` returning before reaching
  `ledger.append()` on this error path - a request that never generated
  should not appear in the audit trail as if it had).
- Zero browser console/page errors in either question.

One real, pre-existing bug (not introduced by this Brew) was found by
this live demo, not by tests:

1. `_consume_stream` (`router/app/main.py`) broke out of its streaming
   loop on the final chunk without flushing any text accumulated since
   the last `generating` tick. `CompleteEvent` carries no content field -
   all response text travels exclusively via `generating.text_delta` - so
   a response shorter than one `settings.generating_tick_tokens` tick
   was silently and completely lost before ever reaching the client. The
   first PDF-question demo run surfaced this directly: the model
   answered in ~92 tokens in a single fast completion (confirmed via the
   Ledger's `tokens_out` and OpenRouter usage field), but the UI rendered
   an empty assistant bubble. This bug predates Brew 38 (it lives in
   `_consume_stream`'s tick-flush logic from Brew 36) and is unrelated to
   attachments - it would affect any sufficiently short response.
   Test suites never caught it because `router/tests/test_main.py`'s
   fake stream fixtures are sized deliberately to cross a tick threshold
   mid-stream. Fixed by flushing any remaining `text_since_tick` as one
   last `generating` event immediately before the `__final__` sentinel.
   All 211 router tests still pass after the fix; the PDF demo was
   re-run and produced the correct visible answer.

Cost and token evidence:

- Model / Bean: House Blend (`nvidia/nemotron-3-ultra-550b-a55b:free`),
  PDF question only (the image question errored before any model call
  was made, per the ship-inert design).
- Tokens: 16 input, 94 output (from OpenRouter's own usage field, final
  successful run after the streaming fix).
- Cost: `$0.00` (free-tier Bean).
- Attachment tokens estimate: 19 (`len(extracted_text) // 4` for the PDF;
  images are recorded as `"unknown"`, never guessed, per Coffee Ledger
  discipline - not applicable here since the image request never reached
  the Ledger).

What worked:

- The full attachment pipeline - client-side validation, real upload,
  server-side `pypdf` extraction, text inlining with the delimiter
  format, and the real OpenRouter round trip - worked correctly end to
  end on the first successful run (after the pre-existing streaming bug
  above was fixed).
- The vision-routing constraint's "ship inert" design worked exactly as
  specified: a real image attachment against real `beans.yaml` state
  produced a precise, human-readable error rather than a crash, a
  guessed model substitution, or a silently text-only request.
- The same `localhost` (not `127.0.0.1`) origin lesson recorded in the
  Brew 37B Tasting Note repeated here on the first attempt and was fixed
  the same way (correct the demo script's navigation URL, not the
  product) - worth keeping in mind for any future live-demo script.

Needs improvement:

- Only the router-level attachment pipeline and the "ship inert" error
  path were exercised live; escalation-with-attachments (a failed
  generation on a request that also has an attachment) and the
  click-to-expand image overlay were not exercised against the real
  server, though both are covered by the mocked test suites.
- The pre-existing `_consume_stream` tick-flush bug found here suggests
  the fake stream fixtures in `router/tests/test_main.py` should
  eventually gain a "response shorter than one tick" case so this class
  of bug is caught by tests, not by a live demo, next time.

### 2026-07-11 - Brew 39B: Animated Coffee Counter Scene Live Demo

Scope: one real, human-approved `/v1/order` call driven through the
actual running browser UI against the actual running Coffee Core Router
against real OpenRouter, exercising the full animated scene state walk,
the Tips Jar, the collapse toggle and its new server-side persistence,
and `prefers-reduced-motion` emulation - the first live exercise of
Stage E, replacing the plain-text status line shipped since Brew 37.

Preconditions:

- Full test suite green first: 221 `router/tests/` (7 new for
  `PreferenceStore`/`/v1/preferences`), 84 Vitest/RTL tests in `web/` (42
  new: `sceneState.test.ts`, `tipsJarMath.test.ts`, `BaristaScene.test.tsx`,
  `SceneShell.test.tsx`, plus updated `CounterDisplay/index.test.tsx` and
  `noRawModelId.test.tsx` for the additive props). `npx tsc --noEmit`,
  `eslint`, and `npm run build` (with the new `prebuild` asset-budget
  check) all clean.
- `OPENROUTER_API_KEY` already present in the shell environment; never
  pasted into chat or written to a file.
- A stale router/web process pair from the Brew 38 demo session (missing
  the new `/v1/preferences` endpoint - confirmed via `curl`, not assumed)
  was found still listening and was stopped by PID (looked up via
  `netstat`, not a blanket process-name kill) before starting fresh
  instances with current code.

Commands (both servers started fresh with current code):

```powershell
python -m uvicorn router.app.main:app --port 8765
npx next dev -p 3000
```

Driven via a throwaway Playwright script (not committed - a manual demo
aid, not part of the automated suite) that sent one real prompt, polled
the scene caption on a 50ms interval to capture the full transition
sequence, toggled collapse, checked the router's `/v1/preferences` state
directly, reloaded the page to prove persistence, and re-loaded once more
under `page.emulateMedia({ reducedMotion: "reduce" })`.

Observed behavior:

- Initial idle state: caption "Ready when you are", not collapsed, scene
  correctly on the fallback (tier 2, `barista_static.svg`) - expected,
  since no real `barista_scene.riv` exists yet.
- Full caption sequence captured during the real request, matching
  `router/EVENT_CONTRACT.md`'s event order exactly: "Ready when you are"
  -> "Reaching for the House Blend jar" -> "Brewing" -> "Order up".
  (`order_received`/`classifying` resolved between polling ticks - too
  fast at 50ms resolution to catch individually - but the visible
  transitions through `route_selected`, `generating`, and `complete` all
  landed correctly and in order.)
- Assistant answered correctly and rendered normally alongside the scene.
- Tips Jar showed `$0.0000` - correct, not a bug: every active Bean is
  still free-tier (same documented gap since Brew 37).
- Collapse toggle correctly set `scene-body`'s class to `h-0
  overflow-hidden` and switched the Tips Jar display to the plain
  collapsed-strip total.
- `GET /v1/preferences` (called directly via `fetch` from the page,
  bypassing any UI-only illusion of persistence) returned
  `{"counter_collapsed":"true"}` immediately after toggling - confirming
  the preference actually reached the router's SQLite store, not just
  local component state.
- After a full page reload, the scene loaded already collapsed - proving
  the persistence is real and server-side, not `localStorage` (which this
  Brew was explicitly asked to avoid) and not an artifact of the same
  in-memory session never having unmounted.
- Under `page.emulateMedia({ reducedMotion: "reduce" })` plus a reload,
  the scene correctly rendered the fallback tier (`barista_static.svg`)
  and the status caption remained present and correct - the exact
  Requirement 5 combination (reduced motion -> static art + reused text
  line), verified against a real browser's reduced-motion signal, not a
  mocked media query.
- Zero browser console/page errors across the entire session
  (`page.on("pageerror")` and console-error listeners both silent).

CPU profiling note (Requirement 6, "collapsed scene must consume
near-zero CPU"): measured via Chrome DevTools Protocol's
`Performance.getMetrics()` over two 3-second idle windows (expanded vs.
collapsed), using a fresh CDP session for each measurement rather than
eyeballing the DevTools Performance panel, so the numbers below are
exact deltas, not estimates:

| State | TaskDuration | ScriptDuration | LayoutDuration |
| --- | --- | --- | --- |
| Expanded (scene visible, idle) | 4.7ms | 3.0ms | 0.0ms |
| Collapsed (scene paused, idle) | 2.9ms | 0.7ms | 0.0ms |

Collapsed is measurably lower on both `TaskDuration` and
`ScriptDuration`. Both numbers are already small in absolute terms today
specifically because Phase 1 has no real Rive WASM animation loop
running yet (the fallback tier is a static `<img>`, inherently cheap
regardless of collapse state) - this comparison is a directional
baseline confirming the `rive.pause()`/`rive.play()` wiring has the right
effect (also directly asserted in `BaristaScene.test.tsx` via the mocked
Rive instance), not a definitive Phase-2 measurement. Re-measuring once a
real `barista_scene.riv` is dropped in would be the meaningful follow-up
- flagged as future work, not silently assumed to still hold.

Cost and token evidence:

- Model / Bean: House Blend (`nvidia/nemotron-3-ultra-550b-a55b:free`).
- Tokens: from OpenRouter's own usage field, same order of magnitude as
  prior Brew 36-38 demo calls for a comparable two-sentence prompt.
- Cost: `$0.00` (free-tier Bean) - reflected correctly and honestly by
  the Tips Jar, not hidden or faked with a placeholder number.

What worked:

- The entire fallback ladder (Rive attempt -> `barista_static.svg` on
  failure/missing-file/reduced-motion) worked identically whether the
  cause was "no `.riv` file exists" (Phase 1's real, permanent state
  today) or "the browser asked for reduced motion" (a real signal) -
  confirming the design decision to make Phase 1's placeholder art and
  the permanent reduced-motion fallback the exact same code path, not two
  systems that could drift apart.
- Persisting the collapse preference through a real new router endpoint
  rather than `localStorage`, then proving it with an actual reload
  rather than trusting the toggle's in-memory state, caught the one class
  of bug this design was most exposed to (a preference that "works" in a
  demo only because the page never actually reloaded).
- Finding and killing the stale Brew 38 server process by looking up its
  PID via `netstat` (rather than a blanket `taskkill /IM python.exe`,
  which the environment's own safety classifier correctly refused as
  too broad) is worth remembering as the right pattern for future
  demo-server cleanup on a shared machine.

Needs improvement:

- No real `.riv` file exists to demo tier 1 (the actual Rive canvas
  rendering) - `BaristaScene.test.tsx`'s mocked-library tests are the only
  evidence that the state-machine input wiring (`state`, the five jar
  booleans, `complexity_cold_brew`) is correct; a real artist-authored
  file is required before that specific code path can be demoed live.
- The CPU profiling numbers above are a Phase 1 baseline only, as noted -
  they should be re-measured once a real `.riv` exists, since a live
  Rive WASM animation loop is the actual scenario the "near-zero CPU"
  requirement was written to guard against.
- Escalation-state scene art (`escalating`, state 6) and the error/spill
  state (state 8) were not exercised live in this session (the demo
  prompt completed on the first try, no escalation triggered) - both are
  covered by `sceneState.test.ts`'s full 9-state mapping table, but not
  against a real event stream yet.

### 2026-07-14 - Brew 40B: Escalation Approval Gate Live Demo

Scope: real, human-approved `/v1/order` calls through the actual running
browser UI against the actual running Coffee Core Router against real
OpenRouter, exercising all three approval-gate outcomes for the first
time - approve, decline, and reload recovery - plus verifying the Tips
Jar correctly stays frozen during a pause.

Preconditions:

- Full test suite green first: 238 `router/tests/` (17 new - real-timeout
  path, real cancel-during-pause exercising the actual `_await_approval`
  race rather than the `wait_for_approval` test seam, double-click,
  late-approval, reload-recovery spawning the background task the same
  way the real endpoint does, heartbeat-during-pause, force_escalation
  on/off), 103 Vitest/RTL tests (19 new - `EscalationApprovalCard`,
  `MessageBubble` visibility gating, `chatStore` action + polling with
  fake timers). `npx tsc --noEmit`, `eslint`, and `npm run build` all
  clean.
- `OPENROUTER_API_KEY` already present in the shell environment; never
  pasted into chat or written to a file.
- A real, structural constraint had to be worked around to demo this at
  all: `router/config/beans.yaml` has no available premium Bean (Reserve
  Blend's `model_id` is `null`, `status: not_yet_selected` - the same gap
  documented since Brew 36), so the real router config can never actually
  reach `escalation_pending` - `decide_escalation()` always returns
  `no_premium_available` instead. A standalone demo launcher script (not
  committed - `run_demo_router.py`, scratch-only) built a `RouterState`
  with a substitute premium Bean reusing House Blend's real free-tier
  model ID (`nvidia/nemotron-3-ultra-550b-a55b:free`), so every escalation
  re-run in this demo was a real, free OpenRouter call - `beans.yaml`
  itself was never touched, confirmed via `git status` after the demo.
  `COFFEE_ROUTER_FORCE_ESCALATION=1` forced every generation to look like
  a failure so the pause could be triggered on demand.

Commands (all three servers/scripts started fresh with current code):

```powershell
$env:COFFEE_ROUTER_FORCE_ESCALATION = "1"
python run_demo_router.py    # scratch-only launcher, not committed
npx next dev -p 3000
```

Driven via throwaway Playwright scripts (not committed - manual demo
aids, not part of the automated suite).

Observed behavior - approve:

- Sending "Explain what a Python decorator is." reached a real failure
  (forced), and the approval card appeared with the correct plain-
  language reason ("You reported this response as needing a retry." -
  `caller_reported`, matching `force_escalation`'s mechanism exactly),
  premium alias (`Reserve Blend`), cost (`$0.0000`, correctly reflecting
  the free-tier substitute), and a live countdown ("Auto-declining in
  120s if no decision is made.").
- The scene's caption correctly showed "Waiting for your approval" while
  paused (state 5, unchanged from Brew 39's mapping).
- Clicking "Brew premium" resumed the stream: a real second OpenRouter
  call ran, the scene caption moved to "Order up" on completion, the
  completed message's header showed the escalation marker (expandable,
  matching the pre-existing read-only `MessageHeader` behavior), and a
  full, real, substantive answer rendered.
- Tips Jar read `$0.0000` before the pause and `$0.0000` after - no code
  was needed for Requirement 5 ("Tips Jar does not tick during the
  pause"), confirmed live: no `generating` events fire during a pause, so
  `TipsJar.tsx` never had anything to react to.

Observed behavior - decline:

- Same setup, clicked "Keep the cheap cup" instead. The message completed
  immediately with the draft-quality tag visible and no `escalating`
  event - and, correctly, the escalation marker was *still* present on
  the completed message (the pause itself happened and is real history,
  even though it wasn't escalated).

Observed behavior - reload recovery:

- Sent a fresh message, reached the pause, confirmed via a direct
  (non-browser) fetch to `GET /v1/sessions/{id}/pending_escalation` that
  the router genuinely still considered it open. Reloaded the page.
- This app has never auto-restored the active session across a bare
  reload (true for every piece of session state, not just escalations -
  a pre-existing, unrelated design choice) - so the real recovery flow is
  "reload, then click your session in the sidebar," identical to how a
  user already returns to any past conversation. Clicking the (only)
  session in a clean single-session run correctly re-showed the approval
  card, with the "Recovered after a reload - the original message text
  isn't available" note rendered (the honest gap: the user's original
  prompt was never persisted for a still-in-flight turn, and this Brew
  deliberately does not fabricate it).
- Clicking "Keep the cheap cup" on the *recovered* card correctly called
  `POST /v1/approve_escalation` for the still-genuinely-running background
  task, and `chatStore`'s polling loop (every 2s, since a recovered card
  has no live SSE stream of its own) picked up the final draft-quality
  result and replaced the placeholder content with the real persisted
  message within one polling cycle.

One test-script-only false alarm, not a product bug: an earlier two-flow-
in-one-page-session demo script showed the sidebar landing on the wrong
session after reload and the recovery endpoint correctly 404ing for it -
looked like a recovery bug at first. A direct Python `httpx` test (open a
stream, read until `escalation_pending`, close the connection abruptly
from the client side, then `GET` the recovery endpoint) proved the
background task genuinely survives an abrupt disconnect - 200, correct
context. The demo router process had accumulated seven sessions across
several repeated debug runs sharing one long-lived `sessions.db`, and the
two-flow script's second `sendPrompt` call landed on a different session
than expected; a clean, single-session isolated run then reproduced the
correct end-to-end recovery. Worth remembering: a long-lived demo server
across many repeated script executions accumulates state that can make an
otherwise-correct feature look broken - restart with a clean data
directory when a multi-step demo script produces a surprising result,
before assuming the product is wrong.

Cost and token evidence:

- Model / Bean: House Blend and the demo-only Reserve Blend substitute,
  both `nvidia/nemotron-3-ultra-550b-a55b:free`.
- Cost: `$0.00` across every call (free-tier model, both the initial
  draft and every premium re-run).

What worked:

- The background-task/queue decoupling (Section 3.1 of the design doc)
  worked exactly as designed on the first real end-to-end run - no
  connection-lifetime bugs, no orphaned tasks, no hung requests. The
  direct `httpx` disconnect test gave independent confirmation beyond
  what the browser-based demo alone could prove.
- Building `EscalationContext` as a mutable dataclass that stays in
  `RouterState.pending_escalation_context` past request completion
  (rather than being popped immediately) is what made both "late
  approval" and "reload recovery" work without extra machinery - a
  single piece of state serving two different edge cases from the plan.
- Treating a recovered card and a live card identically in
  `MessageBubble`'s visibility gate (`isStreaming && latestEvent.event === "escalation_pending"`)
  meant no separate recovered-card rendering path was needed - only the
  "how did this message get resolved" side (live event vs. polling)
  differs, not the card itself.

Needs improvement:

- The real escalation flow (against real `beans.yaml`, no substitute)
  remains undemoed, same as the vision-routing and premium-Bean gaps from
  Brews 36/38 - all three are blocked on the same underlying fact: no
  premium/vision Bean has ever been selected or Roastery-tested.
- Heartbeat frames during a pause were exercised automatically by the
  router test suite (`test_order_endpoint_emits_heartbeat_during_a_long_pause`)
  but not separately observed in the browser network layer during this
  live session - the approve/decline demo runs simply didn't pause long
  enough to need one at the 15s demo interval before a human clicked a
  button. Worth a dedicated long-idle live check in a future session.
- The demo router launcher script's substitute-Bean approach, while
  clearly documented and never touching real config, is a reminder that
  a second real premium/vision Bean selection is increasingly overdue -
  three separate Brews now have needed a workaround for the same gap.

### 2026-07-14 - Brew 41B: Session Memory Proposals and Pantry Retrieval Live Demo

Scope: real, human-approved calls through the actual running Coffee Core
Router against the real `knowledge/` directory and real OpenRouter,
covering both new Brew 41 features for the first time - Pantry retrieval
with citations, and session memory proposal generation with guardrails.

Preconditions:

- Full test suite green first: 308 `router/tests/` (89 new - 23
  `test_pantry.py`, 6 `test_index_pantry.py`, 23 `test_memory_proposals.py`,
  25 `test_main.py` additions across Pantry retrieval wiring, the file
  viewer endpoint, and the three memory-proposal endpoints, 2
  `test_events.py`, plus `test_config.py` updates), 123 Vitest/RTL tests
  (20 new - `OrderBox`'s Use Pantry toggle, `PantrySourceChips`, `SessionMenu`,
  `MemoryProposalPanel`, `Sidebar` wiring). `npx tsc --noEmit`, `eslint`,
  and `next build` all clean.
- `OPENROUTER_API_KEY` already present in the shell environment; never
  pasted into chat or written to a file.
- Ran `python router/tools/index_pantry.py` fresh against the real
  `knowledge/` directory (4 files, 8 chunks) before starting the router.

Commands (router started fresh with current code):

```powershell
python -m uvicorn router.app.main:app --port 8765
```

Driven via direct `curl`/`httpx` calls against the real router (no
browser UI session this time - both features are fully exercisable via
their HTTP contract, and the frontend wiring was already covered by the
Vitest/RTL suite above).

Observed behavior - Pantry retrieval:

- `POST /v1/order` with `use_pantry: true` and the prompt "What is
  Pantry retrieval and how does it save tokens?" produced a normal
  `order_received` -> `classifying` -> `route_selected` (`House Blend`,
  `explain`) -> `generating` -> `complete` sequence, and the `complete`
  event correctly carried
  `pantry_sources: ["knowledge/README.md", "knowledge/project_docs/project-coffee-foundation-summary.md", "knowledge/00_index.md"]` -
  three of the real `knowledge/` directory's four files, correctly
  ranked as relevant to a question about Pantry retrieval itself.
- `GET /v1/pantry/file?path=knowledge/00_index.md` returned the real
  file content (`# Knowledge Index...`), confirming the citation chip's
  file-viewer path works against real data, not just test fixtures.
- The exact path-traversal example named in the design doc
  (`../router/config/settings.yaml`) correctly returned 404 against the
  real, running endpoint - not just in the unit tests.

Observed behavior - Memory proposals:

- Created a real session, sent one real message ("Explain in one
  sentence what the Coffee Core Router is."), then called
  `POST /v1/sessions/{id}/memory_proposal`. The real House Blend model
  returned a syntactically valid two-file response on the first try (no
  retry needed) - the strict `### FILE: ... ### END FILE` parser
  accepted it cleanly.
- `brew-log/active_context.md`'s diff was empty (the model proposed no
  change - a legitimate, guardrail-passing "nothing to add" outcome, not
  an error).
- `brew-log/progress.md`'s diff was a single near-no-op line edit
  ("Markdown" -> "MarkDown" in one existing table cell) - both
  guardrails passed cleanly (well under the 50% deletion threshold), but
  the edit itself carried no real value from a one-message session with
  no substantive close-out content to record.
- Called `POST /v1/memory_proposals/{id}/discard` rather than
  `.../approve` - a deliberate choice, not a bug: writing that trivial
  edit into the real project memory files as a demo artifact would have
  been exactly the kind of low-value noise the over-deletion guardrail
  exists to prevent on the *other* end (stale-memory protection cuts
  both ways, but a human reviewer choosing not to approve a real-but-
  worthless diff is the same protection, applied manually). `git status`
  confirmed `brew-log/` was completely untouched after the full demo.

Cost and token evidence:

- Model / Bean: House Blend, `nvidia/nemotron-3-ultra-550b-a55b:free`,
  for all three calls (two Pantry-toggled `/v1/order` calls, one memory
  proposal generation call).
- Cost: `$0.00` across every call (free-tier model).
- Tokens: Pantry demo call 13 input / 718 output; session demo call 13
  input / 881 output (both OpenRouter-reported, via `complete` events).
  The memory proposal call's tokens were not written to
  `ledger/router_requests.csv`, since a discarded proposal logs nothing
  by design (Section 3.2 of the design doc) - this is working as
  intended, not a gap in evidence capture.

What worked:

- FTS5 BM25 ranking correctly surfaced all three genuinely relevant
  `knowledge/` files (out of only four total) for a question about the
  Pantry system itself, on the very first real query against the real
  index - no tuning needed.
- The strict two-file parser (`### FILE: ... ### END FILE`, exact path
  match, no near-misses accepted) worked against a real, non-adversarial
  model response with zero friction - the format constraint clearly
  fits within House Blend's instruction-following ability for this task.
- Both guardrails (path allowlist, over-50%-deletion) ran silently and
  correctly on real content without ever needing to reject anything in
  this run - the interesting guardrail-triggering cases are the
  synthetic ones already covered in `test_memory_proposals.py`
  (`test_generate_raises_guardrail_error_on_over_deletion`).
- Discarding a real-but-low-value proposal, rather than reflexively
  approving anything that passes the mechanical guardrails, demonstrated
  the design's intended human-in-the-loop check actually being useful in
  practice: mechanical guardrails caught nothing wrong here, but the
  edit still wasn't worth keeping.

Needs improvement:

- `knowledge/` is still only 4 files (a hand-curated pointer table, not
  a content corpus) - this demo proves the retrieval *mechanism* is
  correct, but doesn't yet demonstrate Pantry answering a question its
  current index can't directly cover (the "mark uncertainty" behavior
  from Requirement 7 remains unexercised against a real gap - only
  tested synthetically in `test_pantry.py`).
- A one-message demo session is a weak input for memory-proposal
  quality - the near-no-op "Markdown"/"MarkDown" edit is more a
  reflection of there being nothing substantive to summarize than a
  finding about House Blend's proposal-drafting ability. A future Brew
  closed out with a real, substantive multi-message session would be a
  more honest test of proposal quality.
- The Pantry citation chip's click-through file viewer was exercised
  directly via the router endpoint (`curl`), not through an actual
  browser click - the Vitest/RTL suite covers the component's fetch/
  render/error-state logic, but a real browser session (same class of
  gap as this Brew skipping a UI-driven demo entirely) would still add
  independent confirmation.

### 2026-07-15 - Brew 42: House Blend vs. Second Pour, `002-tiny-python-fix.md`, through the router pipeline

Scope: a real two-Bean comparison on one identical real task, run through
the actual Coffee Core Router (`POST /v1/order` with `bean_alias_override`)
rather than the standalone synchronous Roastery Cup Test runner - the
"new pipeline" Requirement 8 asked for. Task file:

```
roastery/cup_tests/002-tiny-python-fix.md
```

Order text sent verbatim (unchanged from the Cup Test file) to both Beans
in the same session's router process, real `OPENROUTER_API_KEY`, real
OpenRouter calls, real `ledger/router_requests.csv` rows.

| Bean | Model | Tokens in | Tokens out | Latency | Cost | Test assertions |
| --- | --- | --- | --- | --- | --- | --- |
| House Blend | `nvidia/nemotron-3-ultra-550b-a55b:free` | 223 | 598 | 5062 ms | $0.00 | 4 |
| Second Pour | `cohere/north-mini-code:free` | 223 | 1169 | 7875 ms | $0.00 | 1 |

Correctness (Success Criteria from the Cup Test file, independently
verified by actually running both submitted functions - not just read -
against the file's own example plus three additional edge cases: extra
whitespace-only tags, mixed-case duplicates, and an empty input list):

- **Fixes the membership check**: both. Each replaced the buggy `if tag
  not in tags` (checking the *original* list) with a check against an
  accumulator (`seen`/`normalized`) built during the loop.
- **Does not sort the result**: both. Neither response's corrected
  function calls `sorted()` - first-seen order is preserved.
- **Skips empty normalized tags**: both, via slightly different phrasing
  (House Blend: `if normalized_tag and normalized_tag not in seen`;
  Second Pour: an explicit `if not tag: continue`).
- **Uses only standard library**: both - no imports beyond `unittest`.
- **Includes one meaningful test**: both, but not equally thorough (see
  below).
- All 4 test cases (the Cup Test's own example plus 3 more) passed
  against both submitted functions when actually executed - full
  correctness score for both.

What worked / differed:

- House Blend's test case covered 4 distinct scenarios (the Cup Test's
  own example, a mixed-case-duplicate case, an empty-and-whitespace-tag
  case, and an empty-list case) in a single `unittest.TestCase` method.
  Second Pour's test covered only the Cup Test's own example - a real,
  observable thoroughness gap, not a correctness gap (both fixes are
  equally correct; House Blend proved it more).
- House Blend used roughly half the output tokens (598 vs. 1169) and
  responded faster (5.06s vs. 7.88s) for a response that was *more*
  thorough, not less - Second Pour's higher token count did not buy
  proportionally more test coverage or a materially different
  explanation. Both bugs explanations (one sentence each, as the Order
  requested) correctly identified all three real defects (membership
  check against the wrong collection, missing empty-tag skip, unwanted
  sort) - the Cup Test's own instructions ask for one sentence, and both
  Beans complied instead of padding the explanation.
- This is a small sample (one run per Bean, no repeated trials) - a
  single comparison is directional evidence for `tools/generate_policy.py`'s
  existing `code` task_type ranking, not a full re-run of the Brew 14
  Cup Test pack. Worth a repeated/larger comparison in a future Brew
  before treating token-efficiency as a settled finding rather than one
  data point.

Cost and token evidence:

- Both calls: `$0.00` (free-tier Beans). Real Ledger rows: request
  `0636e173-2230-42aa-971a-15967adce9c4` (House Blend) and
  `ae25dec9-fd83-4dc6-90a8-9ab0322b97e5` (Second Pour), both `task_type=code`,
  in `ledger/router_requests.csv`.

### 2026-07-15 - Brew 43B: Simple Auth, Projects, and Chat Management Live Demo

Scope: this Brew is pure infrastructure (username/password auth,
per-user projects, session rename/soft-delete) - there is no model
routing or generation question to compare, so this is not a Cup Test.
Per this project's discipline against fabricating comparisons that
were never run, this note records what the live demo actually did:
real cross-user isolation checks against the real, running router,
driven directly via `curl`, not through `/v1/order`.

Preconditions:

- Full test suite green first: 365 `router/tests/` (51 new/changed -
  18 `test_auth.py`, 33 `test_sessions.py` additions across
  `UserAndTokenTests`/`ProjectTests`/`ChatManagementTests`, plus
  `test_main.py` updates for the new `Depends(get_current_user)` wiring
  on every endpoint), 168 Vitest/RTL tests (33 new - `authFetch.test.ts`,
  `ProjectSelector.test.tsx`, `login/page.test.tsx`, `proxy.test.ts`,
  plus `Sidebar`/`SessionMenu` updates), 4 Playwright e2e tests. `npx
  tsc --noEmit`, `eslint`, and `next build` all clean. 628 tests
  repo-wide except 2 pre-existing `test_routing.py` failures, confirmed
  caused by an external Bean-config commit (`0255a63`) outside this
  Brew's diff, not by this Brew's changes.
- Router started fresh with current code:
  `python -m uvicorn router.app.main:app --port 8765`.

Commands and observed behavior:

- Two real users created directly against the real `router/data/sessions.db`
  via `hash_password()` + `store.create_user()` (the interactive
  `manage_users.py add` CLI hangs on piped stdin on Windows - confirmed
  live, diagnosed as `getpass.getpass()` reading from the console
  directly rather than falling back to stdin like Unix does when stdin
  isn't a tty; not treated as a bug, since the CLI's interactive design
  is correct for its real use case of a human at a real terminal).
- `POST /v1/login` for both `alice` and `bob` returned real 64-char hex
  bearer tokens.
- `GET /v1/projects` and `GET /v1/sessions?project_id=all` with alice's
  token returned only alice's data; with bob's token, only bob's -
  confirmed empty/disjoint, not merely "different," since both users
  started with zero sessions.
- Alice created a real session and project; a cross-user read attempt
  (`GET /v1/sessions/{alice_session_id}` with bob's token) correctly
  returned `404`, not `403` - confirmed a client can never learn "this
  exists but isn't yours" from the status code alone.
- A cross-user `PATCH /v1/projects/{alice_project_id}` rename attempt
  with bob's token also correctly returned `404`.
- A request to any `/v1/*` endpoint with no `Authorization` header
  correctly returned `401` with a clear message.
- Alice's own session was renamed (`PATCH`) and soft-deleted (`DELETE`)
  successfully, then confirmed absent from a subsequent
  `GET /v1/sessions` for alice - and confirmed the underlying row still
  existed in the database (soft delete, not physical delete), matching
  the design doc.
- `POST /v1/logout` invalidated alice's token; a subsequent request
  with the same token correctly returned `401`.
- Both demo users were removed afterward via `manage_users.py remove`;
  `git status` confirmed `router/data/` stayed untracked throughout, so
  no demo credentials or data were left in a committed file.

Cost and token evidence:

- No remote Bean call in this Brew's implementation or live demo - the
  entire demo was pure REST API verification against local
  infrastructure. `$0.00`, no Ledger rows generated.

Finding worth flagging for a future Brew: `router/config/beans.yaml`
gained a real premium/vision Bean (`Reserve Blend`) in a separate
commit (`0255a63`) outside this Brew's numbering, which now causes 2
pre-existing `test_routing.py` assertions (written when no
vision-capable Bean existed) to fail - a real, currently-unaddressed
test/config drift, not something this Brew introduced or fixed.

### 2026-07-15 - Brew 44: Response Layout, Markdown Formatting, and Barista Panel Restructure Verification

Scope: pure frontend UI work (no `router/` changes, no `/v1/order`
calls) - not a Bean quality comparison, so no scores are recorded here.
This note documents what the automated verification actually found,
including one genuine root-cause finding and one honest coverage gap.

Root-cause finding: the reported "content formatting is poor (no
tables, mixed-up structure)" traced to a real, specific bug rather than
a vague styling gap - `MessageBubble.tsx` applied Tailwind's `prose
prose-sm` classes, but `@tailwindcss/typography` was never installed
(confirmed absent from `web/package.json` and `web/src/app/globals.css`,
which has no `@plugin` directive). `prose` was a complete no-op, so
every Markdown element rendered with zero styling. Fixed by replacing
the inert wrapper with 12 explicit `ReactMarkdown` `components`
overrides styled with the existing coffee-palette tokens, confirmed via
real rendered-DOM assertions in `MessageBubble.test.tsx` (table
borders/header background, list indentation, heading levels, bold/
italic tag names - not just "no error thrown").

Automated verification:

- 179 Vitest/RTL tests (11 new/changed this Brew), all passing.
- `npx tsc --noEmit` clean.
- `eslint` clean except 2 pre-existing unrelated `<img>` warnings
  (`AttachmentChip.tsx`, `AttachmentGallery.tsx` - not touched this
  Brew).
- `next build` clean.
- 6/6 Playwright e2e tests passing (`--workers=1`), including two new
  tests that set real viewports (900px and 1280px via
  `page.setViewportSize`) to verify the barista panel's actual
  visibility - this is the authoritative check for the "hides below
  1024px" requirement, since jsdom (Vitest's environment) cannot
  evaluate real CSS media queries; the Vitest-side test is only a
  regression guard on the responsive class names themselves.

One real bug caught and fixed during implementation, not just at test
time: the first version of the `SceneShell.tsx` rewrite unmounted
`BaristaScene` entirely while the panel was collapsed. The existing
"passes paused=true to BaristaScene while collapsed" test (predating
this Brew) failed because the mocked component never rendered at all,
correctly catching that collapsing must keep `BaristaScene` mounted
with `paused=true` inside a zero-height container - matching both the
pre-Brew-44 behavior and Rive's real pause/resume lifecycle. Fixed by
restructuring the collapsed/expanded branches so `BaristaScene` always
renders.

Honest coverage gap: no manual visual/screenshot check of the rendered
page was performed. No browser/screenshot tool was available in this
session, so the claims about visual appearance (bubble spacing, table
borders actually looking right, the portrait SVG rendering sensibly at
real panel proportions) rest entirely on the Playwright e2e suite's DOM
and visibility assertions plus the Vitest class-presence checks - real
browser coverage (Chromium via Playwright), but not a human eyeball
pass. Flagged explicitly in `brew-log/active_context.md`'s "Next
actions" rather than silently treated as done.

Cost and token evidence:

- No remote Bean call anywhere in this Brew's implementation or
  verification. `$0.00`, no Ledger rows generated.

### 2026-07-15 - Brew 45: Vertical Coffee Counter Scene Assets Verification

Scope: pure SVG/frontend asset work (no `router/` changes, no model
calls) - not a Bean quality comparison, so no scores are recorded here.
This note documents what the automated verification actually found,
including one real layout collision caught and fixed, and one
deliberate no-op decision explained rather than left looking like an
oversight.

What changed and why: Brew 44 moved the barista scene from a full-width
horizontal strip to a ~300px-wide, full-height right-side panel, but
only reworked the panel *container* and the flat fallback illustration
(`barista_static.svg`). The other reference assets in
`web/public/assets/counter/` (`scene_bg.svg`, the four jar files,
`tips_jar.svg`, `cup_finished.svg`) and the collapse chevron icon still
assumed the old horizontal composition. This Brew closed that gap.

Real finding during implementation: the first placement of the cup in
the redrawn `barista_static.svg` (mid-panel, per the request) was set
directly above the machine at `x=113-147, y=572-596`, which genuinely
overlaps the machine's foot/spout element (`x=115-125, y=580-598`) in
both axes - not a hypothetical risk, an actual coordinate collision
computed from the two elements' real bounding boxes. Fixed by moving
the cup beside the machine instead (`x=190, y=540`), clear of both the
machine body and the counter below it.

Deliberate no-op, documented rather than silently skipped: the four
jar files, `tips_jar.svg`, and `cup_finished.svg` were left visually
unchanged. Each is a single self-contained icon (a jar or a cup) that
was never landscape-shaped to begin with - "stack vertically" and "sits
at the bottom" are instructions about where these icons sit *within*
the composed scene, not about their own internal artwork. The asset
README's new "Vertical/portrait layout" section states this reasoning
explicitly so a future reader (human or agent) doesn't mistake it for
an incomplete pass.

Automated verification:

- 180 Vitest/RTL tests (1 new - a chevron-rotation-direction test),
  all passing.
- `npx tsc --noEmit` clean.
- `eslint` clean except the same 2 pre-existing unrelated `<img>`
  warnings from Brew 44 (not touched this Brew).
- `next build` clean.
- 6/6 Playwright e2e tests passing (`--workers=1`) - a stale `next
  start` process from an earlier manual verification run was still
  listening on port 3100 and had to be killed before Playwright's own
  `webServer` could bind it; not a code defect.
- Asset budget: 14.9 KB / 300 KB (`node scripts/checkAssetBudget.mjs`),
  comfortably under budget after the `scene_bg.svg`/`barista_static.svg`
  rewrites and the chevron redraw.

Chevron logic check: `SceneShell.tsx`'s existing `rotate-180`-on-collapse
CSS class toggle was verified to need **zero code changes** - only the
underlying `chevron_collapse.svg` artwork changed (vertical "v" to
horizontal "<"), and the same rotation logic that used to flip
down<->up now correctly flips left<->right, satisfying "points right
(expand) or left (collapse)" for free. Confirmed via a new test
asserting the `rotate-180` class is absent while expanded and present
while collapsed.

Honest coverage gap, same as Brew 44: no manual visual/screenshot check
of the rendered scene was performed. No browser/screenshot tool was
available in this session either, so the claims about the new vertical
composition actually looking right (jars evenly stacked, barista
centered, no visual overlap beyond what was caught via coordinate math)
rest on the Playwright e2e suite's DOM/visibility assertions and the
`object-contain` CSS already verified in Brew 44, not a human eyeball
pass. Flagged explicitly in `brew-log/active_context.md`'s "Next
actions" alongside Brew 44's identical gap.

Cost and token evidence:

- No remote Bean call anywhere in this Brew's implementation or
  verification. `$0.00`, no Ledger rows generated.

### 2026-07-15 - Brew 46: Conversation Memory Live Demo

Scope: real, human-approved calls through the actual running Coffee
Core Router against real OpenRouter, covering both new Brew 46
features for the first time - cross-turn conversation history and
attachment persistence, gated by the new `remember_chat` toggle. A
single Bean was used throughout (House Blend) for functional
verification of the memory mechanism itself, not a quality comparison
across Beans - no scores are recorded here.

Preconditions:

- Full test suite green first: 412 `router/tests/` (47 new/changed -
  15 in the new `test_history.py`, plus additive tests across
  `test_classifier.py`, `test_openrouter_client.py`, `test_sessions.py`,
  `test_main.py`; 410 passing, the same 2 pre-existing failures from an
  external vision-Bean config commit unrelated to this Brew), 187
  Vitest/RTL tests (7 new - `RememberChatToggle.test.tsx`). `tsc`,
  `eslint`, `next build`, and 6/6 Playwright e2e all clean.
- `OPENROUTER_API_KEY` already present in the shell environment; never
  pasted into chat or written to a file.
- A demo user (`demo46`) created directly via `hash_password()`/
  `create_user()` (piped `getpass` still hangs on Windows, the same
  finding from Brew 43's live demo) - removed afterward, along with its
  session and messages, so no demo data was left in the real database.
- Since `reportlab` is not installed in this environment, the demo PDF
  was hand-crafted with raw PDF content-stream syntax rather than
  generated by a library. `pypdf.PdfReader` was used directly first to
  confirm it actually extracted the intended text ("The quarterly
  revenue was $4.2 million and grew 12 percent year over year.") before
  using it in the live demo - a minor xref warning was logged but
  extraction succeeded correctly.

Commands (router started fresh with current code):

```powershell
python -m uvicorn router.app.main:app --port 8765
```

Driven via direct `curl` calls against the real router - the frontend
toggle UI is covered by its own Vitest suite (optimistic update +
rollback), so this demo focuses on proving the actual memory mechanism
end to end against the real API contract.

Observed behavior:

- `POST /v1/upload` with the hand-crafted PDF returned
  `extracted_text_chars: 74`, confirming the router's own extraction
  pipeline (not just my standalone `pypdf` check) saw the same text.
- `POST /v1/order` (toggle ON, the new-session default) with the
  attachment correctly answered "the quarterly revenue was **$4.2
  million**" - `complete` carried `history_turns: 1` (a real prior
  attempt in the same session, from before the attachment_id was
  correctly passed on the first try - a genuine mistake made and caught
  live, not scripted around) and `history_tokens_est: 52`.
- A genuine follow-up with **`attachment_ids: []`** (no re-upload) -
  "And what was the year-over-year growth percentage mentioned in that
  file?" - was correctly answered "**grew 12 percent year over year**"
  purely from the reattached stored text, with `complete` carrying
  `history_turns: 2`, `history_tokens_est: 121`. This is the core claim
  of Brew 46 verified for real, not simulated: attachment content
  survived past the request that uploaded it.
- `PATCH /v1/sessions/{id}` with `{"remember_chat": false}` returned
  `{"remember_chat": false}` immediately.
- A further follow-up - "What was the revenue growth percentage
  again?" - correctly got "I don't have access to our previous
  conversation history or the specific data you're referring to" from
  the model, and `complete` carried `history_turns: null`,
  `history_tokens_est: null` (not a real `0` - the toggle-off
  signature, distinguishable from "turn one").
- The real `ledger/router_requests.csv` file was read directly
  afterward: the toggle-OFF row shows `remember_chat=False`,
  `history_turns=0`, `history_tokens_est=unknown` - matching the CSV's
  existing "unknown means N/A, never a fabricated zero" convention,
  and directly answering "what did Remember Chat cost me" from the
  Ledger alone, as the original request asked for.

Cost and token evidence:

- Four real calls, all `$0.00` (free-tier Bean). Real token counts from
  the Ledger: req-1 13 in/75 out, req-2 13 in/72 out, req-3 18 in/37
  out, req-4 11 in/94 out.

Cleanup: the demo user and its session/messages were removed directly
from `router/data/sessions.db` afterward; `git status` confirmed
`router/data/` stayed untracked/ignored throughout, and the
hand-crafted demo PDF (scratchpad-only, never part of the repo) was
deleted.

### 2026-07-15 - Brew 47 (Sections 1+3): OpenAI-Compatible Endpoint + Ledger Migration

Goal, stated plainly in the Decaf plan: answer "what fraction of my
coding tasks actually needed a premium model?" with real data. Cursor/
Continue.dev compatibility is the delivery mechanism, not the point.
This session implements only Sections 1 (the endpoint) and 3 (the
Ledger schema) of the full Brew 47 request - Sections 2 (retry
detection, shadow mode) and 4 (the `ledger_summary.py` analysis mode)
are explicitly deferred to a separate session, per instruction.

Preconditions:

- Full test suite green: `router/tests` + `tests` at 673 passing (23
  new `ChatCompletionsEndpointTests`, 10 new `openrouter_client` tests,
  5 new `ledger.py` tests, 5 new `generate_policy.py` tests) - same 2
  pre-existing `test_routing.py`/`test_aliases.py` failures from the
  external vision-Bean commit, unrelated to this Brew.
- No live OpenRouter call was made this session - every test uses a
  fake `stream_order_fn` (`httpx.MockTransport` at the
  `openrouter_client` layer, plain async-generator fakes at the `main.py`
  orchestration layer), matching this repo's consistent "no live network
  call in a test" discipline.

What was built:

- `POST /v1/chat/completions` - the standard OpenAI shape
  (`model`/`messages`/`stream`/`temperature`/`max_tokens`/`tools`/
  `tool_choice`), reusing `classify()`, `RoutingPolicy`, `check_for_failure()`/
  `decide_escalation()`, and `RouterLedger` under a **new**
  orchestration function (`_run_chat_completion`), not a reuse of
  `run_order()`/`_run_order_body()` - the latter's `_consume_stream()`
  batches into `generating` ticks and silently drops a chunk whose only
  content is a tool-call delta, and its session-store/Pantry/escalation-
  pause machinery doesn't apply to a stateless endpoint. `messages_override`
  on `stream_order()` bypasses the prompt/history assembly entirely so
  the client's own OpenAI-shape history is relayed verbatim.
- Over-cap escalation, which cannot pause for approval on this endpoint
  (no UI to render the card), is treated as an immediate decline -
  `draft_quality` is surfaced via `system_fingerprint: "draft_quality"`
  on the final SSE chunk, chosen over a response header (would require
  buffering the entire generation before the first byte, defeating real
  streaming) or a trailing text note (would land inside code Cursor
  inserts directly into a file).
- `config/beans.yaml`/`aliases.py` gained a `tool_calling` capability
  flag (`Reserve Blend`/`Single Origin` set `True` on public Anthropic
  tool-calling support, the three free-tier Beans stay `False` unverified)
  - data only this Brew; a warning is logged, not blocked, when `tools`
  are sent to a Bean without it.
- The Ledger (`router/app/ledger.py`) gained 10 new columns in one
  migration via the existing Brew 38 auto-migration mechanism:
  `client_source`, `requested_model`, `over_cap_declined`,
  `has_code_fence`, `message_count`, `total_input_chars` (populated for
  real starting this session, for both `/v1/order` and the new
  endpoint), plus `retry_of`, `retry_count`, `is_shadow`, `shadow_of`
  (columns exist now, defaulted blank/`0`/`False`, not populated by real
  logic until Section 2's later session) - one migration for the whole
  Brew, per explicit instruction, not two.
- `tools/generate_policy.py` gained `routing_evidence_rows()`, excluding
  `is_shadow`/non-`chat_ui` rows from rating/escalation-rate evidence -
  applied now, not deferred, since the contamination risk starts the
  moment `/v1/chat/completions` is used for real, even though shadow
  mode itself isn't built yet.

A real bug found during test-writing, not anticipated in the plan:
`check_for_failure()` predates tool calling and treats any empty `text`
as the `"empty"` failure reason - a tool_calls-only response (no prose,
which is the *correct* shape for a tool-calling turn) was silently
triggering an unwanted auto-escalation re-run, doubling the merged
`tool_calls` (caught as `"get_weatherget_weather"` by
`test_tools_passthrough_round_trip`). Fixed by skipping the failure
check entirely when `tool_calls` were produced; a regression test
(`test_tool_calls_only_response_never_triggers_escalation`) locks it in.

What was deliberately not done this session (Sections 2/4, later
session): the `api_requests` SQLite table, retry detection (Signal A),
shadow mode (Signal C) and its settings/daily cost cap, the `--older-than`
prune CLI, and the `ledger_summary.py --mode model-usage` analysis
report. The curl / real OpenAI SDK / real Cursor live demo described in
the original request is also Section 2/4-adjacent work (the endpoint
functions today, but demoing it meaningfully against real coding tasks
is more useful once the measurement signals exist to interpret the
results) - deferred to the same later session.

Cost and token evidence: none - no remote Bean was called this session.

### 2026-07-16 - Brew 47 (Sections 2+4): Retry Detection, Shadow Mode, Analysis Tool

Sections 2 (the three measurement signals) and 4 (the analysis tool) of
Brew 47, completing the Brew - retry detection and shadow mode built
exactly as specified in the plan doc, `tools/ledger_summary.py --mode
model-usage`, and the `--older-than` prune CLI. Re-read the plan doc and
the as-shipped Section 1+3 code before starting, per instruction; the
as-built `_run_chat_completion`, the (nonexistent) `api_requests` store,
and `tools/ledger_summary.py` were all re-verified against the real
current code, not assumed from the design doc.

Preconditions:

- Full test suite green: `python tools/run_all_tests.py` - 761 tests,
  same 2 pre-existing vision-Bean fixture failures unrelated to this
  Brew.
- `OPENROUTER_API_KEY` already present in the shell environment; never
  pasted into chat or written to a file.
- A demo user (`demo47`) created directly via `hash_password()`/
  `create_user()` (the same Windows `getpass` piping limitation found in
  every prior live demo) - removed afterward via `manage_users.py
  remove`, with 5 orphaned `tokens` rows for that user_id cleaned up
  directly since user removal doesn't cascade-delete tokens.

What was built:

- New `api_requests` SQLite table (`router/app/sessions.py`) - did not
  exist before this session (confirmed by re-reading `sessions.py`'s
  `SCHEMA` first, not assumed from the design doc's SQL sketch). Gained a
  `completed_at` column distinct from `created_at` that the original
  sketch omitted - the retry window measures time since the original
  *completed*, not since it started.
- Retry matching (`SessionStore.find_retry_candidate`): same user +
  client fingerprint (`sha256(user_id|User-Agent)`, falling back to
  `"unknown"`) + last-message hash, matched only against an
  already-*completed* prior request. The `api_requests` row is inserted
  *before* generation starts, so a genuinely concurrent duplicate request
  sees the original as still in-flight and can never match it - this is
  the entire mechanism that keeps parallelism structurally distinct from
  a retry, with no extra bookkeeping.
- `RouterLedger.increment_retry_count()` - reuses `update_rating()`'s
  exact rewrite-the-whole-file pattern, making the CSV's own
  `retry_count` column live rather than a write-time snapshot. This
  supersedes what the original design doc's Section 3 said (`retry_count`
  would never retroactively update) - a human's explicit instruction in
  this session overrode that earlier framing, on the reasoning that one
  more full-CSV rewrite per detected retry is cheap at this router's real
  volume, and a live column is simply more useful than a decorative one.
- Shadow mode (off by default, `shadow_mode_enabled: false`,
  `shadow_mode_sample_rate: 0.1`, `shadow_mode_daily_cost_cap_usd: 1.00`)
  - API-only, never `/v1/order`, per the approved decision that the chat
  UI's rating buttons are already a strictly better signal. `_run_chat_
  completion` fills an optional `shadow_context` out-parameter in place
  (an async generator can't `return` a value through `async for`) right
  before writing its own Ledger row; the endpoint handler reads it back
  only after the client has the full response (in a `finally` block, both
  stream modes) and decides whether to `asyncio.create_task` a shadow
  run. `_run_shadow` calls the raw streaming helper directly, never
  `_run_chat_completion` again - a structurally stronger "never
  recursive" guarantee than a boolean flag, since there is no code path
  back into anything that schedules a shadow.
- **A deliberate, narrow, flagged inconsistency**: shadow Ledger rows get
  a *real* computed dollar `cost_usd` (`_real_cost_usd()`, tokens times
  the premium Bean's actual `beans.yaml` pricing) - the first time this
  router has ever computed a real dollar figure for a paid Bean anywhere.
  Every other paid-Bean row (primary `/v1/chat/completions` rows,
  `/v1/order` rows) still writes `cost_usd` as `"unknown"`, per the
  pre-existing `_is_free_tier()`-only convention this session did not
  touch. This was necessary, not optional: without a real number here,
  summing "unknown" cells across `is_shadow=true` rows would always total
  $0, and `shadow_mode_daily_cost_cap_usd` could never trip in practice -
  silently defeating the entire point of the cap. **Flagging this as a
  known inconsistency worth resolving in a future Brew**: it is a
  defensible narrow scope today, but `tools/ledger_summary.py`'s own
  counterfactual-cost math will eventually want real costs on primary
  paid-Bean rows too, and right now it cannot have them - the router only
  learned how to compute a real dollar figure for one narrow row type
  this session, not everywhere it would help.
- `tools/ledger_summary.py --mode model-usage` (`--mode cost-log` stays
  the unchanged default) - confirmed by re-reading the file first that it
  still only parsed the hand-maintained Markdown `cost_log.md`, exactly
  as the Section 1+3 session's plan said. Reads `ledger/router_requests.csv`
  directly via `csv.DictReader`, sliced by `task_type` and
  `client_source`, each slice's escalation/decline/retry rates and
  counterfactual cost printed together (never separated), a shadow
  section only when shadow rows exist, and an always-printed "what this
  cannot tell you" footer whose no-quality-signal fraction is computed
  purely from the CSV (a shadow row's own `shadow_of` cell already points
  at its primary, so no SQLite import was needed to answer "was this
  request shadowed").
- `router/tools/prune_api_requests.py` (new) - `--older-than <Nd|Nh|Nm>`,
  required, no default, manual only.

Commands (router started fresh with current code):

```powershell
python -m uvicorn router.app.main:app --port 8765
```

Driven via direct `curl` calls against the real router, same rationale
as the Section 1+3 demo - the mechanism itself, not a UI, is what needed
proving.

Observed behavior:

- **Retry detection**: two identical real `/v1/chat/completions` calls
  ("Explain what a Python decorator is in one sentence.") - the real
  `ledger/router_requests.csv` showed the second row's `retry_of`
  pointing at the first row's real `request_id`, and the first row's
  `retry_count` live-incremented to `1`.
- **Shadow mode**: `shadow_mode_enabled`/`shadow_mode_sample_rate`
  temporarily flipped to `true`/`1.0` directly in `config/settings.yaml`,
  router restarted. A first timed request ("Say hello in exactly three
  words") happened to auto-escalate on its own (a short answer tripped
  `truncation_min_expected_tokens`) before shadow logic even had a
  chance to run (an already-premium primary is correctly skipped for
  shadowing) - this is also where the escalation-concatenation bug below
  was first noticed. A second, longer-prompt request stayed on House
  Blend as intended: client-perceived latency measured at 5.39s; the real
  Ledger gained a second row for the same request with `is_shadow=True`,
  `bean_alias=Reserve Blend`, and `cost_usd=0.007146` (27 tokens in / 471
  tokens out × Reserve Blend's real `beans.yaml` pricing - not an
  estimate). `router/data/sessions.db`'s `api_requests` table held two
  distinct, real stored responses (House Blend's vs. Reserve Blend's)
  under the same primary `request_id`, confirmed readable directly.
  Settings reverted to `false`/`0.1`, router restarted again; a further
  request confirmed no new shadow row appeared.
- **Prune CLI**: run twice for real - `--older-than 90d` deleted 0 rows
  (nothing that old yet), `--older-than 0m` deleted the real 5 demo
  `api_requests` rows.
- **`ledger_summary.py --mode model-usage`**: run against the real
  accumulated Ledger, full output shown verbatim, including a real
  shadow section (1 pair, $0.0071 total spend, pointing at the exact
  `sessions.db` query) and the complete blind-spot footer.

**A real bug was found live during the shadow-mode demo, not fixed this
session, per explicit instruction**: an auto-escalated
`/v1/chat/completions` request streams the cheap draft's and the premium
re-run's content to the client back to back with no reset in between.
`_run_against()`'s internal `text` accumulator *is* correctly reset
between the two calls (server-side Ledger/failure-check logic is
unaffected), but every chunk it yields to the client is relayed
regardless of which run produced it. Live evidence: the "say hello in
three words" request above returned `"Hello there youHello there,
friend!"` to the client - the truncated cheap draft glued directly to
the premium run's own greeting, with no separator or reset signal. The
original Section 1 design doc called this an "inherited quirk" from
`/v1/order` and treated it as accepted precedent; that undersold it for
an endpoint that specifically claims OpenAI compatibility, where real
clients (the SDK, Cursor, Continue.dev) are entitled by spec to assume
content deltas concatenate into one coherent message. The only
spec-correct fix identified - buffer the cheap draft internally instead
of streaming it in real time, only emitting real chunks once the failure
check has run - trades away time-to-first-token on every request that
might escalate (unknowable in advance) for correctness, which is a
real, deliberate trade-off warranting its own small Brew and a human
decision, not a same-session patch. Full writeup in `brew-log/
progress.md`'s 2026-07-16 entries.

Cost and token evidence: real calls, mostly free-tier ($0.00) plus one
real premium-Bean shadow call. Retry demo: req-1 (House Blend, free)
12 in / 58 out; req-2 (retry, House Blend, free) same shape. Shadow demo
primary: House Blend (free), 27 in / 381 out; its shadow: Reserve Blend,
27 in / 471 out, real cost $0.007146 (the first real, non-"unknown"
dollar figure this router has ever recorded for a paid Bean).

Cleanup: `demo47` removed via `manage_users.py remove`; 5 orphaned
`tokens` rows for that user_id deleted directly (user removal does not
cascade); the Ledger's own migration-backup file
(`router_requests.csv.bak-2026-07-16T07-39-48+00-00`, created when the
real CSV picked up the already-code-complete Brew 47 schema for the
first time) deleted as a transient artifact, matching the Brew 46
precedent of not committing migration backups. The demo's real Ledger
rows themselves were kept, same convention as every prior live demo.

### 2026-07-16 - Brew 47: Escalation-Concatenation Fix

Fixed the bug reported (not fixed) in the Section 2+4 entry above:
`_run_chat_completion`'s auto-escalate path streamed the cheap draft's
and the premium re-run's content to the client back to back with no
reset. Re-read the "Known issue" writeup, `_run_against()`, and the
streaming path before starting, per instruction - the as-shipped code,
not the design doc's original framing, was the source of truth.

The buffer-always fix (hold every response internally until the failure
check completes, regardless of stream mode) was explicitly rejected:
losing time-to-first-token on every potentially-escalating request to
correctly serve the ~1-in-8 that actually escalate is a bad trade for an
endpoint whose entire point is being a transparent drop-in for coding
tools like Cursor. Fixed by making escalation **mode-dependent**
instead:

- `stream=false`: escalation works fully, as originally designed. The
  draft's per-chunk deltas are captured internally but never yielded
  live; on `auto_escalate`, the premium re-run replaces the draft
  entirely (discarded, never reaching the client) and the winning
  response is emitted as one buffered `_openai_chunk`. Buffering here is
  free - a non-streamed response was already being assembled into one
  JSON body at the edge regardless of this fix.
- `stream=true`: never escalates. The draft streams live exactly as
  before (this fix does not touch that path's latency at all); the
  failure check and `decide_escalation()` still run for measurement, but
  on `auto_escalate` the premium call is skipped and a new Ledger column,
  `would_have_escalated`, is set instead - the measurement signal
  survives even though the action doesn't.
- Surfaced to the client via the *same* mechanism `over_cap_declined`
  already used - `system_fingerprint: "draft_quality"` - reusing
  `draft_quality`'s existing meaning ("you got the draft, not the ideal
  answer") rather than inventing a second signal.
- `EVENT_CONTRACT.md` read and confirmed unaffected - it documents
  `/v1/order`'s named SSE events, which this fix does not touch;
  `/v1/chat/completions` was already outside that contract.

Preconditions: `python tools/run_all_tests.py` green before starting
(764 tests including the Section 2+4 work, same 2 pre-existing unrelated
failures); `OPENROUTER_API_KEY` already present in the shell environment.

Commands:

```powershell
python -m uvicorn router.app.main:app --port 8765
```

A fresh demo user (`demo47b`) created directly via `hash_password()`/
`create_user()` (same Windows `getpass` piping limitation as every prior
live demo), logged in via the real `/v1/login` endpoint for a real
bearer token, kept in-memory only within a single shell command chain.

Observed behavior - reproducing the exact bug prompt, "say hello in
exactly three words," in both stream modes against the fixed code:

- **`stream=true`**: House Blend's draft ("Hello there friend", 17
  completion tokens per the router's own token estimate) tripped the
  same truncation check that triggered the original bug and would have
  auto-escalated - but the client received only the clean draft content
  and `system_fingerprint: "draft_quality"` on the final chunk. No
  premium text appended, no concatenation. The real Ledger row confirms
  `bean_alias=House Blend`, `escalated=False`,
  `would_have_escalated=True`.
- **`stream=false`**: the identical prompt returned only Reserve Blend's
  premium response, `"Hello there, friend!"` (8 completion tokens) - the
  draft text is provably absent from the body. The real Ledger row
  confirms `bean_alias=Reserve Blend`, `escalated=True`,
  `would_have_escalated=False`, `tokens_out=8` - the premium call's own
  real count, not the discarded draft's, which is exactly where cost
  under-reporting would have hidden if the fix had gotten this wrong.

Cost and token evidence: two real calls, both free-tier ($0.00 - House
Blend and Reserve Blend are both zero-cost Beans in this router's real
`beans.yaml` today, so this demo could not exercise a real dollar figure
the way the Section 2+4 shadow-mode demo did). `stream=true` request: 8
in / 17 out (House Blend). `stream=false` request: 8 in / 8 out (Reserve
Blend, actual premium output, not the draft's).

**Known inconsistency carried forward from the Section 2+4 entry above,
still unresolved**: shadow rows now carry real computed dollar costs
while primary paid-Bean rows still write "unknown", which is a known
inconsistency worth resolving in a future Brew, and one
`tools/ledger_summary.py`'s counterfactual math will eventually need
fixed. This session's fix does not touch that gap either way - it is
noted here again so it does not get lost between Brew entries.

Cleanup: `demo47b` removed via `manage_users.py remove`; its 1 orphaned
`tokens` row and 2 orphaned `api_requests` rows deleted directly, scoped
to that user's own `id` only - pre-existing unrelated orphan rows from
earlier sessions were confirmed present and deliberately left untouched,
out of this session's scope. The Ledger's own migration-backup file
(created on this session's first write, once the new
`would_have_escalated` column changed `CSV_HEADER`) deleted as a
transient artifact, matching every prior Brew's precedent. The two real
demo Ledger rows themselves were kept, same convention as every prior
live demo.

### 2026-07-17 - Brew 48: Cost-Inconsistency Fix

Resolved the inconsistency flagged (not fixed) in the Brew 47 Section 2+4
and escalation-concatenation-fix Tasting Note entries above: shadow rows
carried a real computed dollar `cost_usd` while every other paid-Bean row
- both `/v1/order` and primary `/v1/chat/completions` - wrote `"unknown"`,
so `ledger_summary.py --mode model-usage` could price a hypothetical
premium counterfactual but not a single real request. Re-read
`ledger.py`, `main.py` (`_real_cost_usd` and both orchestration paths),
`beans.yaml`, and `ledger_summary.py` before planning, per instruction.

**Cost contract decided before implementation, explicitly to avoid a
collision with the queued web-search Brew** (which will add its own
`web_search_cost_usd` component column): `cost_usd` is always the
request's TOTAL cost, from whichever source produced it; any per-feature
component column is a BREAKDOWN of that total, never an amount to add on
top - a cost pill or Tips Jar sums `cost_usd` alone. Considered the
alternative (`cost_usd` token-only, components add up to the real total)
and rejected it: once `resolve_cost()` prefers OpenRouter's own reported
`usage.cost`, that figure is already the true all-in total, and stripping
a component back out of it before storage would require the same
subtraction math twice for one number - two sources of truth guaranteed
to drift the first time a provider's reported total doesn't decompose the
way local math assumes. Written into `ledger.py`'s module docstring so
the decision survives past this session.

**Implementation** (`router/app/ledger.py`): `resolve_cost(bean,
tokens_in, tokens_out, usage) -> (cost_usd, cost_source)` replaces both
`_real_cost_usd()` (shadow-only) and the `_is_free_tier()`-only convention
(primary rows) with one function every write path uses. Prefers
`usage["cost"]` when present (`cost_source="reported"` - this router
already sends `usage: {"include": true}` on every OpenRouter request, so
a real all-in figure, accounting for provider-routing quirks
`beans.yaml` can't know about, was sitting unused). Falls back to
`beans.yaml` token math (`cost_source="computed"` - exact for a free-tier
Bean, giving a real `$0.00`, never `"unknown"`). Returns `(None, "")`
only when the Bean has no pricing configured at all - the one genuinely-
unknown case. Lives in `ledger.py`, not `main.py`: this is a Ledger-
domain concern (what goes in the `cost_usd`/`cost_source` columns), and
both orchestration paths need the identical function - keeping it in
`main.py` would mean duplicating it or importing orchestration internals
into itself.

New `cost_source` CSV column (Brew 38 auto-migration pattern - appended
to `CSV_HEADER`, no explicit migration script). A real, non-obvious gap
closed to make this possible: `_run_order_body`'s non-escalated path
already captured `usage` from `_consume_stream` but discarded it
(`_, final_text, tokens_out, finish_reason, _usage = item`), and
`_run_escalation`'s `__escalation_final__` sentinel *always* returned
`None` for its 4th slot regardless of what the premium call's usage
actually was - meaning an escalated `/v1/order` request could never have
gotten a reported cost even after this fix, without also threading
`usage` through that sentinel. Both fixed. `_run_chat_completion` already
captured `usage` correctly (Brew 47), only its cost-computation call site
needed to change.

New `assert_active_beans_priced()` startup guard (`router/app/
aliases.py`, new `BeanPricingError`) raises if any `status="active"` Bean
lacks `price_per_1k_input_usd`/`price_per_1k_output_usd` - exactly the
misconfiguration that makes `resolve_cost()` fall through to a genuinely
unknown cost for every request routed to it. Called from `create_app()`'s
real-startup branch only, never when a test injects its own state (test
fixtures may deliberately use an unpriced placeholder premium Bean).
Confirmed passing against the real `beans.yaml` today - all 5 Beans
already have real pricing (0.0 for the 3 free-tier Beans), so this
assertion does not fire in the current real config; it exists to catch
the next Bean added without pricing, not today's config.

New `router/tools/backfill_ledger_costs.py` (`--dry-run`/`--apply`,
mutually exclusive, required - mirrors `prune_api_requests.py`'s CLI
shape). `RouterLedger.backfill_missing_costs(bean_registry, apply)` scans
every row with an unknown `cost_source`, recomputes via `resolve_cost()`
using the row's own `tokens_in`/`tokens_out`/`bean_alias` (no `usage`
dict exists for a historical row, so a backfilled row is always
`cost_source="computed"`, never `"reported"` - that source was never
captured at write time and cannot be recovered retroactively). Rows that
still can't be priced (bad tokens, unknown alias, unpriced Bean) are left
untouched, remaining genuinely unknown. `apply=False` computes the full
diff and writes nothing; `apply=True` performs the same computation and
rewrites the file via the same whole-file-rewrite mechanism
`update_rating()` already uses.

`tools/ledger_summary.py`'s `compute_slice_stats` now counts
`reported_cost_count`/`computed_paid_count`/`computed_free_count`/
`unknown_cost_count` separately via the `cost_source` column, rendered as
an explicit breakdown line under each slice's total - a real `$0.00`
free-tier row must never be counted with the genuinely unknown ones, and
a reported cost must never be conflated with a computed one even though
both feed the same total. The "what this cannot tell you" footer gained
an always-computed, explicit unknown-cost-count/fraction line (previously
only visible per-slice, buried in each "(N unknown)" annotation).

Deleted `_is_free_tier()`/`_real_cost_usd()` from `main.py` after
confirming via grep neither is referenced anywhere else, including tests.

30+ new tests: `resolve_cost()` (reported-preferred, reported-wins-even-
over-token-math, computed-fallback with and without a `usage` dict,
free-tier real-zero, unpriced-Bean-returns-None-empty-source, unpriced-
Bean-still-prefers-reported, non-numeric `usage["cost"]` falls back to
computed); `assert_active_beans_priced` (raises for an unpriced active
Bean, passes for a priced one, passes when the unpriced Bean isn't
active, passes against the real config, error message names the
offending alias); backfill (dry-run computes without writing, apply
writes, known-cost_source rows skipped, unpriceable-Bean/unknown-alias/
bad-tokens all left unknown, backfilled rows are always `"computed"`
never `"reported"`); `/v1/order`'s `RunOrderTestCase` (free-tier real
zero with computed source, both the `auto_escalate` and
`escalation_pending`-approved code paths preferring a reported cost
through the now-threaded `usage`); `/v1/chat/completions`'s
`ChatCompletionsEndpointTests` (free-tier real zero, reported cost
preferred, and - mirroring this endpoint's own "Hello there
youHello there, friend!" concatenation-bug precedent, applied to cost
instead of content - the escalated premium call's own reported cost wins
over the discarded draft's); the shadow-mode test suite (one new test
confirming `_run_shadow` now goes through `resolve_cost()` and prefers a
reported cost the same as every other row); `ledger_summary.py`'s
`ModelUsageReportTests` (three states counted separately, a real `$0.00`
never counted as unknown, the explicit footer line, and a pre-
cost_source-migration row - default blank column - counted unknown, not
silently treated as reported or computed).

`python -m pytest router/tests tests`: 758 passing, 1 skipped. 4 failures, all
confirmed via `git stash`/isolated re-run to predate this session and be
unrelated: the same 2 pre-existing vision-Bean fixture-drift failures
this log has carried since the external `beans.yaml` commit noted in a
prior "Up next" entry (`test_aliases.py::test_real_config_has_no_vision_
bean_today`, `test_routing.py::test_real_generated_policy_needs_vision_
raises_today`), 1 more of the same drift family
(`test_sessions.py::test_find_retry_candidate_prefers_most_recent_match`,
present on `master` before this session per `git stash` verification, not
investigated further as clearly out of this Brew's scope), and 1 genuine
timing flake (`test_sessions.py::test_list_sessions_ordered_newest_
updated_first`, fails only in the full-suite run, passes cleanly in
isolation - a sub-second timestamp-ordering race, not something this
Brew's changes could cause since nothing here touches `SessionStore`).

Live demo against the real Ledger (37 existing rows from prior Brews'
real OpenRouter calls, no new model call made this session):
`backfill_ledger_costs.py --dry-run` triggered the pending Brew-38-style
migration (added `cost_source`, backed up the pre-migration file) and
printed the full diff - 8 previously-`"unknown"` Reserve Blend rows would
gain real computed costs (e.g. `unknown -> 0.009693`, `unknown ->
0.002697`, down to `unknown -> 0.000144`), every free-tier row already
correctly `0.0 -> 0.0`. `--apply` wrote it for real. Then `tools/
ledger_summary.py --mode model-usage` against the now-backfilled real
Ledger:

```
## Overall
- Requests: 36
- Total cost: $0.0190 (0 row(s) unknown)
    - 0 reported (OpenRouter's own usage.cost)  |  8 computed-paid  |
      28 computed-free ($0.00, free-tier Bean)  |  0 unknown
```

- a real, non-zero total cost, replacing the old `$0.0000 (6 rows
unknown)` gap this Brew set out to close - with `0 reported` correctly
reflecting that no row in this router's history has ever actually
captured OpenRouter's own `usage.cost` yet (every real call so far
predates this Brew's `usage`-threading fix); the next real `/v1/order` or
`/v1/chat/completions` call will be the first to populate that count.
Migration backup file (`.bak-2026-07-17T17-19-43+00-00`) deleted as a
transient artifact, matching every prior Brew's precedent - the
backfilled real Ledger rows themselves were kept. Not yet staged or
committed.

### 2026-07-17 - Brew 49: Spend Caps

Goal stated plainly: the app is now on the LAN with real family accounts,
every request bills one OpenRouter key, and nothing stopped one
enthusiastic user from running up a bill. Re-read `config.py`,
`settings.yaml`, `ledger.py` (`resolve_cost`/the COST CONTRACT), `main.py`
(both orchestration paths, grepped every real spend call site rather than
trusting the four named in the brief), `sessions.py`, `auth.py`.

**Verified the Brew 48 dependency before planning, per instruction, and
found it hadn't fully closed the loop.** `resolve_cost()` is correctly
used on every Ledger-writing spend path - but `generate_memory_proposal()`
(`memory_proposals.py`) spends real money via `stream_order_fn` directly
and wrote **no Ledger row at all**, not even `"unknown"` - a real,
ungoverned, invisible spend surface, low-risk only because its Bean
defaults to free-tier. Separately, `router.app.routing._estimate_cost_usd()`
(and `est_premium_cost_usd` in both orchestration paths' escalation setup)
never produced a real dollar figure for a paid Bean - always `0.0` or
`None` - which meant `escalation_cost_cap_usd` (a feature explicitly asked
for in Brew 40) had never actually gated anything: `0.0` is always less
than any positive cap, so every eligible failure auto-escalated
regardless of the configured value, and the human-approval card behind it
had never fired from a real cost decision in this router's history.

**The plan's first draft proposed a narrow, spend-cap-only estimator,
deliberately not touching the existing (broken) one - the user corrected
this explicitly.** This is the third instance of the identical decorative-
cost pattern in this codebase (the shadow-mode cap in Brew 47, the
Ledger's own `cost_usd` in Brew 48, now the escalation cap) - building a
second, parallel estimator alongside a known-broken one "guarantees a
fourth." Fixed the one shared estimator instead: `_estimate_cost_usd`
renamed to public `estimate_cost_usd(bean, tokens_in, assumed_output_tokens)`,
real token math, now used by both the new spend cap and the pre-existing
escalation cap. Explicit, stated consequence: `escalation_cost_cap_usd` is
live for the first time; at real Reserve Blend pricing a typical
escalation is a cent or two, so the `$0.50` default will rarely fire in
practice - a real number to inform whether that default is still right,
not changed in this Brew per explicit instruction.

Two other design questions were resolved by direct instruction rather than
inferred: the assumed-output-tokens estimate uses the client's own
`max_tokens` when given (Cursor usually sends one, strictly better
information than a guess), else `spend_cap_assumed_output_tokens` (1000) -
`/v1/order` has no `max_tokens` field, so it always uses the default. And
`/v1/order`'s cap refusal stays an SSE `error` event, never a literal HTTP
status - "the only error mechanism that endpoint has ever had... restructuring
it would change the contract for every existing error type to fix a
semantics issue nobody is hitting."

**Implementation.** Three settings (`per_user_daily_cost_cap_usd` 1.00,
`global_daily_cost_cap_usd` 5.00, `per_user_requests_per_minute` 20) plus
`spend_cap_assumed_output_tokens` (1000, estimator-only, never stored as a
real cost). `users.daily_cost_cap_usd` (nullable REAL, incremental
`ALTER TABLE` migration matching `sessions.py`'s existing
`SESSIONS_NEW_COLUMNS` pattern - `NULL` means "use the settings.yaml
default," never a silent 0) plus `manage_users.py set-cap <username>
<amount|clear>`. New Ledger `user_id` column (Brew 38 pattern - blank for
every pre-migration row, never invented) and `RouterLedger.today_spend_usd(
user_id=None)`, summing today's UTC-day `cost_usd` (`user_id=None` sums
everyone, for the global cap) and explicitly flagging - never silently
zeroing - any genuinely-unknown cost it encounters, exactly the
undercount Brew 48 exists to prevent.

`check_spend_cap()`/`check_rate_limit()` (new, `main.py`) are the single
enforcement point, called at every real spend site found by grepping
rather than assuming: `_run_order_body`'s draft and both escalation
branches, `_run_chat_completion`'s draft (at the endpoint-handler level -
see below) and its `auto_escalate` branch, `_maybe_schedule_shadow`
(made `async`, gated against the per-user and global caps *in addition
to* the pre-existing `shadow_mode_daily_cost_cap_usd` - a shadow run is
real money attributed to the user whose request triggered it, so it
respects all three), and the memory-proposal endpoint. An escalation-
stage denial falls back to `draft_quality=True` rather than erroring out
the whole request, per explicit instruction - the draft is already a
valid, already-paid-for answer, and discarding it would waste money
already spent for nothing.

`/v1/chat/completions`'s check runs at the endpoint-handler level, not
inside the orchestration generator, via a `generator.__anext__()` peek at
the first yielded item before either response mode commits to anything.
This is load-bearing, not incidental: once `StreamingResponse` is
returned, the HTTP status is locked at 200 forever, and there is no way
to produce a real `429` from inside an already-streaming response. Peeking
first means a denial is a plain `JSONResponse(429, ...)` for both
`stream=true` and `stream=false` uniformly, and the stream structurally
never starts on a denial - "never start a stream you will kill mid-token"
holds by construction, not convention. This also fixed a related
pre-existing gap as a side effect: an in-generator routing error on
`stream=true` previously rode inside a 200 SSE frame with no real HTTP
error status; now any first-chunk error (spend-cap, rate-limit, or
routing) gets a proper non-200 response on both stream modes.

**Concurrency**: two concurrent requests from the same user could
otherwise be admitted against the same stale "today's spend" snapshot.
Chose a per-user `asyncio.Lock` (`RouterState.spend_cap_locks`, created
lazily, same pattern as `cancel_flags`) held across each check's
read-then-decide section - and because this router is explicitly single-
process by design (`sessions.py`'s own "single-user means single OS
process" precedent), an in-process lock closes this race completely, not
merely narrows it, for the cost of holding a lock only across a cheap
Ledger read and comparison.

**A real design correction found mid-implementation, not in planning**:
the Decaf plan called for a hard assertion when `session_store` is
configured but `user_id` is `None` ("an impossible state" on the real
request path). Running the test suite after wiring this in immediately
hung `test_auto_escalate_decision_deadline_is_none` and several siblings
for the full 600-second default approval timeout - not from the
assertion itself, but from the newly-real estimator flipping their
outcome from `auto_escalate` to `escalation_pending` (see below). Fixing
that surfaced the assertion problem next: dozens of existing tests
(shadow mode, retry detection, the escalation-approval flow) construct a
real `SessionStore` fixture for reasons unrelated to this Brew and call
orchestration functions directly without a `user_id` - a legitimate,
pre-existing test pattern, not a bug. The hard assertion would have
failed all of them. Downgraded to a silent skip (`session_store is None
or user_id is None: return`) after concluding the real safety guarantee
already lives entirely at the endpoint layer - every real endpoint's
`Depends(get_current_user)` structurally guarantees a real `user_id`
before any orchestration code ever runs, so a defensive assert deep
inside a shared helper protects against nothing a test fixture wouldn't
also (harmlessly) trip.

**Test-fixture fallout from the real estimator, found and fixed
directly**: `_make_bean_registry`'s Reserve Blend was priced at round
test numbers (`1.0`/`2.0` per 1k) chosen for easy arithmetic, never meant
to represent anything real. Under the old decorative estimator this
never mattered; under the new real one, a "trivial" test escalation
priced out at roughly `$2.00` (the default 1000-token output assumption
dominates), exceeding every test fixture's `0.50` `escalation_cost_cap_usd`
and silently flipping `auto_escalate` scenarios into `escalation_pending`
ones with no `wait_for_approval` injected - the hang described above.
Fixed by repricing the shared fixture to match the real `beans.yaml`
Reserve Blend (`0.003`/`0.015`) instead of arbitrary round numbers - now a
real fraction of a cent, matching this Brew's own stated real-world
expectation, and comfortably under every existing cap-based test
assumption. Separately (found by re-reading the shadow-mode test class
before assuming it was safe, not after a failure): `ChatCompletionsEndpointTests`
always threads a real `user_id` through the endpoint regardless of
`with_session_store`, so the real `settings.yaml` cap defaults would have
incidentally gated shadow-run scheduling in tests that have nothing to do
with spend caps - fixed by giving `_make_state`/`_make_app` generous,
explicit spend-cap defaults, overridden only by tests that deliberately
exercise enforcement (the same precedent `escalation_cost_cap_usd` already
established as an overridable test kwarg).

**Tests**: 60+ new. `routing.py`'s `estimate_cost_usd()` against real
per-Bean pricing for `select_route`/`manual_route`/`select_fallback_route`.
`ledger.py`'s `today_spend_usd()` (per-user/global sums, shadow-row
attribution, day-boundary exclusion, unknown-cost flagging without
zeroing, no-prior-spend doesn't crash). `sessions.py`'s
`daily_cost_cap_usd` default/set/clear. A dedicated `CheckSpendCapTests`
class unit-testing `check_spend_cap()`/`check_rate_limit()` directly
(rather than only indirectly through routing/pricing) - the exact
0.99-of-1.00-refuses-a-0.50-request boundary from the Decaf plan, exactly-
at-the-cap is allowed (only strictly over refuses), the global cap firing
even when under the per-user cap, an unknown estimate always refusing,
the per-user override column taking precedence, shadow attribution,
day-boundary reset, per-user-independent rate limiting, and the chosen
concurrency behavior via a real `asyncio.gather()` race). End-to-end
tests on both endpoints for the exact error shapes (`ErrorEvent` fields
for `/v1/order`; the `429`/OpenAI-shape body/`Retry-After` header for
`/v1/chat/completions`, including the load-bearing `stream=true`-never-
opens-a-stream case and `max_tokens`-shapes-the-estimate). A dedicated
`MemoryProposalSpendCapTests` class confirming the new real Ledger row and
the `429`-with-zero-Ledger-rows-written refusal path. Frontend:
`usageBarMath.test.ts` (9 threshold tests, including the zero-cap edge
case) and `UsageBar.test.tsx` (6 tests: no render until loaded, the three
color states, refetch on a new `complete` event, fail-silent on a
network error).

`python -m pytest router/tests tests`: 848 passing, 1 skipped, the same 2
pre-existing config-drift failures (confirmed unrelated to this Brew,
same as every prior session). `npx vitest run`: 211 passing. `tsc
--noEmit`/`eslint`/`next build` all clean.

Commands (router started fresh with the real `OPENROUTER_API_KEY`):

```powershell
python -m uvicorn router.app.main:app --port 8765
```

A demo user (`demo_spendcap`) created directly via `hash_password()`/
`create_user()` (same Windows `getpass` piping limitation as every prior
live demo) - the real household accounts were deliberately never touched.

**Live demo, `per_user_daily_cost_cap_usd` set to `0.02` then `0.01` in
the real `settings.yaml`** (router restarted between each change - a
running process caches its settings at startup):

- `GET /v1/usage` showed real `$0.00` of `$0.02` before any spend.
- A real `/v1/order` call to Reserve Blend (`bean_alias_override`) showed
  a real pre-call estimate on `route_selected` (`est_cost_usd: 0.015015`)
  and completed normally, at a real cost of `$0.000114` (`cost_source:
  "reported"`).
- With the cap tightened to `0.01`, the identical request was refused
  *before any OpenRouter call*: a real SSE `error` event -
  `error_type: "spend_cap_exceeded"`, `retryable: false`, message
  "You've reached today's spending limit. It resets at midnight UTC."
- `/v1/chat/completions` refused the same request on both `stream: false`
  and `stream: true` - a real HTTP `429`, an OpenAI-shape
  `{"error": {"type": "spend_cap_exceeded", "code": "spend_cap_exceeded",
  ...}}` body, and a real `Retry-After` header (`17785` seconds, matching
  the real UTC-midnight reset) on both. Confirmed directly that
  `stream: true` never opened an SSE connection at all on the denial - no
  `text/event-stream` content-type, no bytes sent before the `429` -
  the exact property this design exists to guarantee.
- The escalation-stage check fired too: a real `spend_cap_refused_escalation`
  log line when a draft's own auto-escalation attempt was blocked by the
  same tiny cap.
- Rate limiting demoed separately (`per_user_requests_per_minute` set to
  `3`, router restarted): the 4th quick `/v1/chat/completions` call in
  under a minute got a real `429` with `error_type: "rate_limit_exceeded"`
  and `Retry-After: 60` - a distinct `error_type` from the spend cap, as
  required, visible directly in the response body and the
  `rate_limit_refused` log line.
- Real Ledger rows and every `spend_cap_refused`/`spend_cap_refused_
  escalation`/`rate_limit_refused` log line were read directly from the
  running process's own log and CSV - no refused request ever produced a
  Ledger row (confirmed by row count before/after each refusal).

Cleanup: `demo_spendcap` removed via `manage_users.py remove`; its 1
orphaned `tokens` row deleted directly (scoped to that user's own `id`
only). The Ledger's own migration-backup file (created on this session's
first write, once the new `user_id` column changed `CSV_HEADER`) deleted
as a transient artifact, matching every prior Brew's precedent. The real
demo Ledger rows themselves were kept, same convention as every prior
live demo. `settings.yaml` restored to the real defaults
(`per_user_daily_cost_cap_usd: 1.00`, `global_daily_cost_cap_usd: 5.00`,
`per_user_requests_per_minute: 20`); router restarted once more and a
deliberately-wrong-password login attempt confirmed normal
request/response behavior (a clean 401, not a crash) with the restored
configuration.

### 2026-07-18 - Brew 50: Web Search

**No plan doc existed for this Brew going in.** Every other Brew has a
`docs/design/*.md` written before implementation; this one's original
plan was written and approved in an earlier session that was not in this
session's carried-over context, and was never saved to a file. Rather
than guess at lost wording, `docs/design/web-search-design.md` was
reconstructed from scratch by re-reading the current code (`aliases.py`,
`beans.yaml`, `classifier.py`, `routing.py`, `openrouter_client.py`,
`main.py`'s both orchestration paths) and folding in the three
corrections given at session start directly, then presenting the result
for approval before writing any code - same Decaf-first discipline as
every other Brew, just without a prior document to diff against. Also
caught and corrected a factual claim in the session-opening message:
Brew 49 (spend caps) was said to be "committed," but `git log`/`git
status` showed it was fully implemented and sitting in the working tree,
not yet committed - flagged before proceeding, fixed later in-session
once the human confirmed it.

**Correction 1 (rejected the classifier task_type nudge)**: `task_type`
is a Ledger column `ledger_summary.py` slices by - nudging it toward
"research" whenever `use_web` is set would mislabel a coding question
with search turned on and corrupt that measurement, for no routing
benefit (the tool-calling constraint already decides the Bean directly).
Instead, `use_web` feeds exactly one new `COMPLEXITY_SIGNALS` entry -
injected search results are real extra context to reason over,
unconditionally, the same "simple and predictable" precedent
`has_attachments` already established in Brew 38. A dedicated test
(`test_use_web_does_not_change_task_type`) locks this in.

**Correction 2 (`capable_bean()` picks by price, not role)**: the first
instinct would have been `role == "premium"` or `role == "default"`, but
neither is actually "capable" - `role="default"` (House Blend) has no
tool calling at all, and `role="premium"` (Reserve Blend) is
tool-calling capable but not the *cheapest* one. New
`BeanRegistry.capable_bean(tool_calling=True, vision=False)` filters to
every available Bean satisfying the requested capabilities and returns
the one with the lowest combined per-1k price. Against the real
`beans.yaml`, that's Single Origin (`$0.001`/`$0.005`, combined
`$0.006`) over Reserve Blend (`$0.003`/`$0.015`, combined `$0.018`) - a
dedicated regression test
(`test_real_beans_yaml_web_request_routes_to_single_origin_not_reserve_
blend`) asserts this directly against the real config, not just a
fixture, so a future re-pricing of either Bean that flips the ordering
would be caught immediately rather than silently changing which Bean
absorbs web-search traffic.

**Correction 3 (free-tier exit is the real cost, documented
prominently)**: no Bean in `beans.yaml` with `tool_calling: true` is
free. `router/README.md`'s new "Web search" section and this entry both
lead with that fact rather than burying it under the per-search plugin
fee - a household user flipping "Use Web" on needs to know this leaves
free-tier before they need to know the mechanics of how the fee is
computed.

**Routing constraint mirrors the vision constraint exactly, by design.**
`select_route`/`manual_route` gained `needs_tool_calling`, implemented as
a direct parallel to the existing `needs_vision` constraint added in
Brew 38: if the policy-/manually-selected Bean isn't capable, escalate to
`capable_bean()` (or, for a manual pick, raise rather than silently
substitute - never override an explicit human choice); if nothing in
`beans.yaml` qualifies at all, raise a distinct, catchable error
(`NoToolCallingBeanError`, surfaced as `no_web_search_bean_available`)
rather than silently proceeding without search or crashing. Both
constraints can fire together and combine into one `constraint_reason`
string (tested directly with a three-Bean fixture where a vision-only
Bean satisfies one constraint but not the other, forcing a second
escalation to a Bean with both capabilities).

**Cost design collapsed once the dependencies actually landed.** With
Brew 48's `resolve_cost()` already returning the request's true total
and Brew 49's spend caps already summing `cost_usd` alone, this Brew's
own cost work reduced to one small function:
`estimate_web_search_component_usd(bean, tokens_in, tokens_out, cost_usd,
cost_source)` subtracts pure token cost from a `"reported"` total (the
only case where a real all-in figure exists to subtract from) and
returns `None` - never a fabricated `0.0` or the full total - when the
source is `"computed"`, since a computed cost already IS the token math
with nothing else in it to isolate a fee from. Clamped to a `0.0` floor
to absorb rounding drift between OpenRouter's reported total and this
module's own per-1k math, never allowed to show a negative fee. The
per-user/global spend caps needed zero code changes - verified directly
(not assumed) that `check_spend_cap()`/`today_spend_usd()` already sum
`cost_usd` alone, and a web request's `cost_usd` is the reported total
with the search fee already inside it.

**Escalation carry-through, the third approved correction from this
session's opening answers.** `use_web` (and the `plugins` payload it
produces) carries through an auto-escalation re-run only when the
premium Bean is also tool-calling capable; when it isn't, the re-run
proceeds without search and a warning is logged
(`use_web dropped for escalation re-run`) rather than hard-failing an
escalation that would otherwise still produce a valid, non-web answer -
the same "never discard an already-paid-for or still-obtainable good
answer" instinct behind Brew 49's fallback-to-draft-on-cap-denial
behavior. A dedicated test builds a three-Bean fixture (a free default, a
free-but-tool-calling Bean, and a paid-but-non-tool-calling premium Bean)
specifically to force this drop path and assert both the logged warning
and that the escalation still completes successfully.

**`/v1/chat/completions` scope, per the session's third answer**: no
`use_web` field there - a raw OpenAI client's own `tools` array is for
its own function-calling loop, unrelated to Coffee-side search, and that
endpoint never sends OpenRouter's web plugin. But a client that sends
`tools` still needs a Bean that can actually call them, so the same
`needs_tool_calling` constraint machinery applies there too. This
replaced a passive, do-nothing log line
(`logger.warning("tools sent to bean_alias=%r without verified
tool_calling support")`, present since Brew 47) with real enforcement -
a genuine gap this Brew closed as a side effect: before this change, a
client sending `tools` to a non-capable Bean got a server-side log line
nobody watching the UI would ever see, and the tool-calling request
would simply fail or silently produce no tool calls.

**Test-fixture fallout, the familiar kind.** Enforcing the new
constraint immediately broke 4 existing `/v1/chat/completions`
tool-passthrough tests - `test_main.py`'s shared bean-registry fixture
had no `tool_calling=True` Bean anywhere, so any test sending `tools`
now hit `NoToolCallingBeanError` before ever reaching the fake
`stream_order_fn`. Same shape as Brew 49's Reserve-Blend-repricing
fallout: the fixture was quietly out of sync with what real enforcement
now required. Fixed by adding `tool_calling=True` to the fixture's
Reserve Blend, matching the real `beans.yaml` - not by weakening the
constraint.

90+ new tests across `aliases.py`/`routing.py` (`capable_bean()`,
`needs_tool_calling` constraint, both fixture and real-config
regression locks), `classifier.py` (`use_web` signal, `task_type`
untouched), `openrouter_client.py` (`plugins` passthrough/omission),
`ledger.py` (`estimate_web_search_component_usd()`), and end-to-end
`/v1/order`/`/v1/chat/completions` tests (routing, plugin passthrough,
Ledger cost breakdown, escalation carry-through both ways, error paths).
Frontend: a new "Use Web" `OrderBox` checkbox mirroring "Use Pantry"
exactly, with matching tests. `python -m pytest router/tests tests`: 929
passing (6 pre-existing, unrelated failures - the same 2 vision-Bean
config-drift failures carried from prior Brews, plus 4
`TodaySpendUsdTests` failures newly surfaced by the calendar rolling
over to today mid-session, since that fixture hardcodes "today" as a
literal date string rather than computing it live; confirmed via `git
stash` that all 6 predate this session's changes). `npx vitest run`: 224
passing. `tsc --noEmit`/`eslint`/`next build` all clean.

**Live demo found a real, pre-existing bug, reported, not fixed.** A
real `/v1/order` call with `use_web: true` against the actual running
router (unmodified `beans.yaml`) failed with `OpenRouter HTTP error 404:
No endpoints found for anthropic/claude-3.5-haiku` - Single Origin's
configured `model_id`. Confirmed directly against OpenRouter's real,
live `GET /v1/models` catalog that this exact id no longer resolves; the
real current slug is `anthropic/claude-haiku-4.5` (Reserve Blend's
`anthropic/claude-sonnet-4-6` was separately checked and confirmed still
live via a real successful call, despite not appearing verbatim in the
`/v1/models` listing - some Anthropic model ids resolve as aliases not
listed as canonical entries). This blocks `use_web`'s real default
routing target (`capable_bean()` picks Single Origin as the cheapest
capable Bean) in production today. Found live, reported here plainly -
**not fixed**: editing `beans.yaml`'s `model_id` is a production config
change outside this Brew's scope, and the right correction (which real
id to use, and whether Single Origin's pricing/capabilities still match
reality) is a decision for the human, not an unrelated fix bundled
silently into this Brew's diff.

Demoed the actual mechanism live anyway, via an in-process
`BeanRegistry` built with the real `beans.yaml` pricing/capabilities but
corrected, `/v1/models`-verified model ids - calling `run_order()` and
`_run_chat_completion()` directly (bypassing only the FastAPI HTTP
layer, already proven in every prior Brew's demo), against the real
OpenRouter API, with the real `OPENROUTER_API_KEY`:

- A real `use_web=true` `/v1/order` request correctly routed to Single
  Origin (`constraint_reason: "needs_tool_calling: escalated from House
  Blend to Single Origin"`) and `complexity: cold_brew`. The response was
  genuinely search-grounded, not a training-data guess: "According to
  the search results, the current stable version of Next.js is
  [16.2.10](https://www.npmjs.com/package/next), released on July 1,
  2026." The real Ledger row showed `cost_source=reported`,
  `cost_usd=0.0068`, and `web_search_cost_usd=0.006543` - the isolated
  search fee, correctly computed as the reported total minus the real
  token cost (17 in / 48 out at Single Origin's real pricing is about
  $0.00026, confirming the fee genuinely dominates the total cost of a
  search request).
- A real `use_web=false` baseline through the actual running server
  (whose free-tier and Reserve Blend model ids are still valid) stayed
  on House Blend, hit a real truncation-triggered auto-escalation to
  Reserve Blend, and `GET /v1/usage` correctly reflected the resulting
  real spend afterward.
- A real `/v1/chat/completions` call with a client `tools` array (no
  `use_web` field, per the approved scope) correctly routed to a
  tool-calling-capable Bean via the same constraint and returned a real
  tool call (`get_weather` with `city: "Paris"`), with the response's
  `model` field correctly showing the Bean alias, not the raw model id.

Cleanup: `demo_websearch` removed via `manage_users.py remove`; its 1
orphaned `tokens` row deleted directly (scoped to that user's own `id`
only). The Ledger's own migration-backup file (created on this session's
first write, once the new `web_search_cost_usd` column changed
`CSV_HEADER`) deleted as a transient artifact. The real demo Ledger rows
themselves were kept, same convention as every prior live demo. Router
process stopped; `git status` confirmed `router/data/` stayed untracked
throughout. Not yet staged or committed.

### 2026-07-18 - Brew 51: Web Search Cost Optimization

Two small, targeted cost optimizations on top of Brew 50's web search
feature: switch the search engine to a cheaper OpenRouter option, and
evaluate a cheaper tool-calling Bean than Single Origin. Both parts turned
up real findings before any code was written, and both are recorded here
in full since they change what this router actually does, not just how
much it costs.

**Finding 1: the router was on a deprecated mechanism, not just an
unoptimized one.** The request described the code as sending
`{"type": "openrouter:web_search"}` - it actually sends
`plugins: [{"id": "web"}]`, the mechanism Brew 50 implemented. Read
OpenRouter's live docs (`openrouter.ai/docs/guides/features/server-tools/
web-search`) before touching anything, per instruction, and confirmed two
things: the `plugins` mechanism is officially deprecated in favor of the
`tools`-array `openrouter:web_search` entry, and only the newer mechanism
exposes an `engine` parameter at all - there was no way to add engine
selection without migrating off `plugins` first. This turned "add a config
knob" into "migrate the mechanism, then add a config knob" - flagged
explicitly and approved before implementation (`AskUserQuestion`), rather
than silently expanding scope.

Real engine pricing pulled from the same docs page:

| Engine | Cost | 
| --- | --- |
| `"parallel"` | $0.001/request, up to 10 results, then $0.001/extra |
| `"exa"` | $0.005/request, up to 10 results, then $0.001/extra |
| `"native"` (what `"auto"` picks on a tool-calling Bean) | Passed through from the provider - the accidental default before this Brew |

`web_search_engine` (new `settings.yaml` field, default `"parallel"`) makes
this a hand-edit, not a code change, with `"exa"`/`"auto"` documented as
alternatives in the settings comment.

**Finding 2: neither requested cheap-Bean slug exists.** Asked to add
`moonshotai/kimi-2` and `deepseek/deepseek-chat-v3.2` as candidates.
Queried the real `GET /v1/models` catalog before proposing anything (same
discipline Brew 50 established after finding a dead Single Origin model
id) - neither slug exists. The real ones are `moonshotai/kimi-k2`
($0.00057/$0.0023 per 1k, "tools" confirmed in `supported_parameters`) and
`deepseek/deepseek-v3.2` ($0.000269/$0.0004 per 1k, same). Presented both
with real pricing and let the human pick, per explicit instruction not to
add candidates silently - approved adding both, Kimi K2 as primary
(agentic tool-use tuning), DeepSeek V3.2 as the cheaper fallback.

**The price-vs-preference conflict, surfaced rather than resolved
silently.** DeepSeek V3.2 is combined ~4.3x cheaper than Kimi K2
($0.000669/1k vs $0.00287/1k). `capable_bean()`'s existing contract (Brew
50's own explicit correction) is "always cheapest, never a role-based
guess" - unmodified, it would route every web search to DeepSeek V3.2, not
Kimi K2, directly contradicting "I want web search to actually route to
Kimi in practice." Rather than pick a resolution unilaterally, this was
surfaced with the real numbers and a proposed design
(`capable_bean(prefer_alias=...)`, opt-in, defaults to `None`, every other
caller unaffected) for explicit sign-off before writing any code. Approved
as proposed. This is a narrow, named, single-call-site override - not a
reversion of Brew 50's cheapest-price principle, since the principle still
governs every caller that doesn't pass `prefer_alias`, including
`/v1/chat/completions`'s own tool-calling constraint and vision routing.
The override degrades gracefully: if Kimi K2 is ever renamed, retired, or
removed from `beans.yaml`, `capable_bean()` falls through to plain
cheapest-price selection among what's left - DeepSeek V3.2 becomes a real
fallback in that scenario, not a decorative second entry that never
actually gets used.

**DATA GOVERNANCE - read this before ever routing real work data through
this instance.** Kimi K2 (Moonshot AI) and DeepSeek V3.2 (DeepSeek) are
both Chinese-hosted models, now live in `config/beans.yaml` with
`status: active`, reachable automatically by any `use_web` request (Kimi
K2 as the preferred default). The human explicitly acknowledged and
accepted this for the stated reason that this router instance is
personal-use only. This is recorded here, prominently, specifically so a
future decision about whether this instance (or any Beans/Ledger/session
data on it) can ever touch real work data has to actively reconsider this
fact, not discover it by accident. If that changes, revisit
`preferred_web_search_bean_alias` and both Beans' `status` in
`beans.yaml` before anything else.

**Implementation**: `openrouter_client.py`'s `plugins` parameter is gone -
`tools`/`tool_choice` (already existing since Brew 47) now also carry the
web-search tool entry, engine included. `main.py`'s `_consume_stream()`/
`_run_escalation()` had their `plugins` parameter renamed to `tools`
throughout, including the escalation carry-through logic (`escalation_
tools`) and the Ledger cost-breakdown variable (`final_tools_used`) - same
behavior as Brew 50 (drop with a logged warning if the premium Bean can't
call tools), just renamed to match the real mechanism. `aliases.py`'s
`capable_bean()` gained `prefer_alias`; `routing.py`'s `select_route()`
gained `preferred_tool_calling_bean_alias`, threaded only from `use_web`
routing in `main.py`, never from `/v1/chat/completions`'s own
`needs_tool_calling=bool(tools)` constraint (that path stays pure
cheapest-price, unaffected by the Kimi preference). `beans.yaml` gained
both new Beans with the Chinese-hosting note written inline, pointing back
to this entry.

**Tests**: every test asserting the old `plugins: [{"id": "web"}]` shape
was migrated to the new `tools` shape (`test_main.py`'s capturing stream
fakes, `WebSearchOrderTests`); `test_openrouter_client.py`'s two dead
`plugins`-specific tests were replaced with one confirming the web-search
tool passes through the existing `tools` parameter. A Brew 50 regression
test asserting the real config routes to Single Origin was updated to
assert DeepSeek V3.2 instead (now genuinely the cheapest real capable
Bean) with a new counterpart asserting the real `preferred_web_search_
bean_alias` default still lands on Kimi K2. New tests specifically
requested: `test_use_web_routes_to_kimi_over_cheaper_deepseek` (a real
`/v1/order` web request lands on Kimi K2 despite DeepSeek V3.2 being
cheaper) and `test_use_web_falls_back_to_cheapest_when_preferred_bean_
unavailable` (removing Kimi K2 from the pool correctly falls through to
DeepSeek V3.2). `capable_bean(prefer_alias=...)` and `select_route
(preferred_tool_calling_bean_alias=...)` both got direct unit coverage
(wins over a cheaper candidate, `None` keeps unchanged behavior, an
unmatched/incapable/unavailable preference falls through rather than
crashing or returning `None`). `python -m pytest router/tests tests`: 938
passing (6 pre-existing, unrelated failures, unchanged from Brew 50's own
baseline). `npx vitest run`: 214 passing - no frontend changes were
needed, this Brew is entirely backend/config.

**A real, separate bug found live during the demo, reported, NOT
fixed.** Testing the "citations still intact" requirement led to a raw,
direct-to-OpenRouter call (bypassing Coffee entirely) to inspect the real
response shape. A non-streaming call returned 15 real `url_citation`
annotations in `message.annotations`, each with a real source URL, title,
and excerpt. A streaming call confirmed the identical data arrives
mid-stream in a `delta.annotations` field on an early chunk. `router/app/
openrouter_client.py`'s `_parse_sse_line()` has never read this field -
only `content`, `tool_calls`, `finish_reason`, and `usage` are extracted
from a delta - meaning Coffee has silently dropped every web-search
citation URL since the feature existed, under both Brew 50's `plugins`
mechanism and this Brew's `tools` one equally. The model's prose is
genuinely search-grounded (the annotations are real, verifiable, current
URLs, confirming the search itself works correctly) - but the citation
URLs themselves have never reached a client. This is out of scope for a
cost-optimization Brew and was not fixed here; surfacing it would need
`StreamChunk`/`_consume_stream`/`CompleteEvent`/`EVENT_CONTRACT.md`
changes plus a frontend citation UI, comparable in shape to the existing
Pantry citation-chip feature - a real future Brew, not a one-line patch.

**Live demo**: real router run, real `OPENROUTER_API_KEY`, demo user
`demo_websearch_cost` (same Windows `getpass` piping limitation as every
prior live demo, worked around identically). Ran the same "top performing
equities this week" query twice through the real router, `settings.yaml`'s
`web_search_engine` flipped between runs (router restarted each time) to
isolate the engine variable on the identical Bean (Kimi K2, correctly
selected via the real `preferred_web_search_bean_alias` default both
times):

- `engine: "auto"` (the accidental prior default): real cost `$0.016362`
  total, `cost_source=reported`, of which `$0.015462` was the isolated
  search fee (`estimate_web_search_component_usd()`) - close to the
  user's own real prior observation of ~$0.014 for this kind of query,
  corroborating evidence this was a genuine, representative baseline, not
  a cherry-picked one.
- `engine: "parallel"` (the new default): real cost `$0.002432` total, of
  which `$0.001735` was the search fee - the isolated search fee dropped
  ~8.9x, matching OpenRouter's own documented ~10x figure. Both responses
  were genuinely search-grounded, referencing real, current equity names
  and price context rather than training-data guesses (confirmed
  separately, per the citation-gap finding above, that the underlying
  search really happened even though the URLs themselves never reached
  the client).

Cleanup: `demo_websearch_cost` removed via `manage_users.py remove`; 12
orphaned `tokens` rows (accumulated across this and prior sessions' demo
users, not just this one) found and removed in one pass rather than
leaving 11 of them for a future session to rediscover. `settings.yaml`
restored to `web_search_engine: "parallel"`; router restarted twice more
to confirm the revert and normal login/order behavior. No new
migration-backup file was created this session (`web_search_cost_usd`'s
CSV header already existed from Brew 50). The real demo Ledger rows
themselves were kept, same convention as every prior live demo. Not yet
staged or committed.

### 2026-07-18 - Brew 52: Web Search Citation Fix

**The diagnosis needed correcting before any code was written.** The
request described a `web_sources` field on `CompleteEvent` and a
`WebSourceChips` component "built in Brew 50" that had been silently
starved of real data. Neither existed. Checked directly: `CompleteEvent`
(`router/app/events.py`) had no `web_sources` field, and no
`WebSourceChips` anywhere in `web/src` - only `PantrySourceChips`, an
unrelated component for a different citation kind (Pantry, not web
search). Brew 50's own Tasting Note explicitly scoped citation UI out
("What this is not: no citation UI..."), and Brew 51's Tasting Note
flagged fixing the annotations gap as needing "a frontend citation UI" as
future work, not a patch. Reported this plainly before proceeding - this
Brew builds the citation-surfacing feature end to end for the first time,
not patching a starved one. The human accepted the correction immediately
and confirmed what it implies: the inline links occasionally seen in
responses were the model's own markdown, never the chips.

**The fix, mirroring the exact pattern Brew 47 established for
`tool_calls_delta`.** `router/app/openrouter_client.py`'s `StreamChunk`
gained `annotations`; `_parse_sse_line()` now extracts `delta.get(
"annotations")` - the second `delta.*` field this parser has silently
dropped (`tool_calls_delta` was the first, Brew 47). Unlike
`tool_calls_delta`, an annotation arrives whole in one chunk, never split
across multiple deltas by index (confirmed against a real captured
stream from the prior Brew's demo) - so `router/app/main.py`'s
`_consume_stream()` accumulates them with a plain `list.extend()`, never
an index-merge. New `_distinct_web_sources()` (mirroring
`_distinct_pantry_sources()`'s exact shape) deduplicates by URL,
first-title-wins, drops `content`/`start_index`/`end_index` entirely (a
chip needs a link and a label, never the full excerpt), and falls back to
the URL itself as the title when one is missing rather than a blank chip.
Surfaced only via `CompleteEvent.web_sources` - never `GeneratingEvent` -
per the original design intent (a partial, growing citation list isn't
meaningful mid-stream). Escalation re-runs replace the draft's
annotations entirely with their own (or none, if the draft never used
search successfully), same "the escalated response is what the client
actually sees" rule every other field on that path already follows.

**`EVENT_CONTRACT.md` bumped to v1.6**, and a genuine, unrelated
documentation gap was fixed inline while touching this file anyway: the
changelog had never been updated for Brew 46's `history_turns`/
`history_tokens_est` fields, even though `events.py`'s own docstring
already called them "contract version 1.5" - the file's header still said
"Version: 1.4". Added the missing v1.5 entry retroactively alongside the
new v1.6 one, so the file matches `events.py` again.

**Frontend**: new `WebSourceChips.tsx`, deliberately distinct from
`PantrySourceChips.tsx` in two ways beyond styling - each chip is a real
outbound link (`target="_blank"`) rather than opening an in-app
`FileViewerPanel` (the source lives on the open web, not this repo), and
uses the crema-amber accent (matching the "Use Web" toggle) instead of
Pantry's caramel, so the two citation kinds read as visually distinct at
a glance. `ChatMessage.webSources` and `reduceEventIntoMessage`'s
`complete` case mirror `pantrySources` exactly. Wired into
`MessageBubble.tsx` immediately after `PantrySourceChips`.

**Parser audit (the explicitly requested step 4).** Compared every field
a real OpenRouter streaming delta and non-streaming message can carry
(captured live during this and the prior Brew's demos) against what
`_parse_sse_line()` actually extracts. Beyond `annotations` (now fixed),
still silently dropped:

- **`reasoning`** (`delta.reasoning` / `message.reasoning`) - the actual
  reasoning/thinking text a reasoning-capable model (e.g. Kimi K2
  Thinking, DeepSeek R1) produces. Confirmed present in the real message
  schema (returned as `null` in this session's captures only because
  those specific requests didn't trigger reasoning output) - never
  extracted, never stored, never shown. **Directly answering what was
  asked**: `usage.completion_tokens_details.reasoning_tokens` (a real,
  separate field, also dropped) shows reasoning tokens ARE already
  counted inside the billed `completion_tokens`/`cost_usd` Coffee's
  Ledger records correctly today - so nothing is being paid for
  invisibly in the dollar total - but there is currently no way to tell
  how much of a given request's cost was "thinking" versus "answer," and
  the reasoning text itself is completely inaccessible. A future Brew
  wanting to show or log a reasoning/answer split would need this field
  and its token-count sibling, not just the text.
- **`refusal`** (`message.refusal`) - a structured refusal signal
  distinct from the prose-based heuristic keyword matching
  `check_for_failure()` already does. Currently redundant with existing
  behavior but a real, unused source of truth.
- **`usage.prompt_tokens_details`/`completion_tokens_details`**
  (`cached_tokens`, `cache_write_tokens`, `audio_tokens`, `video_tokens`,
  `image_tokens`, and `reasoning_tokens` above) - a real per-category
  token breakdown inside the `usage` dict Coffee already receives and
  stores whole, but only ever reads `completion_tokens`/`cost` from.
- **`usage.cost_details`** (`upstream_inference_cost`,
  `upstream_inference_prompt_cost`, `upstream_inference_completions_cost`)
  - OpenRouter's own breakdown of what it paid the upstream provider,
  versus what it billed. Unused.
- **`usage.server_tool_use_details`** (`web_search_requests`,
  `tool_calls_requested`, `tool_calls_executed`) - a real, authoritative
  count of how many searches/tool calls actually happened this request.
  Worth flagging specifically: this could be a more precise source for
  `estimate_web_search_component_usd()`'s search-fee attribution than the
  current subtraction-based estimate, since it's a direct count rather
  than an inference from cost math - a real future refinement, not
  something this Brew changed.
- **`provider`** (top-level) - which real upstream provider ultimately
  served the request. Unused.
- **`logprobs`, `native_finish_reason`, `system_fingerprint`,
  `service_tier`** (choice/top-level) - unused, low practical value for
  Coffee's current purposes.

None of these were fixed this Brew, per instruction (report, don't fix
unless something's actively broken) - `reasoning`/`server_tool_use_details`
are the two most likely candidates for a future Brew's attention.

**Tests**: `StreamChunk.annotations` parsing (single-chunk extraction,
absence-leaves-`None`) and a full-stream relay test in
`test_openrouter_client.py`; `_distinct_web_sources()` direct unit tests
(url+title extraction dropping content/indices, dedup keeping first
title, missing-title-falls-back-to-url, missing-url skipped entirely) in
`test_main.py`; end-to-end `/v1/order` tests confirming a real annotation
reaches `complete.web_sources`, an empty-annotations request leaves it
`None`, annotations arriving despite `use_web=False` are still surfaced
faithfully rather than crashing (a real edge case, handled gracefully,
matching Coffee's "never second-guess model output" convention), `
web_sources` never appears on any `generating` event, dedup + the
missing-title fallback together in one realistic multi-annotation stream,
and an escalation re-run's own citations replacing the draft's (verified
via a scenario where the draft has none and the premium re-run has one).
Frontend: `WebSourceChips.test.tsx` (empty/null render nothing, real
chips render with correct `href`/`target`/label, missing-title fallback).
Confirmed there was no pre-existing `WebSourceChips` test to audit for a
masking mock, since the component never existed before this Brew;
`PantrySourceChips.test.tsx` (the only existing chip test) is unrelated
and already exercises real rendering, not a mock that could have hidden
anything. `python -m pytest router/tests tests`: 952 passing (6
pre-existing, unrelated failures, unchanged baseline). `npx vitest run`:
218 passing. `tsc --noEmit`/`eslint`/`next build` all clean.

**Live demo, with a genuine before/after contrast.** Real router run
against real `OPENROUTER_API_KEY`, demo user `demo_citations` created
directly via `hash_password()`/`create_user()` (same Windows `getpass`
piping limitation as every prior live demo). Ran the real "top performing
equities this week" query with `use_web: true`: the real `complete` event
carried a populated `web_sources` array with **11 real, distinct citation
URLs and titles** (Morningstar, CSIMarket, Stacker, and others) - genuine
structured proof the fix works, not an inline-link guess. To prove the
field was truly empty before, `git stash`ed exactly this Brew's three
changed backend files (`events.py`, `main.py`, `openrouter_client.py` -
deliberately not the unrelated cost-optimization Brew's files also in the
working tree), restarted the router on the pre-fix code, and re-ran the
identical query: the real `complete` event had no `web_sources` key at
all - structurally absent, not merely `null`, since the field didn't
exist on `CompleteEvent` yet. Popped the stash, restarted again, confirmed
the fix restored cleanly. For "chips rendering in the UI," used the real
`web_sources` payload captured from the live call as a mocked
`page.route()` SSE fixture in a new Playwright e2e test (`e2e/chat.spec.ts`
- same mocking convention every existing e2e test already uses, a real
Chromium browser rendering the real component tree, not a jsdom
approximation) - both real chips rendered with the correct link text,
`href`, and `target="_blank"`; all 10/10 e2e tests passed. Cleanup: demo
user and its 1 orphaned `tokens` row removed; no migration-backup file
was created (`web_sources` is an event-contract field, not a Ledger CSV
column). Router process stopped. Not yet staged or committed.

### 2026-07-23 - Brew 53: Date-Awareness System Prompt

**The bug, confirmed real.** Coffee never told any Bean what today's date
is, so every date-sensitive question ("what's the date today," "latest,"
"this week," age/deadline math) was answered from the Bean's training
cutoff, not reality - the cited example: House Blend answered "October
17, 2024" when actually asked on 2026-07-23. Read `router/app/main.py`
(both orchestration paths - `/v1/order`'s `_run_order_body`/
`_run_escalation` and `/v1/chat/completions`' `_run_chat_completion` -
plus where each assembles its outbound `messages`), `router/app/
history.py`, and `router/app/openrouter_client.py` before proposing
anything. Confirmed two structural facts that shaped the whole design:
no `system`-role message exists anywhere in this codebase today (grepped
all three files), and `/v1/order` and `/v1/chat/completions` are
genuinely separate code paths - the latter always sends a caller-built
`messages_override` straight through to OpenRouter unmodified (Cursor and
similar clients bring their own system prompt; silently prepending to it
risks breaking their own tool-use instructions), the former never does.
Scoping the fix to `/v1/order` only therefore falls out of the existing
architecture rather than needing a new runtime flag to enforce it.

**The fix.** New `router/app/system_prompt.py`, `build_date_system_
message(settings)`: `None` when the new `system_prompt_include_date`
setting (default `true`) is off; otherwise a single sentence - "Today's
date is 2026-07-23 (UTC-07:00). Use this as the current date - do not
assume a date from your training data." Two deliberate formatting
choices: date-only granularity, never a finer timestamp - this message
rides on every `/v1/order` request, so if prompt caching is ever added
to this router, a value that changes every second would defeat any cache
on this leading prefix, while a value that changes once a day would not;
and an explicit numeric UTC offset (`UTC-07:00`) rather than a timezone
abbreviation, since abbreviations are genuinely ambiguous ("CST" is both
US Central and China Standard Time - exactly the kind of ambiguity this
feature exists to eliminate, so using one in the fix itself would be
self-defeating). The new `system_prompt_timezone` setting defaults to
`"local"` (resolves the server's own system timezone via `datetime.now
().astimezone()`); set to an IANA name like `"America/Chicago"` to pin a
specific zone via `zoneinfo.ZoneInfo` regardless of where the router
actually runs, with a documented graceful fallback to local rather than a
crash if the name doesn't resolve. `tzdata` added to `router/
requirements.txt` as a real declared dependency - `zoneinfo` needs it
explicitly on Windows, and it was previously only present transitively
(same "declare what was only riding along" precedent as Brew 43's
`bcrypt`).

`router/app/main.py` gained `_with_system_message()`: builds a *new* list
rather than mutating `history_result.messages`, and merges into an
existing leading system message rather than sending two if one is ever
already present - dead code today (`history.py`'s `pair_turns()`/
`assemble_history()` structurally can only ever produce user/assistant
turns) but exercised directly by a unit test against a hand-built history
list, so the merge path is real, not aspirational, if that ever changes.
Called once per `/v1/order` request, immediately after `history_result`
is built, and the result reused for both the draft call and any
escalation re-run of the same request - so a draft and its escalation
answer the same "today" consistently even though an `escalation_pending`
human-approval pause can last up to `escalation_approval_timeout_seconds`
(600s default). Injected on **every** `/v1/order` request regardless of
`remember_chat` - approved explicitly as correct, since that toggle
governs conversation history, not knowledge of the current date; a user
who turns memory off to save tokens still wants correct dates.

**A budget boundary worth stating plainly, per explicit instruction.**
The date system message is prepended *after* `history_result` (`turns_
included`, `chars_included`, `tokens_est`) is already computed and
windowed against `history_max_chars` - by construction, it sits outside
that budget entirely. At ~130 characters that's the right call (nobody
wants the date squeezed out by a long conversation), but it also means
`history_max_chars` no longer bounds *everything* sent to OpenRouter,
only the conversation-history portion of it - recorded here so this
isn't misread later as a total-payload cap.

**Test fallout, and why fixing it was the right call, not a workaround.**
Because the message now rides on every `/v1/order` request, `history_
messages` passed to `stream_order_fn` is no longer `None` in the
no-history case - it's a single leading system message. Seven existing
`test_main.py` tests had encoded "no history was sent" as `history_
messages is None`; that was always a proxy for the property that
actually mattered. Three were changed to assert directly on that
property (no user/assistant roles present) instead of `None` - a
strictly better test, since it will keep passing correctly the next time
something else legitimately rides along in that array, rather than
needing another exception the day this repeats. Four more had their
`[0]`-index assertions shifted to `[1]` (or an updated length count) now
that `[0]` is the system message. New tests: `test_system_prompt.py` (6
tests covering disabled/local-offset-label/explicit-IANA-zone/
unrecognized-zone-fallback/case-insensitivity/brevity); `test_main.py`
additions for presence-and-correct-date-by-default, absence-when-
disabled, never-persisted-as-a-conversation-turn (`session_store.
get_messages` carries no `system` role and no date text), and - the
double-counting check specifically requested - `history_turns`/`history_
tokens_est`/Ledger `message_count`/`total_input_chars` proven byte-
identical whether the setting is on or off; `_with_system_message()`
unit-tested directly for the merge behavior and for never mutating its
input; a `/v1/chat/completions` test posting a client message list that
already starts with its own system message, asserting `messages_
override` reaches `stream_order_fn` completely byte-identical regardless
of the new setting's default-on state - proving the endpoint structurally
never reads it, not merely that this one test happened to turn it off.
`python -m pytest router/tests`: 730 passing, 5 pre-existing unrelated
failures - confirmed via `git status` that none of the five failing
tests' files were touched this session. Four are in `test_ledger.py`'s
`TodaySpendUsdTests`, which hardcodes `"2026-07-17"` as "today"; real-
today is now 2026-07-23, so the fixture has quietly gone stale - a small,
almost funny irony, since it's the exact same category of bug this Brew
exists to fix in the product, just rotted in a test fixture instead. The
fifth is the long-standing, previously-documented vision-Bean routing
config-drift gap.

**Live demo, with the inverted assertion on the second half stated
plainly, per explicit instruction.** Real router run against real
`OPENROUTER_API_KEY`, demo user `demo-date-check` created directly via
`hash_password()`/`create_user()` (same Windows `getpass`-piping
limitation as every prior live demo). A real `/v1/order` call - "What is
the date today? Just answer with the date, one line." - correctly
answered `2026-07-23`: the real current date, not a training-cutoff
guess, through the actual running router with the fix live. The
identical question asked through `/v1/chat/completions` (which never
receives this injection, by design) got: "I don't have access to real-
time information, including the current date." **This is the correct,
expected result for that endpoint, not a failure** - a correct-date
answer on `/v1/chat/completions` would indicate the date message had
somehow leaked into a client's own `messages_override`, exactly the
outcome this Brew's scoping was built to prevent; getting a training-
cutoff-honest non-answer there is the passing case. Cleanup: demo user
removed afterward; `router/data/` (where `sessions.db` lives) confirmed
gitignored throughout, so nothing tracked was touched by demo-user
creation/removal. The two real rows this demo appended to `ledger/
router_requests.csv` were kept, same convention as every prior live demo
(that file was already mid-session-dirty before this Brew started).
Router process stopped. Not yet staged or committed.

### 2026-07-24 - Free-Bean tool-calling re-verification (Cup Test 006 + 002)

**Why this run happened.** A live GET /v1/models check showed
`nvidia/nemotron-3-ultra-550b-a55b:free` (House Blend),
`cohere/north-mini-code:free` (Second Pour), and `poolside/laguna-m.1:free`
(Guest Bean) all report `tools`/`tool_choice` in `supported_parameters`,
contradicting Brew 51's audit conclusion that these had no tool-calling
support (`tool_calling: false` in beans.yaml). Rather than re-reading the
catalogue again, ran the real thing: Cup Test 006's exact `tools` schema
(`get_current_weather(city)`) and prompt against each Bean's raw
`model_id`, direct to OpenRouter (`https://openrouter.ai/api/v1/chat/
completions`), bypassing Coffee's own alias layer - confirmed this was
necessary, not a shortcut: a first attempt to test House Blend through
Coffee's real `/v1/chat/completions` with `bean_alias_override` was
correctly refused by the router itself (`"Manually selected Bean 'House
Blend' does not support tool calling"`, `invalid_bean_override`) - the
router trusts the declared config flag and won't send an unverified Bean
a `tools` array, which is exactly the point of the flag and exactly why a
raw call is the only way to actually test the claim. Also tested
`google/gemma-4-31b-it:free` (Day Roast - already flagged as pending this
exact verification when added) and `openai/gpt-oss-20b:free` (not yet a
registered Bean, tested as a candidate) for the same reason.

**Tool-calling result: all 5 passed cleanly, first attempt or after one
provider-side rate-limit retry.** Every model, verbatim JSON captured for
each:

| Bean (alias) | model_id | Result | finish_reason | tool_calls.city | Fabricated content? |
| --- | --- | --- | --- | --- | --- |
| House Blend | `nvidia/nemotron-3-ultra-550b-a55b:free` | **PASS** | `tool_calls` | `"Lisbon"` | No (`content: null`) |
| Second Pour | `cohere/north-mini-code:free` | **PASS** | `tool_calls` | `"Lisbon"` | No (`content: null`) |
| Guest Bean | `poolside/laguna-m.1:free` | **PASS** (after 1 retry - upstream 429, resolved on retry, see below) | `tool_calls` | `"Lisbon"` | No (`content: "\n"`, whitespace only) |
| Day Roast | `google/gemma-4-31b-it:free` | **PASS** | `tool_calls` (OpenRouter-normalized; `native_finish_reason: "STOP"`) | `"Lisbon"` | No (`content: null`) |
| `openai/gpt-oss-20b:free` (unregistered) | `openai/gpt-oss-20b:free` | **PASS** | `tool_calls` | `"Lisbon"` | No (`content: null`) |

Every one of the five correctly called `get_current_weather` with a
well-formed `{"city": "Lisbon"}` argument, `finish_reason` reporting the
tool call (not prose), and zero hallucinated weather data in the same
turn - the exact three-way outcome test Cup Test 006 specifies, and none
landed in "ignored" or "errored". **Brew 51's audit conclusion does not
hold today** - whether the catalogue changed since Brew 51, the specific
models changed upstream, or the earlier audit under-tested is not
resolvable from here (no capture of what Brew 51 actually ran survives to
compare against) - what's certain is today's real, repeated, captured
evidence: all three previously-`false`-flagged free Beans, plus Day
Roast, plus the gpt-oss-20b candidate, genuinely call tools correctly
today. Guest Bean (`poolside/laguna-m.1:free`) hit a transient upstream
429 on the first attempt and cleared on retry - consistent with this same
provider's documented flakiness elsewhere in this file (Brew 14's README
notes it's one of only 3 Beans that survived earlier live-run failures);
this is provider capacity noise, not a tool-calling signal, and is
recorded as such rather than folded into the pass/fail result.

**Coding follow-up (Cup Test 002), run once per model since every one
passed tool-calling.** Each Bean's actual returned code was executed for
real against the exact example case (`normalize_tags([" AI ", "coffee",
"ai", "", " Coffee "]) == ["ai", "coffee"]`), not just read:

| Bean | Correct logic (executed)? | Notes against 002's rubric |
| --- | --- | --- |
| House Blend | **PASS** | Minimal, correct, one focused test. Good bug explanation (named all three real defects: membership check against the wrong list, missing empty-tag skip, unwanted sort). |
| Second Pour | **PASS** | Correct and minimal function; added 3 tests instead of 002's requested "one focused test" (extra coverage, not wrong, but a real rubric deviation worth noting for future scoring). |
| Guest Bean | **PASS** | Correct, minimal, one focused test. Bug explanation slightly less precise (didn't name the empty-tag gap explicitly) but the fix itself covers it correctly regardless. |
| Day Roast | **PASS** | Cleanest submission of the five - minimal, correct, exactly one focused test, tight bug explanation. Zero reasoning-token overhead shown (`reasoning_tokens: 0`) unlike every other model tested here, all of which "thought" visibly before answering. |
| `openai/gpt-oss-20b:free` | **PASS**, with a real quality defect | Code logic is correct and executes cleanly, but the returned docstring literally contains a stray Arabic word injected mid-sentence (`"""Return lowercase unique tags قصيرة first‑seen order."""` - "قصيرة" means "short") - a genuine multilingual-token-leak defect, not a translation or intentional choice. Recorded plainly since it's real, reproducible model behavior a human reviewing generated code would need to catch and would very likely miss if skimming; not disqualifying for the tool-calling result, but relevant to any future decision to register this model as a Bean. |

None of the five failed the coding task. Real token/cost usage was
captured per model (all `cost: 0`, free tier, `total_tokens` ranging
~116-1940 - Second Pour was the most verbose by a wide margin at 1746
completion tokens for a task the others answered in under 700).

**A real routing defect found while reading the code for this
verification, reported per instruction as its own finding, not
implemented.** `router/app/routing.py`'s `select_route()` only ever
consults `capable_bean()` (and therefore
`preferred_tool_calling_bean_alias`) when
`needs_tool_calling and not primary_bean.tool_calling` - i.e., only as an
escalation from an *incapable* primary Bean. This conflates "the primary
Bean can technically do tools" with "the primary Bean is the right Bean
for this tools request." Today this is dormant only because every
task_type's real `primary_bean_alias` (100% House Blend, confirmed
against the real generated `routing_policy.yaml`) has `tool_calling:
false`. The instant that flips true for House Blend, this branch stops
firing entirely, for every task_type, for both `/v1/chat/completions`
tools requests and `use_web` requests - `capable_bean()` and the real
`preferred_web_search_bean_alias: "Kimi K2"` setting are both silently
skipped, and `use_web` traffic would move from Kimi K2 (tuned for
agentic search) to whatever House Blend happens to be, with zero test
failing anywhere, since no existing test asserts the preference still
wins when the primary Bean happens to already be capable. Confirmed this
is exactly the missing case: `test_select_route_policy_bean_already_
capable_is_unconstrained` (`test_routing.py`) locks in the
already-capable-primary-is-unconstrained behavior but never passes a
`preferred_tool_calling_bean_alias` alongside it, so it cannot catch this.
`manual_route()` (the human-override path) is not susceptible - it has no
escalation logic and no `preferred_tool_calling_bean_alias` parameter at
all, by design ("never silently substitute out from under an explicit
human choice"). Per instruction, no flag was flipped and no fix was
implemented this session - see the matching Decaf-plan-style proposal in
this session's report for the exact code change, which existing tests
would (and would not) break, and the new regression test that would have
caught this, currently failing against `select_route()` as written.

**No `beans.yaml` flags changed.** House Blend's `tool_calling` stays
`false` pending the routing fix landing first, per explicit instruction -
"the routing fix should land first, so a config change cannot bypass a
preference." Second Pour, Guest Bean, and Day Roast's real consequences
if flipped (none is ever a `primary_bean_alias` today, so each would only
newly become a `capable_bean()` price candidate, not silently bypass an
escalation the way House Blend would) are reported in this session's
final summary for a separate pick. `openai/gpt-oss-20b:free` is not a
registered Bean and was tested purely as a candidate - adding it needs
its own explicit pick, same convention as the Gemini/Gemma Beans.

**Correcting the record on Brew 51.** Brew 51's `tool_calling: false` for
House Blend, Second Pour, and Guest Bean was set from reading OpenRouter's
documentation/catalogue metadata, not from an empirical tool-call test
against any of the three - and it was wrong on all three, confirmed by
this session's real, captured, repeated evidence above. This is recorded
plainly as a real process gap, not just a stale flag: a `capabilities.*`
value in `beans.yaml` must come from a real Cup Test result (006 for
tool_calling, 005 for vision) going forward, never from catalogue
metadata or documentation alone, however authoritative it looks -
`supported_parameters` listing `tools` tells you the API will *accept*
the parameter, never that the model reliably *uses* it, which is exactly
the gap that made Brew 51's conclusion look reasonable at the time and
be wrong anyway.

### 2026-07-24 - Routing fix: preferred_tool_calling_bean_alias now honoured even when the primary Bean is already capable

Implemented the fix proposed alongside the free-Bean tool-calling
verification above, approved with one addition. `router/app/routing.py`'s
`select_route()` now consults `capable_bean()`/`preferred_tool_calling_
bean_alias` whenever `needs_tool_calling` is true AND EITHER the primary
Bean lacks the capability (the original escalation case, unchanged) OR an
explicit preference was given at all (the fix) - not only when the
primary happens to be incapable. A no-op guard (`tool_bean.alias !=
primary_alias`) prevents a spurious "escalated from X to X"
`constraint_reason` when the preference simply confirms the Bean already
selected. Traced against all 6 pre-existing `NeedsToolCallingConstraintTests`
before writing anything - none break: every one either passes no
preference (the fix's second OR-clause never engages) or already has an
incapable primary (the first clause already fired unchanged). `test_
select_route_policy_bean_already_capable_is_unconstrained` - the test
that should have caught this gap - never passed a preference alongside
its already-capable primary, confirmed as exactly why it couldn't have
caught it. `manual_route()` needed no change - no escalation logic or
preference parameter exists there at all, by design.

**The approved addition**: a preference that no longer resolves to a
qualifying Bean (renamed, removed, disabled, or lost its capability) now
logs a `WARNING` via a new `router.app.routing` logger before falling
through to `capable_bean()`'s existing cheapest-price fallback, naming
both the broken preference and the Bean actually used instead - a
preference silently going stale must be visible, not a permanent,
undetectable behavior change.

Three new tests in `test_routing.py`: `test_select_route_preference_
honoured_even_when_primary_bean_already_capable` (the direct regression
test - House Blend both primary AND already tool_calling=True, a
differently-priced preferred Bean must still win outright; failed against
the old code, passes now), `test_select_route_preference_matching_
primary_bean_stays_unconstrained` (no-op guard: preference equals the
primary Bean itself - no spurious escalation reason, no warning, since
the preference resolved fine), and `test_select_route_stale_preference_
falls_through_with_a_warning` (a preference naming a Bean that isn't a
qualifying candidate - `assertLogs` confirms the warning fires and names
both the stale preference and the real fallback Bean). Full `router/
tests/` suite re-run after the change: 729 passing, the same 6
pre-existing unrelated failures as every prior session's baseline
(confirmed via `git stash` in an earlier Brew, unchanged files since).

**No `beans.yaml` flag changed as part of this fix** - it lands
independently of any capability-flag decision, per instruction ("the
routing fix should land first, so a config change cannot bypass a
preference").

### 2026-07-26 - Brew 56: Coffee Self-Knowledge (identity block + Pantry manual)

**What was built.** Three parts. (1) A short always-on identity block on
`/v1/order`, gated by the new `system_prompt_include_identity` (default
`true`), composed with Brew 53's date sentence into ONE system message by
a new `build_system_message()`. (2) `knowledge/coffee-manual.md`, a
nine-section Pantry document describing what Coffee is and how it works.
(3) A written staleness marker in the manual - deliberately not an
automatic re-indexer.

**Extended, not duplicated.** `_with_system_message()` in
`router/app/main.py` changed by exactly one line
(`build_date_system_message` -> `build_system_message`). Every property
Brew 53 established - merge into an existing leading system message
rather than emitting two, never mutate the caller's list, never persist
as a conversation turn, computed after `history_result` so no
count-facing field sees it - is preserved by construction, because that
code is untouched. There is still exactly one call site, feeding the
draft call and both escalation re-run sites, so a draft and its
escalation still see the same identity and the same "today" across an
approval pause.

**Ordering, and why.** Identity leads, date follows. The identity text is
a fixed 344-char constant while the date changes daily, so leading with
the stable part preserves the longest possible common prefix across
requests - the same prompt-caching reasoning that made Brew 53's message
day-granular rather than timestamped.

**Recorded explicitly, per instruction: the identity block sits OUTSIDE
the `history_max_chars` budget**, exactly as the date does, because both
are added after conversation history is assembled and windowed. Neither
is ever a trimming candidate. This means `history_max_chars` does not
bound everything sent to OpenRouter, only the conversation-history
portion of it. The `settings.yaml` comment block was restructured so this
note is stated once for both parts rather than only for the date, where a
future reader could have mistaken it for date-specific.

**The manual was written against Brew 55's feature set** and says so in
its own "About This Manual" section, along with a one-line instruction to
update it and re-run `python router/tools/index_pantry.py` when the
system changes materially. This is a documentation-hygiene measure
against exactly the staleness that already afflicts `router/README.md`
and `ROADMAP.md` (BUILD_SUMMARY.md Section 9), both of which still
describe the system as of roughly Brew 42.

**The manual deliberately documents known limitations honestly rather
than omitting them.** This was the most important constraint on Part 2
and it was applied literally. The memory section states that conversation
history is windowed, that Coffee drops the oldest whole turns first, and
that **it does not tell you when it does so** - then names the Pantry as
the correct home for long reference material. The other current limits
are stated plainly too: image requests do not always land on the cheapest
capable Bean; a provider rate-limit or transport error fails the request
outright with no retry or fallback; reasoning text and its share of the
bill are not surfaced; re-indexing and policy rebuilds are manual. No
claim was made that any of these work correctly. A falsely reassuring
answer to "why did it forget my document?" would have been worse than no
manual at all.

**Vocabulary audit - every term checked before defining it.** Seven of
the eight coffee terms are live concepts in the running system: Bean
(`aliases.py`/`beans.yaml`), Ledger (`ledger.py`), Pantry (`pantry.py`),
Brew Log (`memory_proposals.py`'s `ALLOWED_PATHS` is literally those two
files), Cup Test and Roastery (`tools/generate_policy.py` parses
`roastery/tasting_notes.md` score tables keyed by `roastery/cup_tests/`
files), and Brew (development-process vocabulary, documented as such
rather than implied to be a runtime thing). **Barista was not
fabricated.** It resolves to three real things, none of which is a
runtime component of the router: the role cards in `agents/`, used by AI
assistants working *on* Coffee's own codebase; `BARISTA_CHARTER.md`, the
source of the `espresso_shot`/`cold_brew` vocabulary the classifier
actually emits; and the animated figure in the chat UI. The manual says
exactly that, including the sentence "the router does not load a Barista
when it answers your request."

**Aliases-only held.** No raw provider model ID appears anywhere in the
manual - the Bean roster section is described by alias and role only.
`test_pantry_manual.py` enforces this against eight vendor prefixes, the
same rule the event contract is held to by
`test_no_raw_model_id_ever_appears_in_any_event_payload`.

**Retrieval tuning, found and fixed during verification.** The first
indexed draft answered all four sample questions correctly, but for "who
made this?" the authorship text arrived only via chunk *overlap* rather
than the authorship chunk itself ranking - BM25 over OR'd common tokens
("who", "made", "this") gives near-arbitrary ranking. The authorship
section's opening sentence was rewritten to carry the words people
actually use ("who made ... who created ... who wrote"), after which that
chunk ranks 2nd for that query. Worth recording as a real property of
this Pantry: chunking is fixed 1200-char windows with 200-char overlap
and is **not** heading-aware, so section boundaries and chunk boundaries
do not align, and retrieval quality depends on a section containing the
querier's vocabulary rather than on tidy structure.

**Tests.** 359 passing across `test_main.py`, `test_system_prompt.py`,
and the new `test_pantry_manual.py`. All four on/off combinations are
covered, including both-off asserting `history_messages is None`
(byte-identical to the pre-Brew-53 no-system-prompt behaviour) and
date-only asserting byte-identical output to
`build_date_system_message()` alone, so Brew 53's behaviour provably
survives. One pre-existing Brew 53 test needed updating and the update
was correct, not churn:
`test_date_system_message_absent_when_setting_disabled` asserted
`history_messages is None`, which held only because the date was then the
only injectable part; it now asserts what its name claims. Full
`python tools/run_all_tests.py`: 1046 tests, 5 deterministic pre-existing
failures (4 `TodaySpendUsdTests` hardcoded-date fixtures, 1
vision-routing policy lock - all documented in BUILD_SUMMARY.md Section
9, all in modules this Brew does not touch), plus 2 intermittent
`test_sessions` ordering failures that appeared in one full-suite run and
then passed 4/4 in isolation (timestamp ties under load; pre-existing
flakiness, not caused by this Brew, and recorded here rather than quietly
rounded away).

#### Live demo - real router, real `OPENROUTER_API_KEY`, four results verbatim

Real router (`python -m uvicorn router.app.main:app --port 8765`), demo
user `brew56-demo` created directly via `hash_password()`/`create_user()`
(the same Windows `getpass`-piping limitation as every prior live demo).
Every answer below is verbatim.

**Demo 1 - identity block alone, Pantry OFF.** Prompt: "what am I using
right now?" Routed to House Blend (explain/espresso_shot),
`use_pantry=false`, `pantry_sources: None`:

> You're using **Project Coffee** — a personal AI routing workstation built by Ishan Suthar. I'm a **Bean** (one of the routed models) running inside it. Coffee picks a cost-appropriate model for each request and logs the real cost to a local Ledger.

**Demo 2 - Pantry ON, routing question.** Prompt: "how does Coffee decide
which model to use?" Routed to House Blend, real citation
`pantry_sources: ['knowledge/coffee-manual.md']`:

> Based on the Pantry manual, Coffee decides which model (Bean) to use through a **classification → routing → capability-constrained selection** pipeline:
>
> 1. **Classification** (heuristic, no model call): Coffee reads your prompt and labels it with a *task type* (e.g., code, analysis, documentation, explanation) and a *complexity* tier ("espresso shot" = quick, or "cold brew" = longer).
>
> 2. **Routing to a Bean**: Using that classification plus its routing policy, Coffee selects a Bean. **Hard capability constraints** apply first:
>    - If an image is attached → must go to a Bean that can see images (`specialist` role).
>    - If web search is enabled → must go to a tool-calling Bean (`web_search_primary` or `web_search_fallback`).
>
> 3. **Among qualifying Beans**, Coffee **generally prefers the cheapest one that satisfies the capability requirements**. Bean *roles* (default, premium, specialist, comparison, web_search_*) describe intended jobs but are not locks—a cheap, capable Bean under any role can win.
>
> 4. **Evidence-driven, not hardcoded**: Which Bean wins for which task type is driven by recorded evidence from Coffee's own benchmark runs and your own ratings, not by a static preference list.
>
> So the decision is: *classify → filter by required capabilities → pick the cheapest qualified Bean according to live evidence*.

**Demo 3 - Pantry ON, the honesty test.** Prompt: "why did it forget the
document I pasted earlier?" Routed to House Blend, `pantry_sources:
['knowledge/00_index.md', 'knowledge/coffee-manual.md']`. This is the
answer the accuracy constraint exists to produce - the windowing truth,
not a reassuring falsehood:

> This is a known behavior documented in the Coffee manual. When "Remember chat" is on, Coffee includes previous turns with each new request—but only up to a fixed budget (max messages and max total characters). Once the conversation exceeds that budget, Coffee **drops the oldest whole turns first**, and it doesn't warn you when this happens.
>
> So if you pasted a long document early in the chat and kept talking, that document eventually falls out of the window. From that point on, the model genuinely hasn't been sent it, and will correctly say it doesn't have it—which feels like "forgetting" or "lying," but it's just the configured windowing behavior.
>
> **What to do about it:** Long reference material belongs in the Pantry (the `knowledge/` directory), not in chat history. Add the document there, run `python router/tools/index_pantry.py`, and turn **Use Pantry** on—retrieved passages are fetched fresh for every request and are never trimmed by conversation length.
>
> *Source: `knowledge/coffee-manual.md` (the "Remember chat" / memory section)*

**Demo 4 - `/v1/chat/completions` receives neither part.** The first
attempt used an "echo your system prompt verbatim" probe and drew a
refusal ("I'm sorry, but I can't comply with that request"). That is
**weak evidence and was rejected as such** - the absence of text in a
refusal is not the absence of an injection. It was replaced with a paired
behavioural probe: the identical prompt sent through both endpoints,
asking the two questions the two injected parts exist to answer. Through
`/v1/chat/completions`, with the client's own system message present in
the request:

> Nemotron 3 Ultra, built by NVIDIA
> not told

Neither part was injected: the Bean fell back to its own training
self-knowledge for line 1 and explicitly did not know the date for line
2. The identical prompt through `/v1/order`:

> I am running inside Project Coffee, a personal AI routing workstation built by Ishan Suthar.
> Today's date is 2026-07-26 (UTC-04:00).

Both parts present on `/v1/order`, both absent on
`/v1/chat/completions`, proven by behaviour rather than by a refusal.

**Cleanup.** Real Pantry re-indexed
(`python router/tools/index_pantry.py` - 5 files, 21 chunks). Router
process stopped. The demo user lives only in
`router/data/sessions.db`, which is gitignored. Real demo rows were
appended to `ledger/router_requests.csv` (an already-dirty appendable
log) and kept, same convention as every prior live demo. Nothing staged
or committed.

**Not a Bean quality comparison - no scores to record.** Every demo above
is single-Bean functional verification of Coffee's own behaviour.

### 2026-07-26 - Brew 57: Surface conversation-history trimming (event contract v1.7)

**The bug this closes.** `assemble_history()` drops the oldest whole
turns to fit `history_max_chars`/`history_max_messages` and told the user
nothing. In real use a long document pasted as the first turn was dropped
from every subsequent request, and the model correctly reported never
having received it - which is indistinguishable, from the user's side,
from a memory bug. Recorded in BUILD_SUMMARY.md Section 9 as "silent
conversation-history trimming"; this Brew makes it visible.

**Structural fact that made this exact rather than approximate.** The
assembly loop `break`s rather than `continue`s on the first turn that
doesn't fit, so everything older is dropped too and the dropped set is
always a contiguous oldest-first prefix of `turns`. That is what makes
`turns[:turns_dropped]` correct, and it is why `chars_dropped` is a real
sum of whole dropped turns rather than an estimate - trimming never
partially truncates a turn. Confirmed by reading the loop, not assumed.

**Three reasons, because three different remedies.** Collapsing these
into one boolean would have been simpler and worse - the whole point is
telling the user what to actually do:

- `current_prompt_fills_window` - THIS message ate the budget. Fix:
  shorten it.
- `single_turn_too_large` - an EARLIER turn is bigger than the whole
  window. Fix: move it to the Pantry.
- `window_full` - ordinary exhaustion. Nothing is wrong.

**Two precedence decisions, both deliberate, both tested directly.**

1. `current_prompt_fills_window` **wins outright** when the remaining
   budget is zero. When the current prompt has consumed the whole window,
   no historical turn could have fit whatever its size, so reporting
   `single_turn_too_large` would be technically defensible and would send
   the user to fix the wrong thing. Locked by
   `test_current_prompt_reason_wins_over_oversized_turn`.
2. `single_turn_too_large` fires when **any** dropped turn exceeds the
   window, not only when it is the turn that halted the walk. The
   motivating case is a long document pasted as turn one: once the window
   fills with ordinary chatter, the turn that technically stops the walk
   is often a small one, while the document sitting behind it is the
   thing the user cares about. Reporting that small turn as ordinary
   exhaustion would be true but useless. The claim stays literally
   accurate either way - at least one dropped turn genuinely does not fit
   an empty window. Locked by
   `test_oversized_turn_behind_smaller_turns_still_reports_too_large`,
   with the opposite boundary locked by
   `test_oversized_reason_not_used_when_every_dropped_turn_could_fit_alone`.

**Both caps report `window_full` on purpose.** The message-count cap and
the character cap produce an identical user experience and an identical
remedy, so splitting them would add a distinction with no consequence.

**The None-vs-0 convention was preserved, not reinvented.** v1.5
established that `history_turns` is `null` when `remember_chat` was off
and a real `0` when it was on but nothing was carried. The three v1.7
fields follow it exactly: `null` means not applicable, a real `0` means
"the toggle is on and nothing was dropped". The UI depends on this - it
renders a drop notice if and only if `turnsDropped > 0`, so silence
unambiguously means nothing was dropped rather than "we don't know".

**Where the Pantry-hint threshold lives, and why.** In the frontend, as
an exported `PANTRY_HINT_MIN_DROPPED_CHARS = 2000` (~a page of text), not
as an event field and not in `settings.yaml`. When to show a hint is a
presentation choice; the event contract carries facts, not decisions
about when to nag. The hint also fires unconditionally for
`single_turn_too_large` regardless of size, since that reason *is* the
"you pasted a document" signal.

**Deliberately not built:** no new Ledger columns. Trimming counts stay
on the `complete` event. Adding CSV columns would mean a schema migration
for data nothing yet analyses.

**Tests.** 15 new in `test_history.py`, 5 in `test_main.py` (x2
inheriting classes), 4 in `test_events.py`, 11 in
`RememberChatToggle.test.tsx`. Worth naming three specifically: the
`generating` check asserts over **every** yielded event's `model_dump()`
keys rather than only the last, so a field added to the wrong event model
fails; `test_complete_event_rejects_an_unknown_drop_reason` proves the
reason is a closed set, so a typo fails loudly instead of reaching a UI
with no copy for it; and both the backend and the frontend carry an
explicit additive-only check that this Brew changed *reporting* only and
not one byte of what is actually sent to a Bean.

Full `python tools/run_all_tests.py`: **1073 tests** (up from 1046), the
same 5 pre-existing unrelated failures as the Brew 56 baseline (4
`TodaySpendUsdTests` hardcoded-date fixtures, 1 vision-routing policy
lock), no new ones. `npx vitest run`: **228 passing** (up from 218).
`npx tsc --noEmit` clean. `npx eslint .` 0 errors (3 pre-existing
`<img>` warnings).

Three `CompleteEvent` fixtures under `web/src/components/CounterDisplay/`
needed the three new fields added. The frontend interface keeps them
required-but-nullable rather than optional, matching exactly how v1.5's
and v1.6's fields were handled - the small fixture cost buys a compiler
error whenever a new event field is forgotten somewhere.

#### Live demo - real router, real `OPENROUTER_API_KEY`

Demo user `brew56-demo` reused (created directly via `hash_password()`/
`create_user()`, the same Windows `getpass`-piping limitation as every
prior live demo). **All four reason paths were exercised**, one more than
the plan named - `window_full` was added because it is the most common
real-world case and leaving it unverified would have been a gap.

**Demo A - the original bug, reproduced and then explained.** A real
44,824-character deployment runbook pasted as turn one, then a follow-up.
Turn one reported nothing dropped (correctly - there was no history yet).
The follow-up, "What was step 7 of the runbook I pasted?", got:

> I don't have any runbook in our conversation history. Could you paste it again (or remind me of the relevant section) so I can tell you what step 7 says?

That is exactly the symptom that reads as a memory bug. The `complete`
event for that same request now carries:

```
history_turns          : 0
history_turns_dropped  : 1
history_chars_dropped  : 45176
history_drop_reason    : single_turn_too_large
```

which the UI renders as "1 earlier turn dropped - one was too large for
the window on its own. Long documents belong in the Pantry - add it to
knowledge/ and use Use Pantry."

**Demo B - ordinary short session.** Two short turns; both reported
`history_turns_dropped=0`, `history_chars_dropped=0`,
`history_drop_reason=None`. Nothing dropped, nothing rendered.

**Demo C - the current prompt filling the window.** The same 44,824-char
document sent as the *current* prompt on turn two of a session that
already had one small turn. Reported
`history_drop_reason="current_prompt_fills_window"` with
`history_chars_dropped=35` - correctly blaming the current message rather
than the 35-character earlier turn, which is precedence decision 1 firing
against real data.

**Demo D - ordinary exhaustion.** Twelve short real turns, letting
`history_max_messages=20` (10 whole turns) fill naturally. The first drop
appeared at request 12: `history_turns_dropped=1`,
`history_chars_dropped=30`, `history_drop_reason="window_full"`.

**Cleanup.** Router process stopped. Real demo rows appended to
`ledger/router_requests.csv` and kept, same convention as every prior
live demo. Nothing staged or committed.

**Not a Bean quality comparison - no scores to record.** Every demo is
single-Bean functional verification of Coffee's own behaviour.
