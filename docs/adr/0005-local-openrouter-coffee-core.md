# ADR-0005: Use local OpenRouter runner as current Coffee Core

Status: Accepted
Date: 2026-07-05

## Context

Project Coffee needs repeatable Roastery Cup Tests: the same Order, same
constraints, same repository state, and controlled named Beans across multiple
runs.

The original attempt to run controlled model comparisons through Cursor was not
sufficient because Cursor Free only exposed Auto mode for Agent usage, not
controlled named model selection. That made it unsuitable as the execution
surface for fair Bean comparisons.

Project Coffee should not depend on Cursor's UI for model execution experiments.
Cursor remains valuable as the Coffee Counter, but Roastery needs an execution
path Coffee can control directly.

The local OpenRouter client and Roastery runner now give Project Coffee:

- controlled model IDs;
- repeatable same-Order execution;
- local shell environment handling for `OPENROUTER_API_KEY`;
- basic retry behavior for transient provider/rate-limit errors;
- per-Bean failure logging;
- comparison tables for latency, usage metadata, previews, and errors.

This preserves the architecture:

- Cursor = Coffee Counter;
- Codex / Cursor / Cline / Continue = Brew Methods or Barista runtimes;
- local OpenRouter client wrapper = current Coffee Core;
- OpenRouter-hosted models = Beans;
- Roastery = evaluation layer;
- Ledger = cost/token/reliability tracking;
- House Blend = evidence-based routing policy.

## Decision

Project Coffee will use the local OpenRouter client and Roastery runner as the
current Coffee Core for Roastery tests and model-routing experiments.

Cursor remains the Coffee Counter. OpenRouter remains the current model gateway.
Models remain replaceable Beans. House Blend remains a routing policy based on
Roastery and Ledger evidence, not a permanent model identity.

This decision can be revisited later if OmniRoute, Cline, Continue, local
models, or another router becomes a better Coffee Core or wrapper.

## Consequences

Positive:

- Project Coffee can select exact Beans by model ID.
- Roastery Cup Tests are more repeatable and fair.
- API key handling stays local to the shell environment and out of the repo.
- Roastery evidence becomes clearer: latency, usage metadata, response previews,
  errors, and per-Bean status are captured consistently.
- Project Coffee depends less on Cursor model UI limitations for experiments.
- House Blend routing can now be updated from local evidence instead of vibes.

Negative / tradeoffs:

- Project Coffee now has more local code to maintain.
- OpenRouter availability can change.
- Free model slugs can fail, disappear, or become rate-limited.
- Runner evidence still requires human review and documentation.
- Output quality still requires human scoring; previews, latency, and token
  counts are not enough.
- This Coffee Core is practical, not permanent.

## Alternatives considered

1. **Use Cursor Auto mode only** - Rejected for Roastery tests because it does
   not provide controlled named Bean selection.
2. **Use Cursor OpenRouter integration directly** - Deferred because the current
   Cursor Free workflow did not expose reliable controlled model selection for
   Agent mode.
3. **Use Cline as a direct BYOK sidecar** - Deferred. It may become useful, but
   earlier tool-call instability made it less reliable for the first Roastery
   MVP.
4. **Continue with manual chat comparisons** - Rejected as the primary path
   because manual comparisons are harder to repeat, measure, and audit.
5. **Postpone routing work** - Rejected because Brew 5 needs evidence to make
   House Blend useful.

## Follow-ups

1. Capture full outputs for future Cup Tests, not only previews.
2. Score output quality after human review.
3. Add route, provider, model, token, and cost fields to Ledger entries where
   available.
4. Consider OmniRoute later as a possible Coffee Core replacement or wrapper.
5. Keep the staged secret-pattern check before commits:

   ```powershell
   git grep --cached -n -I -E "sk-or-v1-|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|ghp_[A-Za-z0-9_]{20,}"
   ```

6. Revisit this ADR if the current OpenRouter runner becomes unreliable or a
   better local model-routing layer appears.
