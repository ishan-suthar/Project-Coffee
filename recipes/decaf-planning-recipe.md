# Recipe: Decaf Planning

Recipe name: Decaf Planning
Version: v0.1
Created: 2026-07-04
Applies to: Read-only planning shots before implementation

## When to use

- Use when the user asks for planning, review, scope selection, or next-shot
  design without implementation.
- Use before medium-risk work, broad changes, or unclear requirements.
- Do not use when the user has already approved a small implementation shot.

## Inputs expected

- Goal:
- Current state:
- Allowed files to inspect:
- Forbidden files or secrets:
- Candidate approaches:
- Required final report:

## Workflow

1. Confirm Decaf Mode and no-edit boundaries.
2. Check `git status --short` and recent commits.
3. Read `knowledge/00_index.md` before larger docs.
4. Read `brew-log/active_context.md` and only the smallest task-relevant files.
5. Compare options against goal, risk, token cost, and scope.
6. List likely files to change in a future implementation shot.
7. List tests, checks, assumptions, and risks.
8. Recommend one next shot and stop before implementation.

## Rules

- One Shot = One Responsibility.
- No file edits during Decaf Mode unless explicitly allowed as planning docs.
- Do not inspect secrets, credentials, API keys, tokens, or private data.
- Prefer Pantry summaries before raw docs.
- Avoid broad folder scans when a smaller file list will answer the question.
- Ask before implementation, commits, installs, network calls, or expensive work.

## Verification

- [ ] Current repo state was checked.
- [ ] Pantry index was used before larger docs.
- [ ] Recommendation is one small next shot.
- [ ] Likely files, checks, risks, and assumptions are listed.
- [ ] No implementation was performed.
- [ ] Nothing was staged or committed.

## Failure modes

- The user actually needs implementation, not planning.
- Pantry is stale or insufficient.
- Scope expands into multiple responsibilities.
- Required files are forbidden or sensitive.
- Verification cannot be defined for the next shot.

## When to escalate

- Escalate to human clarification when scope or safety boundaries are ambiguous.
- Escalate to a stronger review model only for high-risk architecture, security,
  legal, medical, financial, or hardware-critical planning.
- Ask the human before reading sensitive material or using external services.

## Copyable short Order snippet

```text
Barista, use recipes/decaf-planning-recipe.md.

Goal: [planning goal]
Current state: [known state]
Candidates: [options]
Forbidden: no implementation, no secrets, no commits

Report the recommended next shot, likely files, checks, risks, assumptions, and
confirm nothing was changed.
```
