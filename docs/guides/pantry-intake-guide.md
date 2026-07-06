# Pantry Intake Guide

Status: v0.1 practical guide  
Date: 2026-07-06

## 1. Purpose

Pantry Intake is the habit of turning useful project knowledge into safe,
searchable Markdown before a future shot needs it.

Good Pantry notes make `tools/pantry_search.py` more useful. They also reduce
the need to load large files, stale docs, or noisy context into an AI session.

## 2. What Belongs In The Pantry

Use the Pantry for project knowledge that is safe to store in the repository
and useful to search later:

- project summaries;
- setup notes;
- local architecture notes;
- decisions and tradeoffs;
- public datasheet summaries;
- research summaries;
- workflow lessons;
- glossary terms;
- links to safe source documents;
- notes that explain where to find deeper context.

Prefer short notes with clear headings, source labels, dates, and search
keywords.

## 3. What Does Not Belong In The Pantry

Do not put these in the Pantry:

- secrets;
- raw credentials;
- API keys;
- tokens;
- SSH keys;
- OAuth blobs;
- private regulated data;
- production data;
- local credential store exports;
- large binary files;
- generated dependency folders;
- raw logs that may contain private data;
- full vendor PDFs when a safe summary is enough.

If a source might be sensitive, stop and ask for human review before indexing
or summarizing it.

## 4. Safety Rules

- No secrets.
- No raw credentials.
- No private regulated data unless a local and compliant workflow is explicitly
  designed first.
- Summarize large or binary documents before indexing.
- Record source quality and freshness instead of pretending all notes are equal.
- Keep snippets small enough that search results are useful without exposing
  long raw source text.
- Update or mark stale notes when the source changes.

## 5. Recommended Folder Structure

```text
knowledge/
  00_index.md
  project_docs/
  research/
  datasheets/
  decisions/
  notes/
```

Suggested use:

| Folder | Use |
| --- | --- |
| `knowledge/00_index.md` | Entry point, key document table, labels, and keywords. |
| `knowledge/project_docs/` | Project summaries, setup notes, and local workflow notes. |
| `knowledge/research/` | Summaries of public research, articles, or references. |
| `knowledge/datasheets/` | Safe summaries of public datasheets or technical manuals. |
| `knowledge/decisions/` | Decision notes and lightweight ADR-style records. |
| `knowledge/notes/` | Small notes that do not fit the other folders yet. |

## 6. Intake Workflow

1. Add or identify the source.
2. Confirm it is safe to summarize and store.
3. Create a short Markdown summary.
4. Add a table entry to `knowledge/00_index.md`.
5. Label source quality.
6. Label freshness.
7. Add likely search keywords.
8. Run `tools\pantry_search.py` against the relevant root.
9. Adjust headings or keywords if search misses the note.
10. Update the Brew Log if the knowledge changes project state or future work.

## 7. Markdown Summary Template

```markdown
# Topic Name

Status: Current
Freshness: Current
Source quality: Direct project source
Last reviewed: YYYY-MM-DD

## Summary

Short practical summary goes here.

## Key Details

- Detail one.
- Detail two.
- Detail three.

## Search Keywords

keyword one; keyword two; common alias; project-specific term

## Source

Safe source path or public URL goes here.

## Notes

Open questions, caveats, or follow-up items go here.
```

## 8. Research Paper Summary Template

```markdown
# Paper Title

Status: Reviewed
Freshness: Dated
Source quality: Public research paper
Last reviewed: YYYY-MM-DD

## Citation

Author, title, venue, year, and public link if safe.

## Practical Takeaway

One paragraph about why this matters to the project.

## Useful Ideas

- Idea one.
- Idea two.
- Idea three.

## Limits

- Limitation one.
- Limitation two.

## Search Keywords

paper acronym; method name; domain term; project feature
```

## 9. Datasheet Summary Template

```markdown
# Part Or Datasheet Name

Status: Reviewed
Freshness: Current
Source quality: Vendor datasheet
Last reviewed: YYYY-MM-DD

## What It Covers

Short description of the component or document.

## Relevant Specs

| Spec | Value | Notes |
| --- | --- | --- |
| Spec name | Value | Caveat or page reference |

## Safe Operating Notes

- Note one.
- Note two.

## Search Keywords

part number; interface; voltage; protocol; project subsystem
```

## 10. Decision Note Template

```markdown
# Decision Title

Status: Proposed
Date: YYYY-MM-DD
Decision owner: Human name or role

## Context

What problem forced this decision?

## Decision

What did we choose?

## Alternatives Considered

- Option one.
- Option two.

## Consequences

- Benefit.
- Tradeoff.
- Follow-up.

## Search Keywords

decision term; feature name; subsystem; alternative name
```

## 11. Search Tuning Tips

- Use clear headings with the words future-you will search.
- Add a `Search Keywords` section for aliases, acronyms, and common names.
- Prefer one topic per file.
- Put the most important term in the title or a heading.
- Use consistent labels for source quality and freshness.
- Search after intake and adjust only the note, not the tool, when wording is
  the issue.
- Use unique test sentinels for no-results checks.

Useful labels:

| Label type | Suggested values |
| --- | --- |
| Source quality | Direct project source, public official source, public secondary source, human note, unverified note |
| Freshness | Current, dated, stale, unknown |

## 12. Common Mistakes

- Storing secrets because they were near useful docs.
- Copying a huge source instead of writing a safe summary.
- Forgetting source and freshness labels.
- Using vague headings like `Notes`.
- Skipping keywords for acronyms or aliases.
- Letting old notes look current.
- Treating Pantry Search scores as truth instead of a ranking hint.

## 13. How Pantry Search Differs From Future RAG

Pantry Search is local keyword search over Markdown. It does not call a model,
compute embeddings, store vectors, or generate answers.

Future local RAG may add chunking, local snippet packs, stable document IDs, or
optional local embeddings. Pantry Intake comes first because structured,
safe, well-labeled Markdown is useful no matter which retrieval layer comes
later.
