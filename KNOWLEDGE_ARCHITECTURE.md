# Coffee Knowledge Architecture

Version: v0.1 Phase 0 Draft  
Date: 2026-07-02

## Purpose

The Pantry is Coffee's organized knowledge base. It exists so Barista and specialist agents can retrieve the right context at the right time without dumping everything into every prompt.

## Core idea

Do not treat knowledge as a file pile. Treat it as an engineered system.

Bad pattern:

```text
Upload 50 PDFs, 300 source files, 20 notes, and 15 screenshots. Ask the model to understand everything.
```

Better pattern:

```text
Index sources, summarize them, label reliability, extract reusable concepts, connect them to projects, and retrieve only what the task needs.
```

## Pantry structure

```text
pantry/
|
|-- 00_index.md
|-- 01_glossary.md
|-- 02_source_registry.md
|-- 03_freshness_review.md
|
|-- project_docs/
|-- papers/
|-- datasheets/
|-- protocols/
|-- APIs/
|-- notes/
|-- standards/
|-- datasets/
|-- meeting_notes/
|-- lab_notes/
|-- hardware/
|-- medical_research/
|-- ai_ml/
|-- embedded/
```

## Source quality levels

| Level | Name | Meaning |
| --- | --- | --- |
| Bronze | Raw source | Original document imported but not yet summarized or validated. |
| Silver | Processed note | Summarized with key facts, source, date, and relevance. |
| Gold | Trusted project knowledge | Validated, frequently reused, and connected to decisions or recipes. |

## Pantry entry metadata

Each significant Pantry entry should include:

- title;
- source path or citation;
- date added;
- original date of source;
- freshness status;
- reliability level;
- applicable projects;
- tags;
- summary;
- key facts;
- caveats;
- related decisions;
- related recipes.

## Retrieval rule

Barista should retrieve by this order:

1. project-specific notes;
2. active context;
3. related decisions;
4. Gold Pantry entries;
5. Silver notes;
6. Bronze raw sources;
7. external search or live sources if needed;
8. model memory last.

## Freshness policy

Knowledge has an age. Coffee should distinguish between:

- timeless principles;
- stable project decisions;
- slowly changing technical references;
- rapidly changing software/API/pricing/vendor facts;
- high-stakes or time-sensitive information.

Time-sensitive facts should be rechecked before use.

## Future RAG plan

Phase 0 uses organized Markdown. Later phases may add:

- local embeddings;
- vector search;
- semantic search over Pantry;
- document chunking;
- metadata database;
- citation-aware retrieval;
- MCP tools for search;
- automatic source freshness checks.

## Pantry anti-patterns

Avoid:

- giant context dumps;
- unlabelled PDFs;
- notes without source dates;
- mixing facts with opinions;
- relying on model memory when a source exists;
- letting old notes override newer project decisions;
- storing secrets or credentials in the Pantry.

## Pantry success criteria

The Pantry is working when Barista can answer:

- What do we know?
- Where did it come from?
- How reliable is it?
- When was it last checked?
- Which projects use it?
- What should be retrieved for this task?
