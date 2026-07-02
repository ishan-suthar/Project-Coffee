# Brew 2 / Shot 5C Prompt Artifact: Espresso Shot Template

## Metadata

- Brew: Brew 2
- Shot: 5C
- Status: Approved / completed
- Purpose: Add first reusable Espresso Shot template
- Runtime used: Codex
- Commit status: Committed by human after review
- Safety note: Prompt intended for agent chat, not PowerShell

## Why This Prompt Exists

Project Coffee needs local prompt artifacts so long prompts can be reviewed before use, stored after successful shots, and kept out of the terminal. This reduces accidental prompt pasting into PowerShell and gives future Barista Runtimes a local, reviewable pattern to follow.

## Approved Prompt

```text
We are continuing Project Coffee.

Task:
Brew 2 / Shot 5C: Add first reusable Espresso Shot template only.

You are acting as a Barista Runtime for Project Coffee.

Role / architecture context:
- Project Coffee is local-first, model-agnostic, vendor-agnostic, and runtime-agnostic.
- Cursor is the Coffee Counter / IDE.
- Codex is currently acting as the Barista Runtime.
- Cline or another agent may also act as a Barista Runtime later.
- OpenRouter, OpenAI, local models, or another gateway may act as the Coffee Core.
- Beans are replaceable model choices.

Current state:
- Brew 1 / Coffee Status MVP is complete and committed.
- Brew 2 / Shot 5A planning is complete.
- Brew 2 / Shot 5B Prompt Library skeleton is complete and committed.
- prompts/ now exists with README files for the library, Espresso Shots, templates, and archive.

Rule:
One Shot = One Responsibility.

Goal:
Create one reusable Espresso Shot prompt template.

Scope:
Create only this file:
- prompts/templates/espresso-shot-template.md

Allowed file:
- prompts/templates/espresso-shot-template.md

Do not modify:
- prompts/README.md
- prompts/espresso-shots/README.md
- prompts/templates/README.md
- prompts/archive/README.md
- prompts/espresso-shots/
- prompts/archive/
- recipes/
- apps/coffee-status/
- brew-log/
- ledger/
- roastery/
- config/
- DECISIONS/
- README.md
- ROADMAP.md
- CHANGELOG.md
- any .env or credential files

Template content requirements:
- Title: # Espresso Shot Prompt Template
- Purpose: explain this template is for one small, reviewable Project Coffee task.
- Copy/paste safety note:
  - Paste this into the agent chat, not PowerShell or terminal.
  - Terminal commands belong in terminal sections only.
  - Keep prompts and shell commands visually separate.
- Template block: include a fenced text block with a reusable prompt skeleton.
- Placeholder style: use clear placeholders such as [BREW_NUMBER], [SHOT_NUMBER], [SHOT_NAME], [GOAL], [ALLOWED_FILES], [FORBIDDEN_FILES], [VERIFICATION_COMMANDS], and [REPORT_ITEMS].
- Recommended report items:
  - Files created
  - Files modified
  - Verification commands run
  - Verification result
  - Constraints honored
  - Whether the shot passes
  - Recommended commit message
  - Recommended next shot
- Usage notes:
  - Keep each shot small.
  - Prefer one file or one responsibility.
  - Commit manually after review.
  - Do not include secrets.
  - Do not let the agent commit unless explicitly approved.

Constraints:
- Do not add actual Brew 1 or Brew 2 prompt content yet.
- Do not migrate previous prompts yet.
- Do not create archive entries.
- Do not update Brew Log, Roadmap, Changelog, Ledger, or Roastery.
- Do not install packages.
- Do not run Streamlit.
- Do not run tests.
- Do not commit.
- Do not stage files.
- Do not inspect .env files, credential files, API keys, tokens, or private secrets.

Allowed verification:
- git status --short
- Get-Content prompts/templates/espresso-shot-template.md
- git diff -- prompts/templates/espresso-shot-template.md

Report requirements:
- Files created
- Files modified
- Summary of the template content
- Confirmation that only prompts/templates/espresso-shot-template.md changed
- Confirmation that no app code was modified
- Confirmation that Brew Log, Roadmap, Changelog, Ledger, and Roastery were not modified
- Confirmation that no packages were installed
- Confirmation that Streamlit was not run
- Confirmation that no commit was made
- Whether Shot 5C passes
- Recommended commit message
- Recommended next shot

Stop condition:
Stop after the report.
```

## Review Notes

- This prompt successfully produced `prompts/templates/espresso-shot-template.md`.
- The human reviewed and committed the result manually.
- No app code, Brew Log, Roadmap, Changelog, Ledger, or Roastery files were modified.
- No packages were installed.
- Streamlit was not run.

## Reuse Guidance

- Use this artifact as an example of a completed one-file documentation shot.
- For new shots, prefer copying `prompts/templates/espresso-shot-template.md` rather than copying this artifact directly.
- Keep concrete shot artifacts under `prompts/espresso-shots/`.
- Archive superseded prompt artifacts under `prompts/archive/` only in a separate shot.
