# Remote Call Approval Design

Status: Brew 33A design only
Date: 2026-07-08

## 1. Purpose

This document defines the future approval-gated workflow for sending local
Project Coffee evidence or context to a remote Bean from Coffee Counter UI.

The design exists so Project Coffee can remain local-first while still having
a clear, reviewable path for future model calls. It does not implement model
calls, network code, API key inputs, provider clients, or a working send button.

## 2. Non-Goals

Brew 33 does not:

- call OpenRouter;
- call any remote model or external API;
- add an API key input;
- add a working send-to-model button;
- add network code;
- edit OpenRouter runner logic;
- create persistent root or approval config files;
- auto-stage, auto-commit, push, or tag;
- send secrets, `.env` files, raw local Roastery outputs, or private regulated
  data anywhere.

## 3. Current Local-Only Status

Coffee Counter currently supports local-only workflows:

- Dashboard;
- Doctor;
- Release Check;
- Ledger Summary;
- Evidence Bundle;
- Fleet Status;
- Ask Coffee local evidence draft;
- Routing / Approval preview;
- Current State Quick View;
- project root and Fleet switching.

Routing decisions can say a request would require approval, but no remote
execution path exists.

## 4. Future Approval-Gated Flow

Future remote calls must follow this exact shape:

1. User asks a question or gives an Order in Ask Coffee.
2. Routing helper decides whether local-only evidence is enough or a remote
   Bean might help.
3. Evidence Bundle retrieves local evidence from allowlisted sources.
4. Context Preview shows exactly what would be sent.
5. Safety Gate checks the context package:
   - no `.env` or `.env.*`;
   - no secrets;
   - no hidden credential directories;
   - no raw local Roastery outputs;
   - no production or private regulated data;
   - no oversized context;
   - no disallowed file paths.
6. If the Safety Gate blocks, the remote call cannot proceed.
7. User explicitly approves the exact context package.
8. User chooses or accepts a provider/model according to routing policy.
9. System records planned call metadata locally before sending.
10. Remote call occurs only after approval and metadata preparation.
11. Result is shown with:
    - provider and model;
    - context summary;
    - cost estimate and actual cost if available;
    - token estimate and actual usage if available;
    - citations or evidence references;
    - warning if evidence was insufficient.
12. Ledger records the remote-call evidence.
13. User manually reviews generated code or docs before applying.
14. Git actions remain manual.

If any step is incomplete, the system must stay local-only.

## 5. Approval States

Future UI and helpers should use explicit states:

| State | Meaning | Remote call allowed? |
| --- | --- | --- |
| `local_only_no_approval_needed` | Local tools can answer. | No remote call needed |
| `approval_needed_not_requested` | Route may need a remote Bean, but no preview is ready. | No |
| `context_preview_ready` | Exact context package is visible for review. | No |
| `blocked_by_safety_gate` | Safety Gate found disallowed context. | No |
| `user_approved` | User approved the exact context package. | Not yet; metadata still required |
| `user_cancelled` | User declined or cancelled approval. | No |
| `sending` | Approved call is in progress. | Already in progress |
| `succeeded` | Remote call returned successfully. | Complete |
| `failed` | Remote call failed. | No automatic retry |
| `ledger_recorded` | Ledger evidence was written. | Complete |
| `ledger_recording_failed` | Result exists but Ledger write failed. | No further send until resolved |
| `retry_allowed` | Human may retry after reviewing failure/cost. | Only with approval |
| `retry_blocked` | Retry is unsafe or would repeat a blocked condition. | No |

State transitions must be visible. Silent transitions are not allowed.

## 6. Context Package Schema

The context package is the exact review object shown before approval. It is not
persisted or sent in Brew 33.

### Markdown Shape

```markdown
# Remote Context Package Preview

- Request text:
- Route decision:
- Active root:
- Brew / Shot:
- Timestamp:
- Provider / model:
- Estimated tokens:
- Max context items:

## Selected Files

| Path | Reason | Safety classification | Freshness |
| --- | --- | --- | --- |

## Evidence Items

| Source | Heading | Snippet | Score | Reason selected |
| --- | --- | --- | --- | --- |

## Excluded Paths

| Path or pattern | Reason |
| --- | --- |

## Safety Checks

| Check | Status | Notes |
| --- | --- | --- |

## User Approval

- Approved by:
- Approval timestamp:
- Approval checkbox text:

## Ledger Plan

- Ledger entry path:
- Estimated cost:
- Fields to record:
```

### JSON-Like Pseudo-Schema

```json
{
  "request_text": "string",
  "route_decision": {
    "request_class": "string",
    "selected_mode": "string",
    "approval_required": true,
    "reason": "string"
  },
  "active_root": "string",
  "selected_files": [
    {
      "path": "string",
      "reason": "string",
      "safety_classification": "string",
      "freshness_signal": "string"
    }
  ],
  "evidence_items": [
    {
      "source_path": "string",
      "heading": "string",
      "snippet": "string",
      "score": 0,
      "reason_selected": "string"
    }
  ],
  "excluded_paths": [
    {
      "path_or_pattern": "string",
      "reason": "string"
    }
  ],
  "safety_checks": [
    {
      "name": "string",
      "status": "pass|warn|block",
      "notes": "string"
    }
  ],
  "estimated_tokens": 0,
  "max_context_items": 0,
  "user_approval": {
    "status": "pending|approved|cancelled",
    "approved_at": "timestamp-or-null",
    "approval_text": "string"
  },
  "timestamp": "timestamp",
  "brew_shot": "string",
  "provider_model": {
    "provider": "string",
    "model": "string",
    "routing_role": "default|fallback|comparison|manual"
  },
  "ledger_plan": {
    "ledger_path": "ledger/cost_log.md",
    "planned_fields": ["string"]
  }
}
```

## 7. Safety And Redaction Policy

### Always Excluded

Future remote context builders must always exclude:

- `.env` and `.env.*`;
- files or folders with key, token, secret, credential, or credentials names;
- `.git`;
- hidden credential directories such as `.ssh`, `.aws`, `.azure`, `.gcp`, and
  local credential stores;
- raw local Roastery model outputs;
- private regulated data unless a separate compliant local workflow exists;
- large binary files;
- local caches;
- virtual environments;
- `node_modules`;
- build and dist artifacts;
- broad repository dumps.

### Suspicious Pattern Labels

The Safety Gate should detect categories without revealing secret values:

- OpenRouter key-like value;
- OpenAI key-like value;
- Google API key-like value;
- GitHub token-like value;
- generic bearer token-like value;
- private key material-like value.

The UI must display labels and locations only, never full secret values.

### Behavior If Found

If a blocked path or suspicious pattern is found:

1. Block the remote call.
2. Show a clear reason.
3. Do not reveal the full suspected secret.
4. Require the user to remove or redact manually.
5. Record a safe local blocked-event note only if it does not include secret
   content.
6. Do not offer one-click override for secrets.

## 8. Model And Provider Selection Policy

Default behavior remains Decaf or local-only.

Future model selection rules:

- Remote Bean use requires explicit approval.
- Provider and model must be visible before send.
- Provider and model must be logged after send.
- No silent fallback to a premium or expensive model.
- No silent provider switching after approval.
- Docs Q&A may use a cheap/fast approved model.
- Code planning may use a stronger model after context approval.
- Risky code changes require stronger review and explicit approval.
- Benchmark requests use Roastery workflow first.
- Sensitive or private data stays local-only or blocked.
- Decaf mode means no model.

House Blend defaults can guide the model choice, but changing defaults still
requires Roastery evidence.

## 9. Ledger Requirements

Every future approved remote call must record:

- date/time;
- Brew/Shot;
- question or Order;
- route;
- approval ID or approval timestamp;
- provider;
- model;
- estimated tokens;
- actual prompt tokens if available;
- actual completion tokens if available;
- estimated cost;
- actual cost if available;
- Safety Gate result;
- context package summary;
- files included count;
- files excluded count;
- outcome;
- notes;
- confirmation that no secrets were sent.

If token or cost data is unavailable, Ledger must say `unknown`, not invent
values.

## 10. UI Design

Future UI may add these non-local controls only after implementation approval:

- approval checklist;
- context preview panel;
- selected evidence table;
- excluded paths panel;
- redaction warning panel;
- provider/model selection dropdown;
- cost estimate display;
- explicit approval checkbox;
- disabled final button labeled `Send approved context`;
- cancel button;
- Ledger preview;
- post-call result card.

The send button must remain disabled until:

- route requires or allows remote help;
- context preview is ready;
- Safety Gate passes;
- provider/model is selected;
- cost/token estimate is shown or marked unknown;
- user approves the exact context;
- planned Ledger metadata is ready.

Brew 33 does not enable this button.

## 11. Failure And Cancel States

Future implementation must handle:

- user cancels: stay local-only and record nothing unless useful;
- Safety Gate blocks: show reason and do not send;
- missing API key: show setup issue without asking for a key in chat;
- provider unavailable: show provider/model failure and record if safe;
- timeout: stop, show timeout, allow manual retry only after review;
- rate limit: show rate-limit state and record in Ledger/Roastery if relevant;
- model error: show provider/model error without hiding it;
- Ledger write fails: show warning and require manual evidence capture before
  another send;
- malformed response: show raw safe metadata and require review;
- context too large: ask user to reduce selected evidence;
- stale evidence: warn and recommend refreshing local evidence first;
- active root changed mid-flow: invalidate approval and rebuild preview.

Retries require a new review if context, model, provider, active root, or cost
estimate changes.

## 12. Testing Strategy

Future implementation should test:

- approval state names;
- context package required fields;
- blocked path examples;
- suspicious-pattern labels without secret values;
- route requiring approval;
- disabled remote-call state;
- no API key required for local tests;
- no network call function added to local-only paths;
- no `shell=True`;
- active-root change invalidates approval;
- Ledger plan is present before send;
- failed Safety Gate blocks send.

Tests should not call OpenRouter, external APIs, or remote models.

## 13. Implementation Roadmap

Recommended future sequence:

1. Brew 33B: dogfood this design against realistic remote-call scenarios.
2. Brew 33C: close Remote Call Approval Design if complete.
3. Future Brew: add non-executing UI preview helpers and tests only.
4. Future Brew: add local Safety Gate implementation with no network calls.
5. Future Brew: add Ledger planned-call preview.
6. Future Brew: consider remote call implementation only after explicit human
   approval and fresh Roastery/routing review.

## 14. Open Questions

- Should approval IDs be generated in memory or written only when a remote call
  actually occurs?
- Should planned-call metadata be recorded before send if the user cancels?
- Which provider/model list should be visible if House Blend is provisional?
- How should cost estimates be produced when providers do not return reliable
  price data?
- What is the smallest acceptable redaction/safety scanner before any remote
  implementation?
- Should future approval be per message, per session, or per context package?
