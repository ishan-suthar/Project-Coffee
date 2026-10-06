# PLAN-spill-guard-token-log-fix

## Goal

After this plan, `ledger/token_log.md` can be committed to git. Right now it cannot: `.gitignore` line 11 (`**/*token*`) silently excludes it, and unlike `.cursorignore` and `.cursorindexingignore`, `.gitignore` has no negation line to carve the file back in. The Cursor rule `.cursor/rules/project-coffee-spill-guard.mdc` line 20 already states the intended exception in writing: "`ledger/token_log.md` is allowed — it tracks usage metrics, not credentials." This plan makes `.gitignore` match that already-documented intent.

This satisfies Project Coffee's Spill Guard requirement (`GOVERNANCE_AND_SAFETY.md`, "Spill Guard" section) that ignore files correctly separate real secrets from legitimate tracked project data. It is a roadmap-adjacent fix: `ROADMAP.md` Phase 1 exit criteria includes `- [ ] Spill Guard files protect secrets; no credentials in repo`, and this bug (silently dropping a legitimate Ledger file) is the kind of Spill Guard defect that criterion exists to catch.

## Preconditions

Run these exact commands from the repository root in PowerShell and confirm the expected output before making any change. If any check does not match, STOP and report which one failed instead of improvising.

1. Confirm the file exists and is not tracked:
   ```powershell
   Test-Path ledger\token_log.md
   ```
   Expected: `True`

2. Confirm git currently ignores it:
   ```powershell
   git check-ignore -v ledger/token_log.md
   ```
   Expected: one line of output containing `.gitignore:` and `**/*token*` and `ledger/token_log.md`.

3. Confirm `.cursorignore` already has the negation (reference pattern to copy):
   ```powershell
   Select-String -Path .cursorignore -Pattern "!ledger/token_log.md"
   ```
   Expected: one match, `.cursorignore:12:!ledger/token_log.md`

4. Confirm `.gitignore` does NOT yet have the negation (idempotency check):
   ```powershell
   Select-String -Path .gitignore -Pattern "!ledger/token_log.md"
   ```
   Expected: no output (no match). **If this command finds a match, the fix is already applied. STOP and report "already fixed" — do not edit the file again.**

## Files to touch

- `.gitignore` — MODIFY. Add one line, `!ledger/token_log.md`, immediately after the `**/*token*` line. No other line in this file changes.

No other file may be edited under this plan.

## Steps

1. Open `.gitignore` and locate this line (currently line 11):
   ```
   **/*token*
   ```

2. Insert a new line immediately after it so the surrounding block reads exactly:
   ```
   **/*key*
   **/*token*
   !ledger/token_log.md
   **/*password*
   ```
   (The `**/*key*` and `**/*password*` lines already exist; only the `!ledger/token_log.md` line is new, inserted between `**/*token*` and `**/*password*`.)

3. Save the file. Do not change line-ending style: if the file uses CRLF line endings, the new line must also use CRLF. Check first with:
   ```powershell
   (Get-Content .gitignore -Raw) -match "`r`n"
   ```
   If this returns `True`, the file uses CRLF; ensure your editor/tool preserves that when saving.

4. Verify the file has no byte-order mark before saving over it:
   ```powershell
   $bytes = [System.IO.File]::ReadAllBytes(".gitignore")
   "{0:X2} {1:X2} {2:X2}" -f $bytes[0], $bytes[1], $bytes[2]
   ```
   Expected: does not print `EF BB BF` (BOM). If it currently has no BOM, the edited file must also have no BOM — use plain UTF-8 (no BOM) encoding when writing.

5. Re-run the ignore check:
   ```powershell
   git check-ignore -v ledger/token_log.md
   ```
   Expected: no output at all (exit code 1). This confirms the file is no longer ignored.

6. Confirm git now sees the file as trackable:
   ```powershell
   git status --short -- ledger/token_log.md
   ```
   Expected: `?? ledger/token_log.md` (untracked, visible to git — not silently hidden).

7. Confirm nothing else changed:
   ```powershell
   git status --short
   ```
   Expected: exactly one line, `?? ledger/token_log.md` (plus the modified `.gitignore` itself if not yet reviewed — `.gitignore` will show as ` M .gitignore`). No other files should appear as newly untracked or modified.

8. STOP. Do not run `git add` or `git commit`. Staging and committing require explicit human approval per `PROJECT_COFFEE.md` ("Approval Gates") and `GOVERNANCE_AND_SAFETY.md`. Report the diff (`git diff -- .gitignore`) to the human and wait for approval to stage and commit.

## Edge cases a weaker model will miss

1. **File already fixed.** If precondition check 4 finds `!ledger/token_log.md` already in `.gitignore`, do not add a duplicate line. Report "already fixed, no action taken" and stop.
2. **Line ending mismatch.** `.gitignore` may use CRLF (Windows) line endings throughout. Mixing in a bare LF for the new line creates an inconsistent file that some tools flag as a diff-noise issue. Match the existing style (step 4 above).
3. **Negation ordering in gitignore syntax.** A `!pattern` negation only works if it appears *after* the excluding pattern in file-read order, and only if none of the file's parent directories are separately excluded elsewhere in the file. `ledger/` as a directory is not excluded anywhere in `.gitignore` (only the filename pattern `**/*token*` matches), so this negation will work — but placing `!ledger/token_log.md` *before* `**/*token*` instead of after would silently fail to un-ignore the file. Order matters.
4. **BOM introduction.** Some editors save UTF-8 files with a byte-order mark by default. If `.gitignore` currently has no BOM (check step 4 above) and the edit tool introduces one, git and some shells will still function, but it creates unnecessary diff noise and inconsistency with the other Spill Guard ignore files. Keep it BOM-free if it started BOM-free.
5. **Overly broad negation.** Do not write `!*token*` or `!**/*token*` (which would re-include every file matching the token pattern, defeating the Spill Guard rule). The negation must be the exact literal path `!ledger/token_log.md` and nothing broader, matching what `.cursorignore` already does.
6. **Case sensitivity.** Git internally treats paths as case-sensitive and always uses forward slashes, even on Windows. The pattern must be exactly `ledger/token_log.md` (lowercase, forward slash), not `Ledger/Token_Log.md` or `ledger\token_log.md`.
7. **Do not touch `.cursorignore` or `.cursorindexingignore`.** They already have the correct exception (verified in precondition 3). Editing them is out of scope for this plan and risks introducing a duplicate line.
8. **Do not stage or commit.** Even though the fix is small and obviously correct, staging/committing is a Governance Level 5 action requiring explicit human approval (see step 8). Completing the edit is not the same as completing the approval gate.

## Acceptance criteria

Run each command and confirm the exact expected result.

1. ```powershell
   Select-String -Path .gitignore -Pattern "!ledger/token_log.md"
   ```
   Expected: exactly one match.

2. ```powershell
   git check-ignore -v ledger/token_log.md
   ```
   Expected: no output, exit code 1.

3. ```powershell
   Select-String -Path .gitignore,.cursorignore,.cursorindexingignore -Pattern "!ledger/token_log.md"
   ```
   Expected: 3 matches total, one per file (parity across all three Spill Guard ignore files).

4. ```powershell
   git diff --stat -- . ':!.gitignore'
   ```
   Expected: no output (only `.gitignore` changed; nothing else touched).

5. ```powershell
   git status --short
   ```
   Expected: ` M .gitignore` and `?? ledger/token_log.md`, nothing else.

6. Roadmap cross-reference (from `ROADMAP.md` Phase 1 exit criteria, copied verbatim): `- [ ] Spill Guard files protect secrets; no credentials in repo`. This plan is a precondition for checking that box honestly — do not check it as part of this plan; that update belongs to `PLAN-roadmap-phase-reconciliation.md`.

## Rollback

If the change needs to be undone before it is committed:

```powershell
git checkout -- .gitignore
```

If it was already committed and needs to be reverted:

```powershell
git log --oneline -- .gitignore
git revert <commit-hash>
```

Do not run `git revert` without human approval, consistent with the commit/push approval gate in `PROJECT_COFFEE.md`.
