# Agents

Short Barista role cards live here.

Role cards reduce token usage by giving future prompts a compact local reference
for expected behavior, context, and escalation rules. This folder is for small
role definitions, not a full agent framework.

## Start Here

- Use `agents/templates/barista-role-template.md` when creating a new role card.
- Create specialized roles one at a time only when repeated work justifies them.
- Keep role cards short and link to source docs instead of copying them.
- Do not store secrets, credentials, API keys, or private data in role cards.

## Current Roles

| Role card | Use |
| --- | --- |
| `agents/barista-main.md` | Main Project Coffee planning, routing, verification, and closeout role. |
