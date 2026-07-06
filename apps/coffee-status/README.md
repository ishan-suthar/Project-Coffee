# Coffee Status

A local-only status dashboard for Project Coffee.

Coffee Status reads selected Project Coffee status files and displays a small
dashboard for local review. It should not expose secrets, credentials, private
data, or unrestricted Ledger/Roastery contents.

## Requirements

Runtime dependency:

```text
streamlit
```

Do not install dependencies without human approval.

## Run

From the repository root, when Streamlit is already available locally:

```powershell
streamlit run apps/coffee-status/app.py
```

## Test

Run the unit tests from the repository root:

```powershell
python -m unittest discover -s apps/coffee-status/tests
```

Optional syntax check:

```powershell
python -m py_compile apps/coffee-status/app.py apps/coffee-status/src/readers.py apps/coffee-status/src/status_builder.py apps/coffee-status/src/status_model.py
```

## Safety

- Local-only dashboard.
- No secrets, `.env` files, credentials, tokens, SSH keys, OAuth blobs, or
  private data.
- Ledger and Roastery files are existence-only in the current app model.
- Human reviews diffs and commits manually.
