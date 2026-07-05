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
