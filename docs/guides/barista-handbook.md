# Barista Handbook

Status: v0.1 practical guide
Date: 2026-07-06

This handbook helps you choose the right Project Coffee Barista, work mode, and
handoff pattern for a task. It is a practical companion to the Operating Manual,
role cards, and Recipes.

## 1. What A Barista Is

A Barista is a role for doing Project Coffee work. It may be performed by
Codex, Cursor Agent, Cline, another coding agent, or a human using the workflow.

Baristas do not replace human judgment. They help plan, route, implement,
verify, document, and learn from work in small safe shots.

## 2. Main Barista

Use Main Barista by default when the task is unclear, multi-step, or needs
planning, routing, verification, or closeout.

Use for:

- Decaf planning;
- repo maps;
- choosing a specialist;
- coordinating multi-file work;
- updating Brew Log, Roastery, and Ledger;
- deciding the next shot.

Reference: `agents/barista-main.md`.

## 3. Espresso

Espresso is for tiny, well-scoped work.

Use for:

- typo fixes;
- one small test;
- a narrow code fix;
- a tiny README improvement;
- simple scripts with clear validation.

Avoid Espresso when requirements are vague, architecture is involved, or the
change touches production/security-sensitive behavior.

Reference: `agents/espresso-fast-coder.md`.

## 4. Americano

Americano is routine implementation or maintenance that is larger than
Espresso but still ordinary and bounded.

Use for:

- modest feature work with tests;
- routine cleanup;
- small app behavior changes;
- multi-file but low-risk maintenance.

Americano should still start with a short plan, name validation commands, and
keep human review explicit. If the work grows, split it into Espresso shots or
move to Cold Brew.

## 5. Mocha

Mocha handles Python, AI/ML, data, notebooks, Streamlit, and small evaluation
utilities.

Use for:

- Python app work;
- small data-processing helpers;
- Streamlit utilities;
- local model/evaluation scripts;
- reproducible experiments.

Avoid Mocha for sensitive datasets, broad data scans, or new dependencies
without approval.

Reference: `agents/mocha-python-ai.md`.

## 6. Cappuccino

Cappuccino handles research-heavy and document-heavy work.

Use for:

- source-grounded research summaries;
- literature maps;
- method extraction;
- claim comparison;
- careful uncertainty notes.

Cappuccino should cite what it used, separate evidence from interpretation, and
avoid unsupported high-stakes conclusions.

Reference: `agents/cappuccino-research.md`.

## 7. Macchiato

Macchiato handles embedded, firmware, hardware, timing, pin, bus, and datasheet
work.

Use for:

- STM32, ESP32, FreeRTOS, firmware review;
- sensor interface reasoning;
- pin, timing, voltage, current, or bus assumptions;
- cautious hardware planning.

Macchiato must state hardware assumptions and ask before flashing, probing,
changing production firmware, or doing anything hardware-affecting.

Reference: `agents/macchiato-embedded.md`.

## 8. Cortado

Cortado handles DevOps, infrastructure, deployment planning, and configuration
risk.

Use for:

- Docker and Compose review;
- GitHub Actions review;
- Terraform/Kubernetes planning;
- deployment risk analysis;
- cost and rollback review.

Cortado must not apply, deploy, destroy, migrate, or use credentials without
explicit human approval.

Reference: `agents/cortado-devops-infra.md`.

## 9. Flat White

Flat White handles code review.

Use for:

- diff review;
- maintainability review;
- test coverage review;
- privacy/security review;
- rollback and risk review.

Flat White leads with findings by severity and does not edit files unless the
human explicitly changes the shot from review to implementation.

Reference: `agents/flat-white-code-review.md`.

## 10. Latte

Latte is the documentation and productization posture. It is useful when the
work is mostly explanation, guides, templates, README updates, or user-facing
process docs.

Use for:

- documentation passes;
- setup guides;
- onboarding guides;
- template packs;
- changelog and roadmap documentation;
- turning proven workflows into reusable docs.

Latte is not yet a separate role card. Use Main Barista plus the documentation
scope until a repeated pattern justifies a dedicated card.

## 11. Cold Brew

Cold Brew is for long-running, multi-step, higher-risk work.

Use for:

- milestones;
- refactors;
- migrations;
- architecture changes;
- cross-project onboarding;
- work that needs checkpoints and rollback plans.

Cold Brew requires a plan, explicit approval, incremental verification, and
human review at checkpoints.

## 12. How To Pick A Barista

Use this rule of thumb:

| Task shape | Pick |
| --- | --- |
| Unclear, planning, routing, closeout | Main Barista |
| Tiny code/test/doc fix | Espresso |
| Routine bounded implementation | Americano |
| Python, data, AI/ML, Streamlit, eval utilities | Mocha |
| Research or source synthesis | Cappuccino |
| Embedded or hardware reasoning | Macchiato |
| DevOps, infrastructure, deployment risk | Cortado |
| Review only | Flat White |
| Docs, guides, templates, productization | Latte posture |
| Large, risky, multi-step | Cold Brew |

If a task crosses roles, return to Main Barista and split it into smaller
shots.

## 13. How Baristas Use Coffee Systems

Baristas use Recipes for repeatable workflows, such as Decaf planning or small
features with tests.

They use the Brew Log to understand current context and record meaningful work.

They use the Pantry to retrieve small, relevant knowledge before broad scans.

They use the Roastery to record model or workflow evidence, including what was
validated and what remains uncertain.

They use the Ledger to record cost, tokens, time, and value when available.
Unknowns should stay unknown instead of being guessed.

## 14. Approval Gates All Baristas Must Obey

Ask before:

- staging, committing, pushing, or deploying;
- installing dependencies;
- deleting or overwriting files;
- using credentials or touching secrets;
- making network, cloud, database, firmware, or production changes;
- sending sensitive/private context to remote models;
- making expensive model calls;
- changing medical, legal, financial, safety-critical, or hardware-critical
  outputs.

All Baristas must respect Spill Guard. Do not inspect, print, paste, store, or
commit secrets, `.env` files, credentials, SSH keys, tokens, OAuth blobs,
private data, or private regulated data.

## 15. Examples

### Tiny Fix

Use Espresso. Read the named file and nearby test only. Make the smallest diff,
run the narrow validation command, update Brew Log if meaningful, and stop
before staging.

### Repo Map

Use Main Barista in Decaf Mode. Read safe high-level docs, source tree names,
test folders, and config files. Do not edit. Propose one tiny next shot.

### Test Addition

Use Espresso for a tiny test or Americano if the behavior and test touch several
files. Read the target module and existing tests. Add one focused test and run
the relevant test command.

### Research Summary

Use Cappuccino. Confirm the research question and allowed sources. Read Pantry
first, then the smallest source set. Report sources used, uncertainty, caveats,
and gaps.

### Embedded Review

Use Macchiato. Confirm board, MCU, files, and hardware assumptions. Avoid
flashing or hardware-affecting changes without approval. Report assumptions,
datasheet/source evidence, risks, and verification needed.

### Documentation Pass

Use Latte posture with Main Barista coordination. Keep the guide practical,
link to existing source docs, avoid duplicating the full foundation documents,
and run `git diff --check`.
