# Project Coffee Release Packaging Guide

## Purpose

Release packaging is the final local readiness check before tagging or handing off Project Coffee. It gathers the repo, docs, safety, evidence, template, and tool signals that matter for a clean release without changing files or calling external services.

The release check is a checklist, not an approval engine. Human review still decides whether the release is ready.

## When To Run It

Run the release checklist when a Brew closes a meaningful capability, before creating a release tag, or before handing the repo to future-you for setup on another machine.

It is especially useful after documentation-heavy Brews, tool additions, safety changes, template updates, or Roastery/Ledger evidence updates.

## Release Readiness Checklist

Before tagging, confirm:

- the working tree is intentionally clean or intentionally dirty;
- the docs index links the current guides;
- release-facing tools and tests exist;
- the template pack is present;
- AGENTS.md, PROJECT_COFFEE.md, Git ignore, and Cursor ignore files are present;
- raw Roastery outputs and generated local reports are ignored and untracked;
- Brew Log, Roastery, and Ledger evidence are present;
- recent Ledger entries honestly describe model/API usage and local-only work;
- expected tags are reviewed without being automatically created;
- the staged secret-pattern check from Project Coffee policy is run before any commit.

## Using Release Check

Run the full human-readable checklist:

```powershell
python tools/release_check.py --root .
```

Run machine-readable output:

```powershell
python tools/release_check.py --root . --json
```

Run one section:

```powershell
python tools/release_check.py --root . --section tools
```

Fail nonzero when blockers exist:

```powershell
python tools/release_check.py --root . --fail-on-blocker
```

Through the Unified Coffee CLI:

```powershell
python tools/coffee.py release-check --root .
```

## Sections

`repo` checks safe Git status metadata and warns when the working tree has changed or untracked paths.

`docs` checks the docs index and release-facing guide files.

`tools` checks the local Project Coffee tools that are part of the release surface.

`templates` checks the Project Coffee template pack, template README, and template Pantry index.

`safety` checks policy files, ignore files, local output/report ignore rules, and whether known local output/report paths are tracked by Git.

`evidence` checks Brew Log, Roastery, and Ledger evidence files and warns if recent Ledger evidence is missing.

`tags` lists whether expected release tags are already present. It never creates tags.

## Severity Meanings

`OK` means the check passed.

`INFO` means the check is informational, unavailable, or something for the human to consider.

`WARN` means the release can continue only if the human accepts the risk.

`BLOCKER` means the release should stop until the issue is corrected or explicitly waived.

## Safe Commit And Tag Flow

Use this order:

1. Run focused validation for the Brew.
2. Run `python tools/release_check.py --root .`.
3. Review `git status --short`.
4. Review the diff.
5. Stage only intended files.
6. Run the staged secret-pattern check from Project Coffee policy.
7. Commit manually.
8. Create release tags only after human approval.

The release checker does not stage, commit, tag, push, install packages, or call models.

## What The Tool Does Not Do

It does not prove correctness of every tool.

It does not inspect secrets, raw local Roastery outputs, private data, or credential stores.

It does not read generated output folders. It only asks Git whether known local artifact paths are tracked.

It does not create tags or decide release names.

It does not replace human review.

## Evidence To Record

For a release Brew, record:

- date;
- release candidate or tag name if known;
- validation commands run;
- release check status;
- blockers, warnings, and decisions;
- whether raw outputs and generated reports remained untracked;
- cost/tokens as none/local or unknown;
- whether model/API calls occurred;
- human review and commit status.

## v0.1, v0.2, And Pre-v1 Habits

For v0.1-style releases, prioritize repeatability and safety over polish. The release should tell future-you how to set up, validate, onboard, diagnose, and summarize evidence.

For v0.2 or pre-v1 releases, add stronger dogfood evidence, clearer changelog entries, and more complete handoff notes.

Keep tags honest: a tag should describe proven behavior, not future intent.

## Troubleshooting

If Git status is unavailable, run the Git command manually from the repo root and confirm whether the checkout is clean.

If docs warnings appear, add missing guide links or record why the guide is not part of the current release.

If local artifacts are tracked, stop and remove raw outputs or generated reports from version control before tagging.

If the Ledger warning appears, add an honest local Ledger entry for recent release work when relevant.

If JSON output is needed for automation, use `--json` and treat `BLOCKER` counts as stop signs.
