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
