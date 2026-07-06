# 003 Docs Summary

## Purpose

Test documentation clarity, prioritization, and concise next-step writing.

## Order

You are a documentation-focused Barista. Summarize the fictional project status
below for a human maintainer.

Source snippet:

```text
Project: Local Recipe Box

README says the app stores recipes as Markdown files in a local folder. It has
a small Python CLI and no network features. The test README says to run
`python -m unittest`. The current status note says the parser works, but import
deduplication is still manual. The next planned task is to clarify the CLI
examples before adding new parser features.
```

Produce:

1. a concise user-facing summary, maximum 4 bullets;
2. the most likely next step;
3. one risk or open question;
4. one validation command.

Do not invent features beyond the snippet.

## Success Criteria

- Summary is clear and short.
- Next step matches the status note.
- Validation command is plausible.
- Does not add unsupported network, database, or UI claims.

## Scoring Notes

High scores should preserve the source facts and produce useful maintainer
copy. Lower scores should go to answers that over-explain, invent missing
features, or skip the validation command.

