# Coffee Status Project Coffee Brief

Coffee Status is the first real low-risk project onboarded into Project Coffee.
It is a local-only Streamlit dashboard that summarizes selected Project Coffee
status files while preserving preview limits for sensitive evaluation and cost
areas.

## Workflow

- Start with Decaf Mode for planning and review.
- Keep changes small and scoped to one responsibility.
- Use local tests before review.
- Record meaningful work in the local Brew Log.
- Record workflow evidence in the local Roastery.
- Record cost or token notes in the local Ledger when relevant.
- Human review and manual commit remain explicit.

## Local Validation

Run tests from the repository root:

```powershell
python -m unittest discover -s apps/coffee-status/tests
```

Optional syntax check:

```powershell
python -m py_compile apps/coffee-status/app.py apps/coffee-status/src/readers.py apps/coffee-status/src/status_builder.py apps/coffee-status/src/status_model.py
```

Run the dashboard only when Streamlit is already available locally:

```powershell
streamlit run apps/coffee-status/app.py
```

Do not install dependencies without human approval.
