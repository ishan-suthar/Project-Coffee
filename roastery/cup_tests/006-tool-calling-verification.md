# 006 Tool Calling Verification

## Purpose

Verify real tool-calling behavior before trusting `capabilities.tool_calling`
in beans.yaml for a Bean that has never actually been asked to call a tool
through this router. This is the specific evidence Day Roast's `tool_calling:
false` is waiting on (it reports `tools`/`tool_choice` as accepted parameters
in a live GET /v1/models response, but accepting the parameter is not the
same as reliably using it - see beans.yaml's own comment on this). Also worth
re-running against Flat White, since it is now the Bean every tool-calling-
constrained request routes to by price alone, with no tool-calling evidence
of its own yet either.

Cannot be run through `roastery/run_cup_test.py` - its `openrouter_client.py`
wrapper takes a plain text prompt only, no `tools` array. Run as a real `POST
/v1/chat/completions` call (the endpoint that actually relays a `tools`
array unmodified - see router/app/main.py's `_run_chat_completion`) with
`model` set to the Bean's alias, or a real `/v1/order` call with `use_web:
true` to exercise the router's own `openrouter:web_search` tool path
specifically.

## Order

Send a request with this `tools` array:

```json
[
  {
    "type": "function",
    "function": {
      "name": "get_current_weather",
      "description": "Get the current weather for a named city.",
      "parameters": {
        "type": "object",
        "properties": {
          "city": { "type": "string", "description": "City name." }
        },
        "required": ["city"]
      }
    }
  }
]
```

Prompt: "What's the weather like in Lisbon right now? Use the tool - do not
guess."

## Success Criteria

- The response's `tool_calls` contains a real, well-formed call to
  `get_current_weather` with `city` correctly extracted as `"Lisbon"` - not
  prose describing what it would do, and not a fabricated weather answer with
  no tool call at all (the single most likely failure mode for an
  "accepts-the-parameter-but-doesn't-reliably-use-it" model).
- `finish_reason` is `"tool_calls"`, matching what
  `router/app/main.py`'s existing tool-calls-only-response handling already
  expects (see its comment on `check_for_failure()` not punishing a
  well-formed tool call for having empty `text`).
- No hallucinated weather data in the same turn the tool call is made.

## Scoring Notes

This is pass/fail on tool-call correctness, not a quality scale - if the tool
call is malformed, absent, or the model answers with invented weather data
instead of calling the tool, `capabilities.tool_calling` in beans.yaml must
stay/return to `false` for that Bean regardless of how well-written its prose
is elsewhere. Record the raw `tool_calls` JSON actually returned (not just a
pass/fail note) so a borderline result can be re-examined later without
re-running the call.
