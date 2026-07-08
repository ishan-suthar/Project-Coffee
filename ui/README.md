# Project Coffee Counter UI

Status: Brew 27A MVP

The Coffee Counter UI is a local Streamlit control panel for Project Coffee. It
wraps existing safe Project Coffee CLI tools through an allowlisted command
adapter.

## Purpose

The MVP helps you:

- view Project Coffee status;
- run Dashboard, Doctor, Release Check, Ledger Summary, Evidence Bundle, and
  Fleet Status from a local UI;
- ask Coffee for local evidence only;
- see command arguments, stdout, stderr, and exit codes;
- keep approval gates visible before future remote model work.

## Requirements

- Python
- Streamlit
- Project Coffee repository opened locally

The tests for the command adapter do not require Streamlit.

## Setup

Install Streamlit only after approving the dependency:

```powershell
python -m pip install streamlit
```

## Run

From the Project Coffee root:

```powershell
python -m streamlit run ui/coffee_counter_app.py
```

## Safety Notes

- The MVP is local-only.
- It does not call OpenRouter.
- It does not call remote Beans.
- It does not call external APIs.
- It does not edit files.
- It does not inspect raw Roastery local outputs.
- It does not stage, commit, push, or create tags.
- It does not expose arbitrary shell command execution.
- It only wraps allowlisted Project Coffee CLI commands.

## Troubleshooting

- If Streamlit is missing, run the setup command above after approving the
  dependency.
- If a command fails, check the displayed stdout, stderr, and exit code.
- If Evidence Bundle returns no results, try a narrower query.
- If Fleet Status reports a missing registry, use `fleet/projects.example.json`
  or intentionally create a local `fleet/projects.json`.
- If Brew status looks stale, run `python tools/coffee.py dashboard --root .`
  and inspect the Brew Log status files.
