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
| Default Bean | `nvidia/nemotron-3-ultra-550b-a55b:free` | Provisional; confidence improved across all four Brew 14 benchmark Orders | Best combined Brew 14 result: successful on every reviewed benchmark Order, strongest grounded answer, tied or led quality on coding/docs tasks, fastest, and generally lowest-token among successful Beans. |
| Fallback Bean | `cohere/north-mini-code:free` | Provisional; useful but needs stricter review for grounded answers | Completed all four Brew 14 reviewed Orders, but used more tokens than Nemotron and showed unsupported-detail risk on the Pantry-assisted answer. |
| Secondary fallback / comparison Bean | `poolside/laguna-m.1:free` | Provisional comparison Bean; useful for coding/docs, availability-limited for repo-map | Produced strong coding and docs-summary outputs, but failed the repo-map Order with HTTP 429 and needs grounding review on citation-sensitive work. |

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

The Brew 14B multi-task benchmark added two captured and reviewed Orders:

| Task | Bean | Status | Latency | Usage | Quality score | Cost |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `001-decaf-repo-map.md` | `poolside/laguna-m.1:free` | error: HTTP 429 | 0.20s | unknown | 1 | unknown |
| `001-decaf-repo-map.md` | `cohere/north-mini-code:free` | ok | 0.43s | 1797 total | 7 | 0 reported |
| `001-decaf-repo-map.md` | `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.38s | 1257 total | 8 | 0 reported |
| `002-tiny-python-fix.md` | `poolside/laguna-m.1:free` | ok | 1.16s | 2717 total | 10 | 0 reported |
| `002-tiny-python-fix.md` | `cohere/north-mini-code:free` | ok | 0.55s | 2578 total | 10 | 0 reported |
| `002-tiny-python-fix.md` | `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.39s | 656 total | 10 | 0 reported |

The second Brew 14 benchmark pass added docs-summary and Pantry-assisted answer
Orders:

| Task | Bean | Status | Latency | Usage | Quality score | Cost |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `003-docs-summary.md` | `poolside/laguna-m.1:free` | ok | 0.91s | 690 total | 10 | 0 reported |
| `003-docs-summary.md` | `cohere/north-mini-code:free` | ok | 0.57s | 759 total | 9 | 0 reported |
| `003-docs-summary.md` | `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.44s | 661 total | 10 | 0 reported |
| `004-pantry-assisted-answer.md` | `poolside/laguna-m.1:free` | ok | 1.19s | 903 total | 8 | 0 reported |
| `004-pantry-assisted-answer.md` | `cohere/north-mini-code:free` | ok | 0.53s | 1241 total | 6 | 0 reported |
| `004-pantry-assisted-answer.md` | `nvidia/nemotron-3-ultra-550b-a55b:free` | ok | 0.40s | 762 total | 10 | 0 reported |

Across all four Brew 14 benchmark Orders, Nemotron has the strongest
provisional default evidence. Cohere remains the main fallback but needs stricter
human review for citation-sensitive or grounding-sensitive answers. Poolside
remains a comparison Bean and possible coding/docs fallback, but not the
preferred repo-map fallback until availability is more stable.

## Routing Policy By Task Type

| Task type | Default route | Fallback route | Notes |
| --- | --- | --- | --- |
| Decaf planning, explanation, or read-only review | No remote Bean required | `nvidia/nemotron-3-ultra-550b-a55b:free` if a remote Bean is explicitly approved; `cohere/north-mini-code:free` as fallback | Prefer local docs and Pantry first. Brew 14 favored Nemotron for repo-map quality, grounded-answer quality, and efficiency. |
| Routine code and small implementation tasks | `nvidia/nemotron-3-ultra-550b-a55b:free` | `cohere/north-mini-code:free` | Brew 12B and Brew 14B both support Nemotron as the efficient default for tiny standard-library coding Orders. |
| Documentation summaries | `nvidia/nemotron-3-ultra-550b-a55b:free` | `poolside/laguna-m.1:free` or `cohere/north-mini-code:free` | Brew 14C showed all three Beans can handle concise docs summaries; Nemotron and Poolside scored highest, while Nemotron was fastest and lowest-token. |
| Grounded Pantry-assisted answers | `nvidia/nemotron-3-ultra-550b-a55b:free` | `poolside/laguna-m.1:free` with review | Brew 14C showed Nemotron stayed most grounded; Cohere added unsupported details and needs stricter review for this task type. |
| If Nemotron fails or is unavailable | `cohere/north-mini-code:free` | `poolside/laguna-m.1:free` for coding comparison only | Continue to record failures and usage in Roastery. |
| If both default and fallback fail, or a comparison run is needed | `poolside/laguna-m.1:free` | Human chooses next Bean | Treat Poolside as comparison or secondary coding fallback; avoid relying on it for repo-map until a future run succeeds. |
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

- Four benchmark Orders now have captured, reviewed, and scored full-output
  runs: repo-map/planning, tiny Python fix, docs summary, and grounded
  Pantry-assisted answer.
- Quality confidence is still task-limited.
- Actual billing impact beyond returned cost metadata remains uncertain.
- Free endpoint availability can change.
- Performance may vary by task type, context length, and provider load.

## Next Evidence Needed

1. Create per-Bean scorecards after each full output review.
2. Repeat the benchmark pack on later dates or with new Beans to check
   stability.
3. Add more real-project Order types only after the four-task benchmark is
   digested.
4. Continue recording actual cost when OpenRouter exposes it.
5. Revisit routing after multiple successful Roastery comparisons.
