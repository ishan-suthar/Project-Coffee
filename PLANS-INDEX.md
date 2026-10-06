# Plans Index

Status: Audit complete, 2026-07-09
Scope: Full repo audit against the actual governing documents (there is no
`Project_Coffee_PRD.md` or `Project_Coffee_Roadmap.md` in this repo; the real
source of truth is `ROADMAP.md`, `PHASE_0_ROADMAP.md`, and the set of founding
docs listed in the Appendix). Five plans were selected and written as
`PLAN-*.md` files at the repository root. This document ranks them, explains
the recommended order, and records everything else the audit found.

## Ranked plans

### 1. PLAN-spill-guard-token-log-fix.md

`.gitignore` is missing the `!ledger/token_log.md` exception that
`.cursorignore` and `.cursorindexingignore` both already have, and that
`.cursor/rules/project-coffee-spill-guard.mdc` explicitly documents as
intended ("Exception: `ledger/token_log.md` is allowed"). This silently
excludes a real, non-secret Ledger file from every commit. It is a Spill
Guard defect, and Spill Guard/safety items rank above feature work by this
audit's own selection criteria. Effort: S. Fix is a single added line.

### 2. PLAN-root-test-discovery-fix.md

The exact validation command documented in `docs/releases/v1.0-closeout-checklist.md`
and `docs/releases/project-coffee-v1.0-handoff.md` — `python -m unittest discover`,
run bare from the repository root — silently collects zero tests and reports
`OK`. Verified directly: `python -m unittest discover -s tests` finds 214
tests; the bare root command finds 0. Every past "tests pass" claim that
relied on that exact command was never actually checking anything. This
matters most right now because Brew 36 (OpenRouter integration behind
explicit approval) is the next planned shot and is the first real
higher-risk network code path in the project. Effort: M. One new
standard-library script, two doc-line replacements.

### 3. PLAN-roadmap-phase-reconciliation.md

`ROADMAP.md`'s Shot history table correctly lists all 35 Brews, but nothing
in the document connects that history to the five real git tags
(`v0.1`, `v0.1-certified`, `v0.1-proven`, `v1.0-stronger-base`,
`v1.1-coffee-counter-foundation`) that mark actual closeout milestones, and
the Phase 1 exit-criteria checklist has two boxes that were never revisited
after Brew 12-35 shipped. This is the specific kind of drift this audit was
commissioned to find and fix: the living roadmap is the one document this
whole exercise treats as ground truth, and it under-reports what has
actually shipped. Effort: M. Depends on Plan 1's result for one conditional
line.

### 4. PLAN-architecture-doc-drift-cleanup.md

`ARCHITECTURE.md`'s repository-structure diagram still shows `baristas/`,
lowercase `templates/`, and lowercase `decisions/` as canonical, but the
live repo actually uses `agents/` (11 files vs. `baristas/`'s 4, unchanged
since Brew 7), `TEMPLATES/` (uppercase), and a two-location ADR split
(`DECISIONS/` + `docs/adr/`, already correctly indexed in
`brew-log/decisions.md` but never reflected in `ARCHITECTURE.md` itself). A
stale architecture diagram risks a future agent writing new content into the
wrong, superseded location. Effort: S-M. Three files, each a small,
mechanical edit.

### 5. PLAN-brew-log-learning-loop-backfill.md

`brew-log/lessons_learned.md` (3 lines) and `brew-log/mistakes.md` (one
placeholder row) are effectively empty after 35 Brews, despite Constitution
Article 4/5 and `MEMORY_AND_LEARNING.md`'s "Coffee Academy" section
requiring exactly this kind of capture after every significant project. The
raw material already exists in `CHANGELOG.md`, `brew-log/active_context.md`,
and `docs/adr/0005-local-openrouter-coffee-core.md` — it was never
distilled into the dedicated files the architecture defines for this
purpose. Effort: M. Backfills five real, cited lessons and three real,
cited mistakes; establishes the format for future Brews to keep appending to.

## Do this first

**PLAN-spill-guard-token-log-fix.md.** Reasoning: this audit's own selection
criteria state Spill Guard and safety items rank above feature work, and
`ROADMAP.md`'s own Phase 1 exit criteria includes an unchecked box
specifically for "Spill Guard files protect secrets; no credentials in
repo" — this plan is the concrete, verified defect standing between that
box and being honestly checkable. It is also the smallest plan (one line),
has zero dependencies, and its result gates one conditional edit in Plan 3.

Second priority: **PLAN-root-test-discovery-fix.md**, before Brew 36 begins.
Brew 36 (OpenRouter integration behind explicit approval) is the next
planned shot per `ROADMAP.md` and the first real network-call code path in
the project. It should not ship behind a test gate that has been silently
reporting zero-test false passes.

## Dependency graph

```
PLAN-spill-guard-token-log-fix
    |
    v
PLAN-roadmap-phase-reconciliation   (reads Plan 1's result for one conditional line)

PLAN-root-test-discovery-fix        (independent; should land before Brew 36, which is
                                      outside these five plans)

PLAN-architecture-doc-drift-cleanup (independent)

PLAN-brew-log-learning-loop-backfill (independent; references findings from
                                       Plan 1 and Plan 2 as cited lesson content,
                                       but does not require them to have landed first)
```

Plans 2, 4, and 5 can run in any order, in parallel with each other and
after Plan 1. Plan 3 should run after Plan 1 so its conditional exit-criteria
edit reflects the true state.

## Estimated effort

| Plan | Effort |
| --- | --- |
| PLAN-spill-guard-token-log-fix | S |
| PLAN-root-test-discovery-fix | M |
| PLAN-roadmap-phase-reconciliation | M |
| PLAN-architecture-doc-drift-cleanup | S-M |
| PLAN-brew-log-learning-loop-backfill | M |

## Backlog

Found during the audit but did not make the top 5. Not forgotten; ranked
roughly by how soon they should be picked up.

- **`ROADMAP.md` Track A3 status is stale.** Track A3 ("Initialize git and
  Phase 0 commit") is marked "Deferred (human approval)", but git has
  clearly been initialized for a very long time (35 Brews, 200+ commits,
  five tags). This one-line status correction was intentionally left out of
  `PLAN-roadmap-phase-reconciliation.md` to keep that plan's diff scoped to
  the Milestone tags addition and the Spill Guard exit-criteria line; fold
  it into the same pass or a quick follow-up edit.
- **Coffee Doctor WARN: `docs/adr/0005-local-openrouter-coffee-core.md`
  embeds the literal staged secret-pattern check command** instead of
  referring to it by name. `PROJECT_COFFEE.md` itself also embeds the
  literal (placeholder) command text, so the convention is inconsistently
  applied repo-wide, not just in one ADR. Low severity: the embedded text is
  a placeholder pattern, not a real secret regex. Worth a documentation pass
  once the top 5 land.
- **`roastery/model_scorecards/` has only one file** (`shot-3b-nemotron-connectivity.md`)
  even though real Bean evaluation now happens through `roastery/cup_tests/`
  and `roastery/tasting_notes.md` instead. Not a blocker — House Blend has
  ample Cup Test evidence behind it — but `model_scorecards/` and
  `cup_tests/` describe overlapping purposes per `EVALUATION_AND_ROASTERY.md`
  and could use the same kind of reconciliation as Plan 4 gave `pantry/`
  and `baristas/`.
- **No root-level single command runs every check together.** Even after
  Plan 2 fixes test discovery, a human still has to run `doctor`,
  `release-check`, `dashboard`, `ledger-summary`, and `run_all_tests.py`
  as separate commands. `tools/coffee.py` already delegates several of
  these; adding a `verify-all` subcommand that runs the full documented
  validation sequence in one shot would be a reasonable Brew, not urgent.
- **`evals/`, `scripts/`, `examples/` are still empty scaffold directories**
  (README-only) from Phase 0 Shot 1. This matches `ROADMAP.md` Track B7
  ("Create placeholder dirs") — they were only ever meant to be
  placeholders. Not a gap unless a future Brew has concrete work for them.
- **`.cursor/commands/` still does not exist**, per `ROADMAP.md` Track C5
  ("Add `.cursor/commands/` (optional) — Deferred"). The roadmap itself
  already marks this optional and deferred; listed here only for
  completeness, not as an actionable gap.
- **Roastery `E1` ("Define starter benchmark tasks") is marked "Planned"
  and `F4` ("Phase 1 retrospective") is marked "Planned"** in `ROADMAP.md`
  Track E/F, both still open per the roadmap's own status column. Given the
  benchmark work that actually happened in Brew 14 (`roastery/cup_tests/`,
  four Cup Test Orders with recorded evidence), E1 is likely done in
  substance but was never marked complete in the Track E table — another
  small status-currency item in the same family as the Track A3 finding
  above.

## Appendix: Gap matrix

Ground truth used: `ROADMAP.md` (Phase 1, Tracks A-F, Shot history, exit
criteria) and `PHASE_0_ROADMAP.md` (Phase 0 exit criteria), cross-checked
against the founding docs (`VISION.md`, `COFFEE_CONSTITUTION.md`,
`GOVERNANCE_AND_SAFETY.md`, `COFFEE_PRINCIPLES.md`, `COFFEE_VALUES.md`,
`ARCHITECTURE.md`, `BARISTA_CHARTER.md`, `KNOWLEDGE_ARCHITECTURE.md`,
`MEMORY_AND_LEARNING.md`, `EVALUATION_AND_ROASTERY.md`,
`COFFEE_TERMINOLOGY.md`, `AGENTS.md`), the repository's own audit tooling
(`tools/coffee_doctor.py`, `tools/release_check.py`,
`tools/coffee_dashboard.py`), and direct verification (git state, running
the test suite, running the ignore-file checks).

### Phase 0 (foundation)

| Exit criterion | Status | Evidence |
| --- | --- | --- |
| Project identity is clear | DONE | `VISION.md`, `COFFEE_TERMINOLOGY.md` |
| Tool and model independence are explicit | DONE | `ARCHITECTURE.md`, ADR-0002, ADR-0005 |
| Human authority and safety boundaries documented | DONE | `COFFEE_CONSTITUTION.md`, `GOVERNANCE_AND_SAFETY.md` |
| Barista's role is defined | DONE | `BARISTA_CHARTER.md`, `agents/barista-main.md` |
| Pantry and Brew Log structures exist | DONE (Pantry superseded in practice by `knowledge/`; see Plan 4) | `brew-log/`, `knowledge/`, legacy `pantry/` |
| Roastery scorecards exist | DONE | `roastery/cup_tests/`, `roastery/tasting_notes.md` |
| Repository can be opened in Cursor and used by agents | DONE | `.cursor/rules/` (5 rule files), `AGENTS.md` |
| Human can explain Coffee in one paragraph | OPEN (human judgment, not mechanically checkable) | `ROADMAP.md` Track F5 |

### Phase 1 (working daily AI coding environment) — Tracks A-F

| Track | Status | Evidence / note |
| --- | --- | --- |
| A — Repository and Spill Guard | PARTIAL | A1, A2, A4, A5 done; A3 marked "Deferred" but git is clearly initialized (200+ commits) — stale status, see Backlog; token_log.md ignore bug found, see Plan 1 |
| B — Operational skeleton | DONE | all 8 rows done per `ROADMAP.md`, verified present on disk |
| C — Barista becomes operational | PARTIAL | C1-C4, C6 done; C5 (`.cursor/commands/`) explicitly deferred/optional per roadmap, not a real gap |
| D — Tooling and model gateway | PARTIAL | D1-D5 done; D6 (evaluate Continue/Cline) deferred, not attempted |
| E — Roastery and evaluation | PARTIAL | E2-E4 done; E1 marked "Planned" but substantively delivered by Brew 14 and never updated (Backlog); E5 partial, cost mostly unknown for free-tier Beans |
| F — Verification and Phase 1 exit | PARTIAL | F1-F3 done; F4 "Planned" (never run as a discrete retrospective, though `docs/releases/` closeouts serve a similar function); F5 open (human judgment) |
| Phase 1 exit criteria (8 boxes) | 6 of 8 checked | 2 unchecked: Spill Guard (blocked on Plan 1), human-explains-Coffee (open by design) |

### Beyond the roadmap — Brews 12-35 vs. the founding docs

The `ROADMAP.md` Track A-F checklist only covers the original Phase 1
preview scope (roughly Shots 1-11). Brews 12-35 are tracked at the Shot
history level only. Assessed against the founding docs directly (there is
no per-phase checklist for this range to check against):

| Area | Status | Evidence |
| --- | --- | --- |
| Vendor/model independence maintained | DONE, compliant | ADR-0002, ADR-0005; House Blend treats Beans as replaceable throughout |
| No unauthorized remote/network calls | DONE, compliant | No network-call code found in `tools/` or `ui/`; Brews 33-35 built approval-gate UI with explicit no-live-call boundaries, self-documented in `brew-log/active_context.md` |
| Evidence-based routing (not vibes) | DONE, compliant | House Blend's 3 Bean roles are backed by Brew 14's four-Order Cup Test evidence |
| Local-first / simplicity discipline | DONE, compliant | Local RAG (Brew 21-22) deliberately shipped as standard-library keyword search, explicitly deferring embeddings/vector DB per `KNOWLEDGE_ARCHITECTURE.md`'s own "Future RAG plan"; UI packaging (Brew 30) explicitly deferred React/Tauri in favor of keeping Streamlit |
| Documentation duty (Article 4) | DONE, compliant | `CHANGELOG.md`, `ROADMAP.md` Shot history, `brew-log/active_context.md` all current through Brew 35 |
| Small verified steps (Principle 5) | DONE, compliant | Every Brew in this range follows a design -> dogfood -> close pattern with recorded tests/compile checks/dogfood evidence |
| Test-gate integrity | GAP | `python -m unittest discover` (bare, root) silently passes 0 tests; see Plan 2 |
| Spill Guard ignore-file parity | GAP | `.gitignore` vs `.cursorignore`/`.cursorindexingignore` mismatch on `token_log.md`; see Plan 1 |
| Learning loop (Constitution Article 5, Principle 8) | GAP | `brew-log/lessons_learned.md` and `brew-log/mistakes.md` effectively unused despite 35 Brews of material; see Plan 5 |
| Architecture doc currency | GAP | `ARCHITECTURE.md` repo-structure diagram stale vs. `agents/`/`knowledge/`/`TEMPLATES/`/`DECISIONS/`+`docs/adr/`; see Plan 4 |
| Roadmap currency vs. tagged milestones | GAP | No connection in `ROADMAP.md` between Shot history and the 5 real git tags; see Plan 3 |

**Overall verdict on Brews 12-35: valid and consistent with the founding
docs in substance.** No evidence of scope creep past what `VISION.md`'s
"What Coffee is not" rules out, no evidence of unauthorized remote calls or
hidden file changes, and routing/safety decisions are consistently
evidence-based and human-approved at each closeout. The five gaps found are
all documentation-currency and quality-gate-integrity issues, not violations
of the constitution or a sign the project went somewhere it should not
have. They are exactly the kind of gaps that accumulate when 35 Brews ship
in eight days without a dedicated audit pass — which is what this session
was for.
