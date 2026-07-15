# Coffee Counter scene assets

Canonical asset manifest for the animated Coffee Counter scene (Stage E -
see `docs/design/counter-scene-design.md`). Every path below is served by
Next.js directly from `web/public/`, so a browser reaches
`web/public/assets/counter/x.svg` at `/assets/counter/x.svg`.

`BaristaScene` (`web/src/components/CounterDisplay/BaristaScene.tsx`)
always attempts to load `barista_scene.riv` first. As long as that file
is absent (true today - Phase 1) or fails to load, or the browser has
`prefers-reduced-motion: reduce` set, the scene falls back to
`barista_static.svg`. **Dropping a real `barista_scene.riv` at this exact
path is the entire Phase 2 step for the main scene - no code change
required.** The same is true for every other file listed here: replacing
the file in place is the whole job.

## Vertical/portrait layout (Brew 45)

As of Brew 45, the scene lives in a **right-side panel** (roughly 300px
wide, full viewport height), not a full-width strip above the response
section. Every artboard/composite in this directory now assumes a tall
portrait canvas instead of a wide landscape one - `barista_static.svg`
and `scene_bg.svg` both use `viewBox="0 0 260 800"`, and the composed
scene reads top to bottom instead of left to right:

1. **Wall/shelf** (top, roughly `y 0-360`) - the four Bean jars are
   stacked **vertically** on this shelf (one above another), not side
   by side as in the old horizontal layout.
2. **Barista character** - positioned in the **middle** of the panel
   (roughly `y 380-500`), not at the top.
3. **Machine** - just below the barista.
4. **Cup** - appears mid-panel (beside the machine) once `complete`,
   clear of the counter below it.
5. **Counter** - runs along the **bottom** of the panel (roughly
   `y 600-800`). This is the "counter running bottom to top instead of
   left to right" flip: the counter's long/dominant dimension is now
   vertical, not horizontal.
6. **Tips Jar** - sits at the very bottom, below the counter (the real
   interactive `TipsJar` React component already lives here in the
   footer strip of the panel - see `SceneShell.tsx`).

The individual `jar_*.svg`, `tips_jar.svg`, and `cup_finished.svg` files
are each a single self-contained portrait-oriented icon (they were never
landscape - a jar or a cup doesn't have a "wide" and "tall" version).
Nothing about their own artwork needed to change for the vertical
layout; only their **position within the composed scene** changed,
which is what this section documents for whoever composes the real Rive
artboard. `barista_static.svg` (the flat fallback, which *is* a single
composite canvas) and `scene_bg.svg` (the background layer) were both
redrawn to the new portrait arrangement described above.

The collapse chevron (`../icons/chevron_collapse.svg`) is a horizontal
"<" now (was a vertical "v", matching the old horizontal top-strip
layout) - `SceneShell.tsx` rotates it 180° when collapsed, so it reads
as `<` (pointing left, "collapse") while the panel is expanded, and `>`
(pointing right, "expand") once collapsed to the thin right-side strip.

## Files

| File | Purpose | Phase 1 status |
| --- | --- | --- |
| `barista_scene.riv` | Main Rive artboard: Barista + machines + counter, driven by the `CounterFlow` state machine (see below), composed per the vertical layout above. | **Absent on purpose** - its absence is what keeps the fallback tier active. Authoring this requires the Rive graphical editor; no CLI/programmatic path exists to produce one. |
| `barista_static.svg` | Reduced-motion and load-failure fallback illustration - a flat, non-animated composite scene (jars, barista, machine, cup, counter), portrait `viewBox="0 0 260 800"`. Always paired with the reused text status caption (`statusText.ts`), never shown alone. | Real hand-authored placeholder, redrawn portrait in Brew 45. |
| `scene_bg.svg` | Wall/shelf/floor background layer, referenced by the future Rive artboard's own internal artwork, portrait `viewBox="0 0 260 800"`. | Real placeholder (flat rectangles), redrawn portrait in Brew 45. |
| `jar_house_blend.svg` | Labeled jar art for the `House Blend` Bean - topmost on the vertical shelf. | Real placeholder, unchanged (already a portrait single-object icon). |
| `jar_second_pour.svg` | Labeled jar art for the `Second Pour` Bean - second from the top. | Real placeholder, unchanged. |
| `jar_guest_bean.svg` | Labeled jar art for the `Guest Bean` Bean - third from the top. | Real placeholder, unchanged. |
| `jar_reserve_blend.svg` | Labeled jar art for the `Reserve Blend` Bean (the premium Bean - not yet an active model, see `router/config/beans.yaml`) - bottommost on the shelf. | Real placeholder, unchanged. |
| `tips_jar.svg` | The live cost-ticker jar art, sits at the bottom of the panel below the counter. | Real placeholder, unchanged (position-only change, documented above). |
| `cup_finished.svg` | The completed cup that hands off to the response section on `complete`, appears mid-panel beside the machine. | Real placeholder, unchanged (position-only change, documented above). |
| `../icons/steam.svg` | Collapsed-strip brewing indicator (shown only while `generating`). | Real placeholder. |
| `../icons/chevron_collapse.svg` | Collapse/expand toggle icon - horizontal `<`/`>` as of Brew 45 (was vertical). | Real placeholder, redrawn in Brew 45. |
| `../branding/coffee_logo.svg` | Wordmark/glyph, not yet wired into any component. | Real placeholder. |

**Why four jars, not five:** `router/config/beans.yaml` has exactly four
Bean aliases today (`House Blend`, `Second Pour`, `Guest Bean`,
`Reserve Blend`). Earlier drafts of this asset list used roast-style
names (`jar_dark_roast.svg`, `jar_light_roast.svg`, `jar_decaf.svg`,
`jar_single_origin.svg`) that don't correspond to any real Bean - a jar
labeled that way lighting up for a request actually routed to
`Second Pour` would misrepresent which Bean handled the request. Jar
files are named after real aliases instead, so the scene can never show
something that isn't true. If a fifth Bean is ever added to
`beans.yaml`, add a matching `jar_<slug>.svg` here and extend the alias
lookup table in `web/src/components/CounterDisplay/sceneState.ts` - do
not invent art for a Bean that doesn't exist.

## `CounterFlow` state machine (for the Rive artist authoring `barista_scene.riv`)

One number input named exactly `state`, values `0`-`8`:

| Value | Router event | Scene beat |
| --- | --- | --- |
| 0 | (idle - no event yet) | Barista idle, arms at rest |
| 1 | `order_received` | Notepad jot |
| 2 | `classifying` | Chin rub |
| 3 | `route_selected` | Reach toward the matching jar |
| 4 | `generating` | Machine animation - espresso machine for `espresso_shot` complexity, pour-over for `cold_brew` (see the boolean inputs below) |
| 5 | `escalation_pending` | Barista waits, taps foot, looks at the user |
| 6 | `escalating` | Discard cup, grab the premium jar, restart |
| 7 | `complete` | Place cup on counter, steam curl |
| 8 | `error` | Small spill and mop. `cancelled` reuses this same art with a different caption - do not add a 9th state for it. |

Five boolean inputs, exactly one `true` at a time, only meaningful during
states 3-4, `false` otherwise: `jar_house_blend`, `jar_second_pour`,
`jar_guest_bean`, `jar_reserve_blend`, and a spare `jar_default` (shown
if a future Bean alias has no dedicated jar art yet, rather than
highlighting nothing or guessing).

One boolean input `complexity_cold_brew`: `true` selects the pour-over
machine animation during state 4, `false` (including whenever state is
not 4) selects the espresso machine.

These exact names are read by
`web/src/components/CounterDisplay/BaristaScene.tsx` via
`useStateMachineInput(rive, "CounterFlow", "<name>")` - a typo here means
the real Rive file will load but silently never animate correctly.
