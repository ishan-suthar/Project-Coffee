# ADR-0003: Markdown-first memory and knowledge

Date: 2026-07-02
Status: Accepted

## Context

It is tempting to start with databases, vector search, local RAG, dashboards, and complex automation. That risks slowing Phase 0 and hiding knowledge in premature infrastructure.

## Decision

Coffee will start with Markdown files and Git for memory, knowledge, governance, recipes, templates, and evaluations. RAG and databases can be added after usage patterns are clear.

## Consequences

- The system is easy to inspect, version, copy, and edit.
- Agents can read and update files directly.
- Future RAG tools can ingest the Markdown structure.
- Complexity is delayed until justified by real usage.
