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
