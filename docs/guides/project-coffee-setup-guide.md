# Project Coffee Setup Guide

Status: v0.1 practical guide
Date: 2026-07-06
Platform: Windows with PowerShell

This guide prepares Project Coffee for local development on a Windows machine.
It avoids secrets by design. Do not paste API keys into chat, documentation, or
repository files.

## 1. Prerequisites

Install or confirm:

- Git for Windows
- Python 3
- Cursor
- PowerShell

Useful checks:

```powershell
git --version
python --version
Get-Host
```

Do not install or upgrade tools from an agent session without human approval.

## 2. Recommended Folder Layout

Keep Project Coffee in a normal local workspace, for example:

```text
C:\Users\<you>\Project_Coffee
```

Keep credentials outside the repository. Do not store `.env` files, API keys,
tokens, SSH keys, OAuth blobs, or private data in the repo.

## 3. Clone Or Open Project Coffee

If cloning fresh, use Git from a trusted remote:

```powershell
git clone <trusted-project-coffee-repo-url>
cd Project_Coffee
```

If the repo already exists, open the folder in Cursor:

```powershell
cd C:\Users\<you>\Project_Coffee
```

Use placeholders like `<you>` and `<trusted-project-coffee-repo-url>` as values
to replace manually. Do not paste the angle-bracket placeholders into commands
unchanged.

## 4. Verify Repository Health

From the repository root:

```powershell
git status --short
git log --oneline --decorate -5
```

Expected setup state:

- `git status --short` is empty or contains only changes you recognize.
- Recent commits match the work you expect.
- No secret files are staged or visible in review output.

## 5. Cursor Setup

Open the repository folder in Cursor.

Confirm these files exist:

- `AGENTS.md`
- `PROJECT_COFFEE.md`
- `.cursor/rules/`
- `.cursorignore`
- `.cursorindexingignore`

Cursor should read the rules under `.cursor/rules/`. Start new agent sessions
with the relevant Brew/Shot goal and boundaries. For unclear or risky work,
start in Decaf Mode.

## 6. Spill Guard Files

Project Coffee uses Spill Guard to keep secrets and generated files out of
normal agent context and commits.

Check these files:

- `.gitignore`
- `.cursorignore`
- `.cursorindexingignore`

They should exclude secrets, credentials, dependency folders, virtual
environments, caches, build output, generated files, and local overrides.

If a secret appears in output or a diff, stop. Do not repeat the value. Rotate
the secret outside the repo and review Spill Guard coverage.

## 7. OpenRouter Setup

OpenRouter is the current model gateway, but Project Coffee is not permanently
tied to it.

Rules:

- Use an environment variable or Cursor settings only.
- Do not put keys in repository files.
- Do not paste keys into chat.
- Do not include key examples in docs.
- Use non-sensitive prompts for connectivity tests.
- Review pricing before premium model use.

For CLI tools, use an environment variable in the local shell when explicitly
needed and approved. For Cursor-only use, configure the provider in Cursor
settings.

## 8. Run Local Validation

Coffee Status tests:

```powershell
python -m unittest discover -s apps/coffee-status/tests
```

Coffee Certification tests:

```powershell
python -m unittest discover -s apps/coffee-certification/tests
```

Optional syntax check for Coffee Status:

```powershell
python -m py_compile apps/coffee-status/app.py apps/coffee-status/src/readers.py apps/coffee-status/src/status_builder.py apps/coffee-status/src/status_model.py
```

Whitespace check:

```powershell
git diff --check
```

## 9. Run The Certification Tool

List required certification steps:

```powershell
python apps/coffee-certification/app.py --list-required
```

Run a complete certification report by passing all completed steps:

```powershell
python apps/coffee-certification/app.py `
  --completed "Decaf Mode" `
  --completed "Planning" `
  --completed "Implementation" `
  --completed "Tests" `
  --completed "Brew Log update" `
  --completed "Roastery entry" `
  --completed "Coffee Ledger entry" `
  --completed "House Blend usage" `
  --completed "Diff review" `
  --completed "Human approval" `
  --completed "Manual commit"
```

The report should print `Status: COMPLETE` only when all required steps are
supplied.

## 10. Troubleshooting

| Issue | What to do |
| --- | --- |
| PowerShell placeholders fail | Replace placeholders like `<you>` before running commands. |
| LF-to-CRLF warnings | Usually normal on Windows when Git rewrites line endings; review actual diff content. |
| Secret-check false positives | Stop and inspect the staged file names and matching lines carefully; do not commit until resolved. |
| Untracked onboarding files | Review with `git status --short`; stage only intended files after human review. |
| Tests cannot import modules | Run commands from the repository root unless a guide says otherwise. |
| Streamlit is missing | Do not install it from an agent session; ask the human for dependency approval. |
| OpenRouter auth fails | Check local environment or Cursor settings outside the repo; do not print or paste keys. |

## 11. Safe Commit Workflow

1. Review `git status --short`.
2. Review the diff.
3. Stage only intended files.
4. Run the staged secret-pattern check by name from Project Coffee policy.
5. If the check prints anything, stop and do not commit.
6. Run relevant tests or checks.
7. Commit manually with a clear message.

Agents should not stage or commit unless the human explicitly approves that
specific action.

## 12. Next Step After Setup

After setup works, run a tiny Decaf planning shot:

```text
Brew [number] / [shot] - Decaf repo map

Goal: inspect safe high-level files and identify one tiny improvement.
Mode: Decaf Mode only.
Stop before editing.
```

Then follow the Operating Manual for approval, implementation, validation,
evidence, review, staged secret-pattern check, and human commit.
