# Project Coffee — Build Summary

Originally generated 2026-07-22 (through Brew 52) from a full read of the
repository's own history plus commands run against the working tree.
**Updated 2026-07-26 to carry the narrative through Brew 55**, drawing on
the development record since Brew 52.

> **Verification note for this update.** The Brew 52 edition computed every
> figure by running a real command against the working tree. This update
> extends the *narrative* — new Brews, the current Bean roster, new
> known-issues, corrected capability facts — but it does **not** re-run the
> line-count, commit-count, live-test, or Ledger-row commands. Figures that
> require a live command are marked **[refresh]** where they are now
> known-stale, and the reader should re-run the command shown in Section 8
> to get the current value. Everything not so marked is either unchanged
> since Brew 52 or verifiable from the development record. This preserves
> the document's own rule: state what was verified, and never present an
> unverified number as a verified one.

This was AI-assisted development throughout: a human directed the
architecture, reviewed every Decaf plan before implementation, and gated
every commit. Nothing in this repository was staged, committed, or
tagged automatically.

---

## 1. What Project Coffee Is

Project Coffee is one person's local AI-assisted coding setup, built to
solve a specific, everyday problem: routing coding requests to the
cheapest model capable of handling them, tracking exactly what each
request costs, and keeping a running written record of what was built,
what broke, and why — so the system's own history is a real audit trail
instead of a vague memory. It runs entirely on one machine (with optional
LAN access for other devices in the same household), talks to models
through OpenRouter, and exposes both a browser chat UI and an
OpenAI-compatible API endpoint that tools like Cursor or Continue.dev can
point at directly.

The core mechanism is a small FastAPI service ("the router") that sits
between a client and OpenRouter. It classifies each incoming prompt,
picks a model ("Bean") according to a routing policy, streams the
response back over Server-Sent Events, checks whether the response looks
like a failure, and — if it does, and a human approves — re-runs the
request against a stronger, more expensive model. Every request writes
one row to a CSV ledger with its real cost, token counts, and outcome.
The design philosophy running through the whole project, stated
repeatedly in its own planning documents, is: build the smallest correct
thing, verify it against a real running instance (not mocks) before
calling it done, write down what was actually found (including when a
feature turns out to be broken or decorative), and never let an agent
stage, commit, or spend money without a human explicitly approving each
step.

The project uses a consistent coffee vocabulary, which this document
uses throughout: a **Bean** is one configured model (an alias like
"House Blend", its real OpenRouter model ID, pricing, and capability
flags such as vision/tool-calling) defined in `router/config/beans.yaml`.
A **Barista** is an AI persona/role card describing how an agent should
work on a given kind of task. The **Ledger** (`ledger/router_requests.csv`,
`ledger/cost_log.md`) is the cost and usage log — one machine-written CSV
row per real router request, and a hand-maintained Markdown log for
earlier, non-router work. **Pantry** is the local retrieval/knowledge
store (`knowledge/`) the router can search and cite from. The **Brew
Log** (`brew-log/active_context.md`, `brew-log/progress.md`) is the
project's running development diary, updated after each unit of work.
**Cup Test** is the evaluation/benchmark harness that runs the same
prompt across multiple Beans for comparison, and the **Roastery**
(`roastery/`) is the subsystem that holds Cup Test results and
`tasting_notes.md`, the evidence log of what actually happened on real
model runs. A **Brew** is one unit of development work — roughly one
feature or fix cycle, each preceded by a written "Decaf" plan a human
approves before any code is written, and numbered sequentially from
Brew 1 through Brew 55 across this repository's history (this update
carries the record through Brew 55; the Brew 52 edition stopped at 52).

---

## 2. Build Timeline

Every Brew, in order, as recorded in `brew-log/progress.md` and
`ROADMAP.md`. Several Brews landed together in a single commit; that is
called out explicitly rather than implying a clean 1:1 mapping. Brews
40 onward are drawn from `brew-log/progress.md`'s detailed entries, since
`ROADMAP.md`'s own Brew-history table was never updated past Brew 42
(see Section 9).

| Brew | Date | Description | Commit |
| --- | --- | --- | --- |
| 1 | 2026-07-02 | Coffee Status MVP (Streamlit status dashboard skeleton) | early history, pre-dates router work |
| 2 | 2026-07-02 | Prompt Library / Espresso Shot Archive MVP | " |
| 3 | 2026-07-03 | Coffee Status data model + builder hardening | " |
| 4 | 2026-07-04 | Token efficiency foundation: Pantry Lite index, Recipes/Baristas skeleton, role cards | " |
| 5 | 2026-07-04–05 | Roastery Cup Test MVP; first local Bean bake-off; provisional House Blend | " |
| 6 | 2026-07-05 | Safety / Constitution foundation | " |
| 7 | 2026-07-05 | Coffee Certification workflow validation project | " |
| 8 | 2026-07-05–06 | First real project onboarding (Coffee Status) | " |
| 9 (9A–9H) | 2026-07-06 | Productized docs and template pack (Operating Manual, Setup Guide, onboarding, Barista Handbook, Roastery/Ledger guide, routing guide) | " |
| 10 | 2026-07-06 | First external project onboarding proof | " |
| 11 | 2026-07-06 | Standard-library template installer + onboarding doctor | " |
| 12 | 2026-07-06 | Roastery full-output capture | " |
| 13 | 2026-07-06 | Markdown Pantry Search MVP + intake workflow | " |
| 14 | 2026-07-06 | Multi-task Roastery benchmark pack | " |
| 15 | 2026-07-06 | Roastery report generator | " |
| 16 | 2026-07-06 | Coffee Dashboard CLI | " |
| 17 | 2026-07-08 | Coffee Doctor MVP | " |
| 18 | 2026-07-08 | Unified Coffee CLI | " |
| 19 | 2026-07-08 | Ledger Summarizer | " |
| 20 | 2026-07-08 | Release Packaging Check | " |
| 21 | 2026-07-08 | Local RAG design | " |
| 22 | 2026-07-08 | Local Evidence Bundle MVP | " |
| 23 | 2026-07-08 | Model Routing Policy Refinement (design only) | " |
| 24 | 2026-07-08 | Multi-project Fleet Support | " |
| 25 | 2026-07-08 | v1.0 stronger-base closeout ("READY WITH WARNINGS") | tag `v0.1`, `v0.1-certified`, `v0.1-proven` era |
| 26 | 2026-07-08 | Coffee Counter UI Design (Streamlit-first) | " |
| 27 | 2026-07-08 | Streamlit Coffee Counter MVP | " |
| 28 | 2026-07-08 | UI + Evidence Bundle integration | " |
| 29 | 2026-07-08 | UI + routing approval gates | " |
| 30 | 2026-07-08 | UI packaging/polish decision (kept Streamlit, deferred React/Tauri) | " |
| 31 | 2026-07-08 | Streamlit polish pass | " |
| 32 | 2026-07-08 | Coffee Counter project/Fleet switching | " |
| 33 | 2026-07-08 | Remote call approval design (design only, no remote calls added) | " |
| 34 | 2026-07-08 | Remote context package builder + Safety Gate | " |
| 35 | 2026-07-09 | Approval gate dry-run UI | " |
| — | 2026-07-09 | Gate repair: fixed Spill Guard token-log ignore parity and root test discovery (`tools/run_all_tests.py` added) | `e69b814` |
| 36 | 2026-07-09 | **Coffee Core Router** (`router/`): FastAPI SSE service, classifier, routing, escalation, aliases, Ledger, generated routing policy, event contract v1.0 | `2a29f8b` |
| 37 + 38 | 2026-07-10–11 | Coffee Counter Chat UI (`web/`, Next.js) with sessions/rate/cancel; file/image attachments (ships inert, no vision Bean yet); event contract v1.1–v1.2 | landed together in `3ee8810` |
| 39 | 2026-07-11 | Animated Coffee Counter scene, device preferences, 300 KB asset budget | `4375680` |
| 40 | 2026-07-14 | Escalation approval gate UI (background-task decoupling, reload recovery); event contract v1.3 | `84070f9` |
| 41 | 2026-07-14 | Session memory proposals + Pantry retrieval with citations; event contract v1.4 | `a55c07d` |
| 42 | 2026-07-15 | Learning loop (ratings-weighted policy rebuild) + release/perf pass | `889c5f0` |
| 43 | 2026-07-15 | Simple auth, projects, chat management (bcrypt, bearer tokens) | `3fd814a` |
| 44–46 | 2026-07-15 | Response layout/Markdown fix; vertical scene assets; conversation memory (`remember_chat`); event contract v1.5 | landed together in `4539de1` |
| — | 2026-07-15 | Reserve Blend (Claude Sonnet 4.6) and Single Origin added as real premium/vision Beans, outside this log's Brew numbering | `0255a63` |
| 47 | 2026-07-15–16 | OpenAI-compatible endpoint (`/v1/chat/completions`), retry detection, shadow mode, `ledger_summary.py --mode model-usage`; escalation-concatenation bug fixed | `7b252c7` |
| — | — | LAN access config (`allowedDevOrigins`, env-configurable CORS) | `f46c557` |
| — | — | Next.js cache fix, UUID generation, local dev setup | `4e97be2` |
| — | — | Mobile-first responsive layout | `b1c20b9` |
| 48 | 2026-07-17 | Cost-inconsistency fix: real `cost_usd` + `cost_source` on every priced row; backfill CLI | `d44f81e` |
| 49 | 2026-07-17 | Per-user/global spend caps, rate limiting, real `estimate_cost_usd()` | `d8582de` |
| — | 2026-07-18 | Fixed dead Single Origin model slug (`anthropic/claude-haiku-4.5`) | `a76d674` |
| 50 | 2026-07-18 | Web search via OpenRouter, cheapest-capable Bean routing | `ca0348d` |
| 51 + 52 | 2026-07-18 | Web search cost optimization (engine migration, Kimi K2/DeepSeek V3.2 Beans) + citation surfacing (`web_sources`, `WebSourceChips`); event contract v1.6 | landed together in `cba327f` |
| — | 2026-07-18 | iOS Safari viewport meta tag + mobile composer layout fix (the earlier mobile Brew's breakpoints were unreachable on a real iPhone with no viewport meta) | post-`cba327f` |
| 53 | 2026-07-23 | Date-aware system prompt (every `/v1/order` request carries the current date, so Beans stop answering time-sensitive questions from their training cutoff); multi-address `start.ps1` (array/comma-separated `-LanIp`, default LAN + Tailscale addresses) | post-`cba327f` **[refresh]** |
| 54 | 2026-07-23 | Gemini/Gemma Beans added — **Flat White** (`google/gemini-2.5-flash-lite`, vision + tools, ~$0.0001/$0.0004) and **Day Roast** (`google/gemma-4-31b-it:free`, comparison); Reserve Blend slug corrected to canonical dotted `anthropic/claude-sonnet-4.6` | post-`cba327f` **[refresh]** |
| 55 | 2026-07-23 | Tool-calling routing-preference fix: `select_route()` now consults the tool-calling preference whenever one is set, not only when the primary Bean is incapable — closing a latent hole where marking a primary Bean tool-capable would have silently diverted web search away from Kimi K2 with no test failing | post-`cba327f` **[refresh]** |

**Empirical finding recorded during the Brew 54–55 window (no code shipped from it):** a real tool-calling test against all five free Beans found that House Blend, Second Pour, Guest Bean, Day Roast, and `openai/gpt-oss-20b:free` all genuinely issue correct tool calls — meaning Brew 51's `tool_calling: false` flags on the three free Beans were set from documentation and were wrong. The flags were deliberately **left false** anyway, for a different and now-evidenced reason: a provider HTTP 429 (rate limit) fails the whole request hard with no fallback to another Bean, and the free tier's ~20/min, ~200/day ceiling is shared across the whole API key, so routing agent traffic to a free Bean would break mid-task. The flags are now false for the correct reason (Coffee's error handling can't yet survive their rate limits) rather than the wrong one (a belief the models couldn't call tools). See Section 9.

Brews 40 through 52 (plus the escalation-concatenation fix) are recorded
in `brew-log/progress.md` as implemented, tested, and demoed live; as of
the last Brew Log entry read this session, Brews 51–52 were the most
recently completed and, per that entry, still awaiting human review
before staging/commit. This document does not independently confirm the
current staged/unstaged state of the working tree at doc-generation time
beyond what `brew-log/progress.md` itself states.

---

## 3. Architecture

Three parts: the **router** (backend), the **frontend** (browser client),
and **config** (hand-edited YAML plus one generated policy file).

### Modules (one line each)

| File | Role |
| --- | --- |
| `router/app/main.py` | FastAPI app; all 30 HTTP endpoints; request orchestration for `/v1/order` and `/v1/chat/completions` |
| `router/app/classifier.py` | Heuristic `task_type`/complexity classification (`COMPLEXITY_SIGNALS` table) |
| `router/app/routing.py` | Bean selection (`select_route`/`manual_route`/`select_fallback_route`), cost estimation, vision/tool-calling constraints |
| `router/app/aliases.py` | `BeanRegistry` — loads `beans.yaml`, enforces alias-only leakage, `capable_bean()` cheapest-Bean selection |
| `router/app/escalation.py` | Escalation decision logic (auto-escalate / pending-approval / decline) |
| `router/app/events.py` | SSE event Pydantic models (the event contract's as-implemented source of truth) |
| `router/app/ledger.py` | `RouterLedger` CSV writer, `resolve_cost()` (the cost contract), auto-migration |
| `router/app/openrouter_client.py` | Async streaming OpenRouter HTTP client; SSE delta parsing |
| `router/app/sessions.py` | SQLite session/message/user/token/api_requests store |
| `router/app/auth.py` | bcrypt password hashing, bearer token issuance/validation |
| `router/app/pantry.py` | FTS5 chunking, query sanitizing, BM25 retrieval over `knowledge/` |
| `router/app/memory_proposals.py` | Guardrailed diff generation/approval for `brew-log/` files |
| `router/app/history.py` | Conversation-history pairing/windowing for `remember_chat` |
| `router/app/uploads.py` | File/image upload validation, PDF/text extraction |
| `router/app/preferences.py` | Generic key/value device preference store |
| `router/app/config.py` | Settings loader (`settings.yaml`) |
| `router/config/beans.yaml` | Bean roster (see table below) |
| `router/config/routing_policy.yaml` | Generated routing policy (`tools/generate_policy.py`) — never hand-edited |
| `router/config/settings.yaml` | Thresholds, caps, tick cadence, feature toggles |
| `web/src/components/CounterDisplay/` | Animated barista scene (Rive-backed, SVG/reduced-motion fallback) |
| `web/src/components/ResponseSection/` | Message rendering, attachments, Pantry/Web citation chips, escalation approval card |
| `web/src/components/OrderBox/` | Prompt input, attachments, Bean override, Use Pantry/Use Web toggles |
| `web/src/components/Settings/` | Routing-policy rebuild diff review panel |
| `web/src/store/chatStore.ts` | zustand store; all router calls routed through `src/lib/api.ts` |

### Request flow

```
order box (web UI or /v1/chat/completions client)
  -> order_received (SSE)
  -> classifying          (classifier.py: task_type + complexity)
  -> route_selected       (routing.py + aliases.py: Bean chosen, cost estimated)
  -> generating (0+ ticks, streamed text_delta)
      -> [escalation_pending -> escalating]   (optional, human-approved or auto)
  -> complete             (final tokens, cost, pantry/web sources, history stats)
  -> Ledger write         (ledger.py: one CSV row, resolve_cost() for the real dollar figure)
```

The SSE event contract (`router/EVENT_CONTRACT.md`) sits directly between
`route_selected`/`generating`/`complete` and the frontend — it is the
frozen, versioned schema the UI, the animated scene, and any future
consumer are pure readers of. It is at **version 1.6** (7 versions total:
1.0 through 1.6), with every version after 1.0 additive only (new optional
fields, no renames or removals). Brew 53's date-injection and the identity
block that may follow it ride on the request-side system message rather
than the event contract, so they did not require a new contract version.

### Bean roster (`router/config/beans.yaml`, 9 Beans as of Brew 54)

| Alias | Role | Model ID | Vision | Tool-calling | $/1k in | $/1k out | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| House Blend | default | `nvidia/nemotron-3-ultra-550b-a55b:free` | no | no* | 0.0 | 0.0 | active |
| Second Pour | fallback | `cohere/north-mini-code:free` | no | no* | 0.0 | 0.0 | active |
| Guest Bean | comparison | `poolside/laguna-m.1:free` | no | no* | 0.0 | 0.0 | active |
| Reserve Blend | premium | `anthropic/claude-sonnet-4.6` | yes | yes | 0.003 | 0.015 | active |
| Single Origin | specialist | `anthropic/claude-haiku-4.5` | yes | yes | 0.001 | 0.005 | active |
| Kimi K2 | web_search_primary | `moonshotai/kimi-k2` | no | yes | 0.00057 | 0.0023 | active |
| DeepSeek V3.2 | web_search_fallback | `deepseek/deepseek-v3.2` | no | yes | 0.000269 | 0.0004 | active |
| Flat White | specialist | `google/gemini-2.5-flash-lite` | yes | yes | ~0.0001 | ~0.0004 | active |
| Day Roast | comparison | `google/gemma-4-31b-it:free` | yes | no† | 0.0 | 0.0 | active |

Changes since the Brew 52 edition: Reserve Blend's slug was corrected from
the dashed `anthropic/claude-sonnet-4-6` to the canonical dotted
`anthropic/claude-sonnet-4.6` (the dashed form worked only through
undocumented provider leniency). Flat White and Day Roast were added in
Brew 54. Because `capable_bean()` selects the cheapest capable Bean and
has no role filter, Flat White — cheaper than Single Origin while also
vision- and tool-capable — became the effective default target for
image requests and for `/v1/chat/completions` tool requests the moment it
was added. Kimi K2 remains the web-search default via the explicit
`preferred_web_search_bean_alias` override, which price alone would not
have produced.

\* The three free Beans marked *no** for tool-calling were empirically
found to support it (see Section 2's Brew 54–55 finding and Section 9);
the flag is held false on purpose because a provider 429 currently fails
the whole request with no fallback, not because the capability is absent.

† Day Roast's tool-calling flag was left false pending a dedicated Cup
Test, on the principle that a catalogue advertising a `tools` parameter is
not evidence the model uses it correctly.

Kimi K2 and DeepSeek V3.2 are Chinese-hosted models, accepted explicitly
for this personal-use-only instance (`beans.yaml`'s own comment and the
Brew 51 Tasting Note flag this for reconsideration before any real work
data is routed through them). Flat White and Day Roast are Google-hosted;
Day Roast is a free model and therefore subject to the shared free-tier
rate ceiling noted above.

---

## 4. Feature Inventory

**Routing and cost**
- Heuristic task-type/complexity classifier, cheapest-capable-Bean
  selection with an opt-in preferred-alias override (Brew 36, 50, 51) —
  `router/app/classifier.py`, `router/app/aliases.py`.
- Escalation to a premium Bean on detected failure, gated by a human
  approval card that survives a client disconnect (Brew 36, 40) —
  `router/app/escalation.py`, `web/src/components/ResponseSection/EscalationApprovalCard.tsx`.
- Ratings-weighted routing policy rebuild, previewable as a diff before
  applying (Brew 42) — `tools/generate_policy.py`, `web/src/components/Settings/`.
- Real per-request cost resolution (`resolve_cost()`, preferring
  OpenRouter's own reported cost) and a `cost_source` column (Brew 48) —
  `router/app/ledger.py`.
- Per-user/global daily spend caps and per-user rate limiting, enforced
  before every real spend site (Brew 49) — `router/app/main.py`'s
  `check_spend_cap()`/`check_rate_limit()`.
- Web search via OpenRouter's `tools`-array mechanism, cheapest
  tool-calling Bean routing, per-engine cost control (Brew 50, 51) —
  `router/app/openrouter_client.py`, `settings.yaml`'s `web_search_engine`.
- Date-aware system prompt: every `/v1/order` request carries the current
  date (and configurable timezone) so Beans answer time-sensitive
  questions correctly instead of from their training cutoff (Brew 53) —
  `router/app/system_prompt.py`. Scoped to `/v1/order` only; never
  injected into `/v1/chat/completions`, which sends a client's messages
  verbatim.
- Tool-calling routing-preference fix: the preferred tool-calling Bean is
  now consulted whenever a preference is set, not only as a fallback when
  the primary Bean is incapable, and a stale/unresolvable preference logs
  a warning instead of silently falling through to cheapest-price
  selection (Brew 55) — `router/app/routing.py`.

**Chat and UI**
- Next.js 16 + Tailwind v4 + zustand chat client with streaming responses
  (Brew 37) — `web/`.
- File/image attachments: drag-and-drop, paste, PDF/text extraction
  (Brew 38) — `router/app/uploads.py`, `web/src/components/OrderBox/AttachmentChip.tsx`.
- Animated Coffee Counter scene reflecting live request state, with a
  static-SVG/reduced-motion fallback (Brew 39) — `web/src/components/CounterDisplay/`.
- Response layout/Markdown formatting fix and vertical scene-panel
  restructure (Brew 44–46) — `web/src/components/ResponseSection/MessageBubble.tsx`.
- Web-source citation chips (`WebSourceChips.tsx`) and Pantry citation
  chips (`PantrySourceChips.tsx`) (Brew 41, 52).

**Memory and retrieval**
- Cross-turn conversation memory behind a per-session `remember_chat`
  toggle, with windowed history assembly (Brew 46) —
  `router/app/history.py`.
- FTS5/BM25 Pantry retrieval over `knowledge/` with source citations and
  a path-traversal-safe file viewer (Brew 41) — `router/app/pantry.py`.
- Guardrailed session memory proposals (diffs to `brew-log/` files,
  never auto-applied) (Brew 41) — `router/app/memory_proposals.py`.

**Auth and multi-user**
- Username/password login (bcrypt hashing), bearer tokens, CLI-only user
  creation (Brew 43) — `router/app/auth.py`, `router/tools/manage_users.py`.
- Projects (CRUD) and chat session management (rename, soft-delete)
  (Brew 43) — `router/app/main.py`'s `/v1/projects`/`/v1/sessions` routes.

**Governance**
- Retry detection and opt-in shadow mode for `/v1/chat/completions`
  (Brew 47) — `router/app/sessions.py`'s `api_requests` table.
- `tools/ledger_summary.py --mode model-usage`: real-usage analysis
  sliced by task type and client source (Brew 47).
- Escalation-concatenation fix: streamed responses no longer glue a
  discarded draft to a premium re-run (Brew 47).

**Integrations**
- OpenAI-compatible `/v1/chat/completions` endpoint for Cursor,
  Continue.dev, and the OpenAI SDK (Brew 47) — `router/app/main.py`.
- LAN access (CORS + `--host 0.0.0.0` + firewall guidance) via
  `start.ps1`/`stop.ps1` and `CORS_ALLOWED_ORIGINS`.

---

## 5. Engineering Practice

Every Brew in this repository follows the same cycle: a **Decaf plan**
(a written design document under `docs/design/`, produced after reading
the actual current code, not assumed) — human review and explicit
approval of every open question — implementation — tests — a **live
demo** against the real running router and real OpenRouter (not mocks;
tests use mocked/fake transports, but the demo step always uses a real
`OPENROUTER_API_KEY` and a real HTTP round trip) — a Tasting Note
recording exactly what was verified, including failures.

Standing rules, stated repeatedly across `AGENTS.md`, `PROJECT_COFFEE.md`,
and every Brew's own log entry: nothing is staged, committed, tagged, or
pushed without explicit human review; a staged secret-pattern check is
required before any commit; destructive actions, dependency installs,
and sending context to a remote Bean all require approval; Decaf Mode
(read-only, propose-before-act) is the default for risky or unclear work.

**Real, independently-run test counts (this session, 2026-07-22):**

- Backend: `python tools/run_all_tests.py` — **997 tests**, 1 skipped,
  **6 failing** (see Section 9 for names — all pre-existing and
  reproduced live, not introduced by this exercise), across 5 test roots
  (`router/tests` 710, `tests/` 249, `roastery/tests/` 22,
  `apps/coffee-status/tests/` 9, `apps/coffee-certification/tests/` 7).
- Frontend: `npx vitest run` — **218 tests, all passing** (29 test
  files), matching the count `brew-log/progress.md` recorded for Brew 52.
- End-to-end: `npx playwright test` — **10/10 passing** (real Chromium,
  mocked router responses via `page.route()`, no live OpenRouter call).

These tests cover: routing/classification/escalation logic, the SSE
event contract's shape (including a dedicated "no raw model ID ever
leaks" test), the Ledger's cost contract and CSV migrations, auth/session
isolation between users, Pantry/memory-proposal guardrails, spend-cap and
rate-limit enforcement, and (on the frontend) component rendering,
citation chip behavior, responsive layout breakpoints, and full
click-through chat flows in a real browser.

---

## 6. Bugs Found and Fixed

This is the section this project's own process is most explicit about,
because the same *class* of bug recurred multiple times: a feature that
looked complete and correct, but was structurally incapable of ever
doing anything, because the number that should have driven it was always
zero, empty, or dropped before it reached the place that needed it.

**The decorative-cost pattern (three confirmed instances, one shared root cause).**
1. *Shadow-mode cap could never trip* (found during Brew 47): shadow-run
   Ledger rows needed a real dollar `cost_usd` or `shadow_mode_daily_cost_cap_usd`
   could never sum to anything but $0 and would never fire. Fixed by
   giving shadow rows alone a real computed cost — a deliberate, narrow,
   explicitly flagged inconsistency, since every *other* paid-Bean row
   still wrote `"unknown"` at that point.
2. *`ledger_summary.py`'s total was structurally always $0.00* (Brew 48):
   every non-shadow paid-Bean row wrote `cost_usd = "unknown"`, so the
   model-usage report's total spend was permanently `$0.0000 (6 rows
   unknown)` no matter how much money was actually spent. Fixed with a
   shared `resolve_cost()` (prefer OpenRouter's reported `usage.cost`,
   fall back to token math) and a new `cost_source` column distinguishing
   a real `$0.00` free-tier row from a genuinely unknown one. A real
   backfill against the live Ledger moved the reported total from
   `$0.0000 (6 unknown)` to a real `$0.0190 (0 unknown)`.
3. *The escalation cost estimator was always `0.0`* since Brew 40 (found
   during Brew 49 planning): `estimate_cost_usd()` never produced a real
   number for a paid Bean, meaning `escalation_cost_cap_usd` — and the
   entire human-approval card behind it — had never once actually gated
   a real escalation in this router's history; every eligible failure
   auto-escalated regardless of the configured cap. The user's own
   correction to the initial plan (which proposed a second, parallel,
   narrow estimator) named the pattern directly: *"this is the third
   decorative-cost bug in this codebase... building a second estimator
   alongside the broken one guarantees a fourth."* Fixed by making the
   one shared estimator real instead.

**The SSE parser silently dropping fields (two confirmed instances).**
- `_parse_sse_line()` never extracted `delta.tool_calls_delta` until
  Brew 47 needed tool-calling support, and — separately — never
  extracted `delta.annotations` (web search citations) until Brew 52.
  OpenRouter's web search feature had been fully functional and billed
  correctly since Brew 50, but every citation URL it returned was
  silently discarded before it ever reached the client; only inline
  markdown links the model happened to write into its own prose were
  ever visible. Found by a parser field-by-field audit against a real
  captured stream, not assumed. A follow-on audit (Brew 52) found
  `reasoning`, `refusal`, `usage.completion_tokens_details.reasoning_tokens`,
  `usage.cost_details`, and `usage.server_tool_use_details` are *also*
  real, present, and still dropped today — reported, not fixed (see
  Section 9).

**The escalation content-concatenation bug** (found live during Brew 47's
shadow-mode demo): an auto-escalated `/v1/chat/completions` request
streamed the discarded cheap draft's tokens and the premium re-run's
tokens back-to-back with no reset, producing real garbled output like
`"Hello there youHello there, friend!"`. The internal accumulator reset
correctly per call; the bug was that every yielded chunk was relayed
regardless of which run produced it. Fixed by making escalation
mode-dependent: non-streamed requests buffer the draft internally and
discard it entirely on escalation; streamed requests never escalate
mid-stream at all, logging a new `would_have_escalated` column instead so
the measurement signal survives even though the action doesn't.

**The memory-proposal spend with no Ledger row at all** (found during
Brew 49 planning): `generate_memory_proposal()` made a real, billable
OpenRouter call but wrote no Ledger row whatsoever — not even
`"unknown"` — a real, ungoverned, invisible spend surface, low-risk only
because its Bean happened to default to free-tier. Fixed by writing a
real Ledger row via `resolve_cost()`, same as every other spend site.

**The dead Single Origin model slug** (found live during Brew 50's own
demo): `beans.yaml`'s `Single Origin` Bean pointed at
`anthropic/claude-3.5-haiku`, which no longer resolved against
OpenRouter's real `/v1/models` catalog (404). Confirmed against the live
catalog and fixed separately (commit `a76d674`) to the real current slug,
`anthropic/claude-haiku-4.5`. The same "verify a model slug against the
live catalog before trusting a remembered one" lesson recurred again in
Brew 51, when the initially-proposed Kimi/DeepSeek slugs also turned out
not to exist.

**Other real bugs caught by tests or live demos, not shipped:**
a SQLite Windows file-lock bug (connections committed but never closed,
Brew 37); a Zustand selector causing an infinite React render loop
(Brew 37); a truncation-check false positive that flagged any
tool-calls-only response as a failure and triggered an unwanted
auto-escalation (Brew 47); a response shorter than one streaming tick
silently never reaching the client (Brew 38).

**The pattern, named explicitly:** a mechanism can be fully wired,
type-correct, and covered by passing tests, and still never do anything
in production, if the one number or field driving its decision is
structurally always a placeholder (`0.0`, `"unknown"`, a dropped delta
field) rather than a value computed from something real. Every instance
above was caught either by a live demo against the real API (not a
mocked test) or by an explicit, deliberate field-by-field audit against a
real captured payload. The implication for future work on this codebase:
any new cost, cap, or "should this have fired" mechanism should be
checked against one real end-to-end run before being trusted, and any
new field consumed from a streaming provider response should be checked
against a captured real payload, not just the fields the original code
happened to reach for.

---

## 7. Key Decisions and Tradeoffs

- **Aliases only, never raw model IDs.** `bean_alias` values are the only
  model identifiers ever allowed in an SSE event, an API response, or the
  frontend. Raw OpenRouter model IDs exist in exactly three places:
  `beans.yaml`, the Ledger CSV (for audit), and the outbound OpenRouter
  request body. Enforced by a dedicated test
  (`test_no_raw_model_id_ever_appears_in_any_event_payload`).
- **The cost contract**: `cost_usd` is always the request's *total* cost;
  any component column (`web_search_cost_usd`) is a breakdown of that
  total, never an addend. Decided explicitly during Brew 48, in writing,
  before the web-search Brew could introduce a second cost column that
  would have caused silent double-counting in a Tips Jar or cost pill.
- **Escalation made mode-dependent on the OpenAI endpoint, rather than
  buffering every response.** Buffering every potentially-escalating
  streamed request to guarantee correctness was rejected — it would cost
  every request its time-to-first-token to correctly serve the roughly
  1-in-8 that actually escalate. The chosen fix (buffer only when
  `stream=false`; never escalate mid-stream when `stream=true`, logging
  `would_have_escalated` instead) trades a small amount of measurement
  fidelity for latency on the common path.
- **Cheapest-capable Bean selection, with an opt-in preference override.**
  `capable_bean()` picks the cheapest Bean satisfying a capability filter
  by default; `prefer_alias` (used only for web search, defaulting to
  Kimi K2 over the technically-cheaper DeepSeek V3.2) is a narrow,
  single-call-site exception — every other caller is unaffected.
- **`remember_chat` is server-side session state, not a request
  parameter** — resolved once per request from the session store so a
  client can never spoof or bypass it.
- **Chinese-hosted Beans (Kimi K2, DeepSeek V3.2) accepted explicitly**
  for this personal-use-only instance, with an inline `beans.yaml`
  comment and a Tasting Note entry both flagging this for reconsideration
  before any real work data is ever routed through them.
- **Deliberate non-builds**, stated repeatedly across design docs and the
  v1.0 handoff: no billing system, no admin dashboard, no vector
  database/embeddings-based RAG (Pantry retrieval is FTS5/BM25 over
  Markdown), no standalone autonomous coding agent, no automatic
  policy/Pantry re-indexing (both are manual actions), no persistent job
  queue or multi-tenant auth beyond simple bearer tokens.
- **Reversed or corrected mid-build:** the original `use_web` mechanism
  (`plugins: [{"id": "web"}]`) was migrated outright to the `tools`-array
  form after Brew 51 found the `plugins` syntax was OpenRouter-deprecated
  and didn't expose an `engine` parameter at all. The three
  decorative-cost estimators (Section 6) were each planned as narrow,
  isolated fixes at first and corrected, by explicit human instruction
  each time, into fixing the one shared underlying function instead.

---

## 8. Metrics

All numbers in the table below were computed against the working tree on
**2026-07-22 (through Brew 52)**. Brews 53–55 added source, tests, Beans,
commits, and Ledger rows, so every count here is now a **lower bound** and
marked **[stale]**. To refresh, re-run the command in the "How obtained"
column. The most load-bearing refreshes:

```powershell
# commit count and date range
git log --oneline | Measure-Object -Line
git log --format=%ad --date=short   # min/max for the range

# backend / frontend test counts
python tools/run_all_tests.py
cd web ; npx vitest run ; npx playwright test

# Bean count, endpoint count, event-contract version
# (read beans.yaml, count @app. decorators, read EVENT_CONTRACT.md changelog)

# Ledger rows, spend, and cost_source split
python -m tools.ledger_summary --mode model-usage
```

Known directional changes since 2026-07-22: Beans **7 → 9**; several new
Brews and their commits; new tests for the date prompt, the two new Beans,
and the routing-preference fix; and real Ledger rows now accumulating from
actual use rather than only demos, so real spend is above the
2026-07-22 `$0.0877`.

All values below are **[stale as of 2026-07-22]** — see the refresh
commands above.

| Metric | Value (2026-07-22) | How obtained |
| --- | --- | --- |
| Total commits | 163 **[stale]** | `git log --oneline \| wc -l` |
| Date range | 2026-07-02 to 2026-07-18 **[stale]** | `git log --format=%ad --date=short`, min/max |
| Python source files, `router/` (excl. tests) | 22 | `git ls-files router` filtered |
| Python test files, `router/tests/` | 17 | " |
| TypeScript/TSX files, `web/src/` (excl. tests) | 46 | `git ls-files web/src` filtered |
| TypeScript/TSX test files, `web/src/` | 29 | " |
| Lines of code, `router/` (non-test .py) | 7,589 | `wc -l` over tracked files |
| Lines of code, `router/tests/` | 9,049 | " |
| Lines of code, `web/src/` (non-test) | 4,586 | " |
| Lines of code, `web/src/` tests | 2,983 | " |
| Backend tests (`tools/run_all_tests.py`) | 997 total, 991 passing, 6 failing, 1 skipped | run live this session |
| Frontend tests (`npx vitest run`) | 218 passing, 0 failing | run live this session |
| Frontend e2e (`npx playwright test`) | 10 passing, 0 failing | run live this session |
| Beans configured | 7 → **9 as of Brew 54** | `router/config/beans.yaml` |
| API endpoints (`router/app/main.py`) | 30 **[refresh]** | `grep -c "@app\."` |
| Ledger CSV columns | 31 | `ledger/router_requests.csv` header row |
| Event contract versions | 7 (v1.0–v1.6) | `router/EVENT_CONTRACT.md` changelog |
| Real Ledger rows (accumulated live-demo/usage data) | 79 | `ledger/router_requests.csv` |
| Real accumulated spend (all-time, this Ledger) | $0.0877 | summed `cost_usd` across all 79 rows |
| Ledger rows by cost_source | 41 computed, 38 reported, 0 unknown | same |

---

## 9. Open Items

**Deliberately deferred** (named as future work in the Brew Log/Tasting
Notes, not a defect):
- Expanding the Pantry corpus beyond `knowledge/`'s current 4 files.
- Automatic scoring/diffing of shadow-mode response pairs (currently a
  manual SQLite query).
- A non-interactive `manage_users.py` flag, since `getpass.getpass()`
  hangs on Windows when stdin is piped/redirected (worked around for
  every live demo by calling the hashing functions directly).
- Session history re-display showing a past message's full attachment
  text (only `has_attachments: boolean` is stored today).
- Reload recovery for a paused escalation does not resume live token
  streaming — it polls for the final result instead (an explicit,
  documented scope boundary, not a bug).

**Found late, not yet addressed** (real gaps, reported in Tasting Notes,
explicitly out of scope for the Brew that found them):
- The parser-audit findings from Brew 52: `reasoning`/`refusal` message
  fields and `usage.completion_tokens_details.reasoning_tokens`/
  `usage.cost_details`/`usage.server_tool_use_details` are all real,
  present in OpenRouter's schema, and still silently dropped by
  `_parse_sse_line()`. Reasoning tokens are already correctly counted in
  the billed cost the Ledger records (nothing is paid for invisibly in
  the dollar total) — but there is no way to see how much of a bill was
  "thinking" versus "answer," and the reasoning text itself is
  inaccessible.
- No startup check that a Bean's `model_id` still resolves against
  OpenRouter's live catalog — the dead Single Origin slug (Section 6) was
  only caught by a live demo, not by any automated check; the same class
  of drift could recur silently for any Bean.
- `router/README.md` and `ROADMAP.md` are stale as documentation: both
  describe the system as of roughly Brew 42 (event contract "v1.4",
  "no premium Bean has been selected," a 3-Brew-old endpoint count) even
  though `brew-log/progress.md` and the real `beans.yaml`/`EVENT_CONTRACT.md`
  are current through the latest Brew. Reconciled here by preferring the
  Brew Log and source files over the READMEs where they conflicted.

**Surfaced during real use (post-Brew-52), reported, not all fixed:**
- **Silent conversation-history trimming.** When `remember_chat` history
  exceeds `history_max_chars` (default 24,000) or `history_max_messages`,
  `assemble_history()` drops the oldest turns whole, oldest-first, and
  tells the user nothing. In real use a long document pasted as the first
  turn was dropped from every subsequent request, and the model correctly
  reported never having received it — which reads to the user as a memory
  bug rather than a windowing effect. Two mitigations require no code (put
  long reference material in the Pantry; raise `history_max_chars`); a
  proposed Brew would surface trimming honestly in the UI. The proper home
  for long reference documents is the Pantry, not conversation history.
- **Vision routing overcharges.** `default_vision_bean()` selects the
  first vision-capable Bean in file order (Reserve Blend, $0.003/$0.015)
  rather than the cheapest (Single Origin, $0.001/$0.005), so plain image
  attachments on `/v1/order` have been billing the premium Bean when a
  cheaper capable one was available. This is the same
  cheapest-capable-guarantee-not-applied pattern as the Brew 55 routing
  hole; the fix (route `default_vision_bean()` through
  `capable_bean(vision=True)`) is specified but not yet implemented, and it
  interacts with Day Roast: if that fix lands while Day Roast (free +
  vision) is in the roster, Day Roast would become the default image
  handler purely on price, so the two decisions are coupled.
- **Provider rate-limit (429) fails the whole request with no fallback.**
  Traced and confirmed live: any HTTP status ≥400 from OpenRouter raises
  `OpenRouterClientError`, which every call site catches and turns into a
  terminal `ErrorEvent` before the escalation/failure machinery is ever
  reached. The escalation engine only evaluates *completed* responses
  (truncated/empty/refusal-shaped), so a transport error is structurally
  invisible to it. This is why the free Beans' proven tool-calling ability
  cannot yet be used for agent traffic — a single 429, likely on the
  shared free-tier ceiling, kills the request outright. It is also not
  purely a free-tier issue: any Bean can 429 under provider load, so a
  retry-on-transient-error mechanism (typed error category → same-tier
  retry with backoff → fall through to another Bean before reaching for
  premium) would be a general robustness improvement. Proposed as its own
  Brew; not implemented.

**Currently failing tests, confirmed live this session** (all 6 are
pre-existing, unrelated to any change in this document, and reproduced
independently — not taken on the Brew Log's word alone):
- `test_aliases.VisionCapableBeansTests.test_real_config_has_no_vision_bean_today`
  and `test_routing.VisionRoutingConstraintTests.test_real_generated_policy_needs_vision_raises_today`
  — both assert the old "no vision Bean configured" reality; `beans.yaml`
  has had a real vision-capable Bean (Reserve Blend) since a commit
  outside this Brew Log's numbering (`0255a63`), so these fixtures are
  simply stale and need updating, not a product bug.
- Four `test_ledger.TodaySpendUsdTests` failures
  (`test_sums_only_todays_rows_for_the_given_user`,
  `test_user_id_none_sums_every_users_rows_today_for_the_global_cap`,
  `test_shadow_rows_count_toward_the_triggering_users_total`,
  `test_unknown_cost_flagged_not_silently_zeroed`) — these fixtures
  hardcode "today" as a fixed calendar date rather than computing it at
  run time, so they fail whenever the real calendar has rolled past that
  date, exactly as `brew-log/progress.md` predicted when they first
  surfaced during Brew 50. (Noted with some irony: Brew 53 fixed this
  exact bug class — models answering from a hardcoded date — one layer up
  in the product, while the test fixtures carrying the same mistake remain
  unfixed. A ~10-minute cleanup replacing the hardcoded date with a
  run-time-relative one would take the known-failure count from 6 to 2.)

The count of currently-failing tests may have shifted with Brews 53–55 (the
date-prompt Brew updated several history-related tests, and the Bean
additions updated routing regression locks); re-run `python
tools/run_all_tests.py` for the current figure and failure names.

---

## 10. How to Run It

**Prerequisites:** Python 3.11+ with `fastapi`, `uvicorn`, `pydantic`,
`httpx`, `pyyaml`, `pypdf`, `charset_normalizer`, `bcrypt` (see
`router/requirements.txt`); Node.js (tested against v24.16.0) with npm
for `web/`.

**Required environment variable:** `OPENROUTER_API_KEY`, set in your own
shell environment only — never in a file, never passed as an argument,
never logged. `start.ps1` refuses to run without it.

**Quick start** (from the repository root, PowerShell):

```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
.\start.ps1
```

This starts both the router (`python -m uvicorn router.app.main:app`,
port 8765) and the frontend (`npm run dev`, port 3000), each in its own
console window, and stops both cleanly on Ctrl+C. `.\stop.ps1`
force-stops anything still listening on those two ports if something
gets orphaned.

**Manual two-command version:**

```powershell
python -m uvicorn router.app.main:app --port 8765
```
```powershell
cd web
npm run dev
```

Open `http://localhost:3000` — use `localhost`, not `127.0.0.1` (the
router's CORS allowlist and Next.js's dev-mode origin check both key off
the `localhost` string).

**LAN access** (using the app from another device on the same network):
pass `-LanIp <your-machine's-LAN-IP>` to `start.ps1` (or set
`$env:COFFEE_LAN_IP`), which wires `CORS_ALLOWED_ORIGINS` and
`NEXT_PUBLIC_ROUTER_URL` for you; see `router/README.md`'s "LAN access"
section for the manual equivalent and the Windows Firewall rules both
ports need. This has no authentication hardening beyond the existing
login/bearer-token system — fine for a trusted home LAN, not for
anything more public.

**Creating the first user:** there is no signup endpoint by design.
Create a user from the command line:

```powershell
python router/tools/manage_users.py add <username>
```

(You will be prompted for a password interactively; piping a password
via stdin hangs on Windows — a known, documented limitation, not a bug —
so run this in an interactive terminal.)
