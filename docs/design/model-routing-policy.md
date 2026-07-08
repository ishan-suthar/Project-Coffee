# Model Routing Policy

Status: Brew 23 / 23B scenario-reviewed draft
Date: 2026-07-08

## Purpose

This policy defines how Project Coffee should decide between local-only work,
remote Bean use, fallback Beans, comparison runs, and human approval gates.

It is a design document for future routing tools and UI. It does not change the
current runner, call models, or replace human judgment.

## Routing Modes

| Mode | Meaning | Default use |
| --- | --- | --- |
| Decaf / no model | Human and local tools only. No Bean is called. | Planning, safety checks, review, release/checklist work, and unclear tasks. |
| Local evidence only | Use local Project Coffee tools such as Evidence Bundle, Pantry Search, Doctor, Dashboard, Release Check, and Ledger Summary. | Grounded answers, current status, costs, history, and workflow evidence. |
| Default House Blend Bean | Use the current default Bean after the task is safe and approved when context leaves the machine. | Low-risk model-assisted drafting, tiny coding help, docs summaries, and approved evidence-grounded answers. |
| Fallback Bean | Use the current fallback Bean when the default Bean fails or is unavailable and the task is still safe to send remotely. | Approved follow-up after default failure. |
| Comparison Bean | Use a secondary Bean to compare quality, cost, latency, or behavior on the same Order. | Roastery benchmarks and human-approved second opinions. |
| Human approval required | Stop before sending context, spending money, changing defaults, or using sensitive/non-allowlisted file contents. | Private context, cost-bearing calls, safety-sensitive work, broad file contents, or routing changes. |
| Roastery required before routing change | Do not change House Blend roles until benchmark evidence supports it and the human approves. | Promoting, demoting, or replacing default/fallback Beans. |

## Current Bean Roles

| Role | Bean | Current policy |
| --- | --- | --- |
| Default Bean | `nvidia/nemotron-3-ultra-550b-a55b:free` | Use for approved low-risk model assistance. Evidence is strongest across the current Brew 14 benchmark pack, but still provisional. |
| Fallback Bean | `cohere/north-mini-code:free` | Use when the default Bean fails or is unavailable and remote routing is still safe. Use stricter review for grounded answers. |
| Secondary comparison / fallback Bean | `poolside/laguna-m.1:free` | Use for comparison runs or selected coding/docs fallback cases. Avoid relying on it for repo-map tasks until future evidence improves availability confidence. |

The House Blend remains provisional. It is a recorded preference from current
evidence, not a permanent model ranking.

## Task Class Routing

| Task class | Default routing decision | Approval rule | Fallback plan |
| --- | --- | --- | --- |
| Docs summary | Local evidence first; default Bean may draft or polish if content is safe. | Approval required before sending local file contents to a remote Bean unless the human has explicitly allowed that context. | Use fallback Bean if default fails and context is still safe; otherwise summarize locally. |
| Repo map | Decaf / local evidence first. | Approval required before sending repository content or evidence bundles remotely. | Keep plan local or run a comparison Bean only as a Roastery task. |
| Coding fix | Local inspection and tests first; default Bean may help with a small bounded fix after approval. | Approval required before sending code context remotely, especially private or non-allowlisted files. | Use fallback Bean for the same bounded Order if default fails and the context remains safe. |
| Pantry/evidence answer | Local evidence only by default. | Approval required before sending an evidence bundle to a remote Bean. | If grounding is weak, build a better evidence bundle or ask for human validation. |
| Release/checklist work | Decaf and local tools by default. | Remote model use requires approval and should not replace local Release Check or Doctor results. | Use local tools, record blockers, and ask for review. |
| Safety-sensitive work | Decaf / local evidence only by default. | Explicit human approval required before any remote Bean use. Some context may remain disallowed even with approval. | Ask for human review, narrow scope, or stop. |
| Private/local project question | Local evidence only by default. | Approval required before sending any local project evidence to a remote Bean. | Answer from local evidence with assumptions called out. |
| Cost/token question | Ledger Summary and local Ledger evidence only by default. | No remote Bean needed. Approval required if a paid model call is proposed to analyze costs. | Record unknowns honestly and avoid guessing. |
| Model benchmark | Roastery workflow. Comparison Beans are allowed only as explicit benchmark work. | Human approval required before model calls, cost-bearing calls, or House Blend changes. | Record failures in Roastery/Ledger and keep current routing if evidence is insufficient. |
| UI/chat request | Local evidence bundle first; future UI should show routing mode before any remote call. | Approval required before sending local context to a remote Bean. | Use local-only answer, ask for approval, or ask for a narrower query. |

## Routing Inputs

A routing decision should consider:

- user request and stated risk tolerance;
- evidence bundle safety classification;
- Coffee Doctor status;
- Release Check status;
- Ledger cost/token evidence;
- Roastery benchmark evidence;
- current House Blend config;
- whether the needed context is public, allowlisted, private, sensitive, or unknown;
- whether the task can be answered with local tools.

## Routing Outputs

Each future routing decision should produce:

- selected mode;
- selected Bean, if applicable;
- context allowed;
- context preview for any remote route;
- approval needed;
- reason;
- fallback plan.

Example:

```text
Selected mode: Local evidence only
Selected Bean: none
Context allowed: Brew Log, House Blend config, Roastery notes
Approval needed: no
Reason: The question asks for recorded Project Coffee status.
Fallback plan: Ask for human approval before sending an evidence bundle to a remote Bean.
```

## Approval Rules

- No approval is needed for local-only tools that read allowlisted Project
  Coffee docs and do not inspect secrets.
- Approval is required before sending a local evidence bundle to a remote Bean.
- Approval is required before sending file contents outside allowlisted docs.
- Approval is required before model calls that may incur cost.
- Approval is required before changing House Blend defaults or fallback roles.
- Approval is required before sending private, regulated, production,
  hardware-critical, medical, legal, or financial context to a remote Bean.

## Safety Gates

- Never send secrets.
- Never send `.env` files.
- Never send raw local Roastery outputs by default.
- Do not send private or regulated data unless the human explicitly approves and
  the workflow is safe for that data class.
- Prefer Decaf or local-only mode for safety-sensitive workflow tasks.
- If the evidence bundle marks a source as sensitive, excluded, or unknown, keep
  it local unless a human explicitly approves a safe summary.

## Failure Behavior

- If the default Bean fails, use the fallback Bean only when the task is still
  safe for remote routing.
- If a Bean is rate-limited or unavailable, record the failure in Roastery and
  Ledger when relevant.
- If grounding is weak, build a better local evidence bundle or ask for local
  validation before using a remote Bean.
- If the policy is uncertain, choose the safer local-only mode.
- If fallback output conflicts with local evidence, prefer local evidence and
  mark the conflict for human review.

## Roastery Update Rule

House Blend changes require Roastery benchmark evidence and human approval.

Do not promote, demote, or remove a Bean because of a single impressive answer,
marketing claims, or memory. Use repeatable Orders, captured outputs, quality
scores, latency, token/cost evidence, and human fixes needed.

## UI Implications

A future Project Coffee UI or chat surface should show:

- selected routing mode;
- selected Bean, if any;
- whether approval is required;
- what context would be sent remotely, with a preview before approval;
- why the Bean was selected;
- fallback plan if the route fails;
- a clear stop point before remote context is sent.

The UI should make local-only answers feel normal, not like a degraded mode.

## Brew 23B Scenario Review

The policy was reviewed against ten realistic Project Coffee scenarios before
any routing implementation or UI work.

| Scenario | Routing decision | Approval required? | Allowed context | Review result |
| --- | --- | --- | --- | --- |
| Current Brew and next Shot | Local evidence only. | No. | Brew Log, Roadmap, Changelog, and local status docs. | Covered. This should be answered from local evidence, not memory or a remote Bean. |
| Summarize the House Blend decision | Local evidence bundle first; default Bean only if a rewrite is needed. | No for local summary; yes before sending the evidence bundle remotely. | House Blend config, Roastery notes, Ledger, model-routing guide. | Covered. Future UI should show the evidence bundle preview before remote rewrite approval. |
| Fix a tiny Python bug | Local inspection and tests first; default Bean or coding-capable fallback only after context approval. | Yes before code context is sent remotely. | Small approved snippet, relevant test output, no secrets or production configs. | Covered. Local tests remain required before closeout. |
| Search Pantry for onboarding instructions | Local Pantry Search or evidence bundle. | No. | `knowledge/`, onboarding docs, template docs, Brew Log if relevant. | Covered. No remote Bean is needed. |
| Run a model benchmark | Roastery workflow with comparison Beans. | Yes before model calls, costs, or House Blend changes. | The approved Order, selected Beans, runner metadata, and summarized outputs after review. | Covered. Ledger and Roastery recording are required. |
| Send this repo context to a model | Human approval gate before any remote context. | Yes. | Context preview only; no secrets, `.env`, raw local outputs, or excluded paths. | Covered with clarification: future UI/tooling should show exactly what would be sent. |
| Why did Poolside fail? | Local Roastery/Ledger evidence only. | No. | Roastery notes, Ledger entries, House Blend config. | Covered. No model is needed to explain recorded failure evidence. |
| Which files are unsafe to retrieve? | Local policy/evidence answer. | No. | Local RAG design, evidence bundle rules, Doctor/release safety docs, this policy. | Covered. The answer should cite excluded source rules. |
| Future UI: do the next Shot for me | Decaf plan plus safe local tools. | Yes before edits, remote Bean use, staging, commits, or risky actions. | Current Brew Log, relevant docs, allowlisted local evidence. | Covered. UI must preserve human approval and manual commit gates. |
| Default Bean fails or is rate-limited | Use fallback only when task remains safe and approval covers the fallback path. | Possibly. Approval is needed if fallback was not included in the original approved route. | Same approved context; failure metadata for Roastery/Ledger. | Covered with gap: fallback consent should be explicit in future route records. |

## Gaps And Implementation Implications

- Future UI needs a visible route card: selected mode, selected Bean, context
  preview, approval state, reason, and fallback plan.
- Fallback consent should be explicit. A remote approval should say whether it
  authorizes only the default Bean or also authorizes named fallback Beans.
- Brew 24 fleet support should treat routing as project-local state: each
  project or assistant surface needs its own source allowlist, approval state,
  route decision, and evidence record.
- Fleet support should not assume one global context package is safe for every
  project. Evidence bundles need project identity and safety classification.
- Future implementation should keep local-only paths fast and normal so the UI
  does not pressure the human into unnecessary remote calls.

## Non-goals

- No model runner changes in Brew 23A or 23B.
- No automatic OpenRouter calls.
- No embeddings or vector database changes.
- No automatic context upload.
- No permanent claim that any Bean is best for all work.
