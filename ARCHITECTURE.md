# Project Coffee Architecture

Version: v0.1 Phase 0 Draft  
Date: 2026-07-02

## Architecture goal

Project Coffee must remain tool-agnostic, model-agnostic, and vendor-portable. Cursor is the current primary Coffee Counter, but Coffee should be designed so another editor, agent, or model gateway can replace it later.

## Layered architecture

```text
Project Coffee
|
|-- Layer 0: Human operator
|
|-- Layer 1: Coffee Counter
|   |-- Cursor (current primary)
|   |-- VS Code or another IDE (future-compatible)
|   |-- Terminal or CLI interfaces
|
|-- Layer 2: Agent interfaces
|   |-- Cursor Ask / Plan / Agent
|   |-- Cline sidecar
|   |-- Continue sidecar
|   |-- Future Claude Code / Codex / local agents
|
|-- Layer 3: Coffee Core
|   |-- Barista orchestrator
|   |-- House Blend routing policy
|   |-- model configuration
|   |-- approval policy
|   |-- cost policy
|
|-- Layer 4: Beans
|   |-- Nemotron
|   |-- Qwen
|   |-- DeepSeek
|   |-- Claude
|   |-- GPT
|   |-- Gemini
|   |-- future models
|
|-- Layer 5: Recipes and skills
|   |-- prompts
|   |-- workflows
|   |-- checklists
|   |-- reusable commands
|   |-- specialist Barista instructions
|
|-- Layer 6: Pantry
|   |-- project docs
|   |-- papers
|   |-- datasheets
|   |-- protocols
|   |-- APIs
|   |-- notes
|
|-- Layer 7: Brew Log
|   |-- active context
|   |-- decisions
|   |-- lessons learned
|   |-- progress
|   |-- retrospectives
|
|-- Layer 8: Roastery and Coffee Ledger
|   |-- evaluations
|   |-- model scorecards
|   |-- prompt scorecards
|   |-- cost and token tracking
|
|-- Layer 9: Tools and automation
    |-- Git
    |-- tests
    |-- Docker
    |-- CI
    |-- RAG tools
    |-- MCP tools
```

## Repository structure

```text
Project_Coffee/
|
|-- README.md
|-- VISION.md
|-- COFFEE_PRINCIPLES.md
|-- COFFEE_CONSTITUTION.md
|-- AGENTS.md
|-- ARCHITECTURE.md
|-- ROADMAP.md
|-- CHANGELOG.md
|
|-- .cursor/
|   |-- rules/
|   |-- commands/
|
|-- baristas/
|   |-- barista_orchestrator.md
|   |-- espresso_fast_coder.md
|   |-- cappuccino_research.md
|   |-- mocha_ai_ml.md
|   |-- macchiato_embedded.md
|   |-- latte_docs.md
|   |-- sentinel_review.md
|
|-- recipes/
|   |-- coding/
|   |-- research/
|   |-- embedded/
|   |-- documentation/
|   |-- review/
|
|-- pantry/
|   |-- 00_index.md
|   |-- project_docs/
|   |-- papers/
|   |-- datasheets/
|   |-- protocols/
|   |-- APIs/
|   |-- notes/
|
|-- brew-log/
|   |-- active_context.md
|   |-- progress.md
|   |-- lessons_learned.md
|   |-- decisions.md
|   |-- retrospectives/
|
|-- roastery/
|   |-- model_scorecards/
|   |-- workflow_scorecards/
|   |-- benchmark_tasks/
|   |-- tasting_notes.md
|
|-- ledger/
|   |-- cost_log.md
|   |-- token_log.md
|
|-- templates/
|   |-- project_brief.md
|   |-- recipe_template.md
|   |-- lesson_learned.md
|   |-- barista_profile.md
|   |-- model_scorecard.md
|
|-- decisions/
|   |-- ADR-0001-project-coffee-identity.md
|
|-- scripts/
|-- tools/
|-- evals/
|-- examples/
```

## Current implementation choices

These are implementation choices, not identity commitments:

| Role | Current default | Replacement path |
| --- | --- | --- |
| Coffee Counter | Cursor | VS Code, JetBrains, terminal, future IDE. |
| Model gateway | OpenRouter | Direct provider API, local gateway, enterprise gateway. |
| Daily long-context Bean | Nemotron or comparable model | Any future model with better cost-quality tradeoff. |
| Coding sidecar | Cline / Continue as needed | Cursor Agent, Claude Code, Codex, local coding agent. |
| Memory store | Markdown files first | Database, vector store, local app, or hosted knowledge system later. |
| RAG | Manual Pantry first | Local embeddings/vector search later. |

## Modularity rule

Coffee-specific knowledge should live in Coffee files, not only inside one tool's settings. Tool-specific settings may reference Coffee rules, but Coffee's identity should not be trapped inside Cursor, Cline, Claude, ChatGPT, or any vendor dashboard.

## Phase 0 architecture principle

Start with Markdown and Git. Add complexity only when the simple system proves insufficient.
