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
