# Web Search (Brew 50) - Decaf plan

**Reconstructed plan.** The original plan for this Brew was written and
approved in an earlier session, but no `docs/design/*.md` file for it exists
in the repo and it was not in this session's carried-over context (unlike
every other Brew, which has a design doc). Rather than guess at the lost
document's exact wording, this plan was written fresh from the codebase plus
the three corrections and two simplifications given at the start of this
session. Flag anything below that doesn't match what was approved before.

**Dependency note (corrected from this session's opening message):** Brew 48
(cost contract, `resolve_cost()`) IS committed (`d44f81e`). Brew 49 (spend
caps) is fully implemented and readable in the working tree, but `git
status` shows it **not yet committed** - it landed, but "committed" was not
quite accurate. This plan treats Brew 49's code as a stable dependency
either way, since it's sitting in the tree either way.

## Goal

Let the chat UI (and OpenAI-compatible API clients) ask a request to include
live web search results, via OpenRouter's tool-calling-based web search
mechanism, gated by the same spend caps as everything else.

## What triggers it

A new per-request boolean, mirroring the existing `use_pantry` toggle
(`router/app/main.py:2076`, Brew 41) rather than a session-wide setting:

- `OrderRequest.use_web: bool = False` (`/v1/order` - chat UI toggle)
- `ChatCompletionRequest.use_web: bool = False` (`/v1/chat/completions` - a
  raw OpenAI client like Cursor has no way to know about Coffee's Beans or
  which of them can search, so this needs its own explicit field; it cannot
  infer from `tools`, since a client's own `tools` array is for its own
  function-calling loop, unrelated to Coffee-side web search)

## Bean selection: `capable_bean()`

**Correction 2 applied.** Web search requires a Bean with
`capabilities.tool_calling: true` in `beans.yaml` (`Bean.tool_calling`,
Brew 47 - `router/app/aliases.py:46`). Today that's Reserve Blend
($0.003/$0.015 per 1k) and Single Origin ($0.001/$0.005 per 1k) - both
`tool_calling: true`, both non-free. No free-tier Bean (House Blend, Second
Pour, Guest Bean) qualifies.

New `BeanRegistry.capable_bean(*, tool_calling: bool = False, vision: bool =
False) -> Optional[Bean]`, following the existing `vision_capable_beans()`/
`default_vision_bean()` shape (`router/app/aliases.py:116-138`):

```python
def capable_bean(self, *, tool_calling: bool = False, vision: bool = False) -> Optional[Bean]:
    candidates = [
        b for b in self._beans
        if b.is_available
        and (not tool_calling or b.tool_calling)
        and (not vision or b.vision)
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda b: (b.price_per_1k_input_usd or 0.0) + (b.price_per_1k_output_usd or 0.0),
    )
```

Picks the **cheapest capable Bean by beans.yaml pricing**, not
`role == "default"` (which isn't tool-calling-capable anyway) and not the
first match in file order. At today's pricing this returns **Single
Origin**, not Reserve Blend (`0.001+0.005=0.006` vs `0.003+0.015=0.018` per
1k combined) - a new `RoutingPolicy`/`aliases` test asserts this explicitly,
per the correction: a web request with `use_web=True` must route to Single
Origin, not Reserve Blend, when both are capable.

Routing integration: `select_route()`/`manual_route()` gain a `needs_web:
bool = False` kwarg, parallel to the existing `needs_vision` kwarg. When
true and the policy-selected/manually-selected Bean isn't tool-calling
capable, escalate to `capable_bean(tool_calling=True)` exactly like the
existing vision-constraint branch does today
(`router/app/routing.py:110-127`), setting the same
`constraint_reason`-style field ("needs_web: escalated from X to Y"). No
tool-calling-capable Bean configured -> a new `NoWebSearchBeanError`
(subclass of `RoutingError`, mirroring `NoVisionBeanError`), surfaced as
`error_type="no_web_search_bean_available"` - never silently drop the
`use_web` request or silently proceed without search.

**Manual override + use_web conflict**: if a human manually picks a
non-tool-calling Bean (`bean_alias_override`) while also setting `use_web`,
`manual_route()` raises the same way it already does for a manual
vision-incapable pick (`router/app/routing.py:172-177`) - never silently
switches Beans out from under an explicit human choice.

## Classifier: correction 1 applied (reject the task_type nudge)

No change to `TASK_TYPE_RULES` or `task_type` output. `task_type` is a
Ledger column `ledger_summary` slices by (`tools/ledger_summary.py`); a
`use_web` nudge would mislabel a coding question with web search on, and
routing doesn't need it anyway - `needs_web` above is driven directly by the
request's `use_web` flag, not by classification, exactly like
`needs_vision` is driven by attachment content-type, not classification.

Instead, one new `COMPLEXITY_SIGNALS` entry (`router/app/classifier.py:275`),
following the existing `has_attachments` precedent (any attachment pushes
toward `cold_brew`, unconditionally - Brew 38):

```python
ComplexitySignal("use_web", lambda c: c.use_web),
```

`ComplexityContext` gains a `use_web: bool = False` field. Injected search
results genuinely inflate the request (more context to reason over), which
is what `COMPLEXITY_SIGNALS` measures - unlike `task_type`, `complexity` has
no Ledger-slicing role this would corrupt.

## OpenRouter call shape

`stream_order()`/`openrouter_client.py` gains a `plugins: Optional[list] =
None` passthrough parameter, sent as `payload["plugins"]` only when not
None - same pattern as the existing `tools`/`tool_choice` passthrough
(`router/app/openrouter_client.py:117-120`). When `use_web` is set, Coffee
sends `plugins=[{"id": "web"}]` (OpenRouter's built-in web search plugin,
which restricts itself to the underlying model's tool-calling ability - the
reason `capable_bean()` requires `tool_calling=True` above; a Bean without
real tool support can't be trusted to execute the plugin's search-and-cite
loop correctly). Coffee never inspects or reinterprets the search results or
citations - they arrive as part of the assistant turn's content/annotations
and are relayed through exactly like `tool_calls_delta` already is.

## Cost: corrections/simplifications applied

**Section 5 collapses** now that Brew 48 landed. `web_search_cost_usd` is a
**breakdown** of `cost_usd` (which `resolve_cost()` already returns as the
true total, preferring OpenRouter's reported `usage.cost`), never an addend
- exactly the COST CONTRACT `router/app/ledger.py`'s module docstring
already states, written explicitly to anticipate this Brew.

New `RouterLedger` helper, not part of `resolve_cost()` itself (search-fee
attribution is a web-search-specific concern, not a general cost concern):

```python
def estimate_web_search_component_usd(
    bean: Bean, tokens_in: int, tokens_out: int, cost_usd: Optional[float], cost_source: str
) -> Optional[float]:
    """cost_usd (from resolve_cost()) minus the pure token cost = the search
    fee, ONLY when cost_source == "reported" (a real all-in total to
    subtract from). When cost_source == "computed", cost_usd already IS the
    token math with nothing else to subtract - there is no way to isolate a
    search fee from a computed figure, so this returns None (unknown, never
    a fabricated 0.0). Clamped to a minimum of 0.0 to absorb rounding drift,
    never negative."""

    if cost_source != "reported" or cost_usd is None:
        return None
    token_cost = round(
        (tokens_in / 1000) * bean.price_per_1k_input_usd
        + (tokens_out / 1000) * bean.price_per_1k_output_usd, 6,
    )
    return max(0.0, round(cost_usd - token_cost, 6))
```

New `web_search_cost_usd: Optional[float] = None` `CSV_HEADER`/`LedgerRow`
column (Brew 38 auto-migration pattern, blank for every pre-migration row
and for any row where `use_web` was false). A Tips Jar/cost pill still sums
`cost_usd` alone, never `cost_usd + web_search_cost_usd` - this column is
read-only informational breakdown, same as `cost_source`.

**Spend caps already cover this - verified, not assumed.**
`check_spend_cap()` (`router/app/main.py`) and `RouterLedger.today_spend_usd()`
(`router/app/ledger.py`) both sum the `cost_usd` column only. Since a web
request's `cost_usd` is the reported total (search fee included, per the
COST CONTRACT), it is already counted by both the per-user and global daily
caps with zero code changes needed there. The **admission-time estimate**
(`estimate_cost_usd()`, pre-call) cannot include an unknown future search
fee - it stays pure token math against `capable_bean()`'s pricing, same as
every other request; the real fee only becomes visible after the call
completes and lands in the next request's cap check. This is stated
explicitly (not silently assumed) as a known, acceptable estimate-vs-actual
gap - identical in kind to every other request's assumed-output-tokens
estimate already being approximate.

## Visibility / docs (correction 3)

`router/README.md` and the Tasting Note both get a prominent callout,
**more prominent than the per-search fee itself**: no free Bean supports
tool calling, so turning on `use_web` always leaves the free tier, routing
to Single Origin (cheapest capable) or Reserve Blend. This is the real cost
of the feature - the per-search plugin fee is secondary to "this request no
longer costs $0.00."

## Edge cases

- `use_web=True` + no tool-calling Bean configured -> `no_web_search_bean_available` error (SSE `error` event on `/v1/order`, OpenAI-shape error on `/v1/chat/completions`), never silent fallback.
- `use_web=True` + manual override to a non-capable Bean -> raises (see above), never silently switches Beans.
- `use_web=True` + `use_pantry=True` together -> both run; independent toggles, no interaction (Pantry injects local doc chunks, web search injects live results - both are just more context).
- Spend-cap denial with `use_web=True` -> refused before the call exactly like today, no special-casing (the pre-call estimate already reflects the capable Bean's real pricing).
- `cost_source == "computed"` (no reported usage.cost - shouldn't happen for these two Beans, both actively priced, but the general `resolve_cost()` fallback still exists) -> `web_search_cost_usd` stays `None`/unknown, never fabricated as `0.0` or as the full token-computed total.
- Escalation: a `use_web` draft that escalates re-runs against the premium Bean **without** `use_web` re-triggered automatically unless the premium Bean is also tool-calling-capable and the caller still wants search - simplest correct behavior is to carry `use_web`/`plugins` through the escalation re-run unchanged (premium Beans here are both tool-calling capable, so this is usually a no-op difference from today's escalation, just with `plugins` carried through).
- `/v1/chat/completions` with `stream=true` and `use_web=True`: no special handling needed beyond the existing tool_calls_delta passthrough - search results/citations arrive as part of the normal delta stream.

## Tests (planned, not yet written)

- `capable_bean()`: cheapest-wins (Single Origin over Reserve Blend), no-candidates returns None, vision+tool_calling combined filter.
- `select_route`/`manual_route` with `needs_web=True`: escalates a non-capable primary to the cheapest capable Bean; raises `NoWebSearchBeanError` when none configured; manual override to a non-capable Bean + `use_web` raises.
- Classifier: `use_web=True` always yields `cold_brew` via the new signal; `task_type` is unaffected by `use_web` (regression-locks correction 1).
- `stream_order()`: `plugins` sent only when given, omitted (not `null`) otherwise - same convention as `tools`.
- `estimate_web_search_component_usd()`: reported-source subtraction, computed-source returns None, negative-drift clamps to 0.0.
- End-to-end `/v1/order` and `/v1/chat/completions`: real Ledger row has `web_search_cost_usd` populated only when `cost_source == "reported"`; spend cap counts a web request's full `cost_usd` (including the fee) against the per-user/global cap on the *next* request.
- README/Tasting Note: no test, just confirm the free-tier callout is present (manual read).

## Open questions for approval

1. **`plugins` shape**: send a bare `[{"id": "web"}]` with OpenRouter's defaults, or expose `max_results`/a per-request search-depth knob now? Recommend bare defaults now, revisit if real usage shows a need.
2. **Escalation + `use_web`**: carry `use_web`/`plugins` through an auto-escalation re-run unchanged (see Edge cases), or drop search on escalation since the premium Bean is already a strictly better answer? Recommend carrying it through - dropping it would silently change what the user asked for.
3. **`/v1/chat/completions` scope**: add `use_web` there too (this plan's default), or ship `/v1/order`-only first since that's the only client that can render a toggle today? Recommend both now, since the classifier/routing/cost work is identical either way and skipping the API endpoint just means redoing this same plan later.
