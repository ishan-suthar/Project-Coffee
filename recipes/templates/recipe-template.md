# Recipe Template

Recipe name:
Version:
Created:
Applies to:

## When to use

- Use this recipe when:
- Do not use this recipe when:

## Inputs expected

- Goal:
- Scope:
- Relevant files:
- Verification available:
- Constraints or forbidden changes:

## Workflow

1. Confirm the task matches this recipe.
2. Read only the minimum context needed.
3. State the plan, files, risk, and verification.
4. Make the smallest useful change.
5. Verify with the agreed checks.
6. Report changes, results, open items, and next shot.

## Rules

- One Shot = One Responsibility.
- Prefer local-first, model-agnostic, vendor-agnostic work.
- Do not inspect secrets or credential files.
- Do not expand scope without a new plan.
- Keep prompts short by referencing this recipe instead of copying it.

## Verification

- [ ] Expected files changed only.
- [ ] Required checks ran and results were reported.
- [ ] No forbidden files or secrets were touched.
- [ ] The diff is small enough for human review.

## Failure modes

- Scope is too broad.
- Required context is missing.
- Verification cannot run.
- The task needs a stronger specialist or model.

## When to escalate

- Escalate when correctness, safety, security, or architecture risk is high.
- Escalate when a cheap or narrow approach fails verification.
- Ask the human before expensive, external, destructive, or sensitive actions.

