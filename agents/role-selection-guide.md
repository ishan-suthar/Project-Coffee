# Barista Role Selection Guide

Status: Brew 4 token-efficiency guide
Last updated: 2026-07-04

Use this guide to pick a role without rereading every role card. Default to the
smallest role that matches the task.

## Default Starting Role

Start with `agents/barista-main.md` when the task is unclear, multi-step, or
needs planning, routing, verification, or closeout. For planning-only work, also
use `recipes/decaf-planning-recipe.md`.

## Role Selection Table

| Task shape | Use this role | Do not use when |
| --- | --- | --- |
| Planning, routing, closeout, unclear scope | `agents/barista-main.md` | A narrower role clearly fits. |
| Tiny code fix, small test, simple script, minimal refactor | `agents/espresso-fast-coder.md` | Requirements are unclear, risky, or architectural. |
| Python, AI/ML, data, notebooks, Streamlit, small eval utilities | `agents/mocha-python-ai.md` | Data is sensitive or dependencies/external calls are not approved. |
| Research summaries, literature maps, method extraction | `agents/cappuccino-research.md` | The task needs code edits or unsupported high-stakes conclusions. |
| STM32, ESP32, FreeRTOS, firmware, sensors, datasheets | `agents/macchiato-embedded.md` | Hardware assumptions are unverified or flashing is requested without approval. |
| Diff, maintainability, tests, security/privacy, rollback risk | `agents/flat-white-code-review.md` | The user wants edits rather than review. |
| Docker, Compose, GitHub Actions, Terraform, Kubernetes, deploy planning | `agents/cortado-devops-infra.md` | Applying, deploying, credentials, or destructive infra actions are requested. |

## Escalation Rules

- If scope crosses roles, return to Main Barista to split the shot.
- If the task is high-risk, use Decaf planning before implementation.
- Ask before installs, commits, deployments, external calls, credentials,
  destructive commands, or premium-model use.
- Human judgment and manual commits remain final.

## Token-Saving Rules

- Read `knowledge/00_index.md` before large docs.
- Pick one role card, not several, unless the task has a clear handoff.
- Read the selected role card and task-specific files only.
- Prefer recipes by path instead of pasting long instructions.
- Stop and re-plan if a role would require broad scans.

## Copyable Short Order Snippet

```text
Barista, use agents/role-selection-guide.md.

Goal: [task goal]
Mode: [planning / implementation / review]
Scope: [allowed files]
Forbidden: [forbidden files/actions]

Choose the smallest matching role, read Pantry first, avoid broad scans, and
report the selected role, reason, checks, risks, and next shot.
```
