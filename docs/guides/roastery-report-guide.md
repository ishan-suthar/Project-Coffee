# Roastery Report Guide

Status: v0.1 practical guide  
Date: 2026-07-06

## 1. Purpose

The Roastery report generator turns local Cup Test manifests into a draft
Markdown or JSON summary for human review.

Use it when captured runs exist under `roastery/local_cup_outputs/` and you
want a starting point for Roastery notes without rebuilding tables by hand.

## 2. What The Report Generator Does

`tools/roastery_report.py`:

- reads one local Cup Test `manifest.json`;
- reads multiple child run manifests from a parent directory;
- summarizes run ID, creation time, Order file, output directory, and Bean
  status;
- includes latency, token usage, cost metadata, errors, and output file paths
  when present;
- optionally includes short capped local-output excerpts;
- prints a draft report or writes it to an explicit output path;
- can emit JSON for local tooling.

## 3. What It Does Not Do

The report generator does not:

- call OpenRouter;
- call any model;
- call external APIs;
- require `OPENROUTER_API_KEY`;
- score output quality;
- inspect `.env` or credential files;
- include full raw outputs;
- edit `roastery/tasting_notes.md`;
- decide House Blend routing.

It produces a draft. Human review still decides what becomes evidence.

## 4. Generate A Report For One Run

From the Project Coffee repo root:

```powershell
python tools\roastery_report.py --run-dir roastery\local_cup_outputs\brew14-docs-summary-20260706-023220
```

The report prints to stdout when `--output` is omitted.

## 5. Generate A Report For Multiple Runs

Point `--run-dir` at a parent directory that contains child run directories:

```powershell
python tools\roastery_report.py --run-dir roastery\local_cup_outputs
```

The report groups results by run ID. If a child run directory is missing a
manifest, the tool stops with a clear error so the evidence is not partial by
accident.

## 6. Include Previews Safely

Previews are off by default.

To include capped local-output excerpts:

```powershell
python tools\roastery_report.py --run-dir roastery\local_cup_outputs\brew14-pantry-assisted-20260706-023312 --include-previews
```

Limit the excerpt length:

```powershell
python tools\roastery_report.py --run-dir roastery\local_cup_outputs\brew14-pantry-assisted-20260706-023312 --include-previews --max-preview-chars 200
```

Previews are labeled as local-output excerpts. They are only a convenience for
review. They are not a substitute for opening and reviewing the full local
output files.

## 7. Save A Draft Report

Write a draft to a temporary or local review path:

```powershell
python tools\roastery_report.py --run-dir roastery\local_cup_outputs\brew14-python-fix-20260706-022559 --output tmp\roastery-report-draft.md
```

Do not write directly to `roastery/tasting_notes.md`. The tool refuses that
path because generated reports need human review first.

For JSON:

```powershell
python tools\roastery_report.py --run-dir roastery\local_cup_outputs\brew14-python-fix-20260706-022559 --json
```

## 8. Move Reviewed Summaries Into Tasting Notes

After generating a draft:

1. Review the manifest metadata.
2. Open the local raw outputs only if they are safe and expected.
3. Score quality manually using the Roastery rubric.
4. Summarize strengths, weaknesses, and human fixes.
5. Copy only reviewed summary notes into `roastery/tasting_notes.md`.
6. Add an honest Ledger entry when cost or token metadata is available.
7. Keep raw output files local-only.

## 9. Safety Rules

- Do not commit raw outputs.
- Do not paste secrets.
- Do not paste private or regulated data.
- Do not treat generated reports as final scores without human review.
- Use `unknown` when token, cost, latency, or review status is unavailable.
- Keep generated drafts out of commits unless the human intentionally approves
  a reviewed summary artifact.
- Before any commit, run the staged secret-pattern check from Project Coffee
  policy.

## 10. Troubleshooting

| Issue | What to do |
| --- | --- |
| Run directory missing | Check the path and run from the Project Coffee repo root. |
| Manifest missing | Confirm the Cup Test was run with `--save-outputs`. |
| Invalid manifest JSON | Re-run or inspect the local manifest file. |
| Parent directory fails | One child run directory may be missing `manifest.json`; move unrelated folders elsewhere. |
| Previews unavailable | Confirm the manifest output path points inside the selected run directory. |
| Output file not written | Check that the parent folder is writable and that the output path is not `roastery/tasting_notes.md`. |
| Report has TODO scoring rows | That is expected; quality scoring is a human review step. |

