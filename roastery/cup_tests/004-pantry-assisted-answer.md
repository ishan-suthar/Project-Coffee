# 004 Pantry Assisted Answer

## Purpose

Test grounded answering from retrieved local knowledge snippets and citation
discipline without requiring the actual Pantry Search tool.

## Order

You are Barista answering from provided Pantry snippets. Use only the snippets
below. Cite snippet labels in square brackets, such as `[A]`.

Pantry snippets:

```text
[A] Project Coffee uses One Shot = One Responsibility. Non-trivial work should
start with Decaf Mode, then move through approval, implementation, validation,
Brew Log updates, Roastery/Ledger updates, diff review, and human commit.

[B] Pantry Search is local Markdown keyword search. It does not call models,
compute embeddings, store vectors, or replace human review.

[C] Roastery evidence should record commands, outcomes, model or workflow
context, costs/tokens when available, unknowns when unavailable, and lessons
without inventing quality scores.
```

Question:

How should Project Coffee handle a new small documentation improvement from
planning through evidence recording?

Answer with:

1. a short recommended workflow;
2. what evidence to record;
3. one sentence explaining why this is not full RAG.

Every factual claim from the snippets should cite at least one snippet label.

## Success Criteria

- Uses only snippet-provided facts.
- Cites `[A]`, `[B]`, and `[C]` where relevant.
- Gives an actionable workflow.
- Explains that Pantry Search is keyword search, not full RAG.

## Scoring Notes

High scores should be grounded, concise, and well cited. Lower scores should go
to answers that omit citations, add unsupported facts, or treat Pantry Search
as a model or semantic retrieval system.

