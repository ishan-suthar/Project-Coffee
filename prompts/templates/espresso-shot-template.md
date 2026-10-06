# Espresso Shot Prompt Template

## Purpose

Use this template for one small, reviewable Project Coffee task. Copy it, customize the placeholders, and paste the finished prompt into Codex, Cline, or another Barista Runtime.

## Copy/Paste Safety Note

- Paste this into the agent chat, not PowerShell or terminal.
- Terminal commands belong in terminal sections only.
- Keep prompts and shell commands visually separate.

## Template Block

```text
We are continuing Project Coffee.

Task:
[BREW_NUMBER] / [SHOT_NUMBER]: [SHOT_NAME]

You are acting as a Barista Runtime for Project Coffee.

Role / architecture context:
- Project Coffee is local-first, model-agnostic, vendor-agnostic, and runtime-agnostic.
- Cursor is the Coffee Counter / IDE.
- Codex, Cline, or another agent may act as the Barista Runtime.
- OpenRouter, OpenAI, local models, or another gateway may act as the Coffee Core.
- Beans are replaceable model choices.

Current state:
[CURRENT_STATE]

Rule:
One Shot = One Responsibility.

Goal:
[GOAL]

Scope:
[SCOPE]

Allowed changes:
[ALLOWED_FILES]

Forbidden changes:
[FORBIDDEN_FILES]

Allowed verification:
[VERIFICATION_COMMANDS]

Forbidden commands/actions:
[FORBIDDEN_COMMANDS_OR_ACTIONS]

Report requirements:
[REPORT_ITEMS]

Stop condition:
Stop after the report.
```

## Recommended Report Items

- Files created
- Files modified
- Verification commands run
- Verification result
- Constraints honored
- Whether the shot passes
- Recommended commit message
- Recommended next shot

## Usage Notes

- Keep each shot small.
- Prefer one file or one responsibility.
- Commit manually after review.
- Do not include secrets.
- Do not let the agent commit unless explicitly approved.
