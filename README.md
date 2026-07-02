# Project Coffee Phase 0 Foundations

Version: v0.1 Phase 0 Draft  
Date: 2026-07-02

Project Coffee is a personal AI operating system for software engineering, research, embedded systems, hardware, documentation, and long-term learning. Phase 0 establishes the identity, principles, governance, and operating model before implementation begins.

## Why Phase 0 exists

Phase 0 prevents Project Coffee from becoming just another wrapper around today's tools. Cursor, Cline, Continue, OpenRouter, Nemotron, Claude, Codex, and other systems are important, but they are replaceable. The enduring asset is Coffee's memory, knowledge architecture, recipes, evaluation discipline, and human-centered operating philosophy.

## The motto

> Don't chase models. Build systems that outlive them.

## Included documents

| File | Purpose |
| --- | --- |
| VISION.md | Defines what Coffee is, why it exists, and what it must become. |
| COFFEE_PRINCIPLES.md | The core principles that guide all future decisions. |
| COFFEE_VALUES.md | The values that shape Coffee culture and behavior. |
| COFFEE_CONSTITUTION.md | The governing rules for autonomy, safety, learning, and human control. |
| COFFEE_TERMINOLOGY.md | The shared vocabulary for Coffee components. |
| BARISTA_CHARTER.md | Defines Barista as the main orchestrator. |
| BARISTA_OPERATING_MANUAL.md | The default workflow for planning, routing, acting, verifying, documenting, and learning. |
| ARCHITECTURE.md | The tool-agnostic architecture of Project Coffee. |
| KNOWLEDGE_ARCHITECTURE.md | How the Pantry is organized, maintained, searched, and validated. |
| MEMORY_AND_LEARNING.md | How the Brew Log captures decisions, lessons, active context, and improvement loops. |
| GOVERNANCE_AND_SAFETY.md | Privacy, permissions, approvals, secrets, and high-stakes guardrails. |
| EVALUATION_AND_ROASTERY.md | How models, recipes, workflows, and agents are tested. |
| PHASE_0_ROADMAP.md | The actionable Phase 0 build sequence and exit criteria. |
| AGENTS.md | Starter instruction file for Cursor, Cline, Continue, and future agents. |
| DECISIONS/ | Initial architecture decision records. |
| TEMPLATES/ | Reusable templates for projects, recipes, lessons, scorecards, and agents. |

## Suggested first commit

```bash
mkdir Project_Coffee
cd Project_Coffee
git init
# Copy these Phase 0 files into the repository.
git add .
git commit -m "Initialize Project Coffee Phase 0 foundations"
```

## Phase 0 success criteria

Project Coffee is ready to enter Phase 1 when these are true:

- The vision, principles, constitution, Barista charter, and architecture are written.
- The project repository has an initial structure.
- The human operator can explain what Coffee is and what it is not.
- A default governance policy exists for tools, files, secrets, approvals, and model escalation.
- The first Brew Log and Pantry structure exist, even if mostly empty.
- The first evaluation scorecard template exists.
- Cursor/OpenRouter/Cline/Continue decisions can now be implemented without changing Coffee's identity.
