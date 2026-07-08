# Coffee Doctor Guide

Status: v0.1 practical guide  
Date: 2026-07-08

## 1. Purpose

Coffee Doctor is a read-only Project Coffee health checker.

Use it when the Coffee Dashboard shows status and you want a deeper diagnosis
with severity, findings, and safe next actions. It helps identify missing core
files, missing guides, missing local tools, unsafe local artifact tracking, and
missing ignore rules.

## 2. Dashboard Versus Doctor

The Coffee Dashboard answers:

- What is present?
- What is the current status?
- Which major sections look OK?

Coffee Doctor answers:

- What is wrong or risky?
- How severe is it?
- What is the safest next action?

Run the Dashboard first for a quick view. Run Doctor when you need a more
actionable diagnosis.

## 3. What Doctor Checks

Coffee Doctor checks known Project Coffee paths only:

- core workflow files;
- productized docs and guides;
- local Project Coffee tools;
- Roastery evidence files and local artifact tracking;
- Ledger cost log;
- Pantry index;
- template pack files;
- ignore rules for local outputs and reports;
- docs that appear to embed the staged secret-check command instead of naming
  the policy check.

Doctor does not scan the whole repository.

## 4. Severity Levels

| Severity | Meaning |
| --- | --- |
| `OK` | The checked item is present or healthy. |
| `INFO` | Useful context, usually no immediate action required. |
| `WARN` | A non-core issue should be reviewed soon. |
| `FAIL` | A required or safety-critical issue needs attention. |

## 5. CLI Examples

Run Doctor from the Project Coffee root:

```powershell
python tools\coffee_doctor.py
```

Run against an explicit root:

```powershell
python tools\coffee_doctor.py --root C:\Users\iisha\Project_Coffee
```

Check only tools:

```powershell
python tools\coffee_doctor.py --section tools
```

Return JSON:

```powershell
python tools\coffee_doctor.py --json
```

Fail a local validation run when any `FAIL` finding exists:

```powershell
python tools\coffee_doctor.py --fail-on-issue
```

## 6. JSON Mode

Use `--json` when another local script needs structured results:

```powershell
python tools\coffee_doctor.py --root . --json
```

The JSON payload includes:

- `root`;
- `generated_at`;
- `status`;
- `findings`;
- `summary`.

Each finding includes its section, severity, code, message, and suggested safe
next action. Findings that relate to a known path include `path`.

## 7. Section Mode

Use `--section` to focus the diagnosis:

```powershell
python tools\coffee_doctor.py --section core
python tools\coffee_doctor.py --section docs
python tools\coffee_doctor.py --section tools
python tools\coffee_doctor.py --section roastery
python tools\coffee_doctor.py --section ledger
python tools\coffee_doctor.py --section pantry
python tools\coffee_doctor.py --section templates
python tools\coffee_doctor.py --section ignored-paths
```

Use `--section all` for the full check. `all` is the default.

## 8. Fail-On-Issue Mode

By default, Doctor prints findings and exits `0` even when it finds `FAIL`
items. This keeps it useful during exploratory diagnosis.

Use `--fail-on-issue` when a failed local health check should stop a script:

```powershell
python tools\coffee_doctor.py --root . --fail-on-issue
```

`WARN` findings do not cause a nonzero exit by themselves.

## 9. Safety Rules

- Doctor does not modify files.
- Doctor does not call models, OpenRouter, or external APIs.
- Doctor does not install packages.
- Doctor does not inspect `.env` files or credential directories.
- Doctor does not inspect raw local Cup Test outputs.
- Doctor does not inspect local generated report contents.
- Doctor uses `git ls-files` only for the known local Roastery artifact paths.
- Before any commit, run the staged secret-pattern check from Project Coffee
  policy.

## 10. What Doctor Does Not Do

Coffee Doctor does not:

- repair files automatically;
- stage or commit;
- run tests for you;
- decide whether a model output is good;
- inspect secrets;
- inspect production data;
- replace human review.

It suggests safe next actions. A human still chooses the next Shot.

## 11. Suggested Workflow

1. Run the Dashboard.
2. Run Doctor.
3. Pick one issue.
4. Fix one issue per Shot.
5. Validate.
6. Update Brew Log, Roastery, or Ledger when meaningful.
7. Review the diff.
8. Commit manually after approval and the staged secret-pattern check from
   Project Coffee policy.

## 12. Troubleshooting

| Issue | What to do |
| --- | --- |
| Root does not exist | Check `--root` and run from the expected PowerShell working directory. |
| Status is `FAIL` | Review the `FAIL` findings and fix one issue per Shot. |
| Status is `WARN` | Review warnings; many are missing optional docs or template-health issues. |
| Git check is skipped | Confirm the target is a Git repo, or run the allowed local artifact tracking check manually. |
| Local outputs are flagged as tracked | Untrack raw outputs and keep only summarized evidence in tracked docs. |
| JSON parsing fails | Make sure only Doctor JSON is written to stdout. |
| Section output looks incomplete | Confirm `--section` is not filtering to one area. |
