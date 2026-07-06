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
| `cup_tests/` | Repeatable multi-task Cup Test Orders for comparing Beans. |
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

## Multi-Task Benchmark Pack

Brew 14 adds a small repeatable Cup Test pack under `roastery/cup_tests/`.
These Orders make future Bean comparisons less task-limited.

List available Cup Tests without requiring `OPENROUTER_API_KEY`:

```powershell
python roastery/run_cup_test.py --list-cup-tests
```

Use a custom Cup Test directory when needed:

```powershell
python roastery/run_cup_test.py --list-cup-tests --cup-test-dir roastery/cup_tests
```

Run a specific Order file only after human approval for a live model run:

```powershell
python roastery/run_cup_test.py --order-file roastery/cup_tests/001-decaf-repo-map.md
```

If `--order-file` is not provided, the runner keeps using its built-in default
Order.

## Full-Output Capture

Brew 12 adds optional full-output capture so future Cup Tests can preserve raw
model answers locally for human review and quality scoring. The default runner
behavior still writes no files.

Use local tests without API calls:

```powershell
python -m unittest roastery.tests.test_run_cup_test
python -m py_compile roastery/run_cup_test.py roastery/tests/test_run_cup_test.py
python roastery/run_cup_test.py --help
```

Run a real captured Cup Test only when the human has approved a live model run
and `OPENROUTER_API_KEY` is configured outside the repo:

```powershell
python roastery/run_cup_test.py --save-outputs
```

Run and capture a specific benchmark Order:

```powershell
python roastery/run_cup_test.py --order-file roastery/cup_tests/002-tiny-python-fix.md --save-outputs --run-id benchmark-002-example
```

By default, captured runs are saved under:

```text
roastery/local_cup_outputs/
```

Use a custom output directory or run ID when needed:

```powershell
python roastery/run_cup_test.py --save-outputs --output-dir roastery/local_cup_outputs --run-id 20260706-example
```

Each captured run writes:

- one UTF-8 text file per successful Bean;
- `manifest.json` with run metadata, Bean status, latency, usage when
  available, errors when present, output file paths for successful Beans, and
  the Order hash;
- `order_file` metadata when the Order came from a file.

Failed Beans are recorded in the manifest without a successful output file.
The manifest does not include API keys, environment values, or the full Order
text.

Raw outputs must stay local and must not be committed. Summarize and score the
evidence in Roastery docs instead of committing raw model outputs.

When recording evidence, summarize:

- Cup Test file name;
- run ID;
- Beans tested;
- status, latency, tokens, and cost when available;
- quality scores only after human review;
- strengths, weaknesses, and human fixes needed.

Use `unknown` where runtime metadata is unavailable. Do not paste full raw
outputs into tracked docs unless they are tiny and clearly safe.
