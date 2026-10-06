# Animated Coffee Counter Scene Design (Stage E)

Status: Decaf plan - no code written
Date: 2026-07-11

## 0. Reading done before this plan

Read in full: `router/EVENT_CONTRACT.md` (v1.2), `docs/design/coffee-counter-chat-ui-design.md`
(Section 5.2 - the `CounterDisplay` interface freeze and status-text
table; Section 6 - "nothing animates on page load"; Section 7 - zustand
shape), `web/src/components/CounterDisplay/{index,types,statusText}.ts(x)`,
`web/src/app/page.tsx` (current `CounterDisplay` call site and
`sessionCostUsd` derivation), `router/config/beans.yaml`, `router/app/sessions.py`,
`web/package.json`. Checked directly, not assumed: no `ui/` app serves
static files the way Next.js's `public/` convention does, and no
settings/preferences persistence mechanism exists in the router today.

## 1. What already exists - do not rebuild

- `CounterDisplayProps = { event: RouterEvent | null; sessionCostUsd: number }`
  is the frozen interface Stage E was always meant to fill in
  (`coffee-counter-chat-ui-design.md` Section 5.2: "Single interface, so
  Stage E ... can replace the implementation without touching any
  caller"). `statusText.ts`'s data-driven event-to-text table already
  covers all 9 states plus idle and is explicitly meant to be **reused**,
  not replaced (your Requirement 5 says exactly this).
- `page.tsx` already derives `sessionCostUsd` from the active message's
  latest `generating.est_cost_usd` (falling back to the completed
  message's `costUsd`) - this is already "the Tips Jar total," just
  currently rendered as plain text.
- `HydrationMarker` already establishes the "nothing animates before
  hydration" pattern (`data-hydrated` attribute gating CSS transitions) -
  the scene's lazy-load-after-first-paint requirement reuses this same
  mechanism, not a new one.

## 2. Real gaps found - surfaced now, not worked around silently

1. **Canonical paths start with `ui/public/...`, but `ui/` is the
   existing Streamlit app**, not the Next.js chat app - there is no
   `ui/public/` static-asset convention anywhere in this repo, and
   Streamlit would not serve files placed there anyway. The Next.js app
   that actually owns `CounterDisplay` is `web/`, which serves anything
   under `web/public/` at the site root (`/assets/...`). I'm treating
   this as a naming mix-up (using "ui" colloquially for "the chat UI")
   rather than a literal instruction to add browser assets to the
   Streamlit app, and proposing **`web/public/assets/...`** as the
   corrected canonical root. Flagged as Question 1 - please confirm
   before I create any directory.
2. **The five requested jar assets don't match the four real Bean
   aliases.** `router/config/beans.yaml` has exactly four aliases today:
   `House Blend`, `Second Pour`, `Guest Bean`, `Reserve Blend` (the last
   `not_yet_selected`, no model). Your jar list is
   `jar_house_blend`, `jar_dark_roast`, `jar_light_roast`, `jar_decaf`,
   `jar_single_origin` - only the first matches a real alias. A jar
   labeled "Dark Roast" lighting up for a request actually routed to
   `Second Pour` would misrepresent which Bean handled the request,
   which is the same class of problem the "never represent unverified
   output as certain fact" principle (Coffee Constitution Article 1.4)
   already governs for raw-model-ID leakage - this scene must not
   introduce a new way to lie about routing. Flagged as Question 2, with
   a recommended fix below.
3. **The Tips Jar will show `$0.0000` for every real request today.**
   Every active Bean is free-tier; this was already flagged as a known
   gap in the Brew 37 plan ("Tips Jar becomes meaningful once a priced
   Bean exists") and is unchanged. The coin-drop animation will be
   structurally correct and will fire on every `generating` tick, but
   every coin "value" is zero until a priced Bean exists. Shipping as
   real, not faked with placeholder numbers.
4. **No router mechanism exists to persist a UI preference** ("router
   session settings" as you called it isn't a real thing yet - the
   closest existing storage is `SessionStore`, which is scoped to one
   chat session's messages, not a device-wide UI preference like "scene
   collapsed"). This needs a small new addition, described in Section 6.
5. **`.riv` is a compiled binary format authored in the Rive graphical
   editor** - I have no tool access to produce one. Every other asset in
   your canonical list is plain SVG/CSS, which I can hand-author directly
   as real placeholder files at the real canonical paths. So Phase 1
   ships every placeholder asset except `barista_scene.riv` for real (not
   as a separate "temporary sprite system bolted on the side" - the
   *same* fallback code path that Requirement 5 already asks for is what
   renders these SVGs), and `barista_scene.riv`'s absence is exactly what
   keeps the scene on the fallback path until you drop a real file in.
   See Section 4.

## 3. Architecture: one runtime fallback ladder, not two systems

Requirement 5 already specifies a fallback for reduced-motion and for
Rive load failure, both landing on `barista_static.svg` + the reused text
caption. I'm proposing that this *same* mechanism is also Phase 1's
"temporary art" - not a second, throwaway implementation:

```
CounterDisplay (frozen public props, unchanged import path)
  -> SceneShell (collapse state, fade-zone gradient, layout)
       -> StatusCaption (statusText.ts, reused verbatim - always rendered,
                          per Requirement 5; also the collapsed-strip caption)
       -> BaristaScene (state machine wiring, art tier selection)
            tier 1: RiveComponent (@rive-app/react-canvas), only rendered
                    once `barista_scene.riv` reports a successful onLoad
                    AND prefers-reduced-motion is false
            tier 2: <img src="/assets/counter/barista_static.svg">, used
                    whenever tier 1 hasn't loaded (missing file, load
                    error, or reduced-motion) - real hand-authored SVG,
                    not a stub
       -> TipsJar (coin-drop ticks, dollar total)
```

`BaristaScene` always attempts to mount the Rive component (lazily,
after first paint - Section 7), so **Phase 2 requires zero code
changes**: the moment a real `barista_scene.riv` exists at the canonical
path, `onLoad` fires, tier 1 takes over, and tier 2 stops rendering. This
is the literal mechanism your prompt asked for ("no code changes needed"),
not a manual flag I'd have to remember to flip.

The individual jar/tips-jar/cup SVGs referenced *inside* `barista_static.svg`
follow the same rule: `barista_static.svg` is one hand-authored composite
scene for Phase 1 (a simple, flat, labeled illustration - counter, four
jars matching real aliases, a machine silhouette, a cup), swapped whole
when you drop in real art. The per-asset files you listed
(`jar_house_blend.svg` etc.) are referenced by `barista_scene.riv`'s own
internal artwork once that exists, not composed by React at runtime - so
Phase 1 doesn't need to build a compositing layer for them.

### 3.1 State derivation (pure function, per your hard requirement)

```ts
// web/src/components/CounterDisplay/sceneState.ts
type SceneStateIndex = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

function sceneStateIndexFor(event: RouterEvent | null): SceneStateIndex {
  if (event === null) return 0;
  switch (event.event) {
    case "order_received": return 1;
    case "classifying": return 2;
    case "route_selected": return 3;
    case "generating": return 4;
    case "escalation_pending": return 5;
    case "escalating": return 6;
    case "complete": return 7;
    case "error": return 8;
    case "cancelled": return 8; // same art, different caption - statusText.ts already differs
  }
}
```

Table-driven, mirrors the classifier/`statusText.ts` philosophy already
established. This function only ever looks at its `event` argument - no
history, no memory of prior events, matching "no client-side inference of
pipeline state, ever."

### 3.2 The jar-highlight and machine-pick problem (real, not a nitpick)

`GeneratingEvent` has no `bean_alias` or `complexity` field (only
`route_selected` and `escalating` carry `bean_alias`; only `route_selected`
carries `complexity`). A strictly pure function of *only* the latest
event would go blind on jar-highlight and machine-pick the instant a
`generating` tick arrives - it would have to guess, which is exactly what
"no client-side inference" forbids.

`chatStore`'s `ChatMessage` already solves this the same way `sessionCostUsd`
is solved today: it retains `beanAlias` and `complexity` on the message
object as each event updates it (`reduceEventIntoMessage`, already
shipped). I'm proposing `CounterDisplayProps` gain two more fields, read
by `page.tsx` from the exact same `activeMessage` it already reads
`sessionCostUsd` from - not a new derivation, the same one, extended:

```ts
interface CounterDisplayProps {
  event: RouterEvent | null;
  sessionCostUsd: number;
  beanAlias: string | null;        // NEW - additive
  complexity: Complexity | null;   // NEW - additive
  hasVisibleContent: boolean;      // NEW - additive, see Section 3.4 (fade-zone sync)
}
```

This is still a pure function of server-sent facts - every value traces
back to a real field on a real event, just carried forward by the parent
the same way `sessionCostUsd` already is, instead of re-derived inside
`CounterDisplay`. Nothing is inferred; nothing is guessed. Flagged as
Question 3 since the original design doc called this interface "frozen" -
I'm asking before touching it, not treating "additive" as a license to
skip approval.

Jar booleans derive from `beanAlias` via a static alias→jar-key lookup
table (data, not branching logic), `true` only while `sceneStateIndex` is
3 or 4, matching your spec exactly.

### 3.3 Machine pick

`complexity === "espresso_shot"` → espresso machine artwork;
`complexity === "cold_brew"` → pour-over artwork; `complexity === null`
(no `route_selected` yet, e.g. still on `order_received`/`classifying`) →
no machine shown, matching "state 4 (generating) is the only state that
shows a machine" implicit in your spec.

### 3.4 Fade-zone sync (the 300ms buffer)

`hasVisibleContent` (parent-computed: `activeMessage.content.length > 0`)
lets `BaristaScene` hold its *visual* transition into state 7 (cup placed)
for up to 300ms after a `complete` event arrives, if streamed content
hasn't rendered anything yet - polling `hasVisibleContent` on each
prop update (which already happens on every token append, since
`page.tsx` re-renders on every store change) rather than a fixed sleep,
so it resolves the instant content shows up and never waits the full
300ms unless it has to. This buffer only ever delays a visual transition
by a bounded, tiny amount - it does not change what `sceneStateIndex`
*is* (still a pure function of the event), only when the already-decided
state is allowed to render.

## 4. Assets: Phase 1 real files, Phase 2 drop-in replacement

All paths below assume the Question 1 fix (`web/public/assets/...`).
Directories created now; `assets/counter/README.md` documents every file.

| Path | Phase 1 (this Brew) | Phase 2 |
| --- | --- | --- |
| `assets/counter/barista_scene.riv` | **absent on purpose** - its absence is what keeps the fallback tier active | real Rive file with `CounterFlow` state machine |
| `assets/counter/barista_static.svg` | real hand-authored flat illustration (counter, 4 jars matching real aliases, generic machine silhouette, cup) | replaced with better static art if desired |
| `assets/counter/scene_bg.svg` | real simple background layer (wall/shelf/floor, flat shapes) | replaced |
| `assets/counter/jar_house_blend.svg`, `jar_second_pour.svg`, `jar_guest_bean.svg`, `jar_reserve_blend.svg` | real minimal labeled jar SVGs, **renamed to match real aliases** (see Question 2) | replaced |
| `assets/counter/tips_jar.svg` | real minimal jar-with-coins SVG | replaced |
| `assets/counter/cup_finished.svg` | real minimal cup-with-steam SVG | replaced |
| `assets/icons/steam.svg`, `chevron_collapse.svg` | real minimal icon SVGs | replaced |
| `assets/branding/coffee_logo.svg` | real minimal wordmark/glyph | replaced |

Total Phase 1 SVG footprint: expect well under 10 KB (flat shapes, no
embedded raster). The 300 KB budget check (Section 7) is written against
the full `assets/` tree regardless of phase, so it's exercised for real
from day one, not added later as an afterthought.

## 5. Collapse persistence: new `/v1/preferences` endpoint

No existing router mechanism stores a UI preference. Proposing the
smallest addition that fits the router's existing patterns
(`router/app/sessions.py`'s SQLite style, not a new paradigm):

- `router/app/preferences.py`: `PreferenceStore`, one SQLite table
  (`router/data/preferences.db` - same Spill-Guard-ignored `router/data/`
  directory Brew 37 already created, no new ignore-file entry needed),
  schema `key TEXT PRIMARY KEY, value TEXT`. Device-wide, not
  session-scoped (the router is single-process/single-user, same
  non-goal already accepted since Brew 36).
- `main.py`: `GET /v1/preferences` (returns `{}` or the stored dict),
  `POST /v1/preferences` (body `{"key": str, "value": str}`, upserts one
  key). Generic key/value, not `counter_collapsed`-specific, so any
  future preference reuses it without another schema change.
- Frontend: `chatStore` (or a small new `usePreferencesStore`) loads
  `GET /v1/preferences` once on mount, writes through `POST
  /v1/preferences` on toggle - no `localStorage` anywhere in this
  feature, matching your instruction.

Flagged as Question 4 - this is new server-side persistent state, however
small, and the Constitution's "requires confirmation" bar
(Article 3) covers new persistent writes.

## 6. Collapse behavior

Collapsed strip: `StatusCaption` text + `steam.svg` (only rendered while
`sceneStateIndex === 4`, i.e. actually brewing) + the Tips Jar dollar
figure, per your spec. Collapsing sets a `paused` flag passed into the
Rive hook (`rive?.pause()` / `rive?.play()` around the collapse toggle,
not just a CSS `display: none` on the canvas - Rive keeps ticking the
state machine on an invisible canvas otherwise, which is exactly the
"near-zero CPU" requirement's failure mode) and also skips mounting
`BaristaScene`'s tier-2 SVG entirely while collapsed (cheaper than
hiding it).

## 7. Performance budget enforcement

`web/scripts/checkAssetBudget.mjs`: sums file sizes under
`web/public/assets/counter/` + `web/public/assets/icons/` +
`web/public/assets/branding/`, fails (non-zero exit) if the total exceeds
300 KB. Wired as a `prebuild`/`pretest` npm script so it runs on every
`npm run build` and every `npm test`, not a separate manual step someone
has to remember. The "collapsed scene consumes near-zero CPU" claim is
verified by a documented manual profiling note in the Tasting Note (
Chrome DevTools Performance tab, collapsed vs. expanded, comparing main-
thread activity over a fixed window) - Playwright/Vitest can't measure
real CPU usage, so this is recorded as observed evidence, not asserted by
an automated test.

## 8. Tests

- **State mapping table test**: all 9 `sceneStateIndexFor` outputs
  (including `cancelled` reusing 8), plus the jar-boolean table for all
  four real aliases and the "no bean yet" (`null`) case.
- **Collapse pause behavior**: `rive.pause()`/`rive.play()` called at the
  right times (Rive hook mocked - `@rive-app/react-canvas` needs a real
  canvas/WASM context jsdom can't provide, same reasoning `web/src/lib/api.ts`
  is mocked in `AttachmentChip.test.tsx` rather than hitting a real
  server).
- **Fallback rendering**: `onLoadError` (or the file simply never
  resolving in the mock) renders tier 2 (`barista_static.svg`), not a
  blank/broken canvas.
- **Tips Jar accumulation math**: coin-drop throttling (at most one
  coin per 500ms) against a synthetic rapid sequence of `generating`
  events; final amount persists after `complete` until the next
  `order_received` resets it.
- **Reduced motion**: `prefers-reduced-motion: reduce` forces tier 2 even
  when Rive would otherwise have loaded successfully (mocked media
  query, same pattern as any `matchMedia` test).
- Existing `noRawModelId.test.tsx` gets new fixtures covering the three
  additive props so that suite still proves no raw model ID ever reaches
  the scene layer either.

## 9. Non-goals for this Brew

- No real `.riv` file - I cannot author one; Phase 2 is entirely your
  drop-in step once real art exists.
- No escalation-with-attachments or vision-error scene states beyond
  reusing state 8 (`error`) - `no_vision_bean_available` is just another
  `error_type`, already covered by the existing state-8 art with the
  existing error caption text.
- No per-session (as opposed to device-wide) collapse preference - your
  spec described one persisted preference, not one per chat session.
- No accessibility audit beyond `prefers-reduced-motion` - a full a11y
  pass on the new scene (ARIA roles for the Rive canvas, keyboard focus
  order for the collapse chevron) is real future work, flagged but not
  silently done here.

## 10. Open questions requiring your decision

1. **Canonical asset root**: `web/public/assets/...` (corrected) instead
   of the literal `ui/public/assets/...` in your prompt. *(Recommended -
   `ui/` is the Streamlit app; Next.js won't serve files placed there.)*
2. **Jar asset naming**: rename the three non-matching jars to the real
   remaining aliases - `jar_second_pour.svg`, `jar_guest_bean.svg`,
   `jar_reserve_blend.svg` - dropping `jar_dark_roast`/`jar_light_roast`/
   `jar_decaf`/`jar_single_origin` as asset names, since no Bean has
   those names. *(Recommended - keeps the scene honest about which real
   Bean handled the request, matching Article 1.4.)*
3. **`CounterDisplayProps` extension**: add `beanAlias`, `complexity`,
   `hasVisibleContent` (all additive, all sourced from data `page.tsx`
   already tracks). *(Recommended - the alternative is guessing inside
   `CounterDisplay`, which the brief explicitly forbids.)*
4. **New `/v1/preferences` endpoint + SQLite table** for the collapse
   preference, generic key/value shape for future reuse. *(Recommended -
   smallest correct addition matching existing `SessionStore` patterns.)*
5. **`@rive-app/react-canvas` install**: confirmed to add as directed -
   no alternative proposed, just confirming it's the only new npm
   dependency this Brew needs.

## 11. Files touched (CREATE/MODIFY)

```
web/public/assets/counter/README.md                 CREATE - asset manifest, CounterFlow input names
web/public/assets/counter/barista_static.svg         CREATE - real placeholder art
web/public/assets/counter/scene_bg.svg               CREATE
web/public/assets/counter/jar_house_blend.svg        CREATE
web/public/assets/counter/jar_second_pour.svg        CREATE
web/public/assets/counter/jar_guest_bean.svg         CREATE
web/public/assets/counter/jar_reserve_blend.svg      CREATE
web/public/assets/counter/tips_jar.svg               CREATE
web/public/assets/counter/cup_finished.svg           CREATE
web/public/assets/icons/steam.svg                    CREATE
web/public/assets/icons/chevron_collapse.svg         CREATE
web/public/assets/branding/coffee_logo.svg           CREATE
web/src/components/CounterDisplay/types.ts           MODIFY - additive props
web/src/components/CounterDisplay/index.tsx          MODIFY - SceneShell wiring
web/src/components/CounterDisplay/sceneState.ts       CREATE - pure state/jar/machine mapping
web/src/components/CounterDisplay/BaristaScene.tsx    CREATE - Rive/fallback tier logic
web/src/components/CounterDisplay/TipsJar.tsx         CREATE - coin-drop + dollar total
web/src/components/CounterDisplay/SceneShell.tsx      CREATE - collapse/fade-zone/layout
web/src/components/CounterDisplay/*.test.tsx          CREATE - per Section 8
web/src/lib/preferences.ts                            CREATE - GET/POST /v1/preferences client
web/src/app/page.tsx                                  MODIFY - pass new props to CounterDisplay
web/scripts/checkAssetBudget.mjs                       CREATE - 300 KB build-time check
web/package.json                                       MODIFY - @rive-app/react-canvas, prebuild script
router/app/preferences.py                              CREATE - PreferenceStore (SQLite)
router/app/main.py                                      MODIFY - GET/POST /v1/preferences
router/tests/test_preferences.py                        CREATE
brew-log/, roastery/tasting_notes.md                    per usual close-out
```

## 12. Workflow from here

1. You review this plan and answer Section 10's five questions.
2. On approval: router preferences endpoint first (small, testable in
   isolation), then the frontend state-mapping/component tree against
   real placeholder SVGs, then the asset-budget script, then tests.
3. Live demo: a real request through the real UI, screen-recording note
   of the full state walk (idle → order_received → ... → complete),
   collapse/expand exercised, reduced-motion exercised via DevTools
   emulation.
4. Brew Log, Tasting Note (including the CPU profiling note), summary.
