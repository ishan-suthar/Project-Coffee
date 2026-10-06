# Coffee Counter Chat UI Design

Status: Brew 37A draft - Decaf plan, no code written
Date: 2026-07-10

## 0. Reading done before this plan

Read in full: `router/EVENT_CONTRACT.md`, `router/app/main.py`,
`router/app/ledger.py`, `router/app/routing.py`, `router/app/escalation.py`,
`router/app/aliases.py`, `router/config/settings.yaml`,
`docs/design/coffee-core-router-design.md`. Inspected `ui/coffee_counter_app.py`
(1772 lines) in full, plus `ui/README.md`, `docs/design/coffee-counter-ui-design.md`,
and `docs/design/ui-packaging-and-polish-plan.md`. Confirmed Node.js
v24.16.0 and npm 11.13.0 are already installed on this machine.

## 1. What already exists - explicit supersession, not duplication

`ui/coffee_counter_app.py` is a Streamlit control panel with seven tabs:
`Home / Overview`, `Ask Coffee`, `Evidence Bundle`, `Routing / Approval`,
`Ledger`, `Fleet`, `Safety / Commands`. Two of those tabs are directly
relevant here:

- **`Ask Coffee`** answers questions from local evidence only - no model
  call, ever (`docs/design/coffee-counter-ui-design.md`, `ui-packaging-and-polish-plan.md`).
- **`Routing / Approval`** (Brews 29, 33-35) shows routing-mode previews,
  a context package preview, a Safety Gate checklist, and a **dry-run**
  approval flow that explicitly never sends anything. Every one of those
  Brews' closeout notes says the same thing: *"Brew 36 is the earliest
  possible real OpenRouter integration, if that path is chosen."*

Brew 36 chose that path. This plan is what `Ask Coffee` and
`Routing / Approval` were explicitly built to lead into - Brew 30C's own
packaging decision named this exact migration ("React ... remain[s] a
later optional migration path... [once] the important work [of]
workflow stabilization... [is] proven") as the deferred option, not a
rejected one.

**Decision: this new chat UI supersedes the *purpose* of `Ask Coffee` and
`Routing / Approval` (real chat, real routing, real approval) without
touching their code in this Brew.** The other five Streamlit tabs
(`Home / Overview`, `Evidence Bundle`, `Ledger`, `Fleet`, `Safety / Commands`)
are local ops tooling unrelated to chat and are explicitly out of scope -
`ui/coffee_counter_app.py` is not modified by this plan. Once the new UI
is live, a follow-up Brew should add a short banner to those two
Streamlit tabs pointing at it (not in this plan's file list - flagged in
Section 11, Backlog).

This is not silent duplication: it is a named, reasoned supersession of
two specific tabs' purpose, leaving the rest of the Streamlit app alone.

## 2. Two real technical conflicts found during planning

Surfacing these now, per Constitution Article 1.4 ("never represent
unverified output as certain fact") - both change the literal stack
request and need your sign-off before implementation.

### 2.1 Native `EventSource` cannot POST

Native browser `EventSource` only issues GET requests with no body. The
existing `POST /v1/order` needs a JSON body (`{"prompt": ...}`, soon also
`session_id` and `bean_alias_override` - Section 4). GET with the prompt
in a query string would put chat content in URLs, server logs, and
browser history - a Spill Guard-relevant downgrade from the current
design (`docs/design/coffee-core-router-design.md` Section 4 deliberately
keeps prompt text out of the `order_received` event body for the same
reason).

**Resolution:** use `fetch()` with a `ReadableStream` reader to manually
parse the `text/event-stream` response body for `POST /v1/order` and
`POST /v1/retry`. This is the standard workaround for this exact
`EventSource` limitation, uses no additional library (the parsing is
~30 lines of plain `TextDecoder`/`ReadableStream` code, one shared
utility function), and every other endpoint that has no body
(none currently planned) could still use real `EventSource` if one is
added later. If you would rather keep literal `EventSource` and accept
prompt-in-query-string, say so and this plan will change; the default
here is the fetch-stream approach.

### 2.2 `generating.est_cost_usd` is hardcoded to `0.0` today

`router/app/main.py`'s `_consume_stream()` emits `GeneratingEvent(...,
est_cost_usd=0.0)` unconditionally - it was never wired to a real
per-token running cost, because every Bean in `beans.yaml` is currently
free-tier and `0.0` was simply correct. The "Tips Jar" live cost counter
(Section 5.2) will therefore only ever tick from `0.0` today - not a bug
introduced by this plan, but worth knowing before you watch it and expect
movement. It will start reflecting real numbers once a priced Bean
exists and a future Brew wires incremental cost estimation into
`_consume_stream`. Not in this plan's scope to fix.

## 3. Router additions required (Python/FastAPI side)

Everything below lives under `router/`, following Brew 36's established
patterns (pure logic modules + thin FastAPI routes, mocked in tests, no
live network call in any test).

### 3.1 Session storage - SQLite

New module `router/app/sessions.py`. Two tables:

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,        -- uuid4
    project TEXT NOT NULL,      -- grouping key, see below
    title TEXT NOT NULL,        -- first user message, truncated to 80 chars
    created_at TEXT NOT NULL,   -- ISO-8601 UTC
    updated_at TEXT NOT NULL
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,        -- uuid4
    session_id TEXT NOT NULL REFERENCES sessions(id),
    request_id TEXT NOT NULL,   -- ties back to the Ledger row
    role TEXT NOT NULL,         -- "user" | "assistant"
    content TEXT NOT NULL,
    bean_alias TEXT,            -- null for role="user"
    task_type TEXT,
    complexity TEXT,
    cost_usd REAL,
    latency_ms INTEGER,
    escalated INTEGER,          -- 0/1
    draft_quality INTEGER,      -- 0/1
    rating TEXT,                -- null | "good" | "needed_fixing" | "failed"
    created_at TEXT NOT NULL
);
```

`project` is a client-supplied grouping string (default: the basename of
the router's working directory), not a rebuild of Fleet support inside
the router - Fleet's own multi-root logic (`tools/fleet_status.py`) stays
untouched and unrelated. This keeps session grouping simple and avoids
scope creep into re-implementing Brew 24 inside the router.

Database file: `router/data/sessions.db`. **New Spill Guard requirement:**
`router/data/` must be added to `.gitignore`, `.cursorignore`, and
`.cursorindexingignore` (it is user runtime data - chat history - not
source, matching the existing `roastery/local_cup_outputs/` /
`roastery/local_reports/` precedent). This is a required Spill Guard
ignore-file change, called out explicitly per this repo's own hard
lesson from the Brew 36 gate-repair session (`brew-log/mistakes.md`: the
three ignore files must be checked for parity whenever one is edited).

### 3.2 New/changed endpoints

| Endpoint | Method | Change |
| --- | --- | --- |
| `POST /v1/order` | existing | Add optional `session_id: str \| None` and `bean_alias_override: str \| None` fields to `OrderRequest`. When `session_id` is given, persist the user message and the eventual assistant message into `sessions.py` once `complete` fires. When `bean_alias_override` is given, `routing.py`'s selection is skipped entirely; `route_selected.policy_entry` becomes `"manual/<slug>"` instead of a policy path - no event-contract schema change, `policy_entry` was always a free-form string (see Section 2, EVENT_CONTRACT.md's "additive-only" rule is not violated: no field added, removed, or renamed). |
| `POST /v1/retry` | existing | Unchanged. This is Brew 36's caller-reported-failure re-evaluation endpoint, distinct from "re-brew" (see 3.3). Not wired to the rating buttons in this plan - see Section 11, Backlog. |
| `POST /v1/rate` | **new** | Body: `{"request_id": str, "rating": "good" \| "needed_fixing" \| "failed"}`. Writes the rating into both the matching `ledger/router_requests.csv` row (rewriting the file - CSV has no in-place row update, matching the existing `RouterLedger.read_all_rows()` machinery) and the matching `messages` row in SQLite. No other side effect - it does not trigger escalation or retry. |
| `POST /v1/cancel` | **new** | Body: `{"request_id": str}`. Sets a per-request `asyncio.Event` that `run_order()`'s generation loop checks each iteration; on a set event, the loop breaks early and yields a `CancelledEvent(reason="client_cancel_request")` - the first real use of that already-defined-but-unused event type (`router/app/events.py:CancelledEvent`, reserved since Brew 36). Distinct from a client just closing the connection (still handled by the existing `asyncio.CancelledError` path in `sse_stream()`, which cannot emit a final event because nothing is listening) - `/v1/cancel` lets the *server* stop spending tokens even if the client display is what triggered it. |
| `GET /v1/sessions?project=...` | **new** | Returns sessions for a project, newest-updated first: `id`, `title`, `created_at`, `updated_at`, `cost_total_usd` (sum of that session's message costs). |
| `GET /v1/sessions/{id}/messages` | **new** | Full message history for one session, in the same shape the UI needs to re-render a conversation on load. |
| `POST /v1/sessions` | **new** | Creates a session. Body: `{"project": str}`. Returns the new `id`. Called lazily on first message in a fresh chat, not on page load (Requirement: first paint never blocked). |

### 3.3 Re-brew vs. retry - two different things, not one

**Re-brew** (Requirement, Response section) is "regenerate this answer,
optionally with a different Bean" - a fresh generation. It is implemented
as a new `POST /v1/order` call reusing the original prompt text (fetched
from the session's stored `messages` row, never re-typed by the user),
with `bean_alias_override` set if the dropdown selection differs from the
original route. It creates a new `request_id` and a new assistant message
in the session - the old one stays in history, not replaced.

**`/v1/retry`** (Brew 36, existing) is "I'm telling you the *already-shown*
result was bad" - it re-runs the escalation *decision* (not the
generation) for a request that already completed, using the failure info
already stored. This plan does not change its behavior and does not wire
UI to it directly; the rating buttons write to `/v1/rate` only (Section
3.2). Whether "failed" should also trigger `/v1/retry` automatically is
an open question (Section 10, Question 5), deliberately not decided here.

### 3.4 CORS

`router/app/main.py`'s `create_app()` needs `fastapi.middleware.cors.CORSMiddleware`
allowing `http://localhost:3000` (Next.js dev default). Without this, the
browser blocks every `fetch()`/stream call from the new UI to the router
at `http://127.0.0.1:8765`. This is required for the UI to function at
all, not an optional polish item.

### 3.5 Router file list (CREATE/MODIFY)

```
router/app/sessions.py          CREATE - SQLite session/message storage
router/app/main.py              MODIFY - CORS, /v1/rate, /v1/cancel, /v1/sessions*,
                                          OrderRequest.session_id + bean_alias_override,
                                          cancel-flag checking in the generation loop
router/app/ledger.py            MODIFY - add update_rating(request_id, rating) that
                                          rewrites router_requests.csv with the matching
                                          row's rating field set
router/app/routing.py           MODIFY - add a manual-override path (see 3.2) that
                                          bypasses policy selection
.gitignore                      MODIFY - add router/data/
.cursorignore                   MODIFY - add router/data/
.cursorindexingignore           MODIFY - add router/data/
router/tests/test_sessions.py   CREATE
router/tests/test_main.py       MODIFY - new endpoint tests
router/tests/test_ledger.py     MODIFY - update_rating tests
router/tests/test_routing.py    MODIFY - manual-override tests
```

No change to `router/EVENT_CONTRACT.md`'s event shapes - `CancelledEvent`
already exists in the schema and gets used, not redefined.

## 4. Frontend: stack, placement, and the deps that need approval

### 4.1 Placement

New top-level directory `web/` - not inside `ui/` (that name is claimed
by the Python/Streamlit app; mixing a Node project into it would make
`ui/` ambiguous about which runtime owns it). Sibling of `router/`,
`roastery/`, `ui/`. Flagged for your confirmation, same as the router
plan flagged `router/` vs `apps/` (Section 10, Question 1).

### 4.2 Dependencies requiring approval

Node.js (v24.16.0) and npm (11.13.0) are already installed on this
machine - not new. Everything below is new to *this repository* and
requires `npm install`, which Governance treats as a dependency-install
action needing explicit approval before it runs:

| Package | Purpose |
| --- | --- |
| `next`, `react`, `react-dom` | Framework (App Router, as requested) |
| `typescript`, `@types/react`, `@types/node` | TypeScript (as requested) |
| `tailwindcss`, `postcss`, `autoprefixer` | Styling (as requested) |
| `zustand` | State (as requested) |
| `react-markdown`, `remark-gfm` | Markdown rendering (as requested) |
| `shiki` | Code highlighting (as requested) |
| `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` | Component tests - **not explicitly named in your stack list**, needed to fulfill "Component tests for CounterDisplay... and the message header." Recommending Vitest (Next.js's current first-party-documented choice) over Jest; say if you'd rather Jest. |
| `@playwright/test` (+ `npx playwright install` for browser binaries) | Playwright smoke test (as requested) - the browser binary download is a separate, larger one-time fetch beyond the npm package itself, flagged separately since it is not a small install. |

No other UI library is proposed. `date-fns` or similar for "relative
timestamp" formatting was considered and rejected in favor of a ~15-line
hand-written `formatRelativeTime()` utility - one more thing to ask
approval for, for a problem small enough not to need a dependency
(Coffee Principle 9).

`web/node_modules/` needs a `.gitignore` entry (root `.gitignore` already
has a bare `node_modules/` pattern with no path scoping - it already
covers `web/node_modules/` with no change needed; verified by pattern,
not assumed).

## 5. Layout regions

### 5.1 Left sidebar

Sessions grouped by `project` (Section 3.1), each row: title, relative
timestamp (`updated_at`, formatted client-side), session cost total
(`cost_total_usd`, formatted with the same tabular-nums mono treatment as
message cost pills). Collapsible to an icon rail (persisted collapse
state in `localStorage`, not the sessions DB - purely a UI preference).

Fetched via `GET /v1/sessions` **after** interactive (Requirement: first
paint never blocked) - the shell renders with an empty/skeleton sidebar
immediately, then a `useEffect` in a client component fetches and a
zustand store populates it. No server-side fetch in a Server Component
for this data.

### 5.2 Status line (`CounterDisplay`)

Single interface, so Stage E (the animated scene) can replace the
implementation without touching any caller:

```ts
// web/src/components/CounterDisplay/types.ts
interface CounterDisplayProps {
  event: RouterEvent | null;   // latest SSE event for the active stream, or null (idle)
  sessionCostUsd: number;      // "Tips Jar" running total for the active message
}

// The only export other components may import.
declare function CounterDisplay(props: CounterDisplayProps): JSX.Element;
```

Everything else (the status-text mapping table, the Tips Jar tick
animation, eventually the animated scene) lives *inside* this component's
module and is not imported directly by callers - this is what makes the
Stage E swap safe.

Status-text table (data-driven, matching the classifier's own
table-not-ifs philosophy from Brew 36):

| Event | Status text |
| --- | --- |
| `order_received` | "Taking your order" |
| `classifying` | "Thinking it over" |
| `route_selected` | "Reaching for the {bean_alias} jar" |
| `generating` | "Brewing" |
| `escalation_pending` | "Waiting for your approval" |
| `escalating` | "Reaching for the {bean_alias} jar" (re-used, premium alias this time) |
| `complete` | "Order up" |
| `error` | "Order dropped" *(not specified in your request - proposed, say if you want different wording)* |
| `cancelled` | "Order cancelled" *(same - proposed)* |
| idle (`event === null`) | "Ready when you are" *(same - proposed)* |

Tips Jar ticks up on every `generating` event using that event's
`est_cost_usd` (see Section 2.2 caveat), reset to `0` on `order_received`
of a new message.

### 5.3 Response section

One message pair (user + assistant) per turn. Assistant message header:
Bean alias badge (JetBrains Mono, tabular-nums, never a raw model ID -
Requirement, tested explicitly, Section 8), cost pill, latency, and an
escalation marker that expands to show `reason` + `premium_bean_alias`
from the `escalation_pending`/`escalating` events for that turn, when
present. `complete.draft_quality === true` renders a visible "draft, not
escalated" tag (distinct styling from the escalation marker - a
draft-quality tag can appear *without* an escalation marker, e.g. the
no-premium-Bean case from Brew 36 still emits `escalation_pending` once
before falling straight to `draft_quality: true`).

Streaming body: `react-markdown` + `remark-gfm`, syntax highlighting via
`shiki`, re-rendered incrementally as `generating` deltas arrive (the
router does not send raw text deltas today - see Section 9, gap).

Footer: rating buttons (good / needed fixing / failed) -> `POST /v1/rate`;
copy button (`navigator.clipboard`, no library); re-brew button with an
optional Bean-override dropdown (aliases only, populated from
`GET /v1/beans` - see Section 9, another small router gap this surfaces).

### 5.4 Order box

Textarea: Enter sends, Shift+Enter inserts a newline (standard
`onKeyDown` check for `e.key === "Enter" && !e.shiftKey`). Routing hint
line appears once `route_selected` arrives for the in-flight message
("Espresso Shot, House Blend" - `complexity` then `bean_alias`, comma
joined, Title Case complexity). Manual Bean override selector (aliases
only) sets `bean_alias_override` on the next `/v1/order` call and is
itself what "logs as a manual route" means - no separate logging
mechanism, it is the existing `policy_entry: "manual/<slug>"` behavior
from Section 3.2.

## 6. Design tokens (Tailwind config)

```js
// web/tailwind.config.ts (excerpt)
colors: {
  cream:        "#F5EDE3",  // background
  latte:        "#EAD9C4",  // surfaces
  caramel:      "#C99B6F",  // borders/accents
  "medium-roast": "#8B5E3C", // secondary text
  espresso:     "#3E2A1E",  // primary text
  "crema-amber": "#D97E30", // the ONE active-state accent - do not add a second accent color
},
fontFamily: {
  sans: ["var(--font-humanist-sans)", "system-ui", "sans-serif"],
  mono: ["var(--font-jetbrains-mono)", "monospace"],
},
transitionTimingFunction: {
  DEFAULT: "ease-out",
},
transitionDuration: {
  DEFAULT: "150ms",
},
```

"Humanist sans" is a category, not a specific named font - proposing
**Inter** (widely available, free, humanist-leaning, already common in
Next.js starters via `next/font/google` with zero extra npm package
since `next/font` ships with Next.js itself). Say if you have a specific
humanist sans in mind instead. JetBrains Mono likewise via `next/font/google`
- no separate font-loading library needed.

`tabular-nums` applied via Tailwind's `tabular-nums` utility class
(built in, no config needed) on every element rendering aliases, costs,
or latency, per your spec.

Nothing animates on page load: the shell's own mount transition is
disabled (`transition-none` on first paint, or simply no transition
classes applied until `useEffect` confirms mount) - only *interaction*
triggers the 150ms ease-out transitions (hover, tab switch, streaming
text reveal).

## 7. State (zustand)

One store, `web/src/store/chatStore.ts`, roughly:

```ts
interface ChatState {
  activeSessionId: string | null;
  sessions: SessionSummary[];           // sidebar list, hydrated post-interactive
  messages: Record<string, Message[]>;  // keyed by sessionId
  activeStream: {
    requestId: string;
    latestEvent: RouterEvent | null;
    accumulatedText: string;
  } | null;
  // actions: startOrder, appendStreamEvent, cancelActive, rate, rebrew, ...
}
```

No React Context, no separate state library beyond zustand, per your
stack list.

## 8. Raw-model-ID-never-in-UI test

Requirement: "Raw model IDs must never appear anywhere in the UI. Add a
test." Two layers, matching the defense-in-depth pattern the router
already uses (`router/tests/test_events.py` +
`router/tests/test_main.py`'s duplicate no-leak tests):

1. **Component test**: render the message header and `CounterDisplay`
   with a fixture `RouterEvent` list, assert the rendered DOM text never
   contains any string from a fixture raw-model-ID list (mirrors
   `router/tests/test_events.py::test_no_raw_model_id_ever_appears_in_any_event_payload`).
2. **Playwright smoke test**: after the real send-prompt-see-stream
   assertion, additionally assert the full page's rendered text content
   does not contain any of the raw model IDs pulled live from
   `router/config/beans.yaml` at test setup time (not hardcoded, so it
   stays correct if Beans change) - this is the strongest version of the
   check because it runs against real rendered output, not a fixture.

## 9. Small router gaps this UI work surfaces (not silently worked around)

- **No raw text deltas today.** `router/app/events.py`'s `GeneratingEvent`
  only carries `tokens_out` (a count) and `est_cost_usd` - not the actual
  generated text chunk. The router's internal `_consume_stream()` *does*
  accumulate real text (`accumulated_text`), it just never emits it. For
  the Response section to stream markdown live, `GeneratingEvent` needs a
  new optional field, e.g. `text_delta: str | None`. This is an
  **additive** field (per `EVENT_CONTRACT.md`'s own rule: "new optional
  fields... never a rename or removal, without a version bump" - adding
  one is explicitly the allowed case), but it is a real contract change
  and needs your sign-off before implementation, not an assumption.
  Alternative: hold the full text until `complete` and render it all at
  once (no true token-by-token streaming in the UI). Recommending the
  additive field since "streaming markdown" is explicit in your request.
- **No `GET /v1/beans` endpoint.** The Bean-override dropdowns (Order Box
  and re-brew) need the list of available aliases. `router/app/aliases.py`'s
  `BeanRegistry.known_aliases()` already exists; this just needs a thin
  new `GET /v1/beans` route returning `[{alias, role, available}]` -
  small, additive, listed in Section 3.5's file list under `main.py`.

## 10. Open questions requiring your decision before implementation

1. Confirm `web/` as the frontend directory name and placement (Section
   4.1), or propose a different name.
2. Vitest vs Jest for component tests (Section 4.2) - defaulting to
   Vitest unless you say otherwise.
3. `EventSource` vs `fetch()`-stream resolution (Section 2.1) - defaulting
   to `fetch()`-stream to preserve POST-body prompts, unless you'd rather
   keep literal `EventSource` and accept GET/query-string prompts.
4. Add `text_delta` to `GeneratingEvent` for true streaming markdown
   (Section 9), or hold text until `complete`?
5. Should a "failed" rating also trigger `/v1/retry`'s escalation
   re-evaluation automatically, or stay purely a Ledger/session record
   with no side effect (current default, Section 3.3)?
6. Status-text wording for `error`, `cancelled`, and idle states (Section
   5.2) - proposed defaults given, not specified in your request.
7. Humanist sans font choice - proposing Inter via `next/font/google`
   (Section 6) unless you have a specific one in mind.

## 11. Backlog (explicitly not in this plan)

- Adding a "try the new chat UI" banner to the Streamlit `Ask Coffee` and
  `Routing / Approval` tabs once this ships (Section 1).
- Wiring `/v1/retry` to the rating buttons (Question 5).
- Real incremental cost estimation in `_consume_stream()` for non-free
  Beans (Section 2.2) - blocked on the same no-premium-Bean gap
  `docs/design/coffee-core-router-design.md` already documented.
- Fleet-aware `project` grouping in sessions (Section 3.1 keeps it
  simple deliberately).
- The animated scene itself (Stage E) - `CounterDisplay`'s interface
  boundary (Section 5.2) exists specifically so that work does not touch
  anything built in this Brew.

## 12. Non-goals for this Brew

- No animated scene - a plain text status line stands in, per your
  request.
- No multi-user auth - single local user, matching the router's own
  single-process/single-user non-goal from Brew 36.
- No production deployment/hosting config - local dev (`next dev`) only.
- No changes to `ui/coffee_counter_app.py` (Section 1).
- No changes to `roastery/openrouter_client.py` or the Cup Test runner.
- No `pip install` or new Python dependency - all router-side changes use
  only the standard library plus already-installed `fastapi`/`pydantic`/
  `httpx`/`pyyaml` (SQLite is Python's built-in `sqlite3` module).

## 13. Workflow from here

1. You review this plan, the two technical-conflict resolutions (Section
   2), and answer Section 10.
2. On approval: router additions first (Section 3), full router test
   suite green (`python tools\run_all_tests.py`), before any frontend
   code - the frontend has nothing to talk to otherwise.
3. `npm install` only after you separately confirm the dependency list in
   Section 4.2 (Governance: installing dependencies always requires
   explicit approval, distinct from approving this plan as a whole).
4. Frontend implementation in small diffs, not committed automatically.
5. Component tests (Vitest/RTL), then Playwright smoke test, then a live
   demo: real router running, real `/v1/order` call through the actual
   UI, screenshot or terminal capture of the working chat.
6. `brew-log/active_context.md` and `brew-log/progress.md` updated;
   `roastery/tasting_notes.md` gets a Tasting Note for the live demo.
7. Summary: files changed, tests added/passing, risks, rollback path.
