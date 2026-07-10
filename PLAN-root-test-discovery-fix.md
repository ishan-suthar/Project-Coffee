# PLAN-root-test-discovery-fix

## Goal

After this plan, running the repository's documented "run all tests" validation step actually runs the project's tests, instead of silently running zero tests and reporting success.

Right now, `docs/releases/v1.0-closeout-checklist.md` and `docs/releases/project-coffee-v1.0-handoff.md` both list `python -m unittest discover` (run from the repository root, no arguments) as a required validation command before declaring release readiness. Running that exact command from the repository root produces:

```
----------------------------------------------------------------------
Ran 0 tests in 0.000s

OK
```

Zero tests collected, exit code 0, printed as `OK`. This is a false-positive quality gate: every "tests pass" claim that relied on this exact command was never actually checking anything. The root cause is that `apps/coffee-status` and `apps/coffee-certification` contain hyphens, which are not valid characters in a Python dotted module path. Their `src/` subdirectories are real packages (they contain `src/__init__.py`), so when `unittest discover`'s namespace-package traversal from the repo root tries to resolve dotted module names through `apps.coffee-status...`, the hyphen breaks resolution and discovery silently yields nothing instead of raising a visible error. Running `python -m unittest discover -s tests` directly (scoped to the `tests/` directory only) works correctly and finds 214 tests, which confirms the tests themselves are fine — only the root-level bare `discover` invocation is broken.

This satisfies Coffee Principle 5 ("Small verified steps beat large magical leaps... verify outputs with tests") and Constitution Article 1.4 ("Coffee must never represent unverified output as certain fact"). It also matters directly for Brew 36 (OpenRouter integration behind explicit approval), the next planned shot per `ROADMAP.md`: that work is higher-risk (first real network/remote-model code path) and must not rely on a test gate that silently passes empty.

## Preconditions

Run these exact commands from the repository root in PowerShell and confirm the expected output. If any check does not match, STOP and report which one failed instead of improvising.

1. Confirm the broken command still reproduces the bug (if this has already been fixed by someone else, the count will not be 0):
   ```powershell
   python -m unittest discover
   ```
   Expected (before fix): `Ran 0 tests in 0.000s` followed by `OK`.
   **If this already shows a nonzero test count, STOP — the bug may already be fixed or the environment differs. Report the actual output and do not proceed.**

2. Confirm the tests directory itself works in isolation (proves the tests are not the problem):
   ```powershell
   python -m unittest discover -s tests
   ```
   Expected: `Ran 214 tests` (or more, if tests were added since this plan was written) ending in `OK` or `OK (skipped=...)`.

3. Confirm the four known test roots exist:
   ```powershell
   Test-Path tests
   Test-Path roastery\tests
   Test-Path apps\coffee-status\tests
   Test-Path apps\coffee-certification\tests
   ```
   Expected: `True` for all four. If any is `False`, STOP and report which one is missing — do not invent a replacement path.

4. Confirm `tools/run_all_tests.py` does not already exist (idempotency check):
   ```powershell
   Test-Path tools\run_all_tests.py
   ```
   Expected: `False`. If `True`, STOP and report "file already exists" — do not overwrite without comparing contents first.

## Files to touch

- `tools/run_all_tests.py` — CREATE. New standard-library script that discovers and runs all four known test roots independently and aggregates the result, so a hyphenated app directory can never again cause a silent zero-test false pass.
- `docs/releases/v1.0-closeout-checklist.md` — MODIFY. Replace the broken `python -m unittest discover` line (line 73 in the "Required Validation Commands" block) with `python tools\run_all_tests.py`.
- `docs/releases/project-coffee-v1.0-handoff.md` — MODIFY. Replace the broken `python -m unittest discover` line (line 116 in the "How To Validate The Repo" block) with `python tools\run_all_tests.py`.

No other file may be edited under this plan. Do not touch `docs/guides/new-project-onboarding-guide.md`, `docs/guides/project-coffee-setup-guide.md`, `apps/coffee-status/tests/README.md`, `apps/coffee-certification/tests/README.md`, `apps/coffee-status/README.md`, `apps/coffee-certification/README.md`, `apps/coffee-status/PROJECT_COFFEE.md`, `apps/coffee-status/roastery/tasting_notes.md`, or `roastery/tests/README.md` — every `unittest discover` reference in those files already uses a correctly scoped `-s <dir>` flag and is not broken.

## Steps

1. Create `tools/run_all_tests.py` with exactly this content:

   ```python
   """Aggregate Project Coffee test suites from every known test root.

   Running `python -m unittest discover` from the repository root silently
   collects zero tests, because apps/coffee-status and apps/coffee-certification
   contain hyphens, which are not valid Python module-name characters and break
   unittest's dotted-module resolution during discovery from the repo root.
   This script discovers each known test root independently, with the correct
   top-level directory for each, and aggregates the results so a hyphenated
   app directory can never again cause a silent zero-test false pass.
   """

   import sys
   import unittest
   from pathlib import Path

   REPO_ROOT = Path(__file__).resolve().parent.parent

   TEST_ROOTS = [
       (REPO_ROOT / "tests", REPO_ROOT),
       (REPO_ROOT / "roastery" / "tests", REPO_ROOT / "roastery"),
       (REPO_ROOT / "apps" / "coffee-status" / "tests", REPO_ROOT / "apps" / "coffee-status"),
       (REPO_ROOT / "apps" / "coffee-certification" / "tests", REPO_ROOT / "apps" / "coffee-certification"),
   ]


   def main() -> int:
       total_run = 0
       total_failures = 0
       total_errors = 0
       missing_roots = []

       for start_dir, top_level_dir in TEST_ROOTS:
           if not start_dir.is_dir():
               missing_roots.append(str(start_dir))
               continue
           loader = unittest.TestLoader()
           suite = loader.discover(start_dir=str(start_dir), top_level_dir=str(top_level_dir))
           runner = unittest.TextTestRunner(verbosity=1)
           print(f"\n=== {start_dir.relative_to(REPO_ROOT)} ===")
           result = runner.run(suite)
           total_run += result.testsRun
           total_failures += len(result.failures)
           total_errors += len(result.errors)

       print("\n=== Summary ===")
       print(f"Test roots checked: {len(TEST_ROOTS)}")
       if missing_roots:
           print(f"Missing test roots (skipped): {missing_roots}")
       print(f"Total tests run: {total_run}")
       print(f"Total failures: {total_failures}")
       print(f"Total errors: {total_errors}")

       if total_run == 0:
           print("FAIL: zero tests were collected across all known test roots.")
           return 1
       if total_failures or total_errors:
           return 1
       return 0


   if __name__ == "__main__":
       sys.exit(main())
   ```

2. Verify the new script compiles:
   ```powershell
   python -m py_compile tools\run_all_tests.py
   ```
   Expected: no output, exit code 0.

3. Run the new script:
   ```powershell
   python tools\run_all_tests.py
   ```
   Expected: `Total tests run:` a nonzero number (at least 214, matching the `tests/` count from precondition 2, plus whatever `roastery/tests`, `apps/coffee-status/tests`, and `apps/coffee-certification/tests` contribute), `Total failures: 0`, `Total errors: 0`, and exit code 0.
   ```powershell
   echo $LASTEXITCODE
   ```
   Expected: `0`

4. Open `docs/releases/v1.0-closeout-checklist.md`. Find this exact block (currently lines 63-75):
   ```
   ```powershell
   git status --short
   git diff --check
   python tools\coffee.py doctor --root .
   python tools\coffee.py release-check --root .
   python tools\coffee.py dashboard --root .
   python tools\coffee.py ledger-summary --root .
   python tools\evidence_bundle.py --root . --query "Project Coffee v1.0 stronger base" --max-results 5
   python tools\fleet_status.py --root .
   python tools\fleet_status.py --root . --registry fleet\projects.example.json --list
   python -m unittest discover
   python -m py_compile tools\coffee.py tools\coffee_dashboard.py tools\coffee_doctor.py tools\ledger_summary.py tools\release_check.py tools\evidence_bundle.py tools\fleet_status.py tools\pantry_search.py tools\roastery_report.py tools\install_project_coffee_template.py roastery\run_cup_test.py
   ```
   ```
   Replace only the line `python -m unittest discover` with `python tools\run_all_tests.py`. Every other line in the block stays exactly the same, including order.

5. Open `docs/releases/project-coffee-v1.0-handoff.md`. Find this exact block (currently lines 107-117):
   ```
   ```powershell
   git status --short
   git diff --check
   python tools\coffee.py doctor --root .
   python tools\coffee.py release-check --root .
   python tools\coffee.py dashboard --root .
   python tools\coffee.py ledger-summary --root .
   python tools\coffee.py evidence-bundle --root . --query "Project Coffee current Brew" --max-results 5
   python tools\coffee.py fleet-status --root . --registry fleet\projects.example.json --list
   python -m unittest discover
   ```
   ```
   Replace only the line `python -m unittest discover` with `python tools\run_all_tests.py`. Every other line in the block stays exactly the same, including order.

6. Confirm exactly two files besides the new script changed:
   ```powershell
   git status --short
   ```
   Expected: `??` for `tools/run_all_tests.py`, ` M` for `docs/releases/v1.0-closeout-checklist.md`, ` M` for `docs/releases/project-coffee-v1.0-handoff.md`. Nothing else.

## Edge cases a weaker model will miss

1. **Do not "fix" unittest discover by adding `__init__.py` files or renaming the hyphenated app directories.** Renaming `apps/coffee-status` or `apps/coffee-certification` would break every other correctly-scoped `unittest discover -s apps/coffee-status/tests` reference across a dozen other doc files (see the grep list in this plan's Goal section) and is far outside the "smallest correct diff" this plan authorizes. The fix is a new aggregator script, not a rename.
2. **Do not replace the correctly scoped `-s <dir>` invocations elsewhere in the docs.** Only the two bare `python -m unittest discover` lines (no `-s` flag) are broken. Lines like `python -m unittest discover -s apps/coffee-status/tests` already work correctly (verified: 9 tests pass) and must not be touched.
3. **Windows path separators in the script.** Use `pathlib.Path` with `/` division as shown in the exact script content above; `pathlib` normalizes this correctly on Windows. Do not hand-write backslash string paths — they break `top_level_dir` resolution across the `unittest.TestLoader().discover()` calls.
4. **Exit code matters, not just printed text.** A weaker model might see `OK` printed by a sub-suite and assume success without checking `$LASTEXITCODE`. Step 3 explicitly checks the exit code because that is what any future CI or release-check automation will actually gate on.
5. **`missing_roots` must not silently pass.** If a future refactor deletes one of the four test directories, the script logs it under "Missing test roots (skipped)" but does not fail by itself — only an overall zero-test count fails. Do not change this to a hard failure as part of this plan; that is a design decision for a future Brew, not this fix.
6. **UTF-8 / BOM in the new Python file.** Write `tools/run_all_tests.py` as plain UTF-8 without a byte-order mark. A BOM at the start of a `.py` file is usually tolerated by CPython's tokenizer but is inconsistent with every other file in `tools/`; check by inspecting the first bytes if unsure:
   ```powershell
   $bytes = [System.IO.File]::ReadAllBytes("tools\run_all_tests.py")
   "{0:X2} {1:X2} {2:X2}" -f $bytes[0], $bytes[1], $bytes[2]
   ```
   Expected: not `EF BB BF`.
7. **Markdown code fence nesting.** Both target doc files wrap the PowerShell block in triple-backtick fences. When editing, replace only the single line inside the fence; do not disturb the fence markers or the language tag (```powershell) above them, and do not accidentally close the fence early.

## Acceptance criteria

1. ```powershell
   python tools\run_all_tests.py
   ```
   Expected: `Total failures: 0`, `Total errors: 0`, `Total tests run:` greater than 0, no `FAIL:` line printed.

2. ```powershell
   echo $LASTEXITCODE
   ```
   Expected: `0`

3. ```powershell
   Select-String -Path docs\releases\v1.0-closeout-checklist.md -Pattern "^python -m unittest discover$"
   ```
   Expected: no match (the broken bare command is gone from this file).

4. ```powershell
   Select-String -Path docs\releases\project-coffee-v1.0-handoff.md -Pattern "^python -m unittest discover$"
   ```
   Expected: no match.

5. ```powershell
   Select-String -Path docs\releases\v1.0-closeout-checklist.md,docs\releases\project-coffee-v1.0-handoff.md -Pattern "python tools\\run_all_tests\.py"
   ```
   Expected: 2 matches, one per file.

6. ```powershell
   python -m unittest discover -s apps\coffee-status\tests
   ```
   Expected: still `OK` (9 tests) — confirms this plan did not disturb the already-correct scoped invocations.

7. Roadmap/PRD cross-reference: `EVALUATION_AND_ROASTERY.md` states models and workflows should be judged by evidence, not assumption. `COFFEE_PRINCIPLES.md` Principle 5 states "verify outputs with tests." This plan directly restores the ability to trust the documented release-validation test command.

## Rollback

```powershell
git checkout -- docs/releases/v1.0-closeout-checklist.md docs/releases/project-coffee-v1.0-handoff.md
Remove-Item tools\run_all_tests.py
```

If already committed:

```powershell
git log --oneline -- tools/run_all_tests.py docs/releases/v1.0-closeout-checklist.md docs/releases/project-coffee-v1.0-handoff.md
git revert <commit-hash>
```

Do not run `git revert` without human approval.
