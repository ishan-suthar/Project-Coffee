# New Project Onboarding Guide

Status: v0.1 practical guide
Date: 2026-07-06

Use this guide to onboard a project into Project Coffee with the smallest safe
local structure. The proven example is `apps/coffee-status`, which was
onboarded in Brew 8.

## 1. Purpose

Project onboarding gives a real project its own local Coffee memory, safety
rules, evidence notes, and cost log without turning the project into a large
process exercise.

The goal is a lightweight repeatable loop:

1. map the project safely;
2. add a minimal Coffee skeleton;
3. complete one tiny improvement;
4. validate locally;
5. record evidence;
6. let the human review and commit manually.

## 2. When To Onboard A Project

Onboard a project when:

- it is real work, not only a Project Coffee internal test;
- the first change can be low-risk and small;
- the project has a local repository or folder you can review safely;
- the human wants future agent work to follow Project Coffee rules;
- the work benefits from Brew Log, Roastery, and Ledger evidence.

Do not onboard during a production incident, secret cleanup, large refactor, or
unclear migration. Use Decaf Mode first.

## 3. Project Selection Checklist

Prefer a first onboarding target that is:

- local-only or low external impact;
- small enough to map quickly;
- covered by at least one validation command;
- free of required secret access for the first shot;
- easy for the human to review;
- not blocked by dependency installation.

Brew 8 selected `apps/coffee-status` because it was local, tested, already
understood, and had a tiny README improvement available.

## 4. Safety Pre-Check

Before inspecting a project:

- read any local `AGENTS.md` or `PROJECT_COFFEE.md`;
- check repository status;
- avoid `.env`, credential, key, token, OAuth, SSH, private, production, and
  regulated-data files;
- avoid generated folders, dependency folders, caches, and build output;
- confirm no staging or commit will happen without human approval.

If the project requires secrets to understand or validate, stop and ask.

## 5. Decaf Repo Map Prompt

Use a read-only prompt like this:

```text
Shot: Project onboarding / Decaf repo map

Mode: Decaf Mode only.

Inspect safe, high-level files only:
- README files
- package/config/build files
- source tree names
- test folders
- docs
- existing AGENTS.md or PROJECT_COFFEE.md
- ignore files

Do not edit files, stage, commit, install packages, run models, or inspect
secrets/private data.

Output:
1. What the project appears to do.
2. Main components.
3. Language/framework/build system.
4. How it appears to run or test.
5. Existing safety/AI workflow files.
6. Missing Project Coffee onboarding files.
7. One tiny safe improvement candidate.
8. Proposed onboarding plan.
9. Files likely to change.
10. Validation commands.
11. Risks and rollback path.
```

## 6. Minimal Onboarding File Set

Use this skeleton only when the project needs local Project Coffee memory:

```text
AGENTS.md
PROJECT_COFFEE.md
.cursorignore
.cursorindexingignore
brew-log/projectbrief.md
brew-log/active_context.md
brew-log/progress.md
knowledge/00_index.md
roastery/tasting_notes.md
ledger/cost_log.md
```

For a project inside a larger monorepo, place this skeleton at that project
root. Brew 8 placed it under `apps/coffee-status/`.

## 7. Spill Guard Setup

Add or verify ignore files that exclude:

- `.env` and local environment files;
- secrets, credentials, private data, keys, tokens, passwords, and OAuth blobs;
- SSH keys and certificate/key material;
- dependency folders;
- virtual environments;
- caches;
- build output;
- logs;
- OS/editor junk.

Do not include the literal staged secret-check pattern in project docs. Refer to
it as the staged secret-pattern check from Project Coffee policy.

## 8. Brew Log Setup

Create:

- `brew-log/projectbrief.md`
- `brew-log/active_context.md`
- `brew-log/progress.md`

The project brief should capture purpose, boundaries, current shape, and first
onboarding shot. Active context should name the current state, next actions, and
blockers. Progress should record onboarding shots in a small table.

Coffee Status example:

- `apps/coffee-status/brew-log/projectbrief.md`
- `apps/coffee-status/brew-log/active_context.md`
- `apps/coffee-status/brew-log/progress.md`

## 9. Pantry Setup

Create `knowledge/00_index.md`.

Keep it sparse at first. Link only safe, useful project notes. Do not store
secrets, credentials, private data, or production data. Mark stale or uncertain
notes clearly.

## 10. Roastery And Ledger Setup

Create:

- `roastery/tasting_notes.md`
- `ledger/cost_log.md`

Roastery records workflow evidence, validation, model use, and what worked.
Ledger records costs, tokens, time, value notes, and unknowns. Unknown cost or
token data should be marked `Unknown`, not guessed.

## 11. First Tiny Improvement Criteria

The first improvement should be:

- low-risk;
- easy to review;
- small enough for one commit;
- testable or manually verifiable;
- independent of secrets and external services;
- not a broad refactor.

Good examples:

- replace a README placeholder with run/test instructions;
- fix a typo in docs;
- add one missing test for existing behavior;
- improve one local error message;
- clarify one local config section.

Brew 8 used the README placeholder in Coffee Status as the first tiny
improvement.

## 12. Validation Commands

Choose commands that match the project and change. Examples:

```powershell
python -m unittest discover -s apps/coffee-status/tests
python -m py_compile apps/coffee-status/app.py apps/coffee-status/src/readers.py apps/coffee-status/src/status_builder.py apps/coffee-status/src/status_model.py
git diff --check
git status --short
```

For another project, replace these with the local test, lint, build, or manual
verification commands. Do not install dependencies without human approval.

## 13. Human Review And Manual Commit Workflow

After implementation:

1. summarize changed files and validation results;
2. human reviews the diff;
3. human stages only intended files;
4. human runs the staged secret-pattern check from Project Coffee policy;
5. human commits manually if satisfied.

Agents should not stage or commit unless explicitly approved for that exact
action.

## 14. Closeout Checklist

The onboarding is complete when:

- Project Coffee onboarding files exist;
- Spill Guard files are present;
- Brew Log reflects current project state;
- Pantry index exists;
- Roastery evidence exists;
- Ledger evidence exists;
- one tiny real improvement is complete;
- validation was run or the reason it could not run is recorded;
- human review happened;
- human manual commit happened.

Record the final state in the project Brew Log and Roastery. Include commit
hashes if available.

## 15. Common Mistakes

- Staging placeholders instead of replacing them.
- Committing too much or mixing onboarding with unrelated refactors.
- Putting the literal secret-check pattern in docs.
- Forgetting app-local Brew Log updates.
- Skipping Roastery or Ledger evidence.
- Claiming costs, tokens, or model quality when they are unknown.
- Installing dependencies as part of onboarding without explicit approval.
- Treating onboarding as permission to inspect secrets.

## 16. Example Sequence From Coffee Status

Brew 8 proved this sequence:

| Shot | Purpose | Result |
| --- | --- | --- |
| 8A | Decaf repo map | Coffee Status selected as a low-risk real project |
| 8B | Minimal Coffee skeleton | App-local rules, Brew Log, Pantry, Roastery, Ledger, and Spill Guard files added |
| 8C | First tiny improvement | README gained local run, test, dependency, and safety notes |
| 8D | Evidence recording | Validation, changed files, review/commit state, cost/token unknowns, and lessons recorded |
| 8E | Closeout | Completion criteria reviewed and Brew 8 marked complete |

Use this as the default path for future project onboarding unless the project is
too risky, too large, or blocked by missing human context.
