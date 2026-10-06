# Pantry Search Guide

Status: v0.1 practical guide  
Date: 2026-07-06

## 1. Purpose

Pantry Search gives Project Coffee a small local way to find useful Markdown
knowledge before loading large files into context.

Use the Pantry Intake Guide when adding or restructuring notes so future
searches have clear headings, labels, and keywords.

It is meant to answer questions like:

- Where did we document the House Blend?
- Which guide mentions onboarding?
- What local note talks about Roastery evidence?

## 2. What Pantry Search Is And Is Not

Pantry Search is:

- local;
- standard-library-only;
- Markdown-first;
- keyword-based;
- safe by default around secret-looking paths;
- useful for quick orientation and context gathering.

Pantry Search is not:

- a model;
- an embedding system;
- a vector database;
- a semantic search engine;
- a replacement for human review;
- permission to inspect secrets or private data.

## 3. When To Use It

Use Pantry Search when:

- a shot needs relevant Project Coffee context;
- you remember a topic but not the file;
- you want to search app-local `knowledge/` notes;
- you need a quick list of candidate docs before reading them;
- you want machine-readable search output for another local tool.

Do not use it to search secret folders, private data, production data, or
credential stores.

## 4. CLI Examples

Search the default `knowledge/` root:

```powershell
python tools\pantry_search.py --query "House Blend"
```

Limit results:

```powershell
python tools\pantry_search.py --query "Roastery evidence" --max-results 5
```

Return JSON:

```powershell
python tools\pantry_search.py --query "onboarding" --json
```

Search a different Markdown root:

```powershell
python tools\pantry_search.py --root docs --query "staged secret-pattern check"
```

Search a different extension:

```powershell
python tools\pantry_search.py --root notes --include txt --query "calibration"
```

## 5. Search A Project Pantry

For an onboarded project, point `--root` at that project's local Pantry or
knowledge folder:

```powershell
python tools\pantry_search.py --root apps\coffee-status\knowledge --query "validation"
```

Keep project Pantry notes small, sourced, and safe to store in the repo.
For intake structure, labels, and note templates, see
`docs/guides/pantry-intake-guide.md`.

## 6. Search A Specific Docs Folder

To search Project Coffee guides:

```powershell
python tools\pantry_search.py --root docs\guides --query "template installer"
```

To search Roastery docs:

```powershell
python tools\pantry_search.py --root roastery --query "full-output capture"
```

The tool searches only files matching the selected extension, defaulting to
`.md`.

## 7. How To Interpret Results

Human-readable output includes:

- file path;
- line number;
- heading context;
- score;
- short snippet.

Higher scores usually mean more query hits, heading hits, or exact phrase hits.
Scores are a ranking aid, not proof that a result is correct. Open the source
file and read the surrounding context before acting.

## 8. Safety Rules

Pantry Search skips sensitive-looking names such as:

- `.env`;
- `.git`;
- `.ssh`;
- `.aws`;
- `secret` or `secrets`;
- `credential` or `credentials`;
- `token`;
- `node_modules`;
- `.venv` or `venv`;
- `__pycache__`.

It does not follow symlinks outside the selected root. It also avoids binary
files and prints only short snippets.

If search output points at a file that might contain private data, stop and ask
for human review before opening it.

## 9. Why This Is Not Full RAG Yet

This is deliberately not full retrieval-augmented generation.

It does not:

- chunk documents for model prompts;
- compute embeddings;
- store vectors;
- call a model;
- call external APIs;
- summarize results automatically.

Brew 13 starts with simple local search because it is easier to inspect, test,
and trust.

## 10. Future Path To Local RAG

A future local RAG path may add:

- reusable search result selection;
- Markdown chunking;
- local snippet packs for prompts;
- stable document IDs;
- optional local embeddings;
- better scoring across headings, links, and front matter.

Each step should stay local-first and preserve the Project Coffee safety rules.

## 11. Troubleshooting

| Issue | What to do |
| --- | --- |
| Root does not exist | Check the path and run from the Project Coffee repo root. |
| No results found | Try fewer terms or search a broader root. |
| Too many results | Add more query terms or lower `--max-results`. |
| Expected file is skipped | Check whether the path name looks sensitive or uses a different extension. |
| JSON output is needed | Add `--json` and parse the `results` list. |
| Search feels too literal | Reword the query; Pantry Search is keyword search, not semantic search. |
| New notes are hard to find | Add clearer headings and `Search Keywords` using the Pantry Intake Guide. |
