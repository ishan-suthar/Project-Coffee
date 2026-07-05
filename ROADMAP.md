# Project Coffee Roadmap

Version: v0.1 Phase 1 Living Document  
Date: 2026-07-02  
Status: Active

Living roadmap for Phase 1 and beyond. Update this file as shots complete.

## Current status

| Field | Value |
| --- | --- |
| Phase | 1 — Working daily AI coding environment |
| Current shot | Brew 7 / Shot 10A — Coffee Certification Project implementation and workflow trace |
| Current milestone | Project Coffee Foundation v0.1 complete; Brew 7 validation underway |
| Next step | Human review, local checks, staged secret-pattern check, and manual commit |
| Recent foundation result | Brew 5 Roastery MVP and Brew 6 Safety / Constitution completed |
| Blockers | Final Brew 7 certification waits on human review and manual commit |

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
| C6 | End-to-end Barista workflow test | In progress (Brew 7) |

### Track D — Tooling and model gateway

| # | Task | Status |
| --- | --- | --- |
| D1 | Confirm Cursor as Coffee Counter | Documented (Shot 3A) |
| D2 | Connect OpenRouter API | Operational through local runner (Brew 5) |
| D3 | Create House Blend routing policy | Done (Shot 3A) |
| D4 | Document model choices as ADR | Done (Shot 3A — ADR-0004) |
| D5 | Test Beans on trivial prompt | Done (Brew 5) |
| D6 | Evaluate Continue and/or Cline | Deferred |

### Track E — Roastery and evaluation

| # | Task | Status |
| --- | --- | --- |
| E1 | Define starter benchmark tasks | Planned |
| E2 | Run first model bake-off | Done (Brew 5) |
| E3 | Record Tasting Notes | Done (Brew 5 initial evidence) |
| E4 | Update House Blend from evidence | Provisional (Brew 5) |
| E5 | Log costs in Coffee Ledger | Partial; usage recorded when available, actual costs unknown |

### Track F — Verification and Phase 1 exit

| # | Task | Status |
| --- | --- | --- |
| F1 | Run Barista on a real small coding task | In progress (Brew 7) |
| F2 | Verify Brew Log updated | In progress (Brew 7) |
| F3 | Verify Roastery has at least one scorecard | Done |
| F4 | Phase 1 retrospective | Planned |
| F5 | Human can explain Coffee in one paragraph | Open |

## Phase 1 exit criteria

- [x] Repo opens in Cursor with consistent Barista rules
- [x] OpenRouter routes to at least one tested Bean
- [x] House Blend policy exists and is documented
- [x] Brew Log, Pantry, Roastery, and Ledger structures are usable
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
| 8A | Roastery Cup Test planning | Complete | 2026-07-04 |
| 8B | Roastery Cup Test templates | Complete | 2026-07-04 |
| 8C | OpenRouter integration | Complete | 2026-07-04 |
| 8D | Local Cup Test runner | Complete | 2026-07-04 |
| 8E | Local Cup Test execution support | Complete | 2026-07-05 |
| 8F | First local Cup Test results | Complete | 2026-07-05 |
| 8G | Free Bean list and retry policy | Complete | 2026-07-05 |
| 8I | Replace unstable free Beans | Complete | 2026-07-05 |
| 8J | Rerun local Cup Test | Complete | 2026-07-05 |
| 8K | Rerun Cup Test evidence | Complete | 2026-07-05 |
| 8L | Choose initial House Blend | Complete | 2026-07-05 |
| 8M | Record provisional House Blend | Complete | 2026-07-05 |
| 8N | ADR for local OpenRouter Coffee Core pivot | Complete | 2026-07-05 |
| 8O | Roastery MVP closeout | Complete | 2026-07-05 |
| 9A | Safety / Constitution gap check | Complete | 2026-07-05 |
| 10A | Coffee Certification Project implementation and trace | In progress - human review and manual commit pending | 2026-07-05 |
