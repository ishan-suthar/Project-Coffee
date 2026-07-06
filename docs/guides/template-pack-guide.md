# Template Pack Guide

Status: v0.1 practical guide
Date: 2026-07-06

Use this guide with `TEMPLATES/project-coffee/` to add a minimal Project Coffee
skeleton to a new project.

For most future onboardings, prefer the dry-run-first installer documented in
`template-installer-guide.md`. Manual copy remains useful when the installer is
not available or the human wants to copy files one by one.

## Purpose

The template pack makes project onboarding repeatable and safer than starting
from scratch. It is based on what worked for Coffee Status in Brew 8.

## What To Copy

Copy the contents of `TEMPLATES/project-coffee/` into the target project root.
For a project inside a monorepo, copy it into that project's local root.

Included files:

- `AGENTS.md`
- `PROJECT_COFFEE.md`
- `.cursorignore`
- `.cursorindexingignore`
- `brew-log/projectbrief.md`
- `brew-log/active_context.md`
- `brew-log/progress.md`
- `knowledge/00_index.md`
- `roastery/tasting_notes.md`
- `ledger/cost_log.md`
- `README.md`

The installer copies the onboarding manifest only and intentionally does not
copy the template pack `README.md` into the target project.

## Installer Workflow

Preview the installer plan first:

```powershell
python tools\install_project_coffee_template.py --target C:\Work\ExternalProject
```

Apply only after review:

```powershell
python tools\install_project_coffee_template.py --target C:\Work\ExternalProject --apply
```

Check onboarding after setup:

```powershell
python tools\install_project_coffee_template.py --check --target C:\Work\ExternalProject
```

See `template-installer-guide.md` for the force overwrite policy and
troubleshooting.

## Fill-In Rules

- Replace prose placeholders such as "Project name goes here."
- Add real validation commands for the target project.
- Keep unknown cost, token, model, or review fields marked as `Unknown` until
  evidence exists.
- Do not add fake API keys, example secrets, real secrets, or private data.
- Do not paste keys into chat or documentation.
- Do not include the literal staged secret-pattern check text. Refer to it by
  name from Project Coffee policy.

## Recommended First Sequence

1. Run a Decaf repo map.
2. Dry-run the template installer or copy the template pack manually.
3. Fill only the minimal project-specific fields.
4. Complete one tiny safe improvement.
5. Run local validation.
6. Update Brew Log, Roastery, and Ledger.
7. Let the human review the diff.
8. Stage only intended files.
9. Run the staged secret-pattern check from Project Coffee policy.
10. Commit manually if satisfied.

## Validation

After filling the template pack, run:

```powershell
git diff --check
git status --short
```

Run the target project's own tests or validation commands before review.

## Common Mistakes

- Copying the pack but leaving placeholders unchanged.
- Treating the template as permission to inspect secrets.
- Adding dependency installs to onboarding.
- Recording guessed token or cost values.
- Committing generated folders, caches, logs, or virtual environments.
- Skipping Roastery or Ledger evidence after the first improvement.
