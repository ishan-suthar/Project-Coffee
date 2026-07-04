# Project Coffee Roadmap

Version: v0.1 Phase 1 Living Document  
Date: 2026-07-02  
Status: Active

Living roadmap for Phase 1 and beyond. Update this file as shots complete.

## Current status

| Field | Value |
| --- | --- |
| Phase | 1 — Working daily AI coding environment |
| Current shot | Brew 4 complete; Brew 5 planning next |
| Current milestone | Brew 4 / Token efficiency foundation complete |
| Next step | Brew 5 / Shot 8A — Roastery Cup Test planning only |
| Recent Brew 4 result | Pantry Lite, reusable Recipes, Barista role cards, role selection guide, and read-only usage verification complete |
| Blockers | None for Brew 4 closeout |

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
| D2 | Connect OpenRouter API | Blocked in shell (Cursor UI only); retry Shot 3B |
| D3 | Create House Blend routing policy | Done (Shot 3A) |
| D4 | Document model choices as ADR | Done (Shot 3A — ADR-0004) |
| D5 | Test Beans on trivial prompt | Blocked (Shot 3B) — retry |
| D6 | Evaluate Continue and/or Cline | Deferred |

### Track E — Roastery and evaluation

| # | Task | Status |
| --- | --- | --- |
| E1 | Define starter benchmark tasks | Planned |
| E2 | Run first model bake-off | Deferred |
| E3 | Record Tasting Notes | Partial (Shot 3B blocked scorecard) |
| E4 | Update House Blend from evidence | Deferred |
| E5 | Log costs in Coffee Ledger | Partial (Shot 3B estimates only) |

### Track F — Verification and Phase 1 exit

| # | Task | Status |
| --- | --- | --- |
| F1 | Run Barista on a real small coding task | Planned |
| F2 | Verify Brew Log updated | Planned |
| F3 | Verify Roastery has at least one scorecard | Partial (blocked scorecard) |
| F4 | Phase 1 retrospective | Planned |
| F5 | Human can explain Coffee in one paragraph | Open |

## Phase 1 exit criteria

- [x] Repo opens in Cursor with consistent Barista rules
- [ ] OpenRouter routes to at least one tested Bean
- [x] House Blend policy exists and is documented
- [ ] Brew Log, Pantry, Roastery, and Ledger structures are usable
- [x] At least one Roastery scorecard exists (Shot 3B blocked — live metrics pending)
- [ ] At least one real task completed through the full brewing cycle
- [ ] Spill Guard files protect secrets; no credentials in repo
- [ ] Human can describe what Coffee is, what it is not, and how Barista works

## Shot history

| Shot | Name | Status | Date |
| --- | --- | --- | --- |
| 1 | Complete operational skeleton | Complete | 2026-07-02 |
| 2 | Barista becomes operational | Complete | 2026-07-02 |
| 3A | House Blend policy and setup docs | Complete | 2026-07-02 |
| 3B | Live OpenRouter connectivity test | Historical blocked context | 2026-07-02 |
| 4B | Coffee Status MVP build | Complete | 2026-07-02 |
| 4C | Coffee Status MVP verification | Complete | 2026-07-02 |
| 4D.1 | Coffee Status MVP status docs | Complete | 2026-07-02 |
| 4D.2 | Coffee Status MVP closeout artifacts | Complete | 2026-07-02 |
| 4D.3 | Final Brew 1 closeout update | Complete | 2026-07-02 |
| 5A | Brew 2 planning | Complete | 2026-07-02 |
| 5B | Prompt Library skeleton | Complete | 2026-07-02 |
| 5C | Reusable Espresso Shot template | Complete | 2026-07-02 |
| 5D | First approved prompt artifact | Complete | 2026-07-02 |
| 5E | Prompt Library verification | Complete | 2026-07-02 |
| 5F.1 | Prompt Library MVP status docs | Complete | 2026-07-02 |
| 5F.2 | Prompt Library MVP retrospective | Complete | 2026-07-02 |
| 5F.3 | Prompt Library MVP ledger estimate | Complete | 2026-07-02 |
| 5F.4 | Prompt Library MVP workflow scorecard | Complete | 2026-07-02 |
| 5F.5 | Final Prompt Library MVP closeout update | Complete | 2026-07-02 |
| 6B | Coffee Status data model contract | Complete | 2026-07-03 |
| 6C | Coffee Status data model tests | Complete | 2026-07-03 |
| 6D | Coffee Status status builder | Complete | 2026-07-03 |
| 6E | Wire Coffee Status app to status builder | Complete | 2026-07-03 |
| 6F | Coffee Status runtime verification and closeout | Complete | 2026-07-03 |
| 7A | Token efficiency foundation planning | Complete | 2026-07-04 |
| 7B | Pantry Lite context index | Complete | 2026-07-04 |
| 7C | Pantry Lite usage verification | Complete | 2026-07-04 |
| 7D | Recipes and Baristas skeleton | Complete | 2026-07-04 |
| 7E | Reusable Decaf planning Recipe | Complete | 2026-07-04 |
| 7F | Main Barista role card | Complete | 2026-07-04 |
| 7G | Main Barista role usage verification | Complete | 2026-07-04 |
| 7H | Espresso Fast Coder role card | Complete | 2026-07-04 |
| 7I | Mocha Python/AI role card | Complete | 2026-07-04 |
| 7J | Cappuccino Research role card | Complete | 2026-07-04 |
| 7K | Macchiato Embedded role card | Complete | 2026-07-04 |
| 7L | Flat White Code Review role card | Complete | 2026-07-04 |
| 7M | Cortado DevOps/Infra role card | Complete | 2026-07-04 |
| 7N | Barista role selection guide | Complete | 2026-07-04 |
| 7O | Barista role read-only usage test | Complete | 2026-07-04 |
| 7P | Token efficiency foundation closeout docs | Complete | 2026-07-04 |
| 8A | Roastery Cup Test planning | Planned | — |
| 4 | First Roastery bake-off | Deferred | — |
| 5 | End-to-end Barista workflow test | Planned | — |
