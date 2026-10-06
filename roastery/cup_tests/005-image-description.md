# 005 Image Description

## Purpose

Test real vision capability for a Bean whose `capabilities.vision: true` comes
from a live GET /v1/models response, not a prior Roastery run - Flat White
(google/gemini-2.5-flash-lite) and Day Roast (google/gemma-4-31b-it:free) both
need this verified against a real image before either is trusted for image
requests. Cannot be run through `roastery/run_cup_test.py` - its
`openrouter_client.py` wrapper is text-prompt only (no image attachment
support). Run this one as a real `POST /v1/order` call against the actual
router instead (matching the Brew 42 precedent of stepping outside the
standalone runner when it can't express what's being tested), with a real
image attached and `bean_alias_override` set to the Bean under test.

## Order

Attach a real photo containing at least: one piece of legible text (a sign,
label, or printed page) and at least three distinct identifiable objects.

Prompt:

You are Barista describing an attached image for a user who cannot see it.

Describe:

1. every distinct object you can identify;
2. any legible text, quoted exactly as it appears;
3. the general scene/setting;
4. anything you are uncertain about - say so explicitly rather than guessing.

## Success Criteria

- Correctly identifies the real objects actually present (verified by the
  human against the real photo, not assumed).
- Transcribes legible text correctly, or explicitly flags it as unclear
  rather than inventing plausible-looking text.
- Does not describe objects, text, or details that are not actually in the
  image (a fabricated detail is a hard failure, not a minor deduction - this
  is the vision-equivalent of the citation discipline in 004).
- States uncertainty when genuinely uncertain, rather than a confident wrong
  answer.

## Scoring Notes

High scores require zero fabricated content - an image description that
invents even one plausible-sounding object or text detail should score low
regardless of how well-written the rest of the answer is. Note latency and
whether the real router `complete` event's `cost_usd`/`tokens_in`/
`tokens_out` match what beans.yaml's configured pricing would predict, so a
pricing-config error surfaces the same way Brew 48's cost-inconsistency fix
was originally found.
