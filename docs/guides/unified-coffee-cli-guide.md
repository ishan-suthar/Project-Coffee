# Unified Coffee CLI Guide

## Purpose

The Unified Coffee CLI gives Project Coffee one command surface for the local tools used most often during daily work. It is a thin wrapper around existing tools, not a replacement for them.

## Why It Exists

Before Brew 18, common Project Coffee checks required remembering several script names. The unified CLI keeps those tools discoverable while preserving each tool's existing behavior, exit codes, and safety boundaries.

Use it when you want one predictable entry point from the Project Coffee root:

```powershell
python tools\coffee.py --help
```

## Subcommands

| Subcommand | Delegates to | Purpose |
| --- | --- | --- |
| `dashboard` | `tools/coffee_dashboard.py` | Show current Project Coffee workflow status. |
| `doctor` | `tools/coffee_doctor.py` | Diagnose repository health issues and safe next actions. |
| `pantry-search` | `tools/pantry_search.py` | Search local Markdown knowledge. |
| `roastery-report` | `tools/roastery_report.py` | Draft a report from local Cup Test manifests. |
| `install-template` | `tools/install_project_coffee_template.py` | Dry-run or apply the onboarding template pack. |
| `check-onboarding` | `tools/install_project_coffee_template.py --check` | Check whether a project has required onboarding files. |

## Examples

```powershell
python tools\coffee.py --version
python tools\coffee.py dashboard --root .
python tools\coffee.py doctor --root . --section tools
python tools\coffee.py pantry-search --root docs --query "House Blend" --max-results 5
python tools\coffee.py roastery-report --run-dir roastery\local_cup_outputs
python tools\coffee.py install-template --target C:\Users\you\scratch-project
python tools\coffee.py check-onboarding --target C:\Users\you\scratch-project
```

## Dashboard Usage

Use `dashboard` for a quick read of Project Coffee status:

```powershell
python tools\coffee.py dashboard --root .
python tools\coffee.py dashboard --root . --json
python tools\coffee.py dashboard --root . --section docs
python tools\coffee.py dashboard --root . --fail-on-missing
```

The wrapper forwards the command to the dashboard tool and returns the dashboard exit code.

## Doctor Usage

Use `doctor` when you want diagnosis rather than a status board:

```powershell
python tools\coffee.py doctor --root .
python tools\coffee.py doctor --root . --json
python tools\coffee.py doctor --root . --section ignored-paths
python tools\coffee.py doctor --root . --fail-on-issue
```

Doctor remains read-only. It checks known safe paths and does not inspect secrets or local raw output folders.

## Pantry Search Usage

Use `pantry-search` to search Markdown knowledge:

```powershell
python tools\coffee.py pantry-search --root knowledge --query "Brew Log"
python tools\coffee.py pantry-search --root docs --query "onboarding" --max-results 3 --json
```

The search tool still controls its own sensitive-path skipping and snippet limits.

## Roastery Report Usage

Use `roastery-report` to generate a draft from local Cup Test manifests:

```powershell
python tools\coffee.py roastery-report --run-dir roastery\local_cup_outputs
python tools\coffee.py roastery-report --run-dir roastery\local_cup_outputs --json
python tools\coffee.py roastery-report --run-dir roastery\local_cup_outputs --output roastery\local_reports\draft.md
```

Generated reports are drafts for human review. Do not commit raw local outputs or generated local reports unless a future policy explicitly changes that.

## Template Install Usage

Dry-run first:

```powershell
python tools\coffee.py install-template --target C:\Users\you\scratch-project
```

Apply only after review:

```powershell
python tools\coffee.py install-template --target C:\Users\you\scratch-project --apply
```

Use `--force` only when overwriting existing onboarding files is intentional and reviewed:

```powershell
python tools\coffee.py install-template --target C:\Users\you\scratch-project --apply --force
```

## Onboarding Check Usage

Use `check-onboarding` after template install or manual onboarding:

```powershell
python tools\coffee.py check-onboarding --target C:\Users\you\scratch-project
```

This delegates to the existing template installer doctor mode, so the required onboarding file list stays in one place.

## Safety Boundaries

- The unified CLI delegates to local standard-library tools.
- It does not call models, OpenRouter, or external APIs by itself.
- It does not read or print secrets.
- It does not inspect `.env`, credential files, private keys, or hidden credential directories.
- It does not inspect raw Roastery outputs except through the existing report tool behavior.
- It returns the delegated tool's exit code so strict checks remain strict.
- It does not stage, commit, push, deploy, or install packages.

Before any commit, stage only intended files and run the staged secret-pattern check from Project Coffee policy.

## Troubleshooting

If a subcommand reports that a delegated tool is missing, confirm you are running from a Project Coffee checkout that contains the expected `tools/` files.

If a delegated tool returns nonzero, run that underlying tool directly with `--help` and inspect its specific validation message.

If PowerShell treats a path oddly, quote the path:

```powershell
python tools\coffee.py check-onboarding --target "C:\Users\you\scratch project"
```

If JSON output looks empty or invalid, first run the same command without `--json` to see the human-readable error.
