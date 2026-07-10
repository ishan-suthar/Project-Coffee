# PLAN-brew-log-learning-loop-backfill

## Goal

After this plan, `brew-log/lessons_learned.md` and `brew-log/mistakes.md` each contain real, evidence-backed entries instead of being empty stubs, and both files carry the correct table/entry format for future Brews to append to. Right now, after 35 completed Brews, `brew-log/lessons_learned.md` is 3 lines ("Add lessons here after each meaningful work session.") and `brew-log/mistakes.md` is a table with a single placeholder row ("— | — | — | —" / "*No entries yet.*"). This is a real gap against `MEMORY_AND_LEARNING.md`'s "Coffee Academy" section ("After every significant project, Coffee should extract reusable learning...") and Coffee Constitution Article 4.3 / Article 5 (the learning loop: "capture what worked... what failed... what needed human correction"), and Coffee Principle 8 ("Every project should teach Coffee"). The raw material already exists across `CHANGELOG.md`, `brew-log/active_context.md`, and `docs/adr/0005-local-openrouter-coffee-core.md` — it was simply never distilled into the dedicated learning files the architecture defines for this purpose.

This plan backfills five real lessons and three real mistakes, each sourced from a specific, named prior Brew, using the exact entry format already defined in `MEMORY_AND_LEARNING.md` ("Example lesson entry") and the exact table format already present in `brew-log/mistakes.md`. No lesson or mistake in this plan is invented; each cites the Brew and source document it came from.

## Preconditions

Run these exact commands from the repository root in PowerShell and confirm the expected output. If any check does not match, STOP and report which one failed instead of improvising.

1. Confirm `brew-log/lessons_learned.md` is still the empty stub (idempotency check):
   ```powershell
   (Get-Content brew-log\lessons_learned.md | Measure-Object -Line).Lines
   ```
   Expected: `3`. If this is a much larger number, someone has already added content — STOP and report instead of overwriting.

2. Confirm `brew-log/mistakes.md` still has only the placeholder row:
   ```powershell
   Select-String -Path brew-log\mistakes.md -Pattern "No entries yet"
   ```
   Expected: exactly one match. If no match, STOP and report — the file may already have real entries.

3. Confirm the three source documents this plan cites still exist:
   ```powershell
   Test-Path CHANGELOG.md
   Test-Path brew-log\active_context.md
   Test-Path docs\adr\0005-local-openrouter-coffee-core.md
   ```
   Expected: `True` for all three.

## Files to touch

- `brew-log/lessons_learned.md` — MODIFY. Replace the stub content with an instructions header (kept) plus five lesson entries in the `MEMORY_AND_LEARNING.md` example format.
- `brew-log/mistakes.md` — MODIFY. Replace the single placeholder table row with three real rows, keeping the existing table header.

No other file may be edited under this plan. Do not edit `CHANGELOG.md`, `brew-log/active_context.md`, or `docs/adr/0005-local-openrouter-coffee-core.md` — they are read-only sources for this plan, not targets.

## Steps

1. Open `brew-log/lessons_learned.md`. Current content is exactly:
   ```
   # Lessons Learned

   Add lessons here after each meaningful work session.
   ```
   Replace the entire file with:

   ```markdown
   # Lessons Learned

   Add lessons here after each meaningful work session. Use the format below
   (see `MEMORY_AND_LEARNING.md`, "Example lesson entry"). Newest entries go
   at the top.

   ---

   # Lesson Learned: Verify parsers against real, messy data during dogfood, not only clean fixtures

   Date: 2026-07-08
   Project: Project Coffee
   Context: Brew 19 / 19B, Ledger Summarizer
   What happened: The Ledger Summarizer's initial parser did not handle
   bullet-style Ledger entries (`Cost:`, `Tokens:`, `Model/API calls:`,
   `Evidence:`, `Notes:`) that were actually present in the real
   `ledger/cost_log.md`. The gap was only found during dogfood against the
   real Ledger, after the tool had already passed its unit tests against
   cleaner fixture data.
   Lesson: Passing tests is not the same as working on real project data.
   Dogfood every local tool against the actual repository files it is meant
   to read before calling it done.
   Action: Added bullet-style entry parsing in Brew 19B-fix. Keep dogfooding
   local tools against real Project Coffee files, not only test fixtures.
   Tags: tooling, testing, dogfood

   ---

   # Lesson Learned: Don't assume an IDE surface exposes the control you need for a fair evaluation

   Date: 2026-07-05
   Project: Project Coffee
   Context: ADR-0005, Roastery Cup Test execution path
   What happened: The original plan was to run controlled Bean comparisons
   through Cursor directly, but Cursor Free's Agent mode only exposed Auto
   mode, not controlled named-model selection. That made Cursor unsuitable
   as the execution surface for fair, repeatable Roastery comparisons.
   Lesson: Before designing an evaluation process around a tool's UI, verify
   the tool actually exposes the specific control (in this case, named model
   selection) the evaluation needs.
   Action: Built a local OpenRouter client and Cup Test runner as the current
   Coffee Core for Roastery experiments instead (ADR-0005). Cursor remains
   the Coffee Counter; the evaluation execution path is separate by design.
   Tags: roastery, evaluation, tooling

   ---

   # Lesson Learned: Free-tier model availability is volatile; keep a documented fallback list

   Date: 2026-07-05
   Project: Project Coffee
   Context: Brew 8 / 8G-8L, first local Cup Test and House Blend selection
   What happened: The first local Cup Test run included free Bean slugs
   (`qwen/qwen3-coder:free`, `deepseek/deepseek-r1:free`) that returned
   provider or rate-limit errors, and had to be replaced with working
   alternatives before House Blend routing could be evidence-based.
   Lesson: Free-tier model slugs can fail, disappear, or become
   rate-limited between runs. Never assume yesterday's working Bean list is
   still valid; keep a documented list of known-failed candidates (see
   `config/house_blend.md`, "Do not use these failed candidates") and rerun
   before trusting a routing decision.
   Action: House Blend now documents both the current Blend and the
   known-failed candidate list explicitly, and routing changes require
   fresh Roastery evidence per Coffee Principle 11.
   Tags: roastery, house-blend, reliability

   ---

   # Lesson Learned: Safety-gate logic needs adversarial dogfood scenarios, not just the happy path

   Date: 2026-07-08
   Project: Project Coffee
   Context: Brew 34 / 34B, Remote Context Package Builder Safety Gate
   What happened: The initial context-package Safety Gate did not block
   requests for broad whole-repository context or `.env`-adjacent content.
   The gap was found only when dogfood testing deliberately tried those
   specific dangerous request shapes, not during normal happy-path testing.
   Lesson: A safety or approval gate must be tested against the specific
   dangerous inputs it exists to catch, not just against the inputs it is
   expected to allow. General "it has a safety check" framing is not
   evidence the check actually blocks the risky case.
   Action: Added explicit request-level blocking for broad repository
   context and `.env` requests in the same Brew (34B), before the feature
   was considered closed. Apply the same adversarial-dogfood standard to
   Brew 36 (OpenRouter integration) before it is considered ready.
   Tags: safety, approval-gates, dogfood

   ---

   # Lesson Learned: A self-built verification tool or bare command can silently pass without checking what it claims to check

   Date: 2026-07-09
   Project: Project Coffee
   Context: Repo audit (this session); `.gitignore` Spill Guard parity gap
   and `python -m unittest discover` false-pass gap
   What happened: Two release-readiness checks that had been treated as
   passing were both silently broken. `.gitignore` was missing the
   `!ledger/token_log.md` exception that `.cursorignore` and
   `.cursorindexingignore` both already had, silently excluding a
   legitimate Ledger file from every commit. Separately, the documented
   validation command `python -m unittest discover` (bare, from repo root)
   collected zero tests and printed `OK`, because hyphenated app directory
   names under `apps/` break unittest's module-path resolution during
   discovery from the root.
   Lesson: A green checkmark from a tool or command is not evidence unless
   you also confirm it checked a nonzero, expected amount of the thing it
   claims to check. Cross-check the three Spill Guard ignore files
   (`.gitignore`, `.cursorignore`, `.cursorindexingignore`) for parity
   whenever one is edited, and confirm a test command's reported count
   before trusting its exit code.
   Action: See `PLAN-spill-guard-token-log-fix.md` and
   `PLAN-root-test-discovery-fix.md`.
   Tags: safety, testing, spill-guard, verification
   ```

2. Open `brew-log/mistakes.md`. Current content is exactly:
   ```
   # Mistakes

   Failures and near-misses to avoid repeating. Promote repeated patterns into Spill Guard rules or Recipes.

   | Date | What happened | Lesson | Action taken |
   | --- | --- | --- | --- |
   | — | — | — | — |

   *No entries yet.*
   ```
   Replace it with:
   ```
   # Mistakes

   Failures and near-misses to avoid repeating. Promote repeated patterns into Spill Guard rules or Recipes.

   | Date | What happened | Lesson | Action taken |
   | --- | --- | --- | --- |
   | 2026-07-08 | Ledger Summarizer (Brew 19) shipped an initial parser that did not handle the bullet-style entries actually present in the real Ledger | Test parsers against real production-shaped data before declaring a tool done, not only clean fixtures | Added bullet-style entry parsing in Brew 19B-fix |
   | 2026-07-08 | Context Package Builder Safety Gate (Brew 34) did not initially block broad whole-repo context or `.env`-adjacent requests | Enumerate and test the specific dangerous request shapes explicitly; general safety framing is not proof of coverage | Added explicit request-level blocking rules in Brew 34B |
   | 2026-07-09 | `.gitignore` lacked the `!ledger/token_log.md` negation that `.cursorignore` and `.cursorindexingignore` both already had, silently excluding a legitimate Ledger file from every commit since it was introduced | The three Spill Guard ignore files must be checked for parity whenever one of them is edited | See `PLAN-spill-guard-token-log-fix.md` |
   ```

3. Confirm exactly two files changed:
   ```powershell
   git status --short
   ```
   Expected: ` M brew-log/lessons_learned.md`, ` M brew-log/mistakes.md`, nothing else.

## Edge cases a weaker model will miss

1. **Do not invent lessons not grounded in a real, named prior Brew.** Every entry in this plan cites a specific Brew number, date, and source document. If asked to add more entries beyond this plan's scope later, the same rule applies: cite the real source, per Constitution Article 6.4 ("Coffee should never invent references to papers, code, tests, or decisions").
2. **Do not backdate the fifth lesson and third mistake row to an earlier date.** They describe findings from this audit session (2026-07-09), not from the Brew they discuss retroactively (Brew 4/token_log.md's original introduction, or Brew 25's release-checklist authoring). Use 2026-07-09 as written.
3. **Table row pipe-escaping.** The mistakes table cells contain backticks (`` `ledger/token_log.md` ``) and literal characters like periods and parentheses. Do not escape or remove the backticks — they render correctly inside a Markdown table cell as-is, matching the style already used elsewhere in `brew-log/decisions.md`.
4. **Preserve the exact horizontal-rule (`---`) separators between lesson entries** in Step 1. Without them, the five entries visually run together under one `#` heading structure, since each entry starts with its own `# Lesson Learned: ...` heading (matching the example format in `MEMORY_AND_LEARNING.md`, which also uses one heading per lesson).
5. **Do not renumber or resequence "Tags:" lines.** Keep tags exactly as given (e.g., `tooling, testing, dogfood`) — they are plain comma-separated text, not a controlled vocabulary enforced elsewhere in this repo, but consistency with the example format in `MEMORY_AND_LEARNING.md` matters for future scans.
6. **UTF-8 BOM and line endings**, same reasoning as the other plans in this set: check both files' existing encoding and line-ending style before saving and preserve it.
7. **This plan does not touch `brew-log/active_context.md`, `brew-log/progress.md`, or `brew-log/decisions.md`.** Those files already serve their own distinct purposes (current state, shot-by-shot progress log, decision index) and already have current content. Do not duplicate this plan's new lesson/mistake content into them.

## Acceptance criteria

1. ```powershell
   (Select-String -Path brew-log\lessons_learned.md -Pattern "^# Lesson Learned:").Count
   ```
   Expected: `5`.

2. ```powershell
   (Get-Content brew-log\mistakes.md | Select-String -Pattern "^\| 2026-").Count
   ```
   Expected: `3`.

3. ```powershell
   Select-String -Path brew-log\mistakes.md -Pattern "No entries yet"
   ```
   Expected: no match (placeholder row is gone).

4. ```powershell
   Select-String -Path brew-log\lessons_learned.md -Pattern "PLAN-spill-guard-token-log-fix.md"
   ```
   Expected: at least one match (the fifth lesson cites it).

5. Roadmap/PRD cross-reference, copied verbatim from `MEMORY_AND_LEARNING.md`, "Brew Log success criteria": "The Brew Log is working when Coffee can answer... What mistakes should we avoid?" This plan makes that question answerable with real, dated entries for the first time.

6. ```powershell
   git status --short
   ```
   Expected: exactly ` M brew-log/lessons_learned.md` and ` M brew-log/mistakes.md`.

## Rollback

```powershell
git checkout -- brew-log/lessons_learned.md brew-log/mistakes.md
```

If already committed:

```powershell
git log --oneline -- brew-log/lessons_learned.md brew-log/mistakes.md
git revert <commit-hash>
```

Do not run `git revert` without human approval.
