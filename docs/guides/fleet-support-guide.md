# Fleet Support Guide

Status: Brew 24 / 24A
Date: 2026-07-08

## Purpose

Fleet support gives Project Coffee a local registry of onboarded projects and a
safe way to summarize their Project Coffee status before a future UI exists.

The Brew 24A MVP is intentionally small: it reads a local JSON registry and
checks only known Project Coffee onboarding marker paths. It does not scan whole
repositories, run Git across external projects, call models, call APIs, or read
secrets.

## What Fleet Support Is

Fleet support is the local layer that lets Project Coffee remember which
projects are part of the working set.

Use it to answer questions like:

- Which projects are registered?
- Which projects have Project Coffee onboarding files?
- Which project needs attention before future UI work?
- Which local project paths should tools know about without guessing?

## Registry Format

The default registry path is:

```powershell
fleet/projects.json
```

The registry is local project state. Do not commit a user-specific
`fleet/projects.json` unless that is explicitly intended and reviewed.

The format is:

```json
{
  "version": 1,
  "projects": [
    {
      "id": "coffee-status",
      "name": "Coffee Status",
      "path": "apps/coffee-status",
      "type": "app",
      "status": "onboarded",
      "notes": "Optional local note."
    }
  ]
}
```

Required project fields:

- `id`
- `name`
- `path`
- `type`
- `status`

`notes` is optional.

## Example Registry

Start from:

```powershell
fleet/projects.example.json
```

The example uses placeholder relative paths only. Copy it locally when a real
registry is needed:

```powershell
Copy-Item fleet\projects.example.json fleet\projects.json
```

Then edit `fleet/projects.json` with local project paths.

## CLI Examples

Show status using the default registry:

```powershell
python tools\fleet_status.py --root .
```

Use the unified Coffee CLI:

```powershell
python tools\coffee.py fleet-status --root .
```

Use an explicit registry:

```powershell
python tools\fleet_status.py --root . --registry fleet\projects.example.json
```

## Listing Projects

List registered projects without running checks:

```powershell
python tools\fleet_status.py --root . --list
```

This reads only the registry file.

## Checking Projects

Run safe onboarding marker checks:

```powershell
python tools\fleet_status.py --root . --check
```

The MVP checks only whether these paths exist:

- `AGENTS.md`
- `PROJECT_COFFEE.md`
- `brew-log/active_context.md`
- `brew-log/progress.md`
- `ledger/cost_log.md`
- `roastery/tasting_notes.md`
- `knowledge/00_index.md` when onboarding markers exist

It does not read these files.

## Project Filters

Check one project by id:

```powershell
python tools\fleet_status.py --root . --project coffee-status --check
```

Use strict exit behavior for automation:

```powershell
python tools\fleet_status.py --root . --project coffee-status --check --fail-on-issue
```

## JSON Mode

Use JSON for future UI or script consumption:

```powershell
python tools\fleet_status.py --root . --check --json
```

JSON output includes root, registry path, generated timestamp, status,
projects, findings, and summary counts.

## Safety Boundaries

Fleet Status:

- uses Python standard library only;
- reads the registry JSON only;
- checks project marker paths by existence only;
- does not read `.env`;
- does not inspect hidden credential directories;
- does not inspect raw Roastery local outputs;
- does not run Dashboard or Doctor inside external project paths in Brew 24A;
- does not run Git scans across external projects in Brew 24A;
- does not call models, OpenRouter, or external APIs.

Unsafe project paths are rejected if they point into hidden credential,
dependency, secret, token, virtual environment, raw-output, or local-report
locations.

## What Fleet Status Does Not Do Yet

Brew 24A does not:

- auto-discover projects;
- repair onboarding files;
- run tests in registered projects;
- run Git across registered projects;
- run Coffee Doctor inside registered projects;
- decide model routing for a project;
- send any project context to a remote Bean.

Those behaviors need separate approval and design.

## Future UI Use

A future Project Coffee UI can use the registry to show:

- registered projects;
- project onboarding status;
- missing Project Coffee markers;
- local-only evidence links;
- project-specific routing state from future Brew work.

The UI should preserve the same rule as the CLI: local evidence first, explicit
approval before remote context, and no automatic staging or commits.

## Troubleshooting

If the registry is missing, copy the example registry and edit it locally.

If JSON parsing fails, validate commas, quotes, braces, and brackets.

If a project is missing onboarding files, use the template installer in dry-run
mode first:

```powershell
python tools\install_project_coffee_template.py --target path\to\project
```

If a project path is rejected as unsafe, move the registry entry to the real
project root and keep credential or generated-output paths out of the fleet
registry.
