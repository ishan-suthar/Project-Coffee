# Coffee Memory and Learning

Version: v0.1 Phase 0 Draft  
Date: 2026-07-02

## Purpose

The Brew Log is Coffee's working memory. It captures the state of projects, decisions, lessons, active context, progress, and recurring patterns so Coffee improves over time instead of starting fresh every session.

## Brew Log structure

```text
brew-log/
|
|-- active_context.md
|-- progress.md
|-- lessons_learned.md
|-- decisions.md
|-- open_questions.md
|-- mistakes.md
|-- retrospectives/
|-- project_sessions/
|-- weekly_summaries/
```

## Memory types

| Memory type | Purpose | Example |
| --- | --- | --- |
| Active context | What matters right now. | Current milestone, blockers, next steps. |
| Project memory | Stable project facts. | Architecture, stack, constraints. |
| Decision memory | Why choices were made. | Why Cursor was chosen as the Coffee Counter. |
| Lesson memory | What Coffee learned. | A model over-edited files; require smaller diffs next time. |
| Pattern memory | Reusable approaches. | A good recipe for writing Streamlit test scaffolds. |
| Failure memory | Mistakes to avoid. | Never run dependency upgrades without branch and tests. |

## When to update memory

Update the Brew Log when:

- a project goal changes;
- a major decision is made;
- a task completes;
- a model fails or succeeds in a notable way;
- a workflow becomes reusable;
- a risk is discovered;
- an assumption is corrected;
- a new project starts;
- a long session ends.

## Session closeout ritual

At the end of each meaningful work session, Barista should write:

1. What changed?
2. What was verified?
3. What remains open?
4. What did we learn?
5. What should Coffee remember next time?
6. Did any Recipe, rule, or scorecard need updating?

## Coffee Academy

Coffee Academy is the long-term learning loop. After every significant project, Coffee should extract reusable learning into:

- new Recipes;
- updated Barista policies;
- new evaluation tasks;
- model Tasting Notes;
- improved templates;
- better Pantry entries;
- new safety rules.

## Example lesson entry

```markdown
# Lesson Learned: Keep agent edits small

Date: 2026-07-02
Project: Project Coffee
Context: Early agent setup
What happened: A broad prompt caused the agent to propose too many files at once.
Lesson: For new projects, request a plan first, then approve one file group at a time.
Action: Add this to Barista Operating Manual and Cold Brew mode.
Tags: agent-control, safety, workflow
```

## Memory hygiene

Memory should be useful, not endless.

Rules:

- Keep active context short.
- Archive old session notes.
- Promote repeated lessons into Recipes or rules.
- Do not store secrets.
- Label uncertainty.
- Prefer concise structured notes over long transcripts.

## Brew Log success criteria

The Brew Log is working when Coffee can answer:

- Where did we leave off?
- Why did we make this decision?
- What has already been tried?
- What mistakes should we avoid?
- Which recipe worked last time?
- What should be done next?
