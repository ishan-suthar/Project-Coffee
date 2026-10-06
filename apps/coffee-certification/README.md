# Coffee Certification

A small Python standard-library project for Brew 7.

This app validates whether a Project Coffee workflow has covered the required
end-to-end certification steps. It is intentionally local-only and dependency
free.

## Required Steps

The certification checklist covers:

- Decaf Mode
- Planning
- Implementation
- Tests
- Brew Log update
- Roastery entry
- Coffee Ledger entry
- House Blend usage
- Diff review
- Human approval
- Manual commit

## Certification Status

Brew 7 is complete when all required steps are supplied and the report prints
`Status: COMPLETE`.

## Run

List the required steps:

```powershell
python apps/coffee-certification/app.py --list-required
```

Build a report from completed steps:

```powershell
python apps/coffee-certification/app.py `
  --completed "Decaf Mode" `
  --completed "Planning" `
  --completed "Implementation"
```

## Test

Run the tests from the repository root:

```powershell
python -m unittest discover -s apps/coffee-certification/tests
```
