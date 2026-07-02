# House Blend — Model Routing Policy

Version: v0.1 Phase 1 Draft  
Date: 2026-07-02  
Status: Active (documentation only; live routing TBD after Roastery bake-off)

House Blend is Project Coffee's default model-routing policy. It is **configuration**, not identity. Models are Beans; this file describes how Barista chooses them.

Reference: `DECISIONS/ADR-0002-model-and-vendor-independence.md`, `DECISIONS/ADR-0004-house-blend-routing.md`, `BARISTA_CHARTER.md`.

---

## What Beans are

**Beans** are replaceable language models accessed through a gateway (currently OpenRouter). Examples: Nemotron, Qwen, DeepSeek, Claude, GPT, Codex-class models, and future providers.

- Bean names belong in configuration and the Roastery, not in Coffee's identity.
- Routing decisions should be explainable and revisable after evaluation.
- The House Blend is updated from evidence in `roastery/` and `ledger/`, not from hype.

---

## Routing overview

| Role | Bean (draft) | Gateway | Notes |
| --- | --- | --- | --- |
| Default reasoning / long-context | Nemotron | OpenRouter | Primary daily Bean for planning, synthesis, multi-file context |
| Fast coding | Qwen Coder or DeepSeek Coder | OpenRouter | Exact model ID TBD after bake-off |
| Review / sentinel | Nemotron first | OpenRouter | Claude only with explicit human approval |
| Expensive escalation | Claude or Codex-class | OpenRouter | When Barista cannot proceed confidently |
| Free / testing | Free-tier endpoints only | OpenRouter | Small tests only; never sensitive data |

**Current gateway:** OpenRouter (implementation choice; replaceable per ADR-0002).

---

## Default Bean

**Default reasoning / long-context Bean: Nemotron via OpenRouter.**

Use Nemotron as the House Blend default when:

- the task needs multi-file or long-context reasoning;
- Barista is planning, routing, or synthesizing across docs;
- routine implementation is moderate scope (Americano mode);
- review work does not yet require premium escalation.

Do **not** use Nemotron (or any remote Bean) as default when:

- Decaf Mode is active (no API calls required for read-only work);
- the task is trivial and a fast coding Bean suffices;
- sensitive private data would be sent to a remote model without approval.

---

## When to use cheap / fast Beans

Route to **Qwen Coder, DeepSeek Coder, or comparable fast coding Beans** when:

- Espresso Shot mode: small, isolated code edits;
- scope is one or few files with clear acceptance criteria;
- latency and cost matter more than deep architecture reasoning;
- the Recipe or specialist is `espresso_fast_coder.md`.

**Exact fast coding model:** TBD — select after Roastery bake-off on a small coding benchmark. Until then, Barista states which candidate Bean it would use and why.

**Do not** use cheap Beans for:

- security-sensitive review without Sentinel follow-up;
- large refactors or Cold Brew milestones;
- tasks where a previous cheap attempt failed.

---

## When to use Nemotron

Use **Nemotron** when:

- long context or cross-document reasoning is needed;
- Barista orchestrator is running the full brewing cycle;
- Cappuccino-style research synthesis with Pantry context;
- Sentinel Review at standard tier (before premium escalation);
- default daily work where no cheaper Bean is clearly sufficient.

---

## When to escalate to Claude / Codex-level models

Escalate to **Claude, Codex-class, or strongest available premium Bean** only when:

- architecture or subtle correctness risk is high;
- cheaper Beans disagree or failed verification;
- security, safety, or production impact is significant;
- the codebase is large or unfamiliar and Nemotron is insufficient;
- Barista **cannot proceed confidently** with the current Bean.

**Requirements before escalation:**

1. State why escalation is needed.
2. Estimate rough cost (context size × model tier).
3. Name cheaper alternatives already considered.
4. Obtain **explicit human approval** before running large expensive tasks.

Premium Beans are **escalation specialists**, not defaults.

---

## When to stay in Decaf Mode

Stay in **Decaf Mode** (read-only; no remote model required for local inspection) when:

- user requests "Decaf Mode", "plan only", "read only", or "do not edit";
- risk or uncertainty is high (unfamiliar repo, production, secrets);
- the task is planning, explanation, or review of a proposal only;
- credentials, migrations, or destructive actions are under consideration;
- sensitive data must not leave the machine.

Decaf does not forbid using a model for *analysis* if the human approves and context is safe — but **no file edits, installs, commits, or destructive commands**.

---

## Cost and risk estimation (before each task)

Before acting, Barista should briefly state:

| Factor | What to estimate |
| --- | --- |
| Work mode | Decaf / Espresso / Americano / Cold Brew |
| Bean | Which model and why |
| Context size | Small / medium / large (files and docs in scope) |
| Risk | Low / medium / high (data, production, scope) |
| Cost | Rough tier: negligible / low / moderate / high |
| Approval | Needed? (yes/no and for what) |

**Pause and ask** when risk is medium-high, cost is moderate-high, or sensitive data may enter the prompt.

---

## Coffee Ledger — logging model usage

After tasks with known or estimable API usage, log to:

- `ledger/cost_log.md` — date, task, model, task type, est./actual cost, value notes
- `ledger/token_log.md` — date, task, model, input/output tokens, total, notes

**Never log:** API keys, tokens as credentials, or secret values.

Log even rough estimates when exact billing is unknown — improves routing over time.

---

## Roastery — recording model quality

When comparing Beans or after notable model performance:

1. Use `TEMPLATES/model_scorecard.md`
2. Save to `roastery/model_scorecards/`
3. Add summary pointers in `roastery/tasting_notes.md` if useful

Record: correctness, completeness, code quality, instruction following, cost, latency, supervision needed, risk behavior, reuse potential.

**Promote or demote** Beans in this file only after evidence from bake-offs (Shot 4+).

---

## Free / testing Beans

Use **free-tier OpenRouter endpoints** only when:

- running small connectivity or trivial prompts (Shot 3B);
- Roastery benchmark dry runs on non-sensitive fixtures;
- cost exploration with explicit human approval.

**Never** use free/testing Beans for:

- private credentials, medical, financial, or proprietary data;
- production decisions;
- large context dumps.

---

## Revision policy

Update this file when:

- Roastery bake-off results favor a different fast coding Bean;
- pricing or availability changes materially;
- a Bean repeatedly fails verification for a task class.

Record substantive changes in `DECISIONS/` and `brew-log/decisions.md`.

---

## Quick routing table

| Task type | Mode | Bean (draft) |
| --- | --- | --- |
| Plan, explain, review proposal | Decaf | None required (local); or Nemotron if analysis approved |
| Tiny code fix | Espresso Shot | Fast coding Bean (TBD) |
| Small feature with tests | Espresso / Americano | Fast coding or Nemotron |
| Multi-step milestone | Cold Brew | Nemotron; escalate if stuck |
| Research synthesis | Cappuccino | Nemotron + Pantry |
| Code/security review | Decaf / Sentinel | Nemotron; Claude with approval |
| Architecture / hard bug | Cold Brew | Nemotron → escalate to Claude/Codex with approval |
| Connectivity test | Espresso | Free Bean; non-sensitive prompt only |
