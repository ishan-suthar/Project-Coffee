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
from typing import Any, AsyncIterator, Dict, Optional

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


async def stream_order(
    model: str,
    prompt: str,
    *,
    api_key: Optional[str] = None,
    timeout_seconds: int = 60,
    http_client: Optional[httpx.AsyncClient] = None,
) -> AsyncIterator[StreamChunk]:
    """Stream one prompt to one OpenRouter model.

    api_key defaults to os.environ["OPENROUTER_API_KEY"] when not supplied.
    http_client lets tests inject an httpx.AsyncClient built with
    httpx.MockTransport - no live network call is ever made in tests, and
    the only real caller of this function without an injected client is
    router/app/main.py at actual demo/runtime.
    """

    resolved_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
    if not resolved_key:
        raise OpenRouterClientError("OPENROUTER_API_KEY is not set.")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "usage": {"include": True},
    }
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
    if choices:
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            content_delta = content
        finish_reason = choices[0].get("finish_reason")

    usage = data.get("usage")
    return StreamChunk(content_delta=content_delta, finish_reason=finish_reason, usage=usage)


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
