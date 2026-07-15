# Coffee Counter Chat UI

The web client for the Coffee Core Router - a Next.js 16 (App Router,
Turbopack) + TypeScript + Tailwind v4 + zustand chat interface. Built
starting Brew 37; see `docs/design/coffee-counter-chat-ui-design.md` for the
original design and `router/README.md` for the backend it talks to.

Not to be confused with "Coffee Counter" the *editor/IDE layer* referenced
in `ARCHITECTURE.md` (Cursor, VS Code, etc.) - this is a separate, later
addition: a purpose-built browser chat client for the router, not another
IDE integration. See `ARCHITECTURE.md`'s disambiguation note where the term
first appears.

## Run

The router must be running first (see `router/README.md`):

```powershell
python -m uvicorn router.app.main:app --port 8765
```

Then, from this directory:

```powershell
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Use `localhost`, not
`127.0.0.1` - the router's CORS allowlist and Next.js dev-mode
`allowedDevOrigins` both key off the `localhost` origin string (a real
mismatch caught during the Brew 37 live demo).

## Environment variables

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_ROUTER_URL` | Base URL of the running Coffee Core Router. Defaults to `http://127.0.0.1:8765` (`web/src/lib/api.ts:ROUTER_BASE_URL`) if unset. |

No API key or secret is ever read, stored, or sent by this frontend -
`OPENROUTER_API_KEY` lives only in the router's process environment.

## Config that matters

This app has no config files of its own beyond standard Next.js/Tailwind
config (`next.config.ts`, `tsconfig.json`, `postcss.config.mjs`). The
config that actually shapes behavior lives on the router side:
`router/config/*.yaml` (Beans, routing policy, settings) - see
`router/README.md`'s Config section.

## Event contract

Every SSE event this app consumes is documented in `router/EVENT_CONTRACT.md`
(currently v1.4) - `web/src/lib/events.ts` mirrors it field-for-field and is
kept in sync manually (no codegen step). If a component reads a field that
isn't in that contract, that's a bug in this app, not the router.

## Structure

- `src/components/CounterDisplay/` - the animated Coffee Counter scene
  (frozen `{event, sessionCostUsd, ...}` interface; see
  `docs/design/counter-scene-design.md`).
- `src/components/Sidebar/` - session list, per-session `⋮` menu ("Close
  out this session"), and the Settings gear icon.
- `src/components/OrderBox/` - the prompt input, attachments, Bean
  override, and Use Pantry toggle.
- `src/components/ResponseSection/` - message rendering, attachments,
  Pantry citation chips + file viewer, the escalation approval card.
- `src/components/MemoryProposal/` - the session close-out diff review
  panel.
- `src/components/Settings/` - the routing-policy rebuild diff review
  panel (`SettingsPanel.tsx`) and the shared `DiffView.tsx` unified-diff
  renderer it shares with `MemoryProposalPanel.tsx`.
- `src/store/chatStore.ts` - zustand store; all router calls go through
  `src/lib/api.ts`.

## Tests

```powershell
npm run test        # Vitest + React Testing Library, component-level
npm run test:e2e     # Playwright smoke test - mocks the router via page.route(), no live network call, no OPENROUTER_API_KEY needed
npx tsc --noEmit
npx eslint .
npm run build
```

If `npx vitest run` reports a worker crash with no failing assertions
(an environment resource-contention issue, not a real test failure seen
during Brew 42), re-run with `npx vitest run --no-file-parallelism`.

## Performance scripts

- `node scripts/checkAssetBudget.mjs` - fails if the animated scene's
  `public/assets/` total exceeds 300 KB. Runs automatically on
  `prebuild`/`pretest`.
- `node scripts/reportBundleSize.mjs` - one-shot report (no threshold) of
  the always-shipped baseline JS and the full `.next/static/chunks/`
  directory. Run after `npx next build`. Added in Brew 42, since this
  Next.js version's Turbopack build no longer prints a per-route First
  Load JS table.
