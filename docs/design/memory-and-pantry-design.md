# Session Memory Proposals and Pantry Retrieval Design (Brew 41)

Status: Decaf plan - no code written
Date: 2026-07-15

## 0. Reading done before this plan

Read in full: `brew-log/` (`active_context.md`, `progress.md`, `decisions.md`,
`lessons_learned.md`, `mistakes.md`, `open_questions.md`), `MEMORY_AND_LEARNING.md`,
`COFFEE_CONSTITUTION.md` (Articles 4-8), `knowledge/00_index.md` and the rest
of `knowledge/`, `AGENTS.md`, `.cursor/rules/project-coffee-spill-guard.mdc`,
`tools/coffee_context_package.py`, `router/app/config.py`, `router/app/ledger.py`,
`router/app/sessions.py`, `router/app/aliases.py`, `router/EVENT_CONTRACT.md`
(v1.3), `web/src/components/{Sidebar,OrderBox}/index.tsx`.

## 1. What already exists - do not rebuild

- `router/app/sessions.py:SessionStore.get_messages(session_id)` already
  returns the full transcript (role, content, bean_alias, task_type,
  complexity, cost, latency, escalated, draft_quality, rating,
  created_at) - exactly what a memory-proposal generator needs, nothing
  to add here.
- `tools/coffee_context_package.py` already has everything a new indexer
  needs for Spill Guard compliance: `is_unsafe_path()`,
  `UNSAFE_PATH_PARTS`/`UNSAFE_FILE_SUFFIXES`/`UNSAFE_PATH_MARKERS`, and
  `redact_or_label_suspicious_text()` (already imported by
  `router/app/config.py` for startup safety checks) - the indexer reuses
  this exact module, not a reimplementation.
- `router/config/settings.yaml` + `router/app/config.py:Settings` already
  establish the additive-settings pattern (comment explaining purpose +
  pointer to the implementing file) - both new features' settings follow
  it exactly.
- `router/app/ledger.py:CSV_HEADER`'s `task_type` column is already a
  free-form string (not an enum) - `task_type=memory` needs **zero**
  schema change, confirmed by reading the dataclass and the real CSV
  header.
- `router/EVENT_CONTRACT.md` is at v1.3 with an established additive-only
  bump convention - `pantry_sources` becomes v1.4 the same way
  `decision_deadline`/`heartbeat` became v1.3.
- Python's bundled `sqlite3` module has FTS5 compiled in (verified
  directly: created an in-memory FTS5 table and queried it, not
  assumed) - no new dependency for the Pantry index.

## 2. Real gaps found - surfaced now, not worked around silently

1. **"memory-bank/" and "activeContext.md"/"progress.md" don't exist under
   those names.** This repo's equivalent is `brew-log/active_context.md`
   and `brew-log/progress.md` (snake_case, under `brew-log/`, not
   `memory-bank/`). I'm treating your request as referring to these two
   real files - say now if you actually meant something else.
2. **`knowledge/` has exactly 4 files today** (`00_index.md`, `README.md`,
   `project_docs/README.md`, `project_docs/project-coffee-foundation-summary.md`)
   - it's a hand-curated *pointer table* to other repo docs (`brew-log/`,
   `ROADMAP.md`, `AGENTS.md`, `config/house_blend.md`, etc.), not a
   content corpus itself. Indexing literally `knowledge/` (as asked) will
   produce a real but very small index - useful chiefly as the retrieval
   *mechanism* proven correct, not as a rich Q&A corpus yet. See Question
   1 (Section 8) - I'm not silently expanding the indexer's root beyond
   what was asked.
3. **No per-session menu exists in the Sidebar today.** Every session is
   currently a single plain button (`onClick={() => selectSession(...)}`)
   - "Close out this session" needs a new UI affordance (a small `⋮`
   menu per session), not an extension of something that already exists.
4. **`router/tools/` doesn't exist yet** - this Brew creates it.
5. **FTS5's `MATCH` operator is not free-text-safe** - a raw prompt like
   `"what's the Ledger's cost_usd column for?"` is not a valid FTS5 query
   string as-is (unescaped punctuation, quotes). Retrieval needs a small
   query-sanitizing step (tokenize, quote each term, join with `OR`) -
   not just piping the prompt straight into `MATCH`.
6. **Constitution Article 6.4 - "Coffee should never invent references to
   papers, code, tests, or decisions" - is the direct governing rule for
   Requirement 7** (citation honesty). I'm treating this as authoritative
   for the "don't fabricate citations" requirement, not inventing a
   separate policy.

## 3. Memory Proposals

### 3.1 Generation flow

New endpoint `POST /v1/sessions/{session_id}/memory_proposal` (a plain
request/response, **not** SSE/streaming - unlike Brew 40's escalation
wait, there is no multi-minute human-decision phase here, only one
model call, so the heavier background-task/heartbeat machinery from
Brew 40 is deliberately not reused here - a bounded single call doesn't
need it):

1. Load the session transcript via `SessionStore.get_messages()`.
   Build a plain-text transcript (`role: content`, most recent messages
   kept if the transcript exceeds a new `memory_proposal_max_transcript_chars`
   setting - truncate from the **start**, keeping the most recent
   context, since a close-out cares about where things ended up).
2. Read the **current on-disk content** of both `brew-log/active_context.md`
   and `brew-log/progress.md` (never a cached/stale copy).
3. Call a cheap Bean (new setting `memory_proposal_bean_alias`, default
   `"House Blend"`, matching the existing `classifier_model_fallback_bean_alias`
   pattern) with a prompt that includes both files' current content, the
   transcript, and asks for the **full new content** of each file in a
   strict delimited format:
   ```
   ### FILE: brew-log/active_context.md
   <complete new file content>
   ### END FILE

   ### FILE: brew-log/progress.md
   <complete new file content>
   ### END FILE
   ```
   Router parses this strictly - if either marker is missing or a
   `### FILE:` path doesn't exactly match one of the two allowed paths,
   the whole proposal is rejected with a clear error (never guess which
   part goes where).
4. Run both guardrail checks (Section 3.3) against each file's proposed
   new content vs. its current on-disk content. A guardrail failure
   rejects the proposal outright - the UI never sees it.
5. Compute a unified diff per file (Python's stdlib `difflib.unified_diff`
   - zero new dependency) and return:
   ```json
   {
     "proposal_id": "...",
     "files": [
       {"path": "brew-log/active_context.md", "diff": "--- ...\n+++ ...\n@@ ...", "new_content": "..."},
       {"path": "brew-log/progress.md", "diff": "...", "new_content": "..."}
     ]
   }
   ```
   Stored server-side in `RouterState.memory_proposals: Dict[str, MemoryProposal]`
   (same in-memory, no-TTL-sweep precedent as `pending_escalation_context`).

**Recommendation on diff rendering**: a unified diff string rendered as a
styled `+`/`-` block, not a full interactive side-by-side view - stdlib,
no new npm dependency, still fully reviewable. Flagged as Question 2 in
case you want a real side-by-side diff instead (would need a small new
client-side diff algorithm or a new dependency).

### 3.2 Approve / discard

- `POST /v1/memory_proposals/{proposal_id}/approve` - **re-runs both
  guardrail checks against the current on-disk content** (defense in
  depth against a race: someone/something edited the file between
  proposal generation and approval), then writes both files, appends
  **one** Ledger row (`task_type="memory"`, `bean_alias` = the Bean that
  generated the proposal, real `tokens_in`/`tokens_out`/`cost_usd`/`latency_ms`
  from the generation call, `escalated=False`, `escalation_approved=None`
  i.e. "n/a" - all using the existing `LedgerRow` schema, no new column),
  and removes the proposal from `memory_proposals`.
- `POST /v1/memory_proposals/{proposal_id}/discard` - removes the
  proposal from state, writes nothing, logs nothing (matches "the Ledger
  records real actions" - a discard isn't one).
- Never writes without this explicit approval call - there is no
  auto-approve path anywhere in this design.

### 3.3 Guardrails (Requirement 3)

Both checks run at generation time (reject before the UI ever sees a
bad proposal) **and** again at approval time (defense against a stale
proposal):

1. **Path allowlist**: the *only* two writable paths are the literal
   strings `brew-log/active_context.md` and `brew-log/progress.md`,
   resolved and checked to be exactly those two real files under the
   repo root (`Path(path).resolve() == (ROUTER_ROOT.parent / path).resolve()`)
   - not "anything under `brew-log/`" or "anything under `memory-bank/`"
   as a prefix rule, matching your literal "may only touch those two
   files."
2. **Over-deletion protection**: using `difflib`, count original
   non-blank lines vs. lines that survive into the new content (a line
   present in old but absent from new counts as deleted). If
   `deleted_lines / original_lines > 0.5` for either file, refuse the
   whole proposal with a clear reason - this also correctly blocks the
   degenerate "delete everything, write one new line" case, not just
   large diffs in general.

## 4. Pantry Retrieval

### 4.1 Indexer (`router/tools/index_pantry.py`)

CLI script, run manually (`python router/tools/index_pantry.py`) - no
background scheduler, matching the existing `sweep_stale_uploads()`
sweep-on-access precedent rather than new infrastructure.

- Walks `knowledge/` (Question 1, Section 8, on scope).
- For each file: skip via `tools.coffee_context_package.is_unsafe_path()`
  first; skip non-text extensions (reuses `router/app/uploads.py`'s
  `TEXT_EXTENSIONS` allowlist philosophy - `.md`, `.txt`, `.py`, `.yaml`,
  `.yml`, `.json` - plus a decode-attempt fallback, never trying to index
  something that isn't clearly text).
- **Incremental by mtime**: a `files` table (`path`, `mtime`) - a file is
  only re-chunked/re-indexed if its on-disk mtime is newer than the
  stored one; unchanged files are skipped entirely on a re-run.
- **Chunking**: fixed-size character windows (`pantry_chunk_size_chars`,
  default 1200) with a small overlap (`pantry_chunk_overlap_chars`,
  default 200) so a fact near a chunk boundary isn't lost. Each chunk
  stored in an FTS5 virtual table with `path`, `chunk_index`, `text`.
- Index file: `router/data/pantry_index.db` - already covered by the
  existing `router/data/` Spill Guard ignore-file entry (Brew 37), no
  new ignore-file entry needed, confirmed by reading `.gitignore`.

### 4.2 Retrieval (Requirement 5)

`OrderRequest` gains `use_pantry: bool = False`. When true, `_run_order_body`
(right after resolving attachments, independent of classification/routing
since it only needs the raw prompt text):

1. Sanitizes the prompt into a valid FTS5 query (tokenize, quote each
   term, `OR`-join - Section 2, Gap 5).
2. Queries the FTS5 index for the top-k chunks (`pantry_top_k` setting,
   default 5) ranked by BM25 (FTS5's built-in `ORDER BY rank`).
3. Prepends the retrieved chunks to the outbound text (extending the
   existing `_build_outbound_content()` used for attachments, not a
   parallel mechanism) with clear source headers:
   ```
   --- Pantry source: knowledge/00_index.md ---
   <chunk text>
   --- end of knowledge/00_index.md ---
   ```
   placed **before** the user's prompt (read-the-material-first
   structure), followed by an uncertainty-instruction preamble
   (Requirement 7): *"Only use the material above if it actually answers
   the question. If it doesn't cover the question, say so plainly rather
   than guessing, and do not claim a source supports something it
   doesn't."*
4. `CompleteEvent` gains `pantry_sources: List[str] | null` (contract
   v1.4) - the **distinct source paths of the chunks actually injected**
   (i.e. what the router deterministically included, not a model
   self-report of what it "used" - a much simpler and more honest
   contract, since the router can state this as fact rather than trusting
   the model to self-attribute). `null` when `use_pantry` was false or no
   chunks matched - never an empty-but-claimed-list.
5. **Graceful degradation**: if `router/data/pantry_index.db` doesn't
   exist yet (indexer never run), the request proceeds without
   retrieval - `pantry_sources` stays `null`. The client already knows
   locally whether it asked for Pantry, so it can render "no Pantry
   sources found" without a new field for that specifically.

### 4.3 Citation chips and file viewer (Requirement 6)

- `ResponseSection` gains a `PantrySourceChips` component (same visual
  language as `AttachmentGallery`'s read-only chips), rendered only from
  `message.pantrySources` (i.e. only for sources the event stream
  actually confirmed were injected - satisfies Requirement 7's "chips
  render only for sources the router actually injected" directly, since
  there is no other path that could populate this field).
- New endpoint `GET /v1/pantry/file?path=knowledge/00_index.md` - **path
  traversal safe**: resolves the requested path, requires it to be
  `is_relative_to()` the real `knowledge/` root after resolution (blocks
  `..`, absolute paths, and symlink escapes), 404s on anything outside
  or on an unsafe path per `is_unsafe_path()` (defense in depth even
  though `knowledge/` itself shouldn't contain secrets). Returns raw file
  content, read-only - no write path exists on this endpoint at all.
- Clicking a chip opens a read-only panel (new `FileViewerPanel.tsx`,
  same `fixed inset-0` overlay pattern already used by
  `AttachmentGallery`'s image expand and `CommandPalette`) showing the
  fetched content in a `<pre>` block.

## 5. Cross-cutting additions

**Settings** (`router/config/settings.yaml` + `Settings`):
```yaml
memory_proposal_bean_alias: "House Blend"
memory_proposal_max_transcript_chars: 20000
pantry_chunk_size_chars: 1200
pantry_chunk_overlap_chars: 200
pantry_top_k: 5
```

**Event contract v1.4**: additive `pantry_sources: string[] | null` on
`complete`. Changelog entry follows the v1.1-v1.3 pattern exactly.

**Ledger**: no schema change - `task_type="memory"` is a new value of an
already-free-form column.

## 6. Tests (as requested)

- **Diff guardrails**: path escape (a proposal naming any path other than
  the exact two allowed, including `brew-log/../secrets.env` and
  `memory-bank/activeContext.md`-style near-misses) refused; over-50%-
  deletion refused for each file independently; a legitimate small edit
  passes both checks.
- **FTS index incremental update**: index a fixture directory, assert
  chunk count; touch one file's mtime and change its content, re-index,
  assert only that file's chunks changed; assert an unsafe-path fixture
  file (e.g. under a `secrets/` subdirectory) is never indexed.
- **Retrieval relevance smoke test**: index small fixture docs with
  distinctive, unambiguous content; query for that content; assert the
  correct fixture file's chunk ranks first and appears in `pantry_sources`.
- **Path traversal attempts on the file viewer**: `../../router/config/settings.yaml`,
  absolute paths, URL-encoded traversal sequences, a symlink pointing
  outside `knowledge/` - all rejected (404), a legitimate real file
  under `knowledge/` succeeds.
- **Citation chip rendering**: chips render only for `pantrySources`
  actually present on the message; no chips when `use_pantry` was false
  or `pantry_sources` came back null; clicking a chip fetches and
  displays the right file.

## 7. Non-goals for this Brew

- No model self-attribution of which sources it actually drew from -
  `pantry_sources` is "what the router injected," a fact the router can
  state honestly, not "what the model claims to have used."
- No free-text editing of a memory proposal before approval - approve or
  discard the model's proposal as generated; regenerate (a fresh
  `POST .../memory_proposal` call) if it's wrong, rather than a partial-
  edit UI.
- No indexing beyond `knowledge/` itself unless Question 1 says
  otherwise.
- No automatic/scheduled re-indexing - manual `python router/tools/index_pantry.py`
  only, matching this repo's "no new background infrastructure"
  discipline.
- No semantic/embedding-based retrieval - FTS5 BM25 only, as specified.

## 8. Open questions requiring your decision

1. **Indexer scope: literally `knowledge/` only (as asked, ~4 files
   today), or `knowledge/` plus the documents its own `00_index.md`
   Source Table points to** (`brew-log/`, `ROADMAP.md`, `AGENTS.md`,
   `config/house_blend.md`, etc. - much more retrieval value today, but
   expands scope beyond the literal instruction). *Recommend: literally
   `knowledge/` only for this Brew, since that's what was asked and
   keeps the diff smallest; the indexer's root is a one-line constant,
   trivially expanded later once `knowledge/` itself grows or you decide
   to widen it.*
2. **Diff rendering: a unified diff string (stdlib `difflib`, no new
   dependency) vs. a real side-by-side old/new view** (would need a
   small new diff algorithm or library). *Recommend unified diff text.*
3. **Memory proposal generation as a plain blocking request/response**
   (no SSE, no background-task/heartbeat machinery from Brew 40) since
   there's no multi-minute human-wait phase, just one bounded model
   call. *Recommend as described - confirm you're fine with this being
   simpler than the escalation flow, not reusing that machinery.*
4. **Settings defaults as proposed** (20,000-char transcript cap, 1200/200
   char chunking, top-k 5, House Blend as the memory-proposal Bean).
   *Recommend as proposed - all tunable later without a schema change.*
5. **"Close out this session" as a new per-session `⋮` menu** (the first
   per-session action of its kind) vs. some other placement you had in
   mind. *Recommend the `⋮` menu - it's extensible for future per-session
   actions.*

## 9. Files touched (CREATE/MODIFY)

```
router/app/memory_proposals.py    CREATE - guardrails, diff computation, prompt building/parsing
router/app/pantry.py              CREATE - FTS5 query helpers, chunk retrieval, safe file-path resolution
router/tools/__init__.py          CREATE
router/tools/index_pantry.py      CREATE - incremental FTS5 indexer CLI
router/app/main.py                MODIFY - new endpoints (memory_proposal generate/approve/discard,
                                            pantry file viewer), OrderRequest.use_pantry,
                                            _run_order_body retrieval + pantry_sources wiring
router/app/config.py              MODIFY - 5 new settings
router/config/settings.yaml       MODIFY - same
router/app/events.py              MODIFY - CompleteEvent.pantry_sources
router/EVENT_CONTRACT.md          MODIFY - v1.4 changelog + pantry_sources field + new endpoints documented
router/tests/test_memory_proposals.py  CREATE
router/tests/test_pantry.py            CREATE
router/tests/test_index_pantry.py      CREATE
router/tests/test_main.py         MODIFY - endpoint-level tests for all of the above

web/src/lib/events.ts             MODIFY - pantry_sources field
web/src/lib/chat.ts               MODIFY - ChatMessage.pantrySources
web/src/lib/api.ts                MODIFY - memory proposal + pantry file calls
web/src/components/Sidebar/
  index.tsx                       MODIFY - per-session "..." menu, "Close out this session"
  SessionMenu.tsx                 CREATE
web/src/components/MemoryProposal/
  MemoryProposalPanel.tsx         CREATE - diff view, approve/discard
  MemoryProposalPanel.test.tsx    CREATE
web/src/components/OrderBox/index.tsx  MODIFY - "Use Pantry" toggle
web/src/components/ResponseSection/
  PantrySourceChips.tsx           CREATE
  PantrySourceChips.test.tsx      CREATE
  FileViewerPanel.tsx             CREATE
  FileViewerPanel.test.tsx        CREATE
  MessageBubble.tsx                MODIFY - render PantrySourceChips
```

## 10. Workflow from here

1. You review this plan and answer Section 8's five questions.
2. On approval: Pantry indexer + retrieval first (router-side, own tests
   green), then Memory Proposals (router-side, own tests green), then
   frontend for both.
3. Live demo: index the real `knowledge/`, ask a Pantry-toggled question,
   click a citation chip; then close out a real session and
   approve/discard a real memory proposal.
4. Brew Log, Tasting Note, summary.
