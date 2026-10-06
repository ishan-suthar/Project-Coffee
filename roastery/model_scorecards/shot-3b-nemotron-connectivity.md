# Model Scorecard: Shot 3B Connectivity Test

Model: nvidia/nemotron-3-super-120b-a12b (Nemotron 3 Super)  
Provider: NVIDIA via OpenRouter  
Date tested: 2026-07-02  
Task type: Connectivity test (Espresso Shot)  
Evaluator: Barista

## Task

Minimal live connectivity test with prompt:

```text
Reply with exactly:
OK
Current Bean:
<Model Name>
```

## Context provided

No repo content. Non-sensitive test prompt only.

## Result summary

**Status: BLOCKED** — `OPENROUTER_API_KEY` not available to the agent shell. Key is configured in Cursor settings only; Barista terminal cannot access Cursor UI credentials per Spill Guard design.

Pre-flight estimates recorded. Live response and actual usage not obtained.

## Scores

| Metric | Score 1-5 | Notes |
|---|---:|---|
| Correctness | — | Not tested (blocked) |
| Completeness | — | Not tested (blocked) |
| Code quality | N/A | Connectivity test |
| Context handling | N/A | No context sent |
| Instruction following | — | Not tested (blocked) |
| Cost efficiency | — | No charge incurred |
| Speed | — | Not measured |
| Supervision required | 5 | Human must expose key to shell or run test in Cursor UI |
| Risk behavior | 5 | No secrets probed in repo; env check only |

## Cost / tokens (pre-flight estimate)

- Input tokens: ~25 (estimated)
- Output tokens: ~15 (estimated)
- Total tokens: ~40 (estimated)
- Cost: ~$0.00 (estimated; no API call made)
- Time: N/A (blocked before request)

## Verdict

- Use for: House Blend default reasoning Bean (pending successful live test)
- Avoid for: N/A until connectivity confirmed
- Escalate when: Shell-based agent tests need `OPENROUTER_API_KEY` in User env (not repo)

## Follow-up

1. Set `OPENROUTER_API_KEY` in Windows User environment **or** re-run Shot 3B manually in Cursor with Nemotron selected.
2. On success, replace this scorecard with actual latency, tokens, and response.
3. Confirm instruction-following on exact reply format.
