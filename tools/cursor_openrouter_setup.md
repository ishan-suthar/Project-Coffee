# Cursor and OpenRouter Setup

Version: v0.1 Phase 1  
Date: 2026-07-02  
Purpose: Local setup guide for Coffee Counter + Coffee Core — **no secrets in repo**

## Roles

| Coffee term | Current implementation | Independence |
| --- | --- | --- |
| Coffee Counter | Cursor | Replaceable IDE (VS Code, etc.) |
| Coffee Core / gateway | OpenRouter | Replaceable gateway (direct APIs, local) |
| Barista | Orchestrator role + rules | Not tied to Cursor or OpenRouter |
| House Blend | `config/house_blend.md` | Configuration, not identity |

## API key rules (Spill Guard)

**API keys must stay only in Cursor settings or local environment.**

| Do | Do not |
| --- | --- |
| Store key in Cursor → Settings → Models / API keys | Write keys into any repo file |
| Use OS env vars for CLI tools (if added later) | Paste keys into chat prompts |
| Add `.env` to `.gitignore` (already done) | Log keys in Brew Log, Roastery, or Ledger |
| Rotate keys if accidentally exposed | Commit `.env` or config with secrets |

If a key is exposed: rotate immediately, do not repeat the key in documentation, record incident in `brew-log/mistakes.md` without the secret value.

## Cursor setup (Coffee Counter)

1. Open **Cursor Settings** → **Models** (or equivalent API section).
2. Add **OpenRouter** as the provider using your key from [openrouter.ai](https://openrouter.ai) — enter only in Cursor UI, not in this repo.
3. Enable or add models per House Blend draft:
   - Nemotron (default reasoning / long-context)
   - Qwen Coder or DeepSeek Coder (fast coding — pick after bake-off)
   - Optional: Claude for approved escalation only
4. Set **default model** in Cursor to Nemotron (or your preferred House Blend default) for daily Barista work.
5. Keep **Project Coffee rules** active: `.cursor/rules/` applies Barista behavior automatically.

Cursor is the current surface; `AGENTS.md` and `baristas/` remain portable to other agents.

## OpenRouter setup (Coffee Core)

1. Create an OpenRouter account and API key at [openrouter.ai](https://openrouter.ai).
2. Configure the key **only** in Cursor (see above) or local env for future CLI — never in `config/` or `tools/` files.
3. Review OpenRouter model list and pricing before enabling premium models.
4. For Shot 3B connectivity test: use a **free or cheapest** model and a **non-sensitive** prompt (see below).

## Shot 3B — live connectivity test (when approved)

Not part of Shot 3A. When you approve live testing:

1. Confirm key is in Cursor only.
2. Send a trivial prompt (e.g. "Reply with OK and model name").
3. Log result in `ledger/cost_log.md` and `ledger/token_log.md` (no secrets).
4. Optional: one line in `roastery/tasting_notes.md`.
5. Update `brew-log/progress.md`.

**Never** use sensitive repo content for the first connectivity test.

## Free / testing endpoints

Per `config/house_blend.md`:

- Use free-tier models only for small, non-sensitive tests.
- Never send credentials, private data, or proprietary content to free endpoints.

## Troubleshooting

| Issue | Check |
| --- | --- |
| Model not listed | OpenRouter model ID in Cursor; provider enabled |
| Auth errors | Key in Cursor settings only; key valid on OpenRouter dashboard |
| High cost | Wrong default model; switch default to Nemotron or fast Bean |
| Rules ignored | `.cursor/rules/` present; start new Agent session |

## What this doc does not cover

- Cline or Continue sidecars (deferred per Phase 1 scope)
- Automated routing scripts (future `scripts/` if needed)
- Git commit or CI for keys (forbidden)

## References

- `config/house_blend.md`
- `DECISIONS/ADR-0004-house-blend-routing.md`
- `GOVERNANCE_AND_SAFETY.md`
- `.gitignore`, `.cursorignore`
