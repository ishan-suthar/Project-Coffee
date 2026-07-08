# Local RAG Guide

## What Local RAG Is

Local RAG is Project Coffee's planned retrieval layer for grounding answers in local project evidence.

It means Project Coffee retrieves a small, safe set of local snippets before answering questions that depend on project facts. The answer can then cite local paths instead of guessing from memory.

In Brew 21, Local RAG is design-only. There is no vector database, no embeddings, no model call, and no chat UI yet.

## Why Project Coffee Needs It

Project Coffee now has many useful surfaces:

- Brew Log;
- Pantry Search;
- Roastery;
- Ledger;
- Dashboard;
- Doctor;
- Unified Coffee CLI;
- Ledger Summary;
- Release Check;
- productized guides and templates.

Without a retrieval layer, a future chat UI could answer from stale memory or miss the best evidence. Local RAG gives future Baristas a disciplined way to find current, cited, local context.

## What It Reads

Default Local RAG sources are planned to include:

- `PROJECT_COFFEE.md`
- `AGENTS.md`
- `brew-log/`
- `docs/`
- `knowledge/`
- `roastery/tasting_notes.md`
- `ledger/cost_log.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- selected app-local Project Coffee files when a specific app or project is in scope.

For app-local retrieval, use only the app's Project Coffee files unless the human explicitly approves a broader project review.

## What It Never Reads By Default

Local RAG must skip:

- `.env` and `.env.*`;
- hidden credential directories;
- API keys, tokens, credentials, SSH keys, OAuth blobs, and private secrets;
- raw local Roastery outputs;
- local generated reports unless explicitly selected for local-only review;
- dependency folders;
- virtual environments;
- build output;
- caches;
- binary files;
- production data;
- private regulated data unless a separate compliant local workflow is designed.

The short version: do not feed the future answer anything secret-looking, generated, binary, or unnecessarily broad.

## Retrieval Levels

### Level 0: No Retrieval / Decaf Answer

Use when a question does not need project facts. The answer should say when it is reasoning from conversation context only.

### Level 1: Keyword Pantry Search

Use the existing Markdown Pantry Search style for quick lookup. This is good for known terms, guide lookup, and simple documentation questions.

### Level 2: Structured Evidence Bundle

Use when the question needs grounded evidence across multiple Project Coffee surfaces. This is the intended Brew 22 implementation target.

### Level 3: Future Embeddings / Vector Search

Optional later work. It should happen only after local safety, storage, rebuild, and approval rules are clear.

## Evidence Bundles

An evidence bundle is a small collection of cited snippets.

Each item should include:

- source path;
- heading;
- snippet;
- reason selected;
- freshness signal;
- safety classification.

The bundle should also say:

- query text;
- query class;
- retrieval level;
- selected root;
- excluded path summary;
- warnings or unknowns.

The point is to make evidence reviewable before any future answer or UI uses it.

## Approval Model For Remote Beans

Local RAG should not call a remote Bean automatically.

If a future workflow wants to send an evidence bundle to OpenRouter or another remote model, it needs human approval first. The human should know what local context will be sent and whether any source is local-only.

For sensitive work, stay Decaf or keep the bundle local.

## How This Supports A Future UI

A future Project Coffee UI should show:

- the user's question;
- retrieval level used;
- evidence bundle;
- cited file paths;
- freshness warnings;
- assumptions;
- whether a remote Bean was used.

The UI should make it easy for the human to inspect evidence before trusting the answer.

## Query Types

Local RAG should support these common question types:

- current status;
- historical decision;
- model benchmark;
- cost/token question;
- onboarding question;
- docs/how-to question;
- cross-project question.

Each type should prefer different sources. For example, cost/token questions should prefer the Ledger, while model benchmark questions should prefer Roastery and House Blend evidence.

## Troubleshooting

If the answer feels stale, check `brew-log/active_context.md`, `brew-log/progress.md`, `ROADMAP.md`, and `CHANGELOG.md`.

If a model claim feels unsupported, check `roastery/tasting_notes.md` and `config/house_blend.md`.

If a cost or token answer is incomplete, check `ledger/cost_log.md` and use Ledger Summary when available.

If retrieval finds nothing, try a smaller query, a known Brew number, a guide name, or a specific project name.

If a source looks sensitive, exclude it and ask the human before proceeding.

## Risks

Main risks:

- stale docs;
- noisy keyword matches;
- overclaiming from a small evidence bundle;
- accidentally including local-only or sensitive context;
- treating generated reports or raw outputs as ordinary docs;
- sending local context to remote Beans without approval.

Project Coffee should treat Local RAG as evidence assembly first and answer generation second.

## Next Step

Brew 22 should implement a local, standard-library evidence bundle builder. It should not add embeddings, vector search, model calls, or a chat UI yet.
