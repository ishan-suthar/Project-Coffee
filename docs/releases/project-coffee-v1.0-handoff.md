# Project Coffee v1.0 Handoff

Status: Brew 25A draft
Date: 2026-07-08

This handoff summarizes the Project Coffee stronger-base state before UI work.
It is meant for future-you, a new Barista, or a human reviewer who needs the
shape of the system without reading every Brew.

## What Project Coffee Is

Project Coffee is a local-first AI operating system for human-centered
engineering work. It keeps workflow rules, project memory, model evidence,
cost notes, safety gates, and reusable tools inside the repository.

Project Coffee is not a single-model wrapper. Beans are replaceable. Human
judgment remains final.

## Current Architecture

| Layer | Current implementation |
| --- | --- |
| Coffee Counter | Cursor-first workflow today; future UI after v1.0 stronger-base closeout |
| Barista workflow | AGENTS rules, operating manual, Brew Log, templates, approval gates |
| Coffee Core | Local OpenRouter client and Cup Test runner for approved model tests |
| Pantry | Markdown knowledge, Pantry Search, Pantry Intake workflow, Evidence Bundle MVP |
| Roastery | Cup Tests, captured local outputs, benchmark pack, report generator, tasting notes |
| Ledger | Cost/token/workflow notes and Ledger Summarizer |
| Safety | Spill Guard ignores, Doctor, Release Check, no secret inspection, human commits |
| Fleet | Local multi-project registry and Fleet Status tool |
| Routing | House Blend config plus Model Routing Policy |

## Completed Brews Through Brew 25

| Brew | Result |
| --- | --- |
| Brew 1-4 | Repository, Spill Guard, Cursor-first workflow, and early operating foundation |
| Brew 5 | Roastery MVP and first House Blend evidence |
| Brew 6 | Safety and Constitution foundation |
| Brew 7 | Coffee Certification workflow validation |
| Brew 8 | First real project onboarding with Coffee Status |
| Brew 9 | Productized docs and template pack |
| Brew 10 | First external project onboarding proof |
| Brew 11 | Template installer and onboarding doctor |
| Brew 12 | Full-output capture for Cup Tests |
| Brew 13 | Markdown Pantry Search MVP and intake workflow |
| Brew 14 | Multi-task Roastery benchmark pack |
| Brew 15 | Roastery report generator |
| Brew 16 | Project Coffee Dashboard |
| Brew 17 | Coffee Doctor |
| Brew 18 | Unified Coffee CLI |
| Brew 19 | Ledger Summarizer |
| Brew 20 | Release Packaging Check |
| Brew 21 | Local RAG design |
| Brew 22 | Local Evidence Bundle MVP |
| Brew 23 | Model Routing Policy Refinement |
| Brew 24 | Multi-project Fleet Support |
| Brew 25 | v1.0 closeout checklist and handoff framework |

## Tool Inventory

| Tool | Purpose | Typical command |
| --- | --- | --- |
| Unified Coffee CLI | One command surface for common Project Coffee tools | `python tools\coffee.py --help` |
| Dashboard | Human-readable/JSON workflow status | `python tools\coffee.py dashboard --root .` |
| Doctor | Repository health diagnosis and safe repair hints | `python tools\coffee.py doctor --root .` |
| Release Check | Release readiness sections and blockers | `python tools\coffee.py release-check --root .` |
| Ledger Summary | Local cost/token/workflow evidence summary | `python tools\coffee.py ledger-summary --root .` |
| Evidence Bundle | Safe local evidence retrieval without embeddings | `python tools\coffee.py evidence-bundle --root . --query "House Blend"` |
| Fleet Status | Multi-project onboarding marker checks | `python tools\coffee.py fleet-status --root .` |
| Pantry Search | Markdown keyword search | `python tools\coffee.py pantry-search --root . --query "onboarding"` |
| Template installer | Dry-run-first onboarding skeleton copy | `python tools\coffee.py install-template --target path\to\repo` |
| Onboarding check | Required Project Coffee file check | `python tools\coffee.py check-onboarding --target path\to\repo` |
| Roastery report | Draft summary from local Cup Test manifests | `python tools\coffee.py roastery-report --run-dir roastery\local_cup_outputs` |
| Cup Test runner | Approved model benchmark runner | `python roastery\run_cup_test.py --list-cup-tests` |

## Safety Rules

- One Shot = One Responsibility.
- Barista writes tools.
- Human runs tools.
- Roastery measures results.
- Human reviews diffs and commits.
- Use Decaf Mode for unclear, risky, or read-only work.
- Do not inspect, print, store, or commit secrets.
- Do not send local context to a remote Bean without approval.
- Do not stage, commit, tag, deploy, install dependencies, or run destructive
  actions without explicit human approval.
- Before any commit, run the staged secret-pattern check from Project Coffee
  policy.

## Current House Blend

The House Blend remains provisional and evidence-based:

- Default Bean: `nvidia/nemotron-3-ultra-550b-a55b:free`
- Fallback Bean: `cohere/north-mini-code:free`
- Secondary comparison/fallback Bean: `poolside/laguna-m.1:free`

The recommendation is not permanent. House Blend changes require Roastery
evidence across relevant Order types and human approval.

## How To Validate The Repo

Run:

```powershell
git status --short
git diff --check
python tools\coffee.py doctor --root .
python tools\coffee.py release-check --root .
python tools\coffee.py dashboard --root .
python tools\coffee.py ledger-summary --root .
python tools\coffee.py evidence-bundle --root . --query "Project Coffee current Brew" --max-results 5
python tools\coffee.py fleet-status --root . --registry fleet\projects.example.json --list
python -m unittest discover
```

## How To Onboard A Project

1. Start in Decaf Mode.
2. Map safe high-level files only.
3. Dry-run the template installer.
4. Apply the template only after approval.
5. Run onboarding check or Fleet Status.
6. Complete one tiny low-risk improvement.
7. Update the app-local Brew Log, Roastery, and Ledger.
8. Let the human review the diff and commit manually.

Primary guides:

- `docs/guides/new-project-onboarding-guide.md`
- `docs/guides/template-installer-guide.md`
- `docs/guides/fleet-support-guide.md`

## How To Use Core Status Tools

- Dashboard answers "what is the current local workflow state?"
- Doctor answers "what looks unhealthy or incomplete?"
- Release Check answers "is this repo ready for a release or handoff?"
- Fleet Status answers "which registered projects look onboarded?"
- Evidence Bundle answers "what local files support this answer?"

Use these tools before asking a remote Bean. If remote context is needed, show
the context plan and ask for human approval first.

## Intentionally Not Done Yet

- No Project Coffee UI.
- No chat UI.
- No automatic remote context sending.
- No embeddings or vector database.
- No background autonomous agent.
- No auto-commit, auto-tag, or auto-deploy.
- No permanent claim that any Bean is best.

## Future UI Direction

The future Coffee Counter UI should make the local system visible before it
makes model calls easy. It should show:

- current Brew and next Shot;
- local evidence bundle previews;
- selected routing mode and why it was selected;
- approval gates before remote context is sent;
- Doctor, Release Check, Fleet, Roastery, and Ledger summaries;
- clear human review and manual commit boundaries.

## Recommended Brews After v1.0

| Brew | Focus |
| --- | --- |
| Brew 26 | Coffee Counter UI Design |
| Brew 27 | Chat UI MVP |
| Brew 28 | UI + Evidence Bundle |
| Brew 29 | UI + Routing Approval Gates |
| Brew 30 | UI packaging/polish |

## Brew 25B Validation Snapshot

Date: 2026-07-08

The v1.0 stronger-base validation stack was dogfooded locally. Git status,
recent history, existing tags, Unified CLI help/version, Dashboard, Doctor,
Release Check, Ledger Summary, Evidence Bundle, Fleet Status, focused unit
tests, syntax compilation, and release doc existence checks were run.

Result: READY WITH WARNINGS.

Blocking failures: none.

Warnings:

- Doctor reports the known ADR literal staged secret-check command warning.
- The default real fleet registry is not present; this is acceptable while the
  example registry remains the committed template.
- Evidence Bundle found useful closeout evidence but showed ranking noise on
  the `v1.0` query.

No model calls, OpenRouter calls, external APIs, tags, staging, or commits were
performed during Brew 25B.

## Handoff Notes

Project Coffee is ready to close the stronger-base phase when Brew 25 evidence
confirms docs, safety, tools, release readiness, and handoff quality. Tags and
commits remain manual human-controlled actions.
