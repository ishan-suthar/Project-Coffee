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
