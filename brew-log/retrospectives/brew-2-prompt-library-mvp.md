# Brew 2 Retrospective: Prompt Library MVP

## Summary

Brew 2 created a local Prompt Library / Espresso Shot Archive for Project Coffee.

## What Worked

- Creating the `prompts/` skeleton first kept scope small.
- The reusable Espresso Shot template captured the Project Coffee shot structure.
- The first approved prompt artifact demonstrated how completed prompts should be archived.
- Verification caught that the prompt artifact was untracked before closeout.
- Manual Git commits kept the human in control.
- The Prompt Library directly addresses the earlier prompt-into-PowerShell mistake.

## What Went Wrong

- One artifact existed locally but was initially untracked.
- The process still depended on manual discipline to commit after each shot.
- It is easy to confuse verification-only shots with commit-producing shots.
- More prompt artifacts from Brew 1 are not yet migrated.

## Fixes And Adaptations

- Committed the untracked prompt artifact before continuing.
- Reran verification after the commit.
- Kept closeout docs, retrospective, ledger, and scorecard as separate shots.
- Continued using Codex for structured repo work and PowerShell for manual commits.

## Lessons Learned

- Prompt artifacts are useful only if committed.
- Verification should check both content and Git state.
- A local Prompt Library improves repeatability and reduces terminal-paste mistakes.
- One Shot = One Responsibility remains effective for documentation infrastructure.
- Project Coffee should keep separating prompts, commands, code, docs, ledger, and roastery work.

## Follow-Up Actions

- Add a Brew 2 ledger estimate in a later shot.
- Add a Brew 2 Roastery workflow scorecard in a later shot.
- Finalize Brew 2 closeout after those artifacts are committed.
- Consider later migration of important Brew 1 prompts into `prompts/espresso-shots/`.
- Consider adding more reusable prompt templates only as separate shots.
