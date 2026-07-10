# PLAN-roadmap-phase-reconciliation

## Goal

After this plan, `ROADMAP.md` accurately reflects that Project Coffee has shipped five tagged milestones (`v0.1`, `v0.1-certified`, `v0.1-proven`, `v1.0-stronger-base`, `v1.1-coffee-counter-foundation`) covering 35 completed Brews, instead of reading as if the project were still working through the original 11-shot Phase 1 checklist (Tracks A-F). Right now `ROADMAP.md`'s "Shot history" table correctly lists all 35 Brews, but nothing in the document connects that history to the actual git tags that mark real closeout milestones, and the Phase 1 exit criteria checklist has two unchecked boxes that were never revisited after Brew 12-35 shipped.

This satisfies Coffee Constitution Article 4 ("Every meaningful task should leave an understandable trace... update the Brew Log when [work] change[s] architecture, assumptions, or project direction") and is the specific gap this whole audit exists to close: a living roadmap document is only useful as source of truth if it stays current with what tags and `docs/releases/` already prove happened.

## Preconditions

Run these exact commands from the repository root in PowerShell and confirm the expected output. If any check does not match, STOP and report which one failed instead of improvising.

1. Confirm the five expected tags exist, in order:
   ```powershell
   git tag -l
   ```
   Expected: exactly these five tag names present (order in output may vary): `v0.1`, `v0.1-certified`, `v0.1-proven`, `v1.0-stronger-base`, `v1.1-coffee-counter-foundation`. If any is missing or additional tags exist, STOP and report the actual tag list — do not invent rows for tags that do not exist.

2. Confirm the tag dates match what this plan assumes:
   ```powershell
   git for-each-ref --format="%(refname:short) %(creatordate:short)" refs/tags
   ```
   Expected:
   ```
   v0.1 2026-07-05
   v0.1-certified 2026-07-05
   v0.1-proven 2026-07-06
   v1.0-stronger-base 2026-07-08
   v1.1-coffee-counter-foundation 2026-07-08
   ```
   If dates differ, use the actual dates from this command's output in Step 1 below instead of the ones given here, and note the discrepancy when reporting completion.

3. Confirm `ROADMAP.md` still has the "Shot history" table as the last section in the file:
   ```powershell
   Select-String -Path ROADMAP.md -Pattern "^## Shot history$"
   ```
   Expected: exactly one match.

4. Check whether `PLAN-spill-guard-token-log-fix.md` has already been applied, since Step 3 below depends on the answer:
   ```powershell
   git check-ignore -v ledger/token_log.md
   ```
   Record the result: if this prints nothing (file not ignored), the Spill Guard fix is applied. If it prints a line referencing `.gitignore` and `**/*token*`, the fix is not yet applied.

## Files to touch

- `ROADMAP.md` — MODIFY. Add one new section, "## Milestone tags", after the existing "## Shot history" table at the end of the file. Conditionally update one line in the "## Phase 1 exit criteria" checklist (see Step 3).

No other file may be edited under this plan.

## Steps

1. Open `ROADMAP.md`. Go to the very end of the file, after the "## Shot history" table (currently ending at the `| Brew 36 | ... |` row, line 190-191). Append this new section exactly, substituting the actual dates from precondition check 2 if they differed from the values shown here:

   ```markdown

   ## Milestone tags

   Project Coffee marks real closeout points with git tags, cross-referenced to
   evidence in `docs/releases/` and `roastery/workflow_scorecards/`. This table
   makes the connection between the Shot history above and the tagged history
   explicit, since the Track A-F checklist below only covers the original
   Phase 1 preview scope (roughly Shots 1-11) and was never extended to name
   every later Brew individually.

   | Tag | Date | Brews covered | Evidence |
   | --- | --- | --- | --- |
   | `v0.1` | 2026-07-05 | 1-6 | `CHANGELOG.md`, `brew-log/progress.md` |
   | `v0.1-certified` | 2026-07-05 | 7 | `roastery/workflow_scorecards/brew-7-coffee-certification.md` |
   | `v0.1-proven` | 2026-07-06 | 8-11 | `docs/guides/new-project-onboarding-guide.md` |
   | `v1.0-stronger-base` | 2026-07-08 | 12-25 | `docs/releases/v1.0-closeout-checklist.md`, `docs/releases/project-coffee-v1.0-handoff.md` |
   | `v1.1-coffee-counter-foundation` | 2026-07-08 | 26-35 | `brew-log/active_context.md` |

   Track A-F below and the exit criteria describe the original Phase 1 preview
   scope only. Brews 12-35 extended past that scope into Roastery hardening,
   Local RAG, the Unified Coffee CLI, Ledger Summarizer, Release Packaging,
   Fleet support, and the Coffee Counter UI, and are tracked at the Shot
   history level and the milestone tags above rather than as additional
   Track A-F rows.
   ```

2. Verify the new section was added correctly:
   ```powershell
   Select-String -Path ROADMAP.md -Pattern "^## Milestone tags$"
   ```
   Expected: exactly one match.

3. Update the Spill Guard exit-criteria line, conditionally, based on precondition check 4:

   - **If precondition check 4 showed the file is NOT ignored** (Spill Guard fix already applied), find this exact line in the "## Phase 1 exit criteria" section:
     ```
     - [ ] Spill Guard files protect secrets; no credentials in repo
     ```
     Replace it with:
     ```
     - [x] Spill Guard files protect secrets; no credentials in repo (verified 2026-07-09: `.gitignore`, `.cursorignore`, and `.cursorindexingignore` carve out `ledger/token_log.md` consistently; see `PLAN-spill-guard-token-log-fix.md`)
     ```

   - **If precondition check 4 showed the file IS still ignored** (Spill Guard fix not yet applied), do not change this line. Leave it exactly as `- [ ] Spill Guard files protect secrets; no credentials in repo`.

4. Do not touch the other unchecked exit-criteria line, `- [ ] Human can describe what Coffee is, what it is not, and how Barista works`. This is a human judgment call, not something a plan execution can verify or check off. Leave it exactly as is.

5. Confirm only `ROADMAP.md` changed:
   ```powershell
   git status --short
   ```
   Expected: ` M ROADMAP.md` and nothing else.

## Edge cases a weaker model will miss

1. **Tag dates or names may have drifted since this plan was written.** Always use the live output of `git for-each-ref` (precondition 2) over the values written into this plan's template if they disagree. Do not silently trust the plan text over the actual repository state.
2. **Do not add Track A-F rows for Brews 12-35.** It is tempting to "complete" the checklist by adding a row per Brew, but the Track A-F structure is scoped to the original Phase 1 preview (Cursor setup, OpenRouter connection, Barista operational, first Roastery bake-off) per `PHASE_0_ROADMAP.md`'s "Phase 1 preview" section. Extending it retroactively for unrelated later work invents structure that was never part of the original design; the Milestone tags table added in Step 1 is the correct, honest way to close this gap without fabricating history.
3. **Conditional edit in Step 3 is not optional.** A weaker model might check the box regardless of the precondition result because "it looks done." The box must only be checked if the Spill Guard ignore-file parity check in precondition 4 actually passed. Checking it prematurely would violate Constitution Article 1.4 ("must never represent unverified output as certain fact").
4. **Markdown table column alignment.** The new table in Step 1 uses standard GitHub-flavored Markdown pipe syntax. Do not add extra spaces for visual alignment inside cells beyond a single space after `|` — this file is read by tooling (`tools/coffee_dashboard.py`, `tools/coffee_doctor.py`) that may parse Markdown tables, and inconsistent spacing has caused parsing issues elsewhere in this repo (see Ledger Summarizer bullet-parsing gap, Brew 19B-fix).
5. **File ending / trailing newline.** `ROADMAP.md` currently ends with the Shot history table and no trailing content after it. When appending the new section, ensure there is exactly one blank line between the end of the Shot history table and the new `## Milestone tags` heading (as shown with the leading blank line in the Step 1 content block), matching the blank-line-before-heading convention used throughout the rest of the file.
6. **Do not re-run this plan twice.** If Step 1's heading already exists (verified by precondition-equivalent check `Select-String -Path ROADMAP.md -Pattern "^## Milestone tags$"` before editing), do not append a second copy. Treat a pre-existing "## Milestone tags" section as "already applied" and stop.
7. **CRLF consistency**, same reasoning as `PLAN-spill-guard-token-log-fix.md`: check `ROADMAP.md`'s existing line-ending style before saving and preserve it.

## Acceptance criteria

1. ```powershell
   Select-String -Path ROADMAP.md -Pattern "^## Milestone tags$"
   ```
   Expected: exactly one match.

2. ```powershell
   (Select-String -Path ROADMAP.md -Pattern "^\| \`v").Count
   ```
   Expected: `5` (five tag rows in the new table; note the table uses backtick-wrapped tag names, so this pattern matches `| \`v0.1\` |` style rows).

3. Copied verbatim from `ROADMAP.md`'s own "Phase 1 exit criteria" section, the two lines under audit must be in one of these two valid end states:
   - Spill Guard line is either exactly `- [ ] Spill Guard files protect secrets; no credentials in repo` (unfixed case) or starts with `- [x] Spill Guard files protect secrets; no credentials in repo (verified` (fixed case) — never anything else.
   - Human-description line is unchanged: `- [ ] Human can describe what Coffee is, what it is not, and how Barista works`.
   Verify with:
   ```powershell
   Select-String -Path ROADMAP.md -Pattern "Human can describe what Coffee is"
   ```
   Expected: the line still starts with `- [ ]`.

4. ```powershell
   git status --short
   ```
   Expected: ` M ROADMAP.md` only.

5. ```powershell
   python tools\coffee_dashboard.py --root .
   ```
   Expected: exits without a Python traceback (confirms the Markdown edit did not break table parsing used by existing tooling). Status line may read `OK` or `WARN`; a traceback is the only failing outcome for this check.

## Rollback

```powershell
git checkout -- ROADMAP.md
```

If already committed:

```powershell
git log --oneline -- ROADMAP.md
git revert <commit-hash>
```

Do not run `git revert` without human approval.
