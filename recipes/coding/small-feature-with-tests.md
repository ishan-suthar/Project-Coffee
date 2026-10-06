# Recipe: Small Feature With Tests

Recipe name: Small Feature With Tests  
Version: v0.1  
Created: 2026-07-02  
Applies to: Routine coding tasks that add or change behavior and require verification

## Purpose

Implement a small, scoped feature or behavior change with tests and a Brew Log closeout — without scope creep or large diffs.

## When to use

- New function, module, or endpoint with clear boundaries
- Behavior change covered by unit or integration tests
- Espresso Shot or Americano mode after plan approval
- First end-to-end Barista workflow test (Phase 1 Track F)

## Inputs needed

- Feature description and acceptance criteria
- Files likely to change
- Test framework in the project (or agreement to add minimal test)
- Approval to edit (explicit or implied for the shot)

## Prompt / procedure

```text
Barista, implement a small feature with tests.

Feature: [describe behavior and acceptance criteria]
Scope: [files or modules allowed to change]
Mode: Espresso Shot (or Americano if slightly larger)

Follow recipes/coding/small-feature-with-tests.md:

1. Decaf check — confirm scope is small; if not, propose Cold Brew plan instead.
2. Inspect — read target files and existing tests.
3. Plan — list files to change, tests to add, verification command.
4. Wait for approval if risk is meaningful.
5. Implement — minimal diff only; match project conventions.
6. Verify — run tests and lint on touched files; report results.
7. Document — Brew Log closeout (active_context, progress, lesson if any).
8. Offer Sentinel Review if security-sensitive.
```

## Verification

- [ ] Tests exist or were updated for the new behavior
- [ ] Tests pass (command and result stated)
- [ ] Lint/type check clean on touched files if applicable
- [ ] Diff is reviewable and minimal
- [ ] Brew Log updated per closeout ritual

## Common failure modes

- Feature grows mid-task → stop and re-plan in Cold Brew mode
- No test harness → agree minimal test approach before coding
- Over-engineering → revert to smallest useful version
- Skipping Brew Log → always close out meaningful work

## Model notes

- Best Bean: project House Blend coding model (TBD Shot 3)
- Cheap acceptable Bean: fast coding model for trivial features
- Escalation Bean: stronger model if tests fail repeatedly or design is unclear

## Example output

Summary format:

```text
## Changes
- [file]: [what changed]

## Verification
- [command]: [pass/fail]

## Open
- [remaining items]

## Brew Log
- Updated active_context.md and progress.md
```

## Lessons learned

*Add entries here after using this Recipe.*
