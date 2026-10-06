# Evaluation and Roastery

Version: v0.1 Phase 0 Draft  
Date: 2026-07-02

## Purpose

The Roastery is where Coffee evaluates models, prompts, tools, agents, and workflows. It prevents hype-driven decisions by turning experience into evidence.

## Why evaluation matters

A model can be impressive in a demo and poor in daily use. Coffee should judge models by practical usefulness:

- Did it solve the task?
- Did it preserve code quality?
- Did it over-engineer?
- Did it follow rules?
- Did it require heavy supervision?
- Was it worth the cost?

## Tasting Notes

Tasting Notes are model and workflow scorecards. They should be short enough to maintain but structured enough to compare.

| Metric | What to record |
| --- | --- |
| Correctness | Did the result work? Did tests pass? |
| Completeness | Did it finish the requested task? |
| Code quality | Was the code readable, simple, and maintainable? |
| Context handling | Did it use the right files and documents? |
| Instruction following | Did it obey AGENTS.md, rules, and constraints? |
| Cost | Approximate token or credit cost. |
| Latency | How long it took. |
| Supervision | How much human correction was needed. |
| Risk behavior | Did it make unsafe assumptions or risky edits? |
| Reuse potential | Should this become a Recipe or routing rule? |

## Model bake-off process

For each important model comparison:

1. choose a repeatable task;
2. define success criteria;
3. run the same task with multiple models;
4. keep context as equal as possible;
5. record cost, latency, output quality, and corrections;
6. choose default routing based on results;
7. update House Blend policy.

## Starter benchmark tasks

| Benchmark | Purpose |
| --- | --- |
| Explain small repo | Tests comprehension and summarization. |
| Implement small feature with tests | Tests coding and verification. |
| Fix failing test | Tests debugging. |
| Refactor one module | Tests restraint and code quality. |
| Summarize research paper | Tests technical reading. |
| Create embedded checklist | Tests domain-specific caution. |
| Review security-sensitive code | Tests risk awareness. |

## Coffee Ledger

The Coffee Ledger tracks:

- model used;
- task type;
- estimated tokens;
- actual cost when known;
- output quality;
- whether escalation was needed;
- whether cheaper model would have sufficed.

## Routing improvement loop

If a model repeatedly performs well on a task type, promote it in the House Blend. If it repeatedly fails, demote it or restrict it to safer uses.

## Roastery success criteria

The Roastery is working when Coffee can answer:

- Which model is best for this type of task?
- Which model is cheapest while still good enough?
- When should we escalate?
- Which prompts reliably work?
- Which workflows produce mistakes?
- Are we improving over time?
