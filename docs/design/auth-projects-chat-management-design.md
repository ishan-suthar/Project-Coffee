# Auth, Projects, and Chat Management Design (Brew 43)

Status: Decaf plan - no code written
Date: 2026-07-15

## 0. Reading done before this plan

Read in full: `router/app/sessions.py`, `router/app/main.py` (all 19
endpoints, `RouterState`, `CORSMiddleware` config, `OrderRequest`), the full
current `web/src/lib/api.ts`, `web/src/lib/sse.ts`, `web/src/store/chatStore.ts`,
`web/src/components/Sidebar/index.tsx` and `SessionMenu.tsx`,
`web/src/app/layout.tsx` and `page.tsx`, `web/e2e/chat.spec.ts`,
`.gitignore`/`.cursorignore`/`.cursorindexingignore`, and
`tools/coffee_context_package.py`'s `UNSAFE_FILE_SUFFIXES`/`UNSAFE_PATH_MARKERS`.
Confirmed directly (not assumed): `bcrypt` (4.0.1) and `passlib` (1.7.4) are
both already importable in this environment (`pip show bcrypt` - required by
`chromadb`, an unrelated package); `router/data/` is already Spill-Guard-
ignored in all three ignore files; `.db`/`.sqlite` suffixes and `token`/
`tokens` path markers are already in `is_unsafe_path()`'s unsafe sets.

## 1. What already exists - do not rebuild

- `router/app/sessions.py:SessionStore` already has a working SQLite
  connect/schema/CRUD pattern (`_connect()`, `_init_schema()`) - the new
  `users`/`tokens`/`projects` tables extend this file's existing `SCHEMA`
  string and `SessionStore` class, not a new store module.
- `router/data/` is already Spill-Guard-ignored end to end (`.gitignore`,
  `.cursorignore`, `.cursorindexingignore` all already list it, confirmed
  by reading all three) - `sessions.db` gaining `users`/`tokens` tables
  needs **no new ignore-file entry**. `is_unsafe_path()` already treats
  `.db`/`.sqlite` files and any path containing `token`/`tokens` as
  unsafe - the "add Spill Guard patterns" ask (Requirement 1) is already
  covered by existing generic rules, confirmed by reading the source, not
  assumed.
- The `⋮` per-session menu (`SessionMenu.tsx`, Brew 41) already exists and
  is functional (currently one item: "Close out this session") - this is
  a partial correction to the request's "currently does nothing or
  doesn't exist as a functional menu": it exists and works, it just only
  has one item today. Requirement 3 extends it, not builds it from
  scratch.
- `web/src/lib/sse.ts:streamSSE()` already uses `fetch()` + manual
  `ReadableStream` parsing (not native `EventSource`) specifically
  because `EventSource` can't send a body - this is also exactly the
  constraint that makes it easy to attach an `Authorization` header here
  too (`EventSource` also can't set custom headers at all, so if this
  app still used it, bearer-token auth on the streaming endpoint would
  need a workaround; `fetch()` has none).
- `public/assets/branding/coffee_logo.svg` already exists - the login
  page's "coffee logo" requirement needs no new asset.
- CORS is already scoped to the exact frontend origin
  (`http://localhost:3000`, not `*`) - required for any credentialed
  cross-origin request to work at all; already correct for this Brew's
  needs, just needs new methods/headers added (Section 6).

## 2. Real gaps found - surfaced now, not worked around silently

1. **The router (`127.0.0.1:8765`) and frontend (`localhost:3000`) are
   different origins**, confirmed by reading both `ROUTER_BASE_URL` and
   `playwright.config.ts`/CORS config. This directly affects "store the
   token in a cookie (httpOnly if possible, otherwise secure cookie)":
   a cross-origin `HttpOnly` cookie the router sets would need
   `SameSite=None; Secure` to actually be sent on subsequent
   `fetch()` calls from `localhost:3000` to `127.0.0.1:8765`, and
   `Secure` cookies require HTTPS - this whole stack is plain local HTTP
   (matching every prior Brew's "local-only, no TLS" pattern, not a new
   restriction). **`HttpOnly` cross-origin cookies will not work in this
   setup as currently deployed.** The only way to get real `HttpOnly`
   protection would be routing every single router call (including the
   SSE stream) through a Next.js server-side proxy so the browser only
   ever talks to its own origin - a much bigger architecture change than
   "simple and local" implies, and not what was asked. Recommendation
   (Question 1, Section 9): a plain (non-`HttpOnly`) cookie, set via
   client-side JS from the `/v1/login` response body (the router itself
   never sets `Set-Cookie` - it just returns the token like any other API
   response), read back into an explicit `Authorization: Bearer <token>`
   header on every request via a new shared fetch wrapper. This sidesteps
   the cross-origin cookie problem entirely rather than fighting it.
2. **Almost every existing API call in `web/src/lib/api.ts` uses a raw
   `fetch()` call site directly** (`listSessions`, `getSessionMessages`,
   `listBeans`, `getPantryFile`, `getPendingEscalation`), not just the
   shared `postJSON()` helper - confirmed by reading the full file.
   Attaching an `Authorization` header and centralizing 401 handling
   needs a shared wrapper used by **every** call site, not just
   `postJSON()` - a real, if mechanical, refactor across the whole file.
3. **105 existing router test call sites** in `router/tests/test_main.py`
   alone use `httpx.AsyncClient` against the real FastAPI app (counted
   directly via grep, not estimated) - "do not break any existing
   functionality" plus adding a hard auth requirement to 19 existing
   endpoints would otherwise mean touching all 105. Recommendation
   (Section 3.1): the `get_current_user` FastAPI dependency is designed
   to be overridable via `app.dependency_overrides` (the standard FastAPI
   testing pattern) - existing tests get a fixed fake user injected via
   one line in `setUp()`/fixture construction, not 105 individual header
   edits. Only the new auth-specific tests exercise the real
   token-in-header path end to end.
4. **`sessions.project` is a free-form `TEXT` column today, not a
   foreign key** - every real session ever created has the literal
   string `"default"` in it (confirmed: `DEFAULT_PROJECT = "default"` in
   both `main.py` and `chatStore.ts`, and `CreateSessionRequest.project`
   defaults to it) - there has never been a second real project value.
   Requirement 2 asks for a nullable `project_id` **foreign key** growing
   alongside this - the plan adds `project_id INTEGER NULL REFERENCES projects(id)`
   as a new column and leaves the old `project` TEXT column in place,
   unused by any new code path, rather than attempting a destructive
   rename/migration of a column real (if currently uninteresting) data
   lives in. SQLite's `ALTER TABLE ... DROP COLUMN` needs 3.35+ and isn't
   worth the risk here for a column that costs nothing to leave inert.
5. **No user has ever existed, so no historical session/message row can
   have a real `user_id`.** Every session/message row created across
   Brews 36-42's live demos will have `user_id IS NULL` once the column
   is added. Once per-user filtering (`WHERE user_id = ?`) is live, these
   rows become invisible to every real user by construction - they are
   not silently deleted, just inaccessible through the authenticated API
   surface. Flagged as Question 2 (Section 9) rather than silently
   deciding whether to migrate them to the first created user.
6. **`bcrypt` is not a `router/requirements.txt` dependency today** -
   it's only present because an unrelated package (`chromadb`) happens to
   pull it in transitively in this specific environment. Using it without
   adding it to `requirements.txt` would work by accident here and break
   in any clean environment. The plan adds it as a real, deliberate,
   disclosed dependency (Section 6) - not a silent reliance on incidental
   environment state.
7. **No Next.js middleware or route-protection mechanism exists at all**
   (`find src -iname middleware.ts` returned nothing) - `/login` and
   route gating are both entirely new surface, not an extension of
   anything.
8. **`web/e2e/chat.spec.ts`'s Playwright smoke test mocks every router
   route via `page.route()`** and never touches a real router process -
   it will need a mocked `/v1/login` route and a pre-seeded token
   (`page.addInitScript()` or `context.addCookies()`) added, or every
   other mocked call will start failing local middleware/401-redirect
   logic that doesn't exist in the mock today.

## 3. Auth (Requirement 1)

### 3.1 Router: schema, hashing, tokens

`router/app/sessions.py`'s `SCHEMA` gains:

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
```

- New `router/app/auth.py`: `hash_password()`/`verify_password()` (thin
  wrappers over `bcrypt.hashpw`/`bcrypt.checkpw`, real dependency added to
  `requirements.txt` - Gap 6), `create_token()` (`secrets.token_hex(32)`
  -> 64 hex chars, matching the literal "random 64-char hex" ask),
  `SessionStore` gains `create_user()`, `get_user_by_username()`,
  `create_token()`, `get_user_for_token()` (joins `tokens`/`users`,
  filters `expires_at > now` - an expired token simply fails lookup,
  no separate cleanup job needed, matching this repo's consistent
  "no new background infrastructure" discipline).
- A FastAPI dependency `get_current_user(authorization: str | None = Header(default=None))`
  in `auth.py`: missing header -> 401 `{"detail": "Missing Authorization header."}`;
  malformed (`Authorization` not starting with `"Bearer "`) -> 401; token
  not found or expired -> 401 `{"detail": "Invalid or expired session token."}`.
  Applied via `Depends(get_current_user)` on every existing and new
  `/v1/*` endpoint **except** `POST /v1/login` - a mechanical per-endpoint
  addition, not a global middleware, so `/v1/login` can stay genuinely
  unauthenticated without an exemption list to maintain.
- `POST /v1/login` (body: `{"username", "password"}`) - looks up the
  user, verifies the password with `bcrypt.checkpw` (constant-time by
  design), creates a token (`expires_at` = now + 30 days, matching the
  literal default asked for), returns
  `{"token": "...", "user": {"id", "username", "display_name"}}`.
  Wrong username or wrong password both return the same generic 401
  (`"Invalid username or password."`) - never revealing which one was
  wrong (a real, if small, security decision worth stating rather than
  leaving implicit).
- `POST /v1/logout` (new, not explicitly requested but a natural pair to
  "Sign out" in Requirement 1's frontend ask) - deletes the caller's
  current token row. Without this, "Sign out" could only clear the
  client-side cookie, leaving the token valid server-side until its
  30-day expiry - a real gap the frontend requirement implies fixing.

### 3.2 CLI: `router/tools/manage_users.py`

```
python router/tools/manage_users.py add       # prompts for username, display name, password (getpass, never echoed)
python router/tools/manage_users.py remove <username>
python router/tools/manage_users.py list
```

Uses `SessionStore` directly (same DB, same schema) - no separate store
or file. `add` refuses a duplicate username with a clear message rather
than a raw `IntegrityError`. Password input via `getpass.getpass()`
(stdlib, no new dependency), never logged or echoed, matching this
repo's `OPENROUTER_API_KEY`-handling discipline applied to a new kind of
secret.

### 3.3 Router: applying auth + session/user scoping

- Every `SessionStore` method that touches `sessions`/`messages` gains an
  **optional** `user_id: Optional[int] = None` parameter (Gap 3 -
  optional, not required, so existing direct-Python-call test sites and
  fixtures that don't care about auth keep compiling unchanged).
  HTTP-level endpoints always pass the real authenticated user's id;
  direct-call tests may omit it (falls back to today's unscoped
  behavior, matching Gap 5's "pre-auth rows stay reachable only when
  explicitly queried without a user filter").
- `list_sessions`/`session_exists`/`get_messages` add `AND user_id = ?`
  (and `AND project_id = ?` where relevant, Section 4) to their queries
  when a `user_id` is supplied. A session lookup for a `session_id` that
  exists but belongs to a different user returns the same 404 the code
  already returns for a genuinely unknown id - **never** a distinct
  403, so a client can't distinguish "doesn't exist" from "not yours"
  (matches the existing `session_exists()`-then-404 pattern used
  throughout `main.py` today, extended rather than replaced).
- `POST /v1/order`'s existing `session_exists(body.session_id)` 404 check
  becomes `session_exists(body.session_id, user_id=current_user.id)` -
  the one existing endpoint where cross-user session access could
  otherwise leak into someone else's chat history via `session_id`.

## 4. Projects (Requirement 2)

### 4.1 Schema and endpoints

```sql
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

`sessions` gains `project_id INTEGER NULL REFERENCES projects(id)` (Gap 4
- additive, old `project` TEXT column left in place, unused).

- `POST /v1/projects` (body: `{"name"}`) -> `{"id", "name", "created_at", "updated_at"}`.
- `GET /v1/projects` -> all of the current user's projects.
- `PATCH /v1/projects/{id}` (body: `{"name"}`) - rename; 404 if the
  project doesn't exist or belongs to another user (same
  can't-distinguish-existence rule as sessions).
- `DELETE /v1/projects/{id}` - deletes the project row and, in the same
  transaction, sets `project_id = NULL` for every session that
  referenced it (the literal "moves its sessions to default" ask - a
  real `UPDATE ... SET project_id = NULL` in the same connection/`with`
  block as the `DELETE`, so a crash between the two can't leave orphaned
  `project_id` values pointing at a deleted row).
- `GET /v1/sessions` gains an optional `project_id` query param
  (int or the literal string `"all"` for "All chats"); omitted or
  `"default"` means `project_id IS NULL`; a specific id filters to it;
  `"all"` drops the project filter entirely (still scoped to the
  authenticated user). `POST /v1/sessions` gains an optional
  `project_id` field on `CreateSessionRequest` (null/omitted = default).

### 4.2 Frontend

- `Sidebar`'s header `<span>{project}</span>` becomes a dropdown
  (`ProjectSelector.tsx`, new): "All chats", "default", then the user's
  real projects (`GET /v1/projects` on mount, same
  fetch-after-interactive pattern the rest of `Sidebar` already uses). A
  "+ New project" option opens a small inline name field + create button
  (no new overlay/modal pattern needed for something this small).
- `chatStore`'s `project: string` field becomes
  `projectFilter: "all" | "default" | { id: number; name: string }` (an
  explicit discriminated selection, not a bare string, so "All chats"
  and "a project literally named default" can never collide - Question 3,
  Section 9, since a user could name a real project "default" and the
  string-based `DEFAULT_PROJECT` sentinel already in `chatStore.ts` would
  otherwise be ambiguous).
- `startNewSession`/`sendPrompt`'s session-creation path passes the
  currently selected project's id (or omits it for "default"/"all" -
  "all" creating a session defaults it to `project_id: null`, matching
  "New session creates sessions under that project" only when a *real*
  project is selected).
- Rename/delete live in a small per-project `⋮` menu next to each
  project in the dropdown (reusing `SessionMenu.tsx`'s stopPropagation/
  dropdown pattern as a base, not a new interaction paradigm).

## 5. Chat management (Requirement 3)

### 5.1 Router

- `sessions` gains `deleted_at TEXT NULL`. Every existing session query
  (`list_sessions`, `session_exists`, `get_messages` indirectly via
  session ownership) adds `AND deleted_at IS NULL` - soft-deleted
  sessions become invisible everywhere without a data-loss risk.
- `DELETE /v1/sessions/{id}` - sets `deleted_at = now()` (scoped to the
  authenticated user, same 404-not-403 rule).
- `PATCH /v1/sessions/{id}` (body: `{"title"}`) - renames, reusing the
  existing `TITLE_MAX_CHARS` truncation `set_title_if_default` already
  applies, but as an explicit human-requested rename this **does**
  overwrite a non-default title (unlike `set_title_if_default`, which
  deliberately never does) - a real, small behavioral distinction worth
  stating plainly since the two look similar but mean different things.

### 5.2 Frontend

- `SessionMenu.tsx` gains "Rename" and "Delete" items alongside the
  existing "Close out this session".
- Delete: a small confirmation step inline in the dropdown (a second
  "Confirm delete" click state, matching this app's existing preference
  for small inline affordances over new modal overlays where the action
  is reversible-enough or low-risk-enough - soft delete means a router-
  side recovery is still technically possible even though no "undo" UI
  exists yet) rather than a new full-screen confirmation dialog
  component - Question 4, Section 9, since a full `fixed inset-0`
  confirmation dialog (matching `MemoryProposalPanel`/`SettingsPanel`'s
  existing overlay pattern) is the more consistent-with-precedent
  alternative if a firmer confirmation step is wanted for something
  destructive-by-user-perception even though it's soft-delete under the
  hood.
- Rename: clicking "Rename" swaps the session row's title `<span>` for
  an inline `<input>` (autofocused, Enter/blur to save, Escape to
  cancel) - no separate panel needed for a single text field.

## 6. Cross-cutting

### 6.1 Frontend: shared authenticated fetch

New `web/src/lib/authFetch.ts`:
- `getToken()`/`setToken()`/`clearToken()` - reads/writes a plain
  (non-`HttpOnly`) cookie (Gap 1's resolution). `login()` in `api.ts`
  calls `setToken()` after a successful `POST /v1/login`.
- `authFetch(url, options)` - wraps `fetch()`, attaches
  `Authorization: Bearer <token>` when a token exists, and on a 401
  response calls `clearToken()` then redirects to `/login` (via
  `window.location.href`, since this can be called from a zustand store
  action outside any React component's router context).
- Every existing direct `fetch()` call site in `api.ts` (Gap 2) and
  `streamSSE()`'s single `fetch()` call switch to `authFetch()`/an
  injected header.

### 6.2 Frontend: `/login` page and route gating

- New `src/app/login/page.tsx` - username/password fields, "Sign in to
  Coffee Counter" heading, `coffee_logo.svg`, coffee-brown theme (reuses
  existing Tailwind v4 tokens - `cream`/`latte`/`caramel`/`espresso`/
  `crema-amber` - already established, no new design tokens). On submit,
  calls the new `api.login()`, stores the token, redirects to `/`.
- New `src/middleware.ts` - redirects `/` to `/login` when the token
  cookie is absent. This is a **UX convenience, not the real security
  boundary** - stated explicitly since middleware only checks cookie
  *presence*, never validity (that would need a network round-trip per
  navigation); the router's `get_current_user` dependency validating the
  real token on every request is what actually enforces auth. A forged
  or stale cookie passes middleware and then gets a real 401 from the
  router, which `authFetch` turns into the same `/login` redirect.
- `Sidebar` gains the logged-in user's `display_name` and a "Sign out"
  button at the bottom (calls `api.logout()`, clears the token, redirects
  to `/login`).

## 7. Tests

- **Auth**: login success (real bcrypt-hashed user, correct password);
  login failure (wrong password, wrong/unknown username - both generic
  401s, asserted not to leak which); expired token rejected (a token row
  with a past `expires_at` inserted directly, then used); missing/
  malformed `Authorization` header rejected; **user isolation** - two
  real users, each with a session, asserting user A's token can never
  list/read/rename/delete user B's session (404, not empty-list, for
  read attempts on a specific id; simply absent from `list_sessions` for
  the list case).
- **Existing endpoint tests**: `app.dependency_overrides[get_current_user]`
  injected once per test class/fixture (Gap 3) - a single-line change
  per test class, not 105 call-site edits. A small dedicated subset of
  *new* tests exercise the real header-based path end to end instead of
  the override, so the override itself is never the only thing proving
  auth works.
- **Projects**: CRUD; user isolation (user A cannot see/rename/delete
  user B's project); delete moves sessions to `project_id IS NULL`
  rather than deleting them (asserted directly against the DB and via
  `GET /v1/sessions`).
- **Chat management**: soft delete excludes a session from every list/
  read path but the row still physically exists; rename overwrites even
  a non-default title (the `set_title_if_default` distinction, Section
  5.1); delete/rename scoped to the owning user (404 for another user's
  session).
- **Frontend**: `authFetch` attaches the header and redirects on 401;
  `/login` page renders and calls `api.login()`; `middleware.ts` redirect
  behavior; `ProjectSelector` CRUD interactions; `SessionMenu` rename/
  delete flows; `web/e2e/chat.spec.ts` updated with a mocked `/v1/login`
  route and a pre-seeded token (Gap 8) so the existing smoke test still
  reaches the main page.

## 8. Non-goals

- No OAuth, no JWT, no refresh-token rotation - a single opaque bearer
  token per login, exactly as asked.
- No public signup form - `manage_users.py` is the only way to create a
  user, exactly as asked.
- No real `HttpOnly` cookie (Gap 1) - explicitly flagged as a trade-off,
  not silently downgraded.
- No password reset flow, no email, no 2FA - out of scope, not
  mentioned, not needed for a CLI-managed family user list.
- No migration of pre-auth (`user_id IS NULL`) sessions to a real user
  unless Question 2 is answered that way.
- No rate limiting on `/v1/login` - a local single-family deployment;
  flagged here as a known absence, not silently assumed acceptable
  without saying so.

## 9. Open questions requiring your decision

1. **Token storage**: a plain, JS-readable cookie (not `HttpOnly`),
   explicit `Authorization: Bearer` header on every request (Gap 1).
   *Recommend as proposed* - true `HttpOnly` cross-origin cookies don't
   work over local HTTP without a full server-side proxy layer, which
   contradicts "simple and local."
2. **Pre-auth sessions** (`user_id IS NULL` once the column exists,
   Gap 5): leave them permanently inaccessible through the authenticated
   API (recommended - this repo's entire session history to date is
   Brew 36-42 live-demo/dogfood content, not real family chat history
   worth a migration) vs. auto-assign them to the first user created via
   `manage_users.py add`.
3. **"All chats" vs. a project literally named "default"**: the plan
   makes `projectFilter` an explicit discriminated value (`"all"` |
   `"default"` | a real project object) specifically so a user naming a
   real project "default" can never collide with the sentinel. *Confirm
   this is the right call* - the alternative (reserving the literal name
   "default" so it can't be used for a real project) is simpler
   server-side but restricts what a user can name a project for a
   reason they'd find surprising.
4. **Delete confirmation UI**: an inline second-click "Confirm delete"
   state in the `⋮` dropdown (recommended, lower-friction, consistent
   with soft-delete's actual reversibility) vs. a full `fixed inset-0`
   confirmation dialog matching `MemoryProposalPanel`/`SettingsPanel`'s
   existing overlay precedent (more consistent with "big, clearly
   irreversible-feeling action" patterns already in this app, even
   though the delete itself is soft).
5. **Multi-device / concurrent sessions**: should logging in again
   invalidate a user's previous token(s), or can multiple tokens stay
   valid at once (e.g. a phone and a laptop both signed in)?
   *Recommend allowing multiple concurrent valid tokens per user* (no
   invalidation on new login) - simpler, and matches a real family's
   likely usage (one person, several devices) better than forcing
   single-session-at-a-time.

## 10. Files touched (CREATE/MODIFY)

```
router/app/auth.py                    CREATE - hashing, token creation/validation, get_current_user dependency
router/app/sessions.py                MODIFY - users/tokens/projects tables, project_id/deleted_at/user_id columns and scoping on every method
router/app/main.py                    MODIFY - POST /v1/login, POST /v1/logout, project CRUD endpoints, DELETE/PATCH /v1/sessions/{id}, get_current_user on every existing endpoint, CORS methods/headers
router/tools/manage_users.py          CREATE - add/remove/list CLI
router/requirements.txt               MODIFY - add bcrypt (Gap 6)
router/tests/test_auth.py             CREATE
router/tests/test_sessions.py         MODIFY - user_id/project_id/deleted_at coverage
router/tests/test_main.py             MODIFY - dependency_overrides fixture change (Gap 3), new project/session-management endpoint tests

web/src/lib/authFetch.ts              CREATE - token storage, Authorization header, 401 redirect
web/src/lib/api.ts                    MODIFY - login()/logout(), project CRUD calls, session rename/delete calls, every call site -> authFetch
web/src/lib/sse.ts                    MODIFY - Authorization header on the streaming fetch
web/src/middleware.ts                 CREATE - cookie-presence route gating (UX only, not the security boundary)
web/src/app/login/page.tsx            CREATE
web/src/components/Sidebar/
  index.tsx                           MODIFY - ProjectSelector, display name + Sign out
  ProjectSelector.tsx                 CREATE
  SessionMenu.tsx                     MODIFY - Rename/Delete items
web/src/store/chatStore.ts            MODIFY - projectFilter, project CRUD actions, session rename/delete actions, login/logout
web/e2e/chat.spec.ts                  MODIFY - mocked /v1/login + seeded token
```

## 11. Workflow from here

1. You review this plan and answer Section 9's five questions.
2. On approval, implementation order (dependency order, not request
   order): **Auth first** (schema, `auth.py`, CLI, `get_current_user` on
   every endpoint, dependency-override test migration, frontend
   `authFetch`/`/login`/middleware) with its own tests green - everything
   else depends on `user_id` existing and being enforced. **Projects**
   next (depends on auth for `user_id` scoping). **Chat management**
   last (independent of projects, but rename/delete are small enough to
   benefit from the session-scoping groundwork already being in place).
3. Full test suite (`python tools/run_all_tests.py`) and frontend suite
   (`tsc`/`eslint`/`vitest`/`next build`) green after each stage, not
   just at the end.
4. Live demo: create two real users via `manage_users.py`, log in as
   each in turn, create sessions/projects under each, and verify
   directly (not just via UI - a direct API call with the wrong user's
   token) that neither can see the other's data.
5. Brew Log and Tasting Note.
