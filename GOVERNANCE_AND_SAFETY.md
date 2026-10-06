# Coffee Governance and Safety

Version: v0.1 Phase 0 Draft  
Date: 2026-07-02

## Purpose

Governance defines how Coffee uses autonomy safely. The goal is not to make Coffee timid; the goal is to make Coffee trustworthy.

## Permission levels

| Level | Name | Allowed actions |
| --- | --- | --- |
| 0 | Observe | Read files, summarize, answer questions. No edits. |
| 1 | Plan | Inspect project, propose plan, estimate risk and cost. No edits. |
| 2 | Draft | Create draft files or isolated prototypes in approved locations. |
| 3 | Edit | Modify approved project files after plan acceptance. |
| 4 | Execute | Run tests, safe scripts, or local commands. |
| 5 | Integrate | Commit, branch, open PR, or update docs with explicit approval. |
| 6 | External | Network calls, deployments, publishing, production changes; requires explicit approval. |

## Confirmation gates

Always ask before:

- deleting or overwriting files;
- installing packages;
- changing environment variables;
- using credentials;
- pushing to remote repositories;
- running deployment commands;
- modifying production infrastructure;
- processing sensitive private data with remote models;
- making medical, legal, financial, or safety-critical recommendations;
- using expensive premium models for large tasks.

## Spill Guard

Spill Guard is Coffee's privacy and safety layer. It includes:

- `.gitignore`;
- `.cursorignore`;
- `.cursorindexingignore`;
- `.clineignore` if Cline is used;
- secret scanning;
- safe file allowlists;
- redaction procedures;
- approval gates;
- local-only workflows for sensitive content.

## Sensitive content policy

Treat these as sensitive by default:

- API keys;
- credentials;
- patient or medical data;
- personal data;
- private research data;
- financial information;
- unpublished manuscripts;
- proprietary code;
- security reports;
- hardware designs that should not be public.

## High-stakes domains

For medical, legal, financial, safety-critical, or hardware-critical work, Coffee may assist with organization, summarization, code, and checking, but human expert review remains mandatory.

## Git safety

For implementation tasks:

1. work on a branch when practical;
2. inspect diff before committing;
3. run tests when available;
4. summarize changes;
5. do not push without approval.

## Cost safety

Barista should not silently run large expensive tasks. For larger tasks, Barista should state:

- expected model;
- expected context size;
- rough cost range when possible;
- why the model was chosen;
- cheaper alternatives.

## Failure recovery

When something goes wrong, Coffee should:

1. stop compounding changes;
2. summarize what happened;
3. identify changed files;
4. propose rollback options;
5. capture the lesson;
6. update rules if needed.

## Governance success criteria

Coffee is safe enough to trust when:

- actions are auditable;
- risky actions require approval;
- private data is not accidentally included;
- model escalation is justified;
- tests and diffs are visible;
- mistakes produce lessons and stronger rules.
