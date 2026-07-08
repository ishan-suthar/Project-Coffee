# Local RAG Design

## Purpose

Project Coffee needs a stronger grounding layer before it gets a chat UI or any model-calling retrieval system. The goal is to make future answers cite local project evidence instead of relying on memory, stale context, or model confidence.

This document designs Local RAG for Project Coffee. It does not implement embeddings, vector search, a database, a model call, or a chat UI.

## Definition

Local RAG means retrieval-augmented generation where the retrieval side is local-first, explicit, inspectable, and safe.

For Project Coffee, Local RAG is the process of:

1. receiving a question;
2. classifying what kind of evidence is needed;
3. retrieving safe local Markdown and project evidence;
4. building a small evidence bundle;
5. giving the human or future Barista enough cited context to answer;
6. requiring explicit approval before any local context is sent to a remote Bean.

Local RAG is not the same as "ask a model over the whole repo." It is a controlled context assembly workflow.

## Retrieval Sources

Default retrieval may use these local sources:

- `PROJECT_COFFEE.md`
- `AGENTS.md`
- `brew-log/`
- `docs/`
- `knowledge/`
- `roastery/tasting_notes.md`
- `ledger/cost_log.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- selected app-local Project Coffee files, such as app-local `AGENTS.md`, `PROJECT_COFFEE.md`, `brew-log/`, `knowledge/`, `roastery/`, and `ledger/`

App-local sources should be included only when the question names that app or the retrieval workflow selects that app explicitly.

## Excluded Sources

Local RAG must not read these by default:

- `.env`
- `.env.*`
- hidden credential directories;
- API keys, tokens, credentials, SSH keys, OAuth blobs, local credential stores, or private secrets;
- raw local Roastery outputs under `roastery/local_cup_outputs/`;
- generated local reports under `roastery/local_reports/` unless explicitly selected for local-only review;
- `node_modules/`;
- virtual environments such as `.venv/` and `venv/`;
- build artifacts and caches;
- binary files by default;
- production data;
- private regulated data unless a separate local and compliant workflow is explicitly designed.

The default stance is to skip anything secret-looking, generated, binary, or too broad.

## Retrieval Levels

### Level 0: No Retrieval / Decaf Answer

Use when the user asks for brainstorming, a plan, or a question that does not need project facts.

Output should say when it is reasoning from current conversation only.

### Level 1: Keyword Pantry Search

Use the existing Markdown Pantry Search pattern for simple keyword retrieval.

Good for:

- known terms;
- guide lookup;
- quick status lookups;
- "where is this documented?" questions.

Limits:

- keyword ranking can miss synonyms;
- results may be noisy;
- freshness must still be judged by the answerer.

### Level 2: Structured Local Evidence Bundle

Use a structured bundle when a future answer needs grounded facts across multiple project surfaces.

Good for:

- current status;
- historical decisions;
- model benchmark evidence;
- cost/token questions;
- onboarding questions;
- release readiness questions;
- cross-project summaries.

Level 2 is the intended Brew 22 MVP. It can be implemented without embeddings by combining known file lists, simple keyword search, section extraction, and source scoring.

### Level 3: Future Embeddings / Vector Search

Optional later work.

Good for:

- semantic search;
- synonym-heavy questions;
- larger project Pantries;
- cross-project discovery.

Requirements before Level 3:

- explicit local embedding model or approved remote embedding policy;
- clear storage location;
- rebuild rules;
- secret/path exclusions;
- evidence bundle compatibility;
- Doctor and Release Check coverage.

## Evidence Bundle Format

Each retrieved item should be represented as a small record:

```text
source_path: docs/guides/example.md
heading: Relevant heading
snippet: Short excerpt, not a full document
reason_selected: Query term match, known source priority, recent Brew Log entry, etc.
freshness_signal: Date, Brew number, changelog recency, or unknown
safety_classification: public-project-doc, local-project-note, local-only-evidence, or restricted
```

The bundle should also include:

- query text;
- query class;
- retrieval level used;
- selected root;
- excluded path summary;
- timestamp;
- warnings when evidence is stale, missing, ambiguous, or local-only.

## Grounding Rules

Generated answers should:

- cite local file paths where possible;
- distinguish facts from assumptions;
- prefer Brew Log, Ledger, Roastery, Roadmap, and Changelog evidence over memory;
- use Project Coffee policy files for workflow and safety answers;
- use Roastery notes for model quality claims;
- use Ledger entries for cost/token claims;
- say "unknown" when evidence is unavailable;
- call out stale docs instead of silently trusting them;
- avoid overclaiming from one piece of evidence;
- never include secrets or raw local outputs in an answer.

If the evidence bundle is weak, the answer should say so plainly.

## Query Classes

### Current Status

Primary sources:

- `brew-log/active_context.md`
- `brew-log/progress.md`
- `ROADMAP.md`
- `CHANGELOG.md`

Expected output:

- current milestone;
- next action;
- blockers;
- cited paths.

### Historical Decision

Primary sources:

- `docs/adr/` when present;
- `DECISIONS/`;
- Brew Log;
- Changelog.

Expected output:

- decision;
- date or Brew;
- rationale;
- current status;
- cited paths.

### Model Benchmark

Primary sources:

- `roastery/tasting_notes.md`
- `config/house_blend.md`
- `ledger/cost_log.md`

Expected output:

- Beans compared;
- task type;
- quality scores only if recorded;
- token/cost data only if recorded;
- current confidence level.

### Cost / Token Question

Primary sources:

- `ledger/cost_log.md`
- Ledger Summarizer output when generated locally;
- Roastery notes for benchmark context.

Expected output:

- known totals;
- unknown/unparseable counts;
- model/API vs local-only distinction;
- cited evidence.

### Onboarding Question

Primary sources:

- `docs/guides/new-project-onboarding-guide.md`
- `docs/guides/template-pack-guide.md`
- `docs/guides/template-installer-guide.md`
- app-local Project Coffee docs for the named app.

Expected output:

- safe onboarding steps;
- files to create;
- validation commands;
- approval gates.

### Docs / How-To Question

Primary sources:

- `docs/README.md`
- relevant guide under `docs/guides/`
- `AGENTS.md`
- `PROJECT_COFFEE.md`

Expected output:

- practical answer;
- exact guide references;
- caveats when guide coverage is incomplete.

### Cross-Project Question

Primary sources:

- root Project Coffee docs;
- selected app-local Project Coffee files;
- app-local Brew Logs, Roastery, Ledger, and Pantry indexes.

Expected output:

- per-project evidence;
- source boundaries;
- unknowns;
- no automatic reading of secrets or production data.

## Safety Rules

Local RAG must follow these rules:

- stay local-first;
- never inspect hidden credential directories or secret-looking files;
- do not read raw Roastery local outputs by default;
- do not call models automatically;
- do not send local context to remote Beans without human approval;
- keep evidence bundles small and reviewable;
- prefer snippets over full files;
- mark local-only evidence clearly;
- skip binary files by default;
- preserve One Shot = One Responsibility;
- preserve Human reviews diffs and commits.

## Integration Plan

### Pantry Search

Level 1 retrieval should reuse the existing Pantry Search behavior and safety posture. Brew 22 can add a wrapper that asks Pantry Search for candidate snippets without changing search internals.

### Coffee CLI

The Unified Coffee CLI should eventually expose Local RAG commands, likely:

- `coffee evidence`
- `coffee rag-bundle`
- or `coffee retrieve`

The first command should build evidence bundles only. It should not call models.

### Coffee Doctor

Doctor should eventually diagnose missing Local RAG inputs, stale indexes, unsafe include paths, and tracked generated bundles if any are introduced.

### Dashboard

Dashboard can show Local RAG readiness:

- Pantry index present;
- key evidence files present;
- latest Brew Log date;
- Roastery/Ledger evidence present;
- excluded local-output paths ignored.

### Ledger Summary

Cost/token questions should route through Ledger Summary evidence rather than relying on memory.

### Future Chat UI

A future chat UI should consume an evidence bundle before composing an answer. The UI should show citations, freshness warnings, and whether the answer used Level 0, 1, 2, or 3 retrieval.

Remote Bean usage must be opt-in per request or per approved workflow.

## Brew 22 MVP Acceptance Criteria

Brew 22 should implement only Level 2 structured local evidence bundles unless the human explicitly changes scope.

Acceptance criteria:

- standard-library only;
- no model calls;
- no external APIs;
- no embeddings;
- no vector database;
- CLI can build an evidence bundle for a query;
- bundle includes source path, heading, snippet, reason selected, freshness signal, and safety classification;
- supports at least current status, model benchmark, cost/token, onboarding, and docs/how-to query classes;
- skips excluded paths;
- cites only safe local snippets;
- JSON output is available;
- human-readable output is available;
- tests cover source selection, exclusions, freshness, JSON, and no-results behavior;
- docs explain how a future UI would consume bundles.

## Brew 22A MVP Implementation Note

The first implementation target is `tools/evidence_bundle.py`, a standard-library
CLI that builds local evidence bundles from allowlisted Project Coffee text
sources. It uses keyword ranking only and intentionally does not implement
embeddings, vector search, model calls, external API calls, or a chat UI.

The MVP is allowed to expose JSON and Markdown bundle output so future Coffee UI
work can consume the bundle without changing retrieval safety boundaries.

## Non-Goals

This design does not include:

- chat UI implementation;
- embeddings;
- vector databases;
- remote model calls;
- automatic prompt construction for remote Beans;
- ingestion of secrets or raw outputs;
- indexing binary files;
- replacing human review;
- replacing Brew Log, Roastery, Ledger, Dashboard, Doctor, or Release Check.

## Open Questions

- Should Brew 22 use a fixed query-class classifier or explicit `--class` argument first?
- Should evidence bundles be saved locally, printed only, or both?
- Should app-local Project Coffee folders be opt-in by path or discovered from a registry?
- How should stale evidence be scored: date, Brew number, or explicit freshness labels?
- Should future Level 3 embeddings be local-only, remote-approved, or both?

## Brew 21B Dogfood Review

The design was reviewed against ten realistic Project Coffee questions before implementation.

| Question | Covered by design? | Primary sources | Notes |
| --- | --- | --- | --- |
| What is the current Brew and next Shot? | Yes | `brew-log/active_context.md`, `brew-log/progress.md`, `ROADMAP.md` | Current Status query class covers milestone, next action, blockers, and cited paths. |
| Why did we choose the current default Bean? | Yes | `roastery/tasting_notes.md`, `config/house_blend.md`, `ledger/cost_log.md` | Model Benchmark query class covers quality evidence, confidence level, tokens, and cost when recorded. |
| What did Brew 19 prove? | Yes | Brew Log, `CHANGELOG.md`, `ledger/cost_log.md`, related guide docs | Historical Decision and Cost / Token query classes can reconstruct proof from completion and dogfood evidence. |
| Which files should be checked before release? | Yes | `docs/guides/release-packaging-guide.md`, `tools/release_check.py` documentation, Brew Log | Docs / How-To and release readiness evidence cover this. Brew 22 should prefer the guide over inferred memory. |
| What evidence supports Project Coffee being v0.1-proven? | Partial | Brew Log, Roastery, Ledger, `ROADMAP.md`, `CHANGELOG.md`, release tags | Covered as a cross-project/historical evidence question, but Brew 22 needs a source profile for "release proof" queries. |
| Which docs explain onboarding a new project? | Yes | `docs/guides/new-project-onboarding-guide.md`, `docs/guides/template-pack-guide.md`, `docs/guides/template-installer-guide.md` | Onboarding query class covers guide selection and approval gates. |
| Which local files should never be retrieved? | Yes | Local RAG design/guide, `AGENTS.md`, `PROJECT_COFFEE.md`, ignore files | Excluded Sources and Safety Rules cover secret, generated, binary, raw-output, and credential exclusions. |
| How would future chat UI answer with local evidence? | Yes | Local RAG design/guide | Integration Plan defines a future UI consuming evidence bundles with citations, freshness warnings, assumptions, and remote-use disclosure. |
| What needs user approval before sending context to a remote Bean? | Yes | Local RAG design/guide, `AGENTS.md`, `PROJECT_COFFEE.md` | Safety Rules and approval model require human approval before sending local context remotely. |
| How will stale or conflicting docs be handled? | Partial | Evidence bundle freshness fields, Brew Log, Roadmap, Changelog | Design says to warn on stale, ambiguous, or missing evidence. Brew 22 needs explicit conflict handling and source precedence. |

### Gaps Found

- Brew 22 needs an explicit query-class-to-source profile table so the implementation does not rely on ad hoc source selection.
- Brew 22 needs a conflict handling rule: when Brew Log, Roadmap, Changelog, guide docs, or Roastery/Ledger disagree, the bundle should include competing snippets and mark the conflict.
- Brew 22 needs a stale-evidence rule that prefers dated Brew Log, Ledger, Roastery, Roadmap, and Changelog entries over undated prose when answering status, benchmark, release, or cost questions.
- "v0.1-proven" or release-proof questions need a named query class or subprofile, likely under Historical Decision or Release Evidence.

### Brew 22 Implementation Implications

- Start with explicit `--class` support or a simple deterministic classifier with visible query class output.
- Include source profiles for current status, historical decision, model benchmark, cost/token, onboarding, docs/how-to, cross-project, and release proof.
- Add freshness metadata to each evidence item using date, Brew number, changelog recency, or `unknown`.
- Add a `conflict` or `warning` field at the bundle level when selected sources disagree.
- Keep output local-only, standard-library only, and model-free.
