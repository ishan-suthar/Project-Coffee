"""
Local Roastery Cup Test runner.

This script runs the same small Order against the configured Beans through the
OpenRouter client wrapper. It prints results only; it does not write scorecards,
ledger entries, routing policy, or House Blend updates.
"""

from __future__ import annotations

import os
from typing import Callable, Iterable, List, Mapping, Sequence

try:
    from .openrouter_client import OpenRouterResult, run_order
except ImportError:  # Allows: python roastery/run_cup_test.py
    from openrouter_client import OpenRouterResult, run_order


DEFAULT_BEANS = (
    "qwen/qwen3-coder:free",
    "deepseek/deepseek-r1:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
)

DEFAULT_ORDER = """\
You are Espresso Fast Coder.

Task: propose a tiny Python standard-library implementation and tests.

Requirement:
- Implement count_extensions(paths), where paths is an iterable of strings.
- Return a dict with counts for ".py", ".md", and "other".
- Matching should be case-insensitive.
- Use only the Python standard library.

Output format:
1. Brief approach, maximum 3 bullets.
2. One fenced python block for extension_counts.py.
3. One fenced python block for test_extension_counts.py using unittest.
"""


Runner = Callable[[str, str, int], OpenRouterResult]


def openrouter_key_available(env: Mapping[str, str] | None = None) -> bool:
    """Return whether the local process has an OpenRouter key configured."""

    source = os.environ if env is None else env
    return bool(source.get("OPENROUTER_API_KEY"))


def run_cup_test(
    beans: Sequence[str] = DEFAULT_BEANS,
    order: str = DEFAULT_ORDER,
    timeout_seconds: int = 120,
    runner: Runner = run_order,
    printer: Callable[[str], None] = print,
) -> List[OpenRouterResult]:
    """Run the same Order against each Bean and keep results in memory."""

    results = []
    total = len(beans)
    for index, bean in enumerate(beans, start=1):
        printer(f"Running Bean {index}/{total}: {bean}")
        result = _run_single_bean(bean, order, timeout_seconds, runner)
        status = "error" if result.errors else "ok"
        printer(f"Finished Bean {index}/{total}: {status}")
        results.append(result)
    return results


def format_results_table(results: Iterable[OpenRouterResult]) -> str:
    """Format a compact comparison table without scoring or writing files."""

    rows = [
        [
            result.model,
            "error" if result.errors else "ok",
            _format_latency(result.latency_seconds),
            _format_usage(result.usage),
            _response_preview(result.response_text),
            "; ".join(result.errors) if result.errors else "",
        ]
        for result in results
    ]
    return _format_table(
        ["Bean", "Status", "Latency", "Usage", "Response preview", "Errors"],
        rows,
    )


def main() -> int:
    if not openrouter_key_available():
        print("OPENROUTER_API_KEY is not set. Set it locally and rerun.")
        return 1

    print("Project Coffee Roastery Cup Test")
    print("No files will be written by this runner.")
    print("")
    results = run_cup_test()
    print("")
    print(format_results_table(results))
    print("")
    print("Cup Test completed successfully. Ready for Shot 8F.")
    return 0


def _run_single_bean(
    bean: str,
    order: str,
    timeout_seconds: int,
    runner: Runner,
) -> OpenRouterResult:
    try:
        return runner(bean, order, timeout_seconds)
    except Exception as exc:
        return OpenRouterResult(
            model=bean,
            response_text="",
            latency_seconds=None,
            usage=None,
            errors=[f"Runner error: {exc}"],
        )


def _format_latency(latency_seconds: float | None) -> str:
    if latency_seconds is None:
        return "unknown"
    return f"{latency_seconds:.2f}s"


def _format_usage(usage: Mapping[str, object] | None) -> str:
    if not usage:
        return "unknown"

    total = usage.get("total_tokens")
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if total is not None:
        return f"{total} total"
    if prompt is not None or completion is not None:
        return f"in={prompt or '?'} out={completion or '?'}"
    return "metadata returned"


def _response_preview(response_text: str, max_chars: int = 80) -> str:
    preview = " ".join(response_text.split())
    if not preview:
        return ""
    if len(preview) <= max_chars:
        return preview
    return f"{preview[: max_chars - 3]}..."


def _format_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    all_rows = [list(headers), *[list(row) for row in rows]]
    widths = [
        max(len(str(row[column])) for row in all_rows)
        for column in range(len(headers))
    ]

    def format_row(row: Sequence[str]) -> str:
        cells = [
            str(value).ljust(widths[column])
            for column, value in enumerate(row)
        ]
        return " | ".join(cells)

    separator = "-+-".join("-" * width for width in widths)
    return "\n".join([format_row(headers), separator, *[format_row(row) for row in rows]])


if __name__ == "__main__":
    raise SystemExit(main())
