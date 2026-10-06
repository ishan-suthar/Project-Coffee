# PLAN-architecture-doc-drift-cleanup

## Goal

After this plan, `ARCHITECTURE.md`'s repository-structure diagram matches the directories that actually exist and are actually used, and the two superseded/duplicate directories (`baristas/`, `pantry/`) carry a short pointer to the directory that replaced them in practice. Right now `ARCHITECTURE.md` (lines 81-155) shows a repo layout with `baristas/`, `templates/` (lowercase), and `decisions/` (lowercase, singular ADR folder) — but the live repository actually uses `agents/` (6 role cards, a role-selection guide, and a role-usage test; `baristas/` has only 3 stale files and was not updated after Brew 7), `TEMPLATES/` (uppercase), and a two-location ADR split of `DECISIONS/` (ADR-0001 through ADR-0004) plus `docs/adr/` (ADR-0005 onward) that is already correctly indexed in `brew-log/decisions.md` but never reflected back into `ARCHITECTURE.md`'s own diagram.

This satisfies Coffee Constitution Article 4 (documentation duty) and Principle 7 ("every important decision should be explainable"). A stale architecture diagram risks a future Barista (or a less capable model executing a future plan) writing new specialist-role content into `baristas/` instead of `agents/`, or new project knowledge into `pantry/` instead of `knowledge/`, because the founding document still names the old location as canonical.

## Preconditions

Run these exact commands from the repository root in PowerShell and confirm the expected output. If any check does not match, STOP and report which one failed instead of improvising.

1. Confirm `agents/` has more content than `baristas/` (proves `agents/` is the active directory):
   ```powershell
   (Get-ChildItem agents -File -Recurse).Count
   (Get-ChildItem baristas -File -Recurse).Count
   ```
   Expected: the `agents` count is greater than the `baristas` count (currently 11 vs 4).

2. Confirm `knowledge/00_index.md` is referenced as the live index and `pantry/00_index.md` is still a seed file:
   ```powershell
   Select-String -Path pantry\00_index.md -Pattern "Seed file"
   ```
   Expected: one match. If this does not match (someone has already populated `pantry/00_index.md` with real content), STOP and report — do not add a deprecation notice to a directory that is now actually in use.

3. Confirm the exact current repository-structure block in `ARCHITECTURE.md` still reads as this plan expects:
   ```powershell
   Select-String -Path ARCHITECTURE.md -Pattern "^\|-- baristas/$"
   ```
   Expected: exactly one match. If no match, `ARCHITECTURE.md` may have already been updated — STOP and report instead of re-editing.

## Files to touch

- `ARCHITECTURE.md` — MODIFY. Update the "## Repository structure" code block (the fenced block starting at `Project_Coffee/` and ending before `## Current implementation choices`) to replace `baristas/`, `templates/`, and `decisions/` entries with the actual current layout.
- `baristas/README.md` — MODIFY. Add a one-line pointer to `agents/` at the top of the file, above the existing content.
- `pantry/00_index.md` — MODIFY. Add a one-line pointer to `knowledge/00_index.md` at the top of the file, above the existing content.

No other file may be edited under this plan. Do not delete `baristas/` or `pantry/` or any file inside them — they remain as historical/legacy directories, not removed.

## Steps

1. Open `ARCHITECTURE.md`. In the "## Repository structure" fenced code block, find these lines (currently around lines 99-107):
   ```
   |-- baristas/
   |   |-- barista_orchestrator.md
   |   |-- espresso_fast_coder.md
   |   |-- cappuccino_research.md
   |   |-- mocha_ai_ml.md
   |   |-- macchiato_embedded.md
   |   |-- latte_docs.md
   |   |-- sentinel_review.md
   |
   ```
   Replace that entire block with:
   ```
   |-- agents/
   |   |-- barista-main.md
   |   |-- espresso-fast-coder.md
   |   |-- cappuccino-research.md
   |   |-- mocha-python-ai.md
   |   |-- macchiato-embedded.md
   |   |-- flat-white-code-review.md
   |   |-- cortado-devops-infra.md
   |   |-- role-selection-guide.md
   |
   |-- baristas/ (legacy, superseded by agents/ since Brew 7; see baristas/README.md)
   |
   ```

2. In the same fenced block, find the Pantry entry (currently around lines 115-123):
   ```
   |-- pantry/
   |   |-- 00_index.md
   |   |-- project_docs/
   |   |-- papers/
   |   |-- datasheets/
   |   |-- protocols/
   |   |-- APIs/
   |   |-- notes/
   |
   ```
   Replace it with:
   ```
   |-- knowledge/
   |   |-- 00_index.md
   |   |-- project_docs/
   |
   |-- pantry/ (legacy seed structure, superseded by knowledge/ since Brew 7B; see pantry/00_index.md)
   |
   ```

3. In the same fenced block, find the templates entry (currently near the end, around lines 141-147):
   ```
   |-- templates/
   |   |-- project_brief.md
   |   |-- recipe_template.md
   |   |-- lesson_learned.md
   |   |-- barista_profile.md
   |   |-- model_scorecard.md
   |
   ```
   Replace it with:
   ```
   |-- TEMPLATES/
   |   |-- project_brief.md
   |   |-- recipe_template.md
   |   |-- lesson_learned.md
   |   |-- barista_profile.md
   |   |-- model_scorecard.md
   |   |-- project-coffee/ (reusable template pack for onboarding new projects)
   |
   ```

4. In the same fenced block, find the decisions entry (currently around lines 148-150):
   ```
   |-- decisions/
   |   |-- ADR-0001-project-coffee-identity.md
   |
   ```
   Replace it with:
   ```
   |-- DECISIONS/
   |   |-- ADR-0001-project-coffee-identity.md
   |   |-- ADR-0002-model-and-vendor-independence.md
   |   |-- ADR-0003-markdown-first-memory-and-knowledge.md
   |   |-- ADR-0004-house-blend-routing.md
   |
   |-- docs/adr/ (ADR-0005 and later; see brew-log/decisions.md for the full index)
   |
   ```

5. Open `baristas/README.md`. Current content is exactly:
   ```
   # Baristas

   Specialist agent profiles live here.
   ```
   Replace it with:
   ```
   # Baristas

   Legacy directory. Superseded by `agents/` since Brew 7 (see
   `agents/role-selection-guide.md`). Kept for history; do not add new
   specialist role cards here.

   Specialist agent profiles live here.
   ```

6. Open `pantry/00_index.md`. Current content is exactly:
   ```
   # Pantry Index

   Status: Seed file. Add curated project knowledge here.
   ```
   Replace it with:
   ```
   # Pantry Index

   Status: Seed file. Add curated project knowledge here.

   Legacy directory. Superseded by `knowledge/` since Brew 7B (see
   `knowledge/00_index.md`, the live retrieval index). Kept for history; do
   not add new project knowledge here.
   ```

7. Confirm exactly three files changed:
   ```powershell
   git status --short
   ```
   Expected: ` M ARCHITECTURE.md`, ` M baristas/README.md`, ` M pantry/00_index.md`, nothing else.

## Edge cases a weaker model will miss

1. **Do not delete or move any files.** This plan only edits three Markdown files to add pointers and correct a diagram. `baristas/barista_orchestrator.md`, `baristas/espresso_fast_coder.md`, `baristas/sentinel_review.md`, and every file under `pantry/` stay exactly where they are.
2. **Case-sensitive rename risk.** `TEMPLATES/` and `templates/` (and `DECISIONS/`/`decisions/`) differ only in case. On Windows' default case-insensitive filesystem, creating a new lowercase directory when an uppercase one already exists can silently collide with or shadow the existing one instead of creating a separate directory. This plan does not create or rename any directory — it only corrects text inside `ARCHITECTURE.md` to describe the directories that already exist (`TEMPLATES/`, `DECISIONS/`) instead of the lowercase names that do not exist. Do not attempt to rename anything to make the casing "consistent."
3. **`agents/templates/` is a real subdirectory, not a naming collision with root `TEMPLATES/`.** `agents/templates/barista-role-template.md` already exists and is unrelated to root `TEMPLATES/`. Do not merge, rename, or cross-reference these two in this plan; that is out of scope.
4. **The `role-selection-guide.md` file, not `role-usage-test.md`, belongs in the diagram.** `agents/role-usage-test.md` is a test record, not a role card; the diagram in Step 1 intentionally lists `role-selection-guide.md` as the index/entry-point file and omits `role-usage-test.md` and `agents/README.md`, matching how the original diagram only listed role-card-shaped files, not every file in the directory.
5. **Do not add a deprecation notice implying `baristas/` or `pantry/` content is wrong.** The wording in Steps 5 and 6 says "superseded" and "legacy," not "deprecated," "broken," or "delete this." Some content in `baristas/barista_orchestrator.md` may still be referenced elsewhere; this plan only redirects where *new* content should go, per Coffee Principle 9 (simplicity, avoid churn) and the "smallest correct diff" convention used throughout this repo's Brews.
6. **Fenced code block integrity.** The "## Repository structure" section in `ARCHITECTURE.md` is one large fenced block (` ```text ... ``` `). All four edits in Steps 1-4 happen inside that single fence. Do not close and reopen the fence between edits, and do not change the fence's language tag (`text`).
7. **UTF-8 BOM and line endings**, same reasoning as the other plans in this set: check `ARCHITECTURE.md`'s existing encoding and line-ending style before saving and preserve it.

## Acceptance criteria

1. ```powershell
   Select-String -Path ARCHITECTURE.md -Pattern "^\|-- agents/$"
   ```
   Expected: exactly one match.

2. ```powershell
   Select-String -Path ARCHITECTURE.md -Pattern "^\|-- baristas/ \(legacy"
   ```
   Expected: exactly one match.

3. ```powershell
   Select-String -Path ARCHITECTURE.md -Pattern "^\|-- knowledge/$"
   ```
   Expected: exactly one match.

4. ```powershell
   Select-String -Path ARCHITECTURE.md -Pattern "^\|-- TEMPLATES/$"
   ```
   Expected: exactly one match.

5. ```powershell
   Select-String -Path ARCHITECTURE.md -Pattern "^\|-- DECISIONS/$"
   ```
   Expected: exactly one match.

6. ```powershell
   Select-String -Path baristas\README.md -Pattern "Legacy directory"
   ```
   Expected: exactly one match.

7. ```powershell
   Select-String -Path pantry\00_index.md -Pattern "Legacy directory"
   ```
   Expected: exactly one match.

8. ```powershell
   git status --short
   ```
   Expected: exactly three modified files, ` M ARCHITECTURE.md`, ` M baristas/README.md`, ` M pantry/00_index.md`.

## Rollback

```powershell
git checkout -- ARCHITECTURE.md baristas/README.md pantry/00_index.md
```

If already committed:

```powershell
git log --oneline -- ARCHITECTURE.md baristas/README.md pantry/00_index.md
git revert <commit-hash>
```

Do not run `git revert` without human approval.
