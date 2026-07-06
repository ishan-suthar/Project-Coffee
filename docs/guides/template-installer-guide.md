# Template Installer Guide

Status: v0.1 practical guide  
Date: 2026-07-06

Use this guide to run the local Project Coffee template installer and onboarding
doctor. The tool is standard-library-only, local, and dry-run-first.

## 1. Purpose

The template installer makes Project Coffee onboarding repeatable without
manually copying each file from the template pack.

It helps with two jobs:

- previewing or applying the minimal Project Coffee onboarding skeleton;
- checking whether a target project already has the required onboarding files.

The installer is a helper, not an approval system. Human review, validation,
the staged secret-pattern check from Project Coffee policy, and manual commit
still remain explicit.

## 2. When To Use The Installer

Use the installer after a Decaf repo map has confirmed that the target project
is safe to onboard.

Good fits:

- a local project with a clear root folder;
- a scratch repo used to test onboarding;
- an external project selected for Project Coffee onboarding;
- a monorepo subproject where the local project root is known.

Do not use it during a production incident, secret cleanup, unclear migration,
or any task where the target path is uncertain.

## 3. Dry-Run First Workflow

Dry-run is the default. It prints what would happen and writes nothing.

From the Project Coffee repository root:

```powershell
python tools\install_project_coffee_template.py --target C:\Work\ScratchProject
```

Review the output sections:

- mode;
- target;
- template;
- files to create;
- files to skip;
- files that would overwrite only with `--force`;
- result.

If the target path is wrong, stop. If existing files would be skipped, review
whether the target already has local rules that should be preserved.

## 4. Apply Workflow

Use `--apply` only after reviewing the dry-run output.

```powershell
python tools\install_project_coffee_template.py --target C:\Work\ScratchProject --apply
```

Apply mode creates missing onboarding files and leaves existing files alone.
After applying, review the diff, fill project-specific placeholders, and run
the target project's validation commands.

## 5. Force Overwrite Policy

Existing files are never overwritten unless `--force` is supplied with
`--apply`.

```powershell
python tools\install_project_coffee_template.py --target C:\Work\ScratchProject --apply --force
```

Use `--force` only when the human has reviewed the existing target files and
explicitly wants the template version to replace them. This is usually rare.
Most onboardings should preserve existing `AGENTS.md`, `PROJECT_COFFEE.md`,
and ignore files until a human decides how to merge them.

## 6. Doctor / Check Workflow

Use `--check` to audit whether a target project appears to have the required
Project Coffee onboarding files.

```powershell
python tools\install_project_coffee_template.py --check --target apps\coffee-status
```

Doctor mode:

- writes nothing;
- checks only required onboarding path existence;
- does not scan the whole repository;
- prints `FOUND files`;
- prints `MISSING files`;
- prints `status` as `COMPLETE` or `INCOMPLETE`.

Exit behavior:

- `0` means onboarding files are complete;
- `2` means required onboarding files are missing;
- another nonzero code means the target path is missing or unsafe.

## 7. Recommended PowerShell Commands

Dry-run into a scratch repo:

```powershell
python tools\install_project_coffee_template.py --target C:\Work\ScratchProject
```

Apply into a scratch repo after review:

```powershell
python tools\install_project_coffee_template.py --target C:\Work\ScratchProject --apply
```

Check Coffee Status:

```powershell
python tools\install_project_coffee_template.py --check --target apps\coffee-status
```

Check an external repo after onboarding:

```powershell
python tools\install_project_coffee_template.py --check --target C:\Work\ExternalProject
```

Review the diff:

```powershell
git diff --check
git status --short
```

## 8. Safety Rules

- Run a Decaf repo map before onboarding a new target.
- Confirm the target path before applying.
- Do not use the installer to inspect secrets.
- Do not add real keys, fake keys, tokens, credentials, or private data.
- Do not stage or commit from the installer workflow.
- Keep human review and manual commit explicit.
- Before any commit, stage only intended files and run the staged secret-pattern
  check from Project Coffee policy.

## 9. What The Installer Does Not Do

The installer does not:

- inspect `.env` files or credential folders;
- scan the target repository;
- install packages;
- run tests;
- run models;
- edit application logic;
- fill project-specific placeholders;
- merge existing rules;
- stage or commit changes;
- copy the template pack `README.md` into the target project.

The tool copies only the fixed onboarding manifest.

## 10. How It Fits Brew 10 External Onboarding

Brew 10 external onboarding follows the same sequence proven by Coffee Status:

1. Decaf repo map.
2. Dry-run installer.
3. Human review of the plan.
4. Apply missing onboarding files.
5. Fill only project-specific placeholders.
6. Complete one tiny improvement.
7. Run validation.
8. Record Brew Log, Roastery, and Ledger evidence.
9. Human reviews the diff and commits manually.

The installer reduces manual copy mistakes, and the doctor gives a quick
completion check before the first tiny improvement or closeout.

## 11. Troubleshooting

| Issue | What to do |
| --- | --- |
| Target does not exist | Create or open the correct local project folder first. |
| Template does not exist | Run the command from Project Coffee or pass `--template` to the template pack path. |
| Existing files are skipped | Review them manually and merge intentionally; use `--force` only with explicit approval. |
| Doctor prints `INCOMPLETE` | Add or restore the missing onboarding files, then rerun `--check`. |
| The wrong target was used in dry-run | Stop and rerun with the correct path; dry-run writes nothing. |
| The wrong target was used with `--apply` | Review `git diff`, then restore only the unintended onboarding files. |
| Validation fails after onboarding | Fix project-specific placeholders or local docs before starting a functional improvement. |

## 12. Examples

Dry-run into a scratch repo:

```powershell
python tools\install_project_coffee_template.py --target C:\Work\ScratchProject
```

Apply into a scratch repo:

```powershell
python tools\install_project_coffee_template.py --target C:\Work\ScratchProject --apply
```

Check `apps/coffee-status`:

```powershell
python tools\install_project_coffee_template.py --check --target apps\coffee-status
```

Check an external repo after onboarding:

```powershell
python tools\install_project_coffee_template.py --check --target C:\Work\ExternalProject
```
