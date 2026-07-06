# House Blend

Status: Provisional
Date: 2026-07-06
Scope: Initial evidence-based routing for local Project Coffee work

House Blend is Project Coffee's model-routing policy. It is configuration, not
identity. Models are replaceable Beans, and routing should change only when
Roastery evidence supports the change.

Reference evidence:

- `roastery/tasting_notes.md`
- `ledger/cost_log.md`
- `brew-log/progress.md`
- `brew-log/active_context.md`

## Current Blend

| Route | Bean | Status | Why |
| --- | --- | --- | --- |
| Default Bean | `nvidia/nemotron-3-ultra-550b-a55b:free` | Provisional; confidence improved for small standard-library coding Orders | Matched reviewed output quality in Brew 12B while remaining fastest and lowest-token in the captured run. |
| Fallback Bean | `cohere/north-mini-code:free` | Provisional | Produced a reviewed, useful full output in Brew 12B; slower/more tokens than Nemotron in the captured run. |
| Secondary fallback / comparison Bean | `poolside/laguna-m.1:free` | Provisional | Produced a reviewed, useful full output in Brew 12B; remains useful for comparison and secondary fallback coverage. |

Do not use these failed candidates as default routes until availability improves
and a new Roastery test succeeds:

- `qwen/qwen3-coder:free`
- `deepseek/deepseek-r1:free`
- `deepseek/deepseek-r1-0528-qwen3-8b:free`

## Evidence Summary

The first local Cup Test was partial:

- `qwen/qwen3-coder:free` returned a provider/rate-limit error.
- `deepseek/deepseek-r1:free` was unavailable for free.
- `nvidia/nemotron-3-ultra-550b-a55b:free` succeeded.

The 8J rerun used the same local runner Order with replacement Beans:

| Bean | Status | Latency | Usage |
| --- | --- | ---: | ---: |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.42s | 726 total |
| `cohere/north-mini-code:free` | ok | 3.77s | 1316 total |
| `poolside/laguna-m.1:free` | ok | 0.81s | 3525 total |

Quality remains unknown beyond response previews looking on-task. Actual cost is
unknown because no cost value was shown in the recorded runner output.

The Brew 12B captured full-output run used the same default coding Order and
preserved local raw outputs for review:

| Bean | Status | Latency | Usage | Quality score | Cost |
| --- | --- | ---: | ---: | ---: | ---: |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.45s | 936 total | 9 | 0 reported |
| `poolside/laguna-m.1:free` | ok | 0.66s | 2158 total | 9 | 0 reported |
| `cohere/north-mini-code:free` | ok | 0.62s | 2272 total | 9 | 0 reported |

Full-output evidence improved confidence that all three current Beans can
complete this small standard-library coding Order. Nemotron remains the default
because it tied on reviewed quality while using fewer reported tokens and lower
latency. This does not prove it is best for other task types.

## Routing Policy By Task Type

| Task type | Default route | Fallback route | Notes |
| --- | --- | --- | --- |
| Decaf planning, explanation, or read-only review | No remote Bean required | `nvidia/nemotron-3-ultra-550b-a55b:free` if a remote Bean is explicitly approved | Prefer local docs and Pantry first. |
| Routine code and small implementation tasks | `nvidia/nemotron-3-ultra-550b-a55b:free` | `cohere/north-mini-code:free` | Based on first same-Order Cup Test evidence. |
| If Nemotron fails or is unavailable | `cohere/north-mini-code:free` | `poolside/laguna-m.1:free` | Continue to record failures and usage in Roastery. |
| If both default and fallback fail, or a comparison run is needed | `poolside/laguna-m.1:free` | Human chooses next Bean | Treat Poolside as comparison or secondary fallback, not primary default. |
| Research, architecture, security-sensitive, or production-risky work | Decaf first | Human-approved Bean only | Human review remains mandatory. |
| Premium escalation | Human-approved premium Bean only | None automatic | Premium Beans require explicit human approval. |

## Operating Rules

- Keep Project Coffee local-first and model-agnostic.
- Do not send secrets, credentials, private keys, or sensitive data to remote Beans.
- Do not route to Qwen or failed DeepSeek free slugs by default until a future
  Roastery test shows they are available and useful.
- Do not update House Blend from vibes, marketing, or single-run impressions
  alone.
- Record model usage and results in Roastery and Ledger when available.
- Premium escalation requires explicit human approval before use.

## Uncertainty And Limitations

- Only one tiny coding Order has a captured, reviewed, and scored full-output run.
- Quality confidence is still task-limited.
- Actual billing impact beyond returned cost metadata remains uncertain.
- Free endpoint availability can change.
- Performance may vary by task type, context length, and provider load.

## Next Evidence Needed

1. Repeat captured-output Cup Tests across more Order types.
2. Create per-Bean scorecards after each full output review.
3. Run at least one non-coding or review-focused Order.
4. Continue recording actual cost when OpenRouter exposes it.
5. Revisit routing after multiple successful Roastery comparisons.
