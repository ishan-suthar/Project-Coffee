# Project Coffee Operating Manual

Status: v0.1 practical guide
Date: 2026-07-06

This manual is the daily workflow guide for Project Coffee. It is meant to be
usable without reading the full foundation documents first.

## Purpose

Project Coffee helps a human and coding agents work together through small,
reviewable, evidence-backed engineering shots. It keeps the durable system in
the repository: rules, memory, templates, project knowledge, routing policy,
evaluation evidence, and cost notes.

Project Coffee is not a wrapper around one model, editor, or provider. Models
are replaceable Beans. Cursor is the current Coffee Counter. OpenRouter is the
current model gateway. Human judgment remains final.

## v1.0 Stronger-base Closeout

The v1.0 stronger-base closeout lives in
`docs/releases/v1.0-closeout-checklist.md` and
`docs/releases/project-coffee-v1.0-handoff.md`. That closeout validates docs,
safety, tools, evidence, routing, fleet support, and handoff quality before UI
work begins.

UI work comes after the stronger-base phase. The v1.0 closeout does not add a
UI, automatic remote context sending, automatic commits, or automatic tags.

## Core Rules

- One Shot = One Responsibility.
- Barista writes tools.
- Human runs tools.
- Roastery measures results.
- Human reviews diffs and commits.
- Prefer the smallest correct diff.
- Use local context before asking a remote model.
- Do not inspect, print, store, or commit secrets.
- Record meaningful work in the Brew Log.
- Record workflow/model evidence in the Roastery when useful.
- Record cost or token notes in the Ledger when available.

## Work Modes

### Decaf Mode

Use Decaf Mode for planning, audit, review, unfamiliar repos, risky work, or
when the human says read-only. Decaf means:

- inspect only safe relevant files;
- do not edit files;
- do not install packages;
- do not stage or commit;
- do not run destructive commands;
- produce a plan and stop for approval.

### Espresso Shot

Use an Espresso Shot for a small, low-risk, approved change. The expected shape
is one narrow responsibility, a small diff, immediate validation, and a clear
closeout note.

### Cold Brew

Use Cold Brew for multi-step, higher-risk, broad, or uncertain work. Cold Brew
needs a written plan, checkpoints, rollback path, and explicit human approval
before major steps.

## Standard Workflow

1. Intake

   Clarify the shot goal, mode, allowed files, forbidden files, validation
   commands, and stop condition.

2. Decaf plan

   Check repository state, read `PROJECT_COFFEE.md`, `AGENTS.md`,
   `brew-log/active_context.md`, and the smallest task-specific files. Identify
   the smallest useful diff.

3. Approval

   Stop before editing when the user requested planning, the risk is meaningful,
   or the allowed scope is unclear.

4. Implementation

   Make only the approved change. Keep one shot to one responsibility. Do not
   mix app logic, docs, tests, and closeout unless the shot explicitly calls for
   those files.

5. Validation

   Run the smallest local checks that match the change. Examples include unit
   tests, syntax checks, `git diff --check`, and manual runtime checks when the
   human asks for them.

6. Brew Log update

   Update active context and progress after meaningful work. Record what
   changed, what was verified, what remains open, and what Coffee should
   remember.

7. Roastery and Ledger update

   Add Roastery notes for model, workflow, or project evidence. Add Ledger notes
   when cost, tokens, time, or value should be remembered. Mark unknowns as
   unknown instead of guessing.

8. Diff review

   Summarize the changed files and validation results. The human reviews the
   diff before commit.

9. Staged secret-pattern check

   Before any commit, the human stages only intended files and runs the staged
   secret-pattern check from Project Coffee policy. If it prints anything, do
   not commit.

10. Human commit

   The human commits manually after review and the staged secret-pattern check
   from Project Coffee policy. Agents do not stage or commit unless explicitly
   approved.

## Approval Gates

Ask before:

- staging, committing, pushing, or deploying;
- deleting or overwriting files;
- installing dependencies;
- running migrations;
- using credentials or touching secrets;
- making network, cloud, database, firmware, or production changes;
- sending sensitive/private context to remote models;
- making expensive model calls;
- changing medical, legal, financial, safety-critical, or hardware-critical
  outputs.

## Spill Guard Rules

Never inspect, print, store, paste, or commit API keys, tokens, credentials,
passwords, SSH keys, OAuth blobs, `.env` files, private production data, or
private regulated data.

Respect `.gitignore`, `.cursorignore`, `.cursorindexingignore`, and app-local
ignore files. If a secret appears in output or a diff, stop, avoid repeating it,
and ask the human to rotate it outside the repository.

## Definition Of Done

A shot is done when:

- the approved scope was completed;
- the diff is small and reviewable;
- validation was run or the reason it could not run is stated;
- no secrets were touched;
- Brew Log, Roastery, and Ledger were updated when meaningful;
- remaining risks and open work are named;
- human review and manual commit remain explicit.

## Rollback Habit

Every plan should have a rollback path. For small docs or code shots, rollback
usually means reverting the intended files before staging. For broader work,
name the exact files, tests, and checkpoints that make rollback safe. Avoid
destructive commands when a simple reverse patch or human-reviewed revert is
enough.

## Brew 7 And Brew 8 Validation

Brew 7 validated the end-to-end workflow with a small standard-library
certification tool. It covered Decaf Mode, planning, implementation, tests, Brew
Log update, Roastery entry, Ledger entry, House Blend usage, diff review, human
approval, and manual commit.

Brew 8 validated real-project onboarding with `apps/coffee-status`. It added an
app-local Coffee skeleton, completed a tiny README improvement, ran local
validation, recorded Roastery/Ledger evidence, and closed the onboarding after
human review and manual commits.

Together, Brew 7 and Brew 8 are the proof that Project Coffee can move from
internal workflow testing to repeatable project onboarding.

## When To Stop And Ask

Stop and ask for human review when:

- the requested change crosses more than one responsibility;
- the repo state is dirty in unrelated ways;
- required files might contain secrets or private data;
- validation requires installing packages or using credentials;
- the change touches production, infrastructure, hardware, medical, legal, or
  financial outputs;
- the model or tool output is uncertain and could mislead future work;
- a commit, push, deploy, or external action is needed.

When in doubt, return to Decaf Mode and propose the smallest next shot.
