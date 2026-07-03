# Brew 2 Workflow Scorecard: Prompt Library MVP

## Metadata

- Brew: Brew 2
- System: Prompt Library / Espresso Shot Archive
- Status: MVP built and verified
- Scope: local prompt artifacts, reusable template, first approved prompt artifact
- Date: 2026-07-02

## Workflow Summary

Brew 2 was selected after Brew 1 closeout. The Prompt Library was built through small shots: planning, skeleton, reusable template, first prompt artifact, verification, status docs, retrospective, and ledger estimate. Verification caught that the first prompt artifact was initially untracked before closeout continued. The artifact was committed, then verification continued.

## Tool/Runtime Observations

- ChatGPT was useful for planning and prompt design.
- Codex was useful for structured repo work and verification support.
- PowerShell manual commits kept the human in control.
- The Prompt Library directly addresses the earlier problem of prompts being accidentally pasted into PowerShell.
- No Streamlit runtime was needed for Brew 2.

## Scores

| Category | Score | Notes |
| --- | --- | --- |
| Scope control | 5 | Each shot stayed focused on one responsibility. |
| Diff size | 5 | Prompt Library changes were small documentation diffs. |
| Human reviewability | 5 | Files were local Markdown and easy to inspect. |
| Prompt clarity | 5 | Template and artifact make shot structure explicit. |
| Reuse value | 4 | Useful starting point; more examples will improve it. |
| Safety / secrets handling | 5 | Prompt guidance warns against secrets and unsafe pasting. |
| Commit hygiene | 4 | Manual commits worked; verification caught one untracked artifact. |
| Verification usefulness | 5 | Verification checked structure, clarity, safety, reuse value, and Git state. |
| Overall workflow | 5 | Small local documentation shots produced a reusable Project Coffee asset. |

## Evidence

- `prompts/` skeleton exists.
- Reusable Espresso Shot template exists.
- First approved prompt artifact exists.
- Verification checked structure, clarity, safety, and reuse value.
- Verification caught the untracked artifact issue.
- Brew 2 remained documentation-only and local-first.
- No packages were installed.
- No app code was changed.

## What Improved

- Prompt artifacts now have a local home.
- Templates and concrete shot artifacts are separated.
- Archive location exists for retired prompts.
- Copy/paste safety is now documented.
- Verification now includes Git state, not just content.

## What Still Needs Improvement

- More successful Brew 1 prompts could be migrated later.
- More templates may be useful later, but should be added one at a time.
- Prompt artifact naming conventions may need refinement after more examples.
- Human commit discipline remains important.

## Recommendations

- Keep using the Prompt Library before long agent prompts.
- Store approved prompt artifacts after successful shots.
- Keep templates generic and artifacts concrete.
- Keep prompts and terminal commands visually separate.
- Continue manual PowerShell commits after review.
- Add more prompt artifacts only as separate shots.
