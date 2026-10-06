# ADR-0002: Model and vendor independence

Date: 2026-07-02
Status: Accepted

## Context

The AI model ecosystem changes quickly. Building around a single vendor can create lock-in, cost problems, and workflow fragility.

## Decision

Coffee will use a modular model-routing policy called House Blend. OpenRouter is the current practical gateway, but it is not part of Coffee's identity.

## Consequences

- Model selection is configuration, not architecture.
- Coffee can use cheap models for routine tasks and stronger models only when needed.
- Expensive models are escalation specialists, not defaults.
- Roastery evaluations guide routing choices.
