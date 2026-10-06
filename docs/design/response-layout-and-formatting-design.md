# Decaf Plan: Response Layout, Markdown Formatting, and Barista Panel Restructure

Status: DRAFT - awaiting approval. No code changes made yet.

## Problem

Three visual problems in the current Coffee Counter Chat UI:

1. Response bubbles are narrow (`max-w-2xl` on both user and assistant
   messages, `web/src/components/ResponseSection/MessageBubble.tsx:30,38`),
   leaving large empty margins. Markdown formatting is poor because
   `MessageBubble.tsx:45` applies Tailwind's `prose prose-sm` classes, but
   **`@tailwindcss/typography` is not installed** (confirmed: absent from
   `web/package.json`, no `@plugin` directive in `web/src/app/globals.css`,
   which only defines `@theme inline` color/font tokens). `prose` is
   therefore a no-op class today - tables, list spacing, heading hierarchy,
   and blockquotes all render with zero styling, which is the real root
   cause of "content formatting is poor."
2. `CounterDisplay` (the barista scene) renders as a full-width horizontal
   strip above the `Sidebar`+`ResponseSection`+`OrderBox` row
   (`web/src/app/page.tsx:31-44`), not beside the response section.
3. General polish: message bubble styling, header/footer subtlety, and
   transitions need tightening per the coffee-brown palette.

## Scope confirmation

Read: `web/src/app/page.tsx`, `web/src/components/ResponseSection/*`,
`web/src/components/CounterDisplay/*` (the "Counter" scene component - no
separate `Counter/` directory exists), `web/src/components/OrderBox/*`,
`web/src/app/globals.css`. No `web/tailwind.config.ts` exists - this is
Tailwind v4, CSS-first config only.

## 1. Response section width and formatting

**Container padding** (`ResponseSection/index.tsx:29`): change
`px-4 py-4` to `px-6 py-4` (24px sides), keep `flex-1 flex-col gap-4
overflow-y-auto`. Width is now naturally 100% of the parent flex column
(the response column inside the new split layout, see Section 2), not a
centered fixed column.

**MessageBubble.tsx**:
- User message: `ml-auto max-w-2xl` -> `ml-auto max-w-[75%]`, background
  stays `bg-latte` (`#EAD9C4`, already the token requested).
- Assistant message: remove `max-w-2xl`, `rounded-lg`, `border
  border-caramel`, and `bg-cream` (no bubble box). Replace with `w-full
  border-l-2 border-crema-amber pl-4 py-3` - full width, no background,
  a left accent border in `crema-amber`.
- Drop the inert `prose prose-sm max-w-none` wrapper; replace with a
  plain `<div className="text-espresso">` and style every Markdown
  element explicitly via `ReactMarkdown`'s `components` prop (below).
  **Decision: do not install `@tailwindcss/typography`.** Its default
  theme doesn't know about the coffee palette and would need per-element
  overrides anyway to hit the brand colors this task asks for (crema
  amber links, latte table headers, etc.) - writing the ~12 element
  overrides directly is the same amount of code as configuring
  typography-plugin overrides, without adding a new dependency. Open
  question 1 below.

**Markdown element overrides** (new `components` entries in
`MessageBubble.tsx`, styled with the existing coffee tokens):
- `table` -> wrapped in `overflow-x-auto`, `w-full border-collapse
  border border-caramel text-sm my-2`
- `thead`/`th` -> `bg-latte font-semibold border border-caramel px-3
  py-2 text-left`
- `td` -> `border border-caramel px-3 py-2`
- `ul`/`ol` -> `list-disc`/`list-decimal pl-6 space-y-1 my-2`
- `h1`-`h6` -> descending size scale (`text-xl font-bold mt-4 mb-2`
  down to `text-sm font-semibold mt-2 mb-1`)
- `p` -> `leading-[1.7] my-2`
- `blockquote` -> `border-l-2 border-caramel pl-3 italic
  text-medium-roast my-2`
- `a` -> `text-crema-amber underline hover:opacity-80`
- `strong`/`em` -> explicit `font-semibold`/`italic` (browser defaults
  already bold/italicize these; making it explicit removes any doubt
  and lets us set `text-espresso` consistently)
- `code` (inline, existing) and the language-tagged code-fence path
  (existing, routes to `CodeBlock`) - unchanged logic, see below.

**CodeBlock.tsx** - Shiki highlighting itself already works (confirmed:
`codeToHtml` call is correct, `github-light` theme, proper fallback to
plain `<pre>` on failure/unknown language). What's missing, per the
request:
- A header bar above the code: language label (lowercase, e.g.
  `python`) on the left, a "Copy" button on the right (same
  copy-to-clipboard pattern already used in `MessageFooter.tsx`'s
  `handleCopy`, including the "Copied" 1.5s flash).
- New testids: `code-block-language-label`, `code-block-copy-button`.

**MessageHeader.tsx** - "smaller and more subtle": `text-xs` (12px) ->
`text-[11px]`, and the bean-alias badge's `text-espresso` ->
`text-medium-roast` (cost pill and latency are already
`text-medium-roast`). Container `flex-wrap` -> `flex-nowrap` so it
reads as one line per the request; on very narrow viewports this can
still visually overflow/wrap in the browser, which is an acceptable
trade-off (not worth a horizontal-scroll affordance for a 3-4-item
badge row).

## 2. Layout restructure: barista panel on the right

**`page.tsx`** restructured so the barista panel sits inside the same
flex row as `ResponseSection`, both above a full-width `OrderBox`:

```tsx
<div className="flex h-screen flex-col">
  <div className="flex flex-1 overflow-hidden">
    <Sidebar />
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex flex-1 overflow-hidden">
        <ResponseSection />
        <CounterDisplay {...props} />
      </div>
      <OrderBox />
    </div>
  </div>
  <CommandPalette />
</div>
```

`ResponseSection` gets `flex-1 min-w-0` (fills remaining space, ~65-70%
in practice). `CounterDisplay`'s outer element gets a fixed-percentage
width class (`lg:w-[32%]`, within the requested 30-35% range) instead of
today's `w-full`.

**`CounterDisplay` / `SceneShell.tsx` rework** (props unchanged - same
`CounterDisplayProps` contract, so `page.tsx` callers elsewhere don't
change):
- Root layout flips from a horizontal top strip (`border-b`, `h-32`
  scene body) to a vertical right-side panel: `border-l border-caramel
  bg-latte` (border moves from bottom to left edge, matching a
  right-hand panel), `flex h-full flex-col`.
- Expanded state: chevron + caption row at top (caption text is still
  useful here as a small label even though it's not the primary status
  surface anymore - kept for continuity/tests), scene body now `flex-1`
  (fills available vertical space) instead of fixed `h-32`, `TipsJar`
  moves from the top bar to a footer strip at the bottom of the panel.
- Fade zone: changes from a bottom `gradient-to-b` into `to-cream` to a
  left-edge `gradient-to-r` `from-latte to-transparent` (a few px wide,
  overlaid on the response-section side of the panel), per the request.
- Collapsed state: width collapses to a thin strip. Reusing the
  `Sidebar`'s own established collapsed-width convention (`w-12`, see
  `Sidebar/index.tsx:83`) for visual consistency instead of inventing a
  new width. Shows: chevron, the plain Tips Jar dollar amount (already
  existing collapsed behavior, `SceneShell.tsx:114-121`), and the steam
  icon while brewing (already existing, `:127-136`) - same content as
  today, just in a vertical strip instead of a horizontal one.
- Responsive hide: outer panel gets `hidden lg:flex` (Tailwind `lg` =
  1024px, matching the request's "below 1024px" breakpoint exactly).
  Below `lg`, a new small always-visible text-only status line (just
  `statusTextFor(event)`, no scene/chevron/Tips Jar/animation) renders
  in its place, positioned above `ResponseSection` inside the same
  column - this is the "same as reduced-motion behavior" fallback the
  request asks for (text-only, no animation attempted), implemented as
  a second small block inside `SceneShell` gated `lg:hidden` rather than
  a new component, keeping the "everything scene-related is private to
  `CounterDisplay/`" rule from the module's own docblock intact.
- All existing `data-testid`s are preserved (`scene-shell`,
  `scene-collapse-toggle`, `scene-caption`, `tips-jar-total`,
  `scene-body`, `scene-collapsed-steam`, `barista-scene`,
  `barista-scene-fallback`/`-rive`) - `SceneShell.test.tsx` and
  `CounterDisplay/index.test.tsx` assert on testids/attributes, not
  layout classes, so both suites should keep passing unmodified; new
  tests are additive.

**`barista_static.svg` viewBox rework** - the tier-2 fallback art
(`web/public/assets/counter/barista_static.svg`, currently `viewBox="0
0 800 260"`, a simple flat-shape placeholder: barista silhouette, 4
jars, a machine block, counter, cup, and a decorative tips-jar shape) is
landscape and needs a portrait layout to read correctly in a tall
panel. Plan: redraw viewBox as `0 0 260 640` and re-stack the existing
elements vertically - barista silhouette at top, the 4-jar shelf below
it (still a horizontal row, just narrower), machine block, counter
strip spanning the width, cup on the counter. Drop the decorative
tips-jar shape from the SVG itself (it would now visually duplicate the
real interactive `TipsJar` React component sitting at the panel's
bottom, per this section's own layout). This is the same "Phase 1
placeholder, real Rive art later" framing already established in
`docs/design/counter-scene-design.md` - not final art, just a
correctly-proportioned placeholder. `object-contain` on the `<img>`
(`BaristaScene.tsx:122`) already handles arbitrary viewBox ratios
correctly, so no JSX changes needed there beyond the container now
being tall instead of wide.

## 3. Overall aesthetic polish

- Palette audit: spot-check `Sidebar`, `OrderBox`, login page, and the
  new panel all use only the existing 6 tokens
  (`cream`/`latte`/`caramel`/`medium-roast`/`espresso`/`crema-amber`) -
  no ad hoc hex values introduced. (Quick grep pass, not a rewrite -
  everything already uses the tokens; this is a verification step.)
- `OrderBox` container (`OrderBox/index.tsx:200`): add `shadow-inner` to
  the existing `border-t border-caramel bg-latte p-3` classes for the
  "text field, not a bordered box" feel.
- Collapse/expand transition: the panel's width change needs an
  explicit `transition-[width] duration-200 ease-out` (the project's
  global default transition duration is 150ms per `globals.css:33`, but
  the request specifies 200ms for this specific transition, so it's set
  locally rather than changed globally).

## Files touched

- `web/src/app/page.tsx` - layout restructure (Section 2)
- `web/src/components/ResponseSection/index.tsx` - padding
- `web/src/components/ResponseSection/MessageBubble.tsx` - width,
  bubble styling, Markdown element overrides
- `web/src/components/ResponseSection/CodeBlock.tsx` - header bar,
  copy button, language label
- `web/src/components/ResponseSection/MessageHeader.tsx` - sizing/color
- `web/src/components/CounterDisplay/SceneShell.tsx` - vertical panel,
  responsive hide, mobile status line, transition
- `web/public/assets/counter/barista_static.svg` - portrait viewBox
- `web/src/components/OrderBox/index.tsx` - inset shadow
- Tests: `MessageBubble.test.tsx`, `CodeBlock` (new test file - none
  exists today), `MessageHeader.test.tsx`, `SceneShell.test.tsx`,
  `page.tsx` (new `page.test.tsx` - none exists today, needed for the
  new responsive/layout assertions), `web/e2e/chat.spec.ts` (any
  selectors relying on the old horizontal scene strip)

No `router/` changes - this Brew is frontend-only.

## Open questions

1. **Markdown styling approach**: write ~12 explicit Tailwind element
   overrides via `ReactMarkdown`'s `components` prop (recommended - no
   new dependency, full palette control, similar code volume to
   configuring the typography plugin) vs. install
   `@tailwindcss/typography` and configure a custom `prose-coffee`
   theme variant. Recommend the former.
2. **Responsive test strategy**: jsdom (Vitest's test environment) has
   no real viewport/media-query layout engine, so "the barista panel
   hides below 1024px" can only be tested as a **class-presence
   assertion** (the panel's wrapper element carries `hidden lg:flex`)
   rather than an actual rendered-width check. Playwright e2e *can*
   set a real viewport and check actual visibility, so the authoritative
   check will live there (`page.setViewportSize({ width: 900, height:
   ... })` + `expect(panel).toBeHidden()`), with the Vitest test as a
   lighter-weight regression guard on the class itself. Recommend both
   layers.
3. **Panel width value**: request says "~30-35%". Recommend a single
   fixed value (`lg:w-[32%]`) rather than a responsive range across
   breakpoints, to keep the flex math simple and predictable (`flex-1
   min-w-0` on the response column absorbs the rest). Confirm 32% is
   fine, or name a different single value.
4. **`barista_static.svg` rework depth**: recommend a straightforward
   re-stack of the existing flat shapes onto a portrait canvas (as
   described above) rather than redrawing new artwork - this is
   placeholder art pending real Rive output per the existing Brew 39
   design doc's tier system. Confirm this scope is right, or say if you
   want the illustration itself improved beyond a layout reflow.
5. **Mobile status line placement**: recommend keeping it owned by
   `CounterDisplay`/`SceneShell` (a `lg:hidden` sibling block inside the
   same component, not a new top-level component in `page.tsx`) to
   preserve the "everything scene-internal stays inside
   `CounterDisplay/`" encapsulation rule already stated in that module's
   docblock. Confirm.

Once approved, implementation proceeds directly (no separate `A`/`B`
sub-brew split needed - this is UI-only, no backend design step
required), followed by updated/new tests, a manual browser check per
the "test the golden path" UI rule, and Brew Log + Tasting Note.
