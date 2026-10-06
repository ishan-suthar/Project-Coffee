"""Async streaming OpenRouter client for the Coffee Core Router.

Distinct from roastery/openrouter_client.py, which is a synchronous,
non-streaming client built for one-shot Roastery Cup Tests. This module
streams chunk-by-chunk so router/app/main.py can emit `generating` SSE
ticks as content arrives (see docs/design/coffee-core-router-design.md
Section 1). The API key is read only from OPENROUTER_API_KEY, or an
explicit override for tests. This module never prints, logs, or stores the
key, and never sends it anywhere but the Authorization header of the single
hardcoded OpenRouter base URL below.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_TITLE_HEADER = "Project Coffee Coffee Core Router"


class OpenRouterClientError(Exception):
    """Raised for missing credentials or unrecoverable transport/API errors."""


@dataclass(frozen=True)
class StreamChunk:
    content_delta: str = ""
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    is_final: bool = False
    # Brew 47 (docs/design/openai-compat-endpoint-design.md Section 1):
    # raw OpenAI-shape tool_calls delta objects, parsed straight through
    # from the provider's own streamed delta - Coffee never interprets
    # these, only relays them. Previously silently dropped by every caller
    # of this module (content_delta was "" for a tool-call-only chunk).
    tool_calls_delta: Optional[List[Dict[str, Any]]] = None
    # Web search citations Brew: raw OpenAI-shape annotation objects
    # (`{"type": "url_citation", "url_citation": {"url", "title", ...}}`),
    # parsed straight through from the provider's own streamed delta - the
    # second delta.* field this module silently dropped (tool_calls_delta,
    # Brew 47, was the first). Unlike tool_calls_delta, an annotation
    # arrives whole in one chunk, never split across multiple deltas by
    # index - see router/app/main.py's _consume_stream, which appends
    # rather than index-merges.
    annotations: Optional[List[Dict[str, Any]]] = None


async def stream_order(
    model: str,
    prompt: str = "",
    *,
    api_key: Optional[str] = None,
    timeout_seconds: int = 60,
    http_client: Optional[httpx.AsyncClient] = None,
    image_data_urls: Optional[List[str]] = None,
    history_messages: Optional[List[Dict[str, str]]] = None,
    messages_override: Optional[List[Dict[str, Any]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Any] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> AsyncIterator[StreamChunk]:
    """Stream one prompt to one OpenRouter model.

    api_key defaults to os.environ["OPENROUTER_API_KEY"] when not supplied.
    http_client lets tests inject an httpx.AsyncClient built with
    httpx.MockTransport - no live network call is ever made in tests, and
    the only real caller of this function without an injected client is
    router/app/main.py at actual demo/runtime.

    image_data_urls (Brew 38): base64 `data:image/...;base64,...` URLs,
    built by the caller from uploaded file bytes at send time - never
    stored pre-encoded (see docs/design/attachments-design.md Section 5).
    When present, the OpenRouter message content becomes the multimodal
    array form; when absent (every non-image request, and every call
    before Brew 38), content stays the plain string - fully backward
    compatible.

    history_messages (Brew 46): oldest-first {"role", "content"} dicts
    prepended before the final (current) message, built by
    router/app/history.py only when the session's remember_chat is true.
    None (the default, and every call before Brew 46) sends exactly the
    single-message payload as before - see docs/design/
    conversation-memory-design.md.

    messages_override (Brew 47): a caller-assembled, already OpenAI-shape
    `messages` list, sent verbatim in place of the prompt/image_data_urls/
    history_messages assembly below - used by /v1/chat/completions, whose
    client has already built its own messages array (including any
    multimodal content-part arrays) and whose history must be relayed
    as-is, never reassembled from Coffee's own session store. When given,
    prompt/image_data_urls/history_messages are ignored entirely. See
    docs/design/openai-compat-endpoint-design.md Section 1.

    tools/tool_choice (Brew 47, and the web search cost optimization
    Brew): relayed to OpenRouter unchanged, only when not None (an empty
    list is never sent - some providers reject it). Coffee never
    interprets these. `use_web` requests send a single
    `{"type": "openrouter:web_search", "parameters": {"engine": ...}}`
    tool entry here - the old `plugins: [{"id": "web"}]` mechanism this
    replaced is officially deprecated by OpenRouter (confirmed against
    its live docs) and only the tools-array form exposes an `engine`.
    """

    resolved_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
    if not resolved_key:
        raise OpenRouterClientError("OPENROUTER_API_KEY is not set.")

    if messages_override is not None:
        messages: List[Dict[str, Any]] = list(messages_override)
    else:
        content: Any = prompt
        if image_data_urls:
            content = [{"type": "text", "text": prompt}] + [
                {"type": "image_url", "image_url": {"url": url}} for url in image_data_urls
            ]
        messages = list(history_messages or [])
        messages.append({"role": "user", "content": content})

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "usage": {"include": True},
    }
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Content-Type": "application/json",
        "X-Title": OPENROUTER_TITLE_HEADER,
    }

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
    try:
        async with client.stream("POST", OPENROUTER_API_URL, json=payload, headers=headers) as response:
            if response.status_code >= 400:
                body = await response.aread()
                raise OpenRouterClientError(_http_error_message(response.status_code, body))
            async for line in response.aiter_lines():
                chunk = _parse_sse_line(line)
                if chunk is not None:
                    yield chunk
    except httpx.TimeoutException as exc:
        raise OpenRouterClientError(f"OpenRouter request timed out: {exc}") from exc
    except httpx.TransportError as exc:
        raise OpenRouterClientError(f"OpenRouter request failed: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()


def _parse_sse_line(line: str) -> Optional[StreamChunk]:
    stripped = line.strip()
    if not stripped or not stripped.startswith("data:"):
        return None

    data_str = stripped[len("data:"):].strip()
    if data_str == "[DONE]":
        return StreamChunk(is_final=True)

    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        return None

    choices = data.get("choices") or []
    content_delta = ""
    finish_reason = None
    tool_calls_delta = None
    annotations = None
    if choices:
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            content_delta = content
        tool_calls_delta = delta.get("tool_calls") or None
        annotations = delta.get("annotations") or None
        finish_reason = choices[0].get("finish_reason")

    usage = data.get("usage")
    return StreamChunk(
        content_delta=content_delta,
        finish_reason=finish_reason,
        usage=usage,
        tool_calls_delta=tool_calls_delta,
        annotations=annotations,
    )


def _http_error_message(status_code: int, body: bytes) -> str:
    try:
        text = body.decode("utf-8")
    except Exception:
        text = ""

    if not text:
        return f"OpenRouter HTTP error {status_code}"

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return f"OpenRouter HTTP error {status_code}: {text}"

    api_error = data.get("error")
    if isinstance(api_error, dict):
        message = api_error.get("message")
        if message:
            return f"OpenRouter HTTP error {status_code}: {message}"

    return f"OpenRouter HTTP error {status_code}: {text}"
