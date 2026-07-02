# Project Coffee Roadmap

Version: v0.1 Phase 1 Living Document  
Date: 2026-07-02  
Status: Active

Living roadmap for Phase 1 and beyond. Update this file as shots complete.

## Current status

| Field | Value |
| --- | --- |
| Phase | 1 — Working daily AI coding environment |
| Current shot | Shot 3A complete |
| Next shot | Shot 3B — Live OpenRouter connectivity test |
| Blockers | None |

## Phase 1 goal

Implement the working daily AI coding environment: Cursor configured, models routable, Barista operational, memory and evaluation loops active.

Reference: `PHASE_0_ROADMAP.md` (Phase 1 preview).

## Phase 1 checklist

### Track A — Repository and Spill Guard

| # | Task | Status |
| --- | --- | --- |
| A1 | Add `.gitignore` aligned with Spill Guard | Done (Shot 1) |
| A2 | Verify `.cursorignore` / `.cursorindexingignore` coverage | Done (Shot 2) |
| A3 | Initialize git and Phase 0 commit | Deferred (human approval) |
| A4 | Add `CHANGELOG.md` | Done (Shot 1) |
| A5 | Add `ROADMAP.md` | Done (Shot 1) |

### Track B — Operational skeleton

| # | Task | Status |
| --- | --- | --- |
| B1 | Create Brew Log files | Done (Shot 1) |
| B2 | Create Brew Log subfolders | Done (Shot 1) |
| B3 | Expand Pantry structure | Done (Shot 1) |
| B4 | Create Ledger | Done (Shot 1) |
| B5 | Create Roastery subfolders | Done (Shot 1) |
| B6 | Create Recipes subfolders | Done (Shot 1) |
| B7 | Create placeholder dirs (`scripts/`, `tools/`, `evals/`, `examples/`) | Done (Shot 1) |
| B8 | Update `brew-log/active_context.md` | Done (Shot 1) |

### Track C — Barista becomes operational

| # | Task | Status |
| --- | --- | --- |
| C1 | Write `baristas/barista_orchestrator.md` | Done (Shot 2) |
| C2 | Write starter specialist profiles | Done (Shot 2) |
| C3 | Write first Recipe | Done (Shot 2) |
| C4 | Expand `.cursor/rules/` | Done (Shot 2) |
| C5 | Add `.cursor/commands/` (optional) | Deferred |
| C6 | End-to-end Barista workflow test | Planned |

### Track D — Tooling and model gateway

| # | Task | Status |
| --- | --- | --- |
| D1 | Confirm Cursor as Coffee Counter | Documented (Shot 3A) |
| D2 | Connect OpenRouter API | Shot 3B (credentials in Cursor only) |
| D3 | Create House Blend routing policy | Done (Shot 3A) |
| D4 | Document model choices as ADR | Done (Shot 3A — ADR-0004) |
| D5 | Test Beans on trivial prompt | Shot 3B |
| D6 | Evaluate Continue and/or Cline | Deferred |

### Track E — Roastery and evaluation

| # | Task | Status |
| --- | --- | --- |
| E1 | Define starter benchmark tasks | Planned |
| E2 | Run first model bake-off | Deferred |
| E3 | Record Tasting Notes | Deferred |
| E4 | Update House Blend from evidence | Deferred |
| E5 | Log costs in Coffee Ledger | Deferred |

### Track F — Verification and Phase 1 exit

| # | Task | Status |
| --- | --- | --- |
| F1 | Run Barista on a real small coding task | Planned |
| F2 | Verify Brew Log updated | Planned |
| F3 | Verify Roastery has at least one scorecard | Planned |
| F4 | Phase 1 retrospective | Planned |
| F5 | Human can explain Coffee in one paragraph | Open |

## Phase 1 exit criteria

- [x] Repo opens in Cursor with consistent Barista rules
- [ ] OpenRouter routes to at least one tested Bean
- [x] House Blend policy exists and is documented
- [ ] Brew Log, Pantry, Roastery, and Ledger structures are usable
- [ ] At least one model bake-off recorded with Tasting Notes
- [ ] At least one real task completed through the full brewing cycle
- [ ] Spill Guard files protect secrets; no credentials in repo
- [ ] Human can describe what Coffee is, what it is not, and how Barista works

## Shot history

| Shot | Name | Status | Date |
| --- | --- | --- | --- |
| 1 | Complete operational skeleton | Complete | 2026-07-02 |
| 2 | Barista becomes operational | Complete | 2026-07-02 |
| 3A | House Blend policy and setup docs | Complete | 2026-07-02 |
| 3B | Live OpenRouter connectivity test | Next | — |
| 4 | First Roastery bake-off | Planned | — |
| 5 | End-to-end Barista workflow test | Planned | — |
