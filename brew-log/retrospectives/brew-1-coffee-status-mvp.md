# Brew 1 Retrospective: Coffee Status MVP

## Summary

Coffee Status MVP was built and runtime verified as Project Coffee's first self-built local dashboard.

## What Worked

- The micro-shot approach worked.
- Building skeleton first, then home page, then reader extraction, then previews kept the work easy to verify.
- Manual PowerShell commits kept control with the human.
- Runtime verification caught the incorrect project-root resolution bug.
- Codex was useful after Cline/OpenRouter/Nemotron had tool-call instability.

## What Went Wrong

- The earlier broad Shot 4B/4C attempt was too large.
- Cline struggled with tool calls on the selected OpenRouter/Nemotron setup.
- A prompt was accidentally pasted into PowerShell instead of the Cline chat.
- Initial project-root resolution pointed to `apps/` instead of the repo root.

## Fixes And Adaptations

- Switched to smaller shots.
- Used no-command/file-only reviews when Cline command execution became unreliable.
- Used Codex for static verification and safer repo work.
- Used PowerShell manually for commits.
- Fixed root resolution and verified in Streamlit.

## Lessons Learned

- One Shot = One Responsibility should remain a core rule.
- App code, documentation updates, ledger updates, and scorecards should be separate shots.
- Runtime verification is necessary even after static checks pass.
- Project Coffee should remain runtime-agnostic: Cline and Codex are both Barista Runtime options.

## Follow-Up Actions

- Add Coffee Ledger estimate in a later shot.
- Add Roastery workflow scorecard in a later shot.
- Finalize Brew 1 closeout after those artifacts are committed.
- Consider a future Brew for improving Coffee Status UI or status model.
