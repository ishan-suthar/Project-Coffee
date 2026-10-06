# Ledger Summary Guide

## Purpose

The Ledger Summarizer turns `ledger/cost_log.md` into a quick local summary of cost, token, and workflow evidence. It is meant to help review what Project Coffee has recorded, not to replace human Ledger updates.

## What It Reads

By default, the tool reads:

```powershell
ledger\cost_log.md
```

It expects Markdown ledger entries, especially the Project Coffee Ledger table with columns for date, task, model or Bean, task type, estimated tokens, actual cost, and value notes. It also tolerates simple legacy Markdown lines that include dates.

## What It Does Not Read

The summarizer does not read raw Roastery local outputs, local report folders, hidden credential folders, `.env` files, private keys, tokens, or external services. It does not scan the whole repository.

## Safety Boundaries

- Standard library only.
- Local file reads only.
- No model calls.
- No OpenRouter calls.
- No external API calls.
- No package installation.
- No secret inspection.
- No staging or committing.

Unknown cost or token fields stay unknown. The tool should summarize evidence, not invent precision.

## CLI Examples

Run the default summary from the Project Coffee root:

```powershell
python tools\ledger_summary.py --root .
```

Run through the unified Coffee CLI:

```powershell
python tools\coffee.py ledger-summary --root .
```

Use a specific ledger file:

```powershell
python tools\ledger_summary.py --root . --ledger ledger\cost_log.md
```

Limit recent entries:

```powershell
python tools\ledger_summary.py --root . --max-entries 5
```

## JSON Mode

Use JSON when another local tool needs structured output:

```powershell
python tools\ledger_summary.py --root . --json
python tools\coffee.py ledger-summary --root . --json
```

The JSON output includes the root, ledger path, generated timestamp, date range, totals, recent entries, and warnings.

## Date Filtering

Use `--from` and `--to` with `YYYY-MM-DD` dates:

```powershell
python tools\ledger_summary.py --root . --from 2026-07-06 --to 2026-07-08
```

Entries without parseable dates are included only when no date filter is active.

## Output Report Mode

Write a Markdown draft report with `--output`:

```powershell
python tools\ledger_summary.py --root . --output tmp\ledger-summary.md
```

The output parent directory must already exist. Keep generated reports local unless a future shot explicitly approves committing one.

## Interpreting Unknown Costs And Tokens

The Ledger intentionally contains honest unknowns. Common examples:

- a model returned usage but no billing data;
- a local tool was not metered;
- a historical entry estimated effort without exact token counts;
- a failed provider call did not return usage.

Unknowns are not failures. They are a signal that future evidence capture can improve.

## Suggested Workflow

1. Run Coffee Doctor:

   ```powershell
   python tools\coffee.py doctor --root .
   ```

2. Run the Ledger Summary:

   ```powershell
   python tools\coffee.py ledger-summary --root .
   ```

3. Review the totals and recent entries.
4. Update `ledger/cost_log.md` manually if evidence is missing.
5. Review diffs.
6. Commit manually only after approval, staging only intended files, and running the staged secret-pattern check from Project Coffee policy.

## Troubleshooting

If the ledger is missing, confirm you are running from the Project Coffee root or pass `--ledger`.

If date filtering fails, use `YYYY-MM-DD` exactly.

If an output path fails, create the parent directory first or choose an existing local folder.

If totals look incomplete, inspect the Ledger entry text. The summarizer is conservative around unknown and mixed cost/token wording.
