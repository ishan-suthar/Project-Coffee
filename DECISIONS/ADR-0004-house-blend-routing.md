# ADR-0004: House Blend routing policy

Date: 2026-07-02  
Status: Accepted

## Context

ADR-0002 established that model routing is configuration, not identity. Phase 1 Shot 3A requires a concrete House Blend policy so Barista can route Beans consistently before live OpenRouter testing.

Coffee needs defaults for reasoning, fast coding, review, escalation, and testing — without locking to a single vendor or model name in architecture docs.

## Decision

Adopt `config/house_blend.md` as the canonical House Blend routing policy with these draft defaults:

| Role | Bean | Gateway |
| --- | --- | --- |
| Default reasoning / long-context | Nemotron | OpenRouter |
| Fast coding | Qwen Coder or DeepSeek Coder (exact ID TBD) | OpenRouter |
| Review / sentinel | Nemotron first; Claude only with explicit approval | OpenRouter |
| Expensive escalation | Claude or Codex-class; only when Barista cannot proceed confidently | OpenRouter |
| Free / testing | Free-tier endpoints only; small non-sensitive tests | OpenRouter |

**Operational rules:**

- Cursor is the current Coffee Counter; Barista remains IDE-independent.
- OpenRouter is the current Coffee Core gateway; Coffee remains vendor-independent.
- API keys live only in Cursor settings or local environment — never in the repo.
- Fast coding model selection is **TBD** until Roastery bake-off (Shot 4).
- House Blend revisions require Roastery evidence or documented pricing/availability change.

## Alternatives considered

1. **Single default model for everything** — Rejected: violates cost discipline and ADR-0002.
2. **Hardcode model IDs in ADRs** — Rejected: models change; policy belongs in `config/house_blend.md`.
3. **Local-only models as default** — Deferred: may supplement later; OpenRouter is current practical gateway.

## Consequences

- Barista and Cursor rules can reference `config/house_blend.md` for routing.
- Shot 3B can test connectivity without changing this ADR.
- Shot 4 bake-off may update fast coding Bean and escalation thresholds in config only.
- No API keys or live tests are implied by accepting this ADR.

## References

- `config/house_blend.md`
- `tools/cursor_openrouter_setup.md`
- `DECISIONS/ADR-0002-model-and-vendor-independence.md`
- `BARISTA_CHARTER.md` (escalation policy)
- `EVALUATION_AND_ROASTERY.md`
