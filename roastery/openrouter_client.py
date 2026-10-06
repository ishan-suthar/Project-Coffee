"""
Small OpenRouter client wrapper for Project Coffee Roastery tests.

The API key is read only from OPENROUTER_API_KEY. This module never prints,
logs, or stores the key.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib import error, request


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class OpenRouterResult:
    """Structured result from a single OpenRouter order."""

    model: str
    response_text: str
    latency_seconds: Optional[float]
    usage: Optional[Dict[str, Any]]
    errors: List[str]


def run_order(model: str, prompt: str, timeout_seconds: int = 60) -> OpenRouterResult:
    """
    Send one prompt to one OpenRouter model and return structured evidence.

    Missing credentials, HTTP errors, and malformed responses are returned in
    errors instead of being raised, so Roastery shots can fail safely.
    """

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return OpenRouterResult(
            model=model,
            response_text="",
            latency_seconds=None,
            usage=None,
            errors=["OPENROUTER_API_KEY is not set."],
        )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-OpenRouter-Title": "Project Coffee Roastery",
    }
    api_request = request.Request(
        OPENROUTER_API_URL,
        data=body,
        headers=headers,
        method="POST",
    )

    start = time.perf_counter()
    try:
        with request.urlopen(api_request, timeout=timeout_seconds) as response:
            latency = time.perf_counter() - start
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        latency = time.perf_counter() - start
        return OpenRouterResult(
            model=model,
            response_text="",
            latency_seconds=latency,
            usage=None,
            errors=[_http_error_message(exc)],
        )
    except error.URLError as exc:
        latency = time.perf_counter() - start
        return OpenRouterResult(
            model=model,
            response_text="",
            latency_seconds=latency,
            usage=None,
            errors=[f"OpenRouter request failed: {exc.reason}"],
        )

    return _parse_response(model=model, latency_seconds=latency, response_body=response_body)


def _parse_response(
    model: str,
    latency_seconds: float,
    response_body: str,
) -> OpenRouterResult:
    try:
        data = json.loads(response_body)
    except json.JSONDecodeError as exc:
        return OpenRouterResult(
            model=model,
            response_text="",
            latency_seconds=latency_seconds,
            usage=None,
            errors=[f"OpenRouter response was not valid JSON: {exc}"],
        )

    choices = data.get("choices") or []
    response_text = ""
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            response_text = content

    if not response_text:
        return OpenRouterResult(
            model=model,
            response_text="",
            latency_seconds=latency_seconds,
            usage=_usage_from(data),
            errors=["OpenRouter response did not include message content."],
        )

    return OpenRouterResult(
        model=model,
        response_text=response_text,
        latency_seconds=latency_seconds,
        usage=_usage_from(data),
        errors=[],
    )


def _usage_from(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    usage = data.get("usage")
    if isinstance(usage, dict):
        return usage
    return None


def _http_error_message(exc: error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except Exception:
        body = ""

    if not body:
        return f"OpenRouter HTTP error {exc.code}: {exc.reason}"

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return f"OpenRouter HTTP error {exc.code}: {body}"

    api_error = data.get("error")
    if isinstance(api_error, dict):
        message = api_error.get("message")
        if message:
            return f"OpenRouter HTTP error {exc.code}: {message}"

    return f"OpenRouter HTTP error {exc.code}: {body}"
