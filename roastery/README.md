# Roastery

Roastery records model, prompt, role, and workflow evaluation evidence.

Use `cup_test_plan.md` before running a model comparison. Do not record fake
costs or invented results. Add real results only after the human runs the same
Order against each Bean and collects usage evidence.

## Cup Test Workflow

Every Roastery Cup Test should use:

1. the same Order;
2. the same repo state;
3. the same constraints;
4. the same Barista role;
5. the same Recipe or prompt template;
6. the same evaluation criteria.

Create one filled copy of `cup-test-template.md` and one filled copy of
`scorecard-template.md` per Bean after the real run. Leave token and cost fields
blank when the runtime does not show usage data. Never guess scores, costs,
tokens, latency, or model outputs.

## Current Files

| File | Use |
| --- | --- |
| `run_cup_test.py` | Local CLI runner for executing the same Order against configured Beans. |
| `openrouter_client.py` | Tiny stdlib OpenRouter wrapper for future Cup Test model calls. |
| `cup_test_plan.md` | Plan for the first repeatable Roastery Cup Test. |
| `cup-test-template.md` | Blank run template for each Bean in a Cup Test. |
| `scorecard-template.md` | Blank reusable scorecard for comparing a Bean run. |
| `tasting_notes.md` | Index of model evaluation notes and scorecards. |
| `model_scorecards/` | Individual Bean/model scorecards. |
| `workflow_scorecards/` | Workflow-level scorecards. |
| `benchmark_tasks/` | Repeatable benchmark task definitions. |

## OpenRouter Client

`openrouter_client.py` reads credentials only from `OPENROUTER_API_KEY` and
returns structured results from one model/order call. It does not store or print
credentials, choose routes, create scorecards, or run Cup Tests by itself.

## Local Cup Test Runner

Run the local Cup Test runner from the repository root:

```powershell
python roastery/run_cup_test.py
```

The runner checks whether `OPENROUTER_API_KEY` is available at runtime, sends the
same default Order to each configured Bean, and prints progress, latency, usage
metadata when returned, response previews, and a comparison table. If one Bean
returns an error, the runner reports it and continues with the remaining Beans.
It retries likely transient provider or rate-limit errors once per Bean, but it
does not retry permanent unavailable-model errors such as HTTP 404. It does not
write Roastery files, calculate scores, update the Ledger, or change House Blend
routing.

The current free Bean list is `poolside/laguna-m.1:free`,
`cohere/north-mini-code:free`, and `nvidia/nemotron-3-ultra-550b-a55b:free`.
Earlier Qwen and DeepSeek candidates were replaced after the first live runs
showed provider/rate-limit and unavailable-endpoint errors.
