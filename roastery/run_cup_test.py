"""
Local Roastery Cup Test runner.

This script runs the same small Order against the configured Beans through the
OpenRouter client wrapper. It prints results only; it does not write scorecards,
ledger entries, routing policy, or House Blend updates.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Callable, Iterable, List, Mapping, Sequence

try:
    from .openrouter_client import OpenRouterResult, run_order
except ImportError:  # Allows: python roastery/run_cup_test.py
    from openrouter_client import OpenRouterResult, run_order


DEFAULT_BEANS = (
    "poolside/laguna-m.1:free",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
)

DEFAULT_OUTPUT_DIR = Path("roastery") / "local_cup_outputs"
MAX_RETRIES = 1
RETRY_DELAY_SECONDS = 1.0
TRANSIENT_ERROR_MARKERS = (
    "http error 429",
    "provider returned error",
    "rate limit",
    "rate-limit",
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
    max_retries: int = MAX_RETRIES,
    retry_delay_seconds: float = RETRY_DELAY_SECONDS,
    sleeper: Callable[[float], None] = time.sleep,
    save_outputs: bool = False,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> List[OpenRouterResult]:
    """Run the same Order against each Bean and keep results in memory."""

    results = []
    total = len(beans)
    for index, bean in enumerate(beans, start=1):
        printer(f"Running Bean {index}/{total}: {bean}")
        result = _run_single_bean(
            bean=bean,
            order=order,
            timeout_seconds=timeout_seconds,
            runner=runner,
            printer=printer,
            retry_label=f"Bean {index}/{total}",
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            sleeper=sleeper,
        )
        status = "error" if result.errors else "ok"
        printer(f"Finished Bean {index}/{total}: {status}")
        results.append(result)

    if save_outputs:
        capture_path = save_full_outputs(
            results=results,
            order=order,
            output_dir=output_dir,
            run_id=run_id,
        )
        printer(f"Full outputs saved to: {capture_path}")

    return results


def save_full_outputs(
    results: Sequence[OpenRouterResult],
    order: str,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> Path:
    """Save successful full outputs and a JSON manifest for human review."""

    base_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    safe_run_id = _safe_run_id(run_id) if run_id else _timestamp_run_id()
    run_dir = base_dir / safe_run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "run_id": safe_run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(run_dir),
        "order_sha256": hashlib.sha256(order.encode("utf-8")).hexdigest(),
        "beans_tested": [result.model for result in results],
        "beans": [],
    }

    for index, result in enumerate(results, start=1):
        status = "error" if result.errors else "ok"
        entry = {
            "bean": result.model,
            "status": status,
            "latency_seconds": result.latency_seconds,
            "usage": result.usage,
            "error": "; ".join(result.errors) if result.errors else None,
            "output_file": None,
        }

        if not result.errors:
            filename = _safe_model_output_filename(result.model, index)
            output_path = run_dir / filename
            output_path.write_text(result.response_text, encoding="utf-8")
            entry["output_file"] = str(output_path)

        manifest["beans"].append(entry)

    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return run_dir


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


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the same Project Coffee Cup Test Order against each Bean.",
    )
    parser.add_argument(
        "--save-outputs",
        action="store_true",
        help="Save full successful Bean outputs and a JSON manifest locally.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for captured runs. Defaults to roastery/local_cup_outputs.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier used as the capture subdirectory name.",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] = ()) -> int:
    args = parse_args(argv)

    if not openrouter_key_available():
        print("OPENROUTER_API_KEY is not set. Set it locally and rerun.")
        return 1

    print("Project Coffee Roastery Cup Test")
    if args.save_outputs:
        output_dir = args.output_dir or str(DEFAULT_OUTPUT_DIR)
        print(f"Full outputs will be saved under: {output_dir}")
    else:
        print("No files will be written by this runner.")
    print("")
    results = run_cup_test(
        save_outputs=args.save_outputs,
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
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
    printer: Callable[[str], None],
    retry_label: str,
    max_retries: int,
    retry_delay_seconds: float,
    sleeper: Callable[[float], None],
) -> OpenRouterResult:
    attempts = 0
    while True:
        result = _call_runner(bean, order, timeout_seconds, runner)
        if attempts >= max_retries or not _should_retry(result):
            return result

        attempts += 1
        printer(f"Retrying {retry_label}: {bean} after transient error")
        if retry_delay_seconds > 0:
            sleeper(retry_delay_seconds)


def _call_runner(
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


def _should_retry(result: OpenRouterResult) -> bool:
    error_text = " ".join(result.errors).lower()
    return any(marker in error_text for marker in TRANSIENT_ERROR_MARKERS)


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


def _safe_model_output_filename(model: str, index: int) -> str:
    digest = hashlib.sha256(model.encode("utf-8")).hexdigest()[:10]
    safe = _safe_path_component(model)
    if len(safe) > 80:
        safe = safe[:80].rstrip(".-_")
    return f"{index:02d}-{safe or 'bean'}-{digest}.txt"


def _safe_run_id(run_id: str) -> str:
    safe = _safe_path_component(run_id)
    if not safe:
        return _timestamp_run_id()
    return safe[:80].rstrip(".-_") or _timestamp_run_id()


def _safe_path_component(value: str) -> str:
    chars = []
    previous_dash = False
    for char in value:
        if char.isalnum() or char in "._-":
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True

    return "".join(chars).strip(".-_")


def _timestamp_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    raise SystemExit(main(sys.argv[1:]))
