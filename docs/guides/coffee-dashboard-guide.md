# Coffee Dashboard Guide

Status: v0.1 practical guide  
Date: 2026-07-06

## 1. Purpose

The Coffee Dashboard gives Project Coffee a quick local health view from the
command line.

Use it when you want to see whether the core workflow files, guides, tools,
Roastery notes, Ledger notes, and House Blend docs are present before starting
or closing a Brew.

## 2. What The Dashboard Reports

`tools/coffee_dashboard.py` reports:

- required Project Coffee core files;
- Brew Log presence and current next action;
- productized guide presence;
- local tool presence;
- Roastery evidence file presence;
- Ledger evidence file presence;
- House Blend file presence and a short routing summary;
- missing required or expected files.

It supports human-readable output, JSON output, section filtering, and a
`--fail-on-missing` mode for stricter local checks.

## 3. What It Does Not Do

The dashboard does not:

- call OpenRouter;
- call any model;
- call external APIs;
- install packages;
- run Git commands;
- read `.env` or credential files;
- inspect raw Cup Test outputs;
- inspect local generated reports;
- decide whether evidence is good enough by itself.

It is a status tool, not a replacement for human review.

## 4. CLI Examples

Run the dashboard from the Project Coffee root:

```powershell
python tools\coffee_dashboard.py
```

Run against an explicit root:

```powershell
python tools\coffee_dashboard.py --root C:\Users\iisha\Project_Coffee
```

Return JSON:

```powershell
python tools\coffee_dashboard.py --json
```

Check only docs:

```powershell
python tools\coffee_dashboard.py --section docs
```

Fail when required core files are missing:

```powershell
python tools\coffee_dashboard.py --fail-on-missing
```

## 5. Human-Readable Mode

Human-readable mode is the default. It prints:

- root path;
- generated timestamp;
- overall status;
- selected dashboard sections;
- missing paths;
- warnings.

Use this mode during normal Project Coffee work because it is easy to scan
before a Decaf plan, closeout review, or handoff.

## 6. JSON Mode

Use `--json` when another local script or dashboard wants structured output:

```powershell
python tools\coffee_dashboard.py --root . --json
```

The JSON output includes:

- `root`;
- `generated_at`;
- `status`;
- `sections`;
- `missing`;
- `warnings`.

JSON mode still does not call models, APIs, Git, or credential-dependent tools.

## 7. Section Mode

Use `--section` to inspect one part of Project Coffee:

```powershell
python tools\coffee_dashboard.py --section brew-log
python tools\coffee_dashboard.py --section tools
python tools\coffee_dashboard.py --section roastery
python tools\coffee_dashboard.py --section ledger
python tools\coffee_dashboard.py --section house-blend
```

Available sections are:

- `overview`;
- `brew-log`;
- `docs`;
- `tools`;
- `roastery`;
- `ledger`;
- `house-blend`;
- `all`.

`all` is the default.

## 8. Fail-On-Missing Mode

Use `--fail-on-missing` when a missing required core file should stop a local
validation run:

```powershell
python tools\coffee_dashboard.py --root . --fail-on-missing
```

Missing optional guide or tool files still appear as warnings. Missing required
core files produce an incomplete status and a nonzero exit code.

## 9. Safety Rules

- Do not use the dashboard to inspect secrets or private data.
- Keep raw Roastery outputs under ignored local paths.
- Keep generated reports under ignored local paths.
- Treat warnings as review prompts, not automatic permission to edit.
- Before any commit, stage only intended files and run the staged
  secret-pattern check from Project Coffee policy.

## 10. Fit In Daily Operations

Good moments to run the dashboard:

- before starting a new Brew;
- after adding or closing a Project Coffee tool;
- after productized docs change;
- before a closeout shot;
- after onboarding a project;
- before human review of a larger documentation diff.

For Brew closeout, use the dashboard as one signal alongside tests, Roastery
evidence, Ledger notes, and human diff review.

## 11. Troubleshooting

| Issue | What to do |
| --- | --- |
| Root does not exist | Check the `--root` path and run from PowerShell with the correct working directory. |
| Status is WARN | Review the Missing and Warnings sections. Expected guide/tool files may be absent. |
| Status is INCOMPLETE | A required core file is missing while `--fail-on-missing` is enabled. |
| Section output looks too small | Confirm `--section` is not filtering the dashboard. |
| JSON parsing fails | Make sure no extra shell text was mixed into stdout. |
| House Blend summary is empty | Confirm `config/house_blend.md` exists and contains the expected routing table. |
| Local outputs are not listed | That is expected; raw outputs are local-only and not inspected by the dashboard. |
