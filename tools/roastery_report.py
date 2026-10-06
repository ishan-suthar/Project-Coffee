"""Generate draft Roastery reports from local Cup Test manifests.

The report generator reads manifest metadata and optional capped local output
previews. It never calls models or external APIs and never writes directly to
Roastery evidence docs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence, TextIO


DEFAULT_MAX_PREVIEW_CHARS = 400


class ReportError(Exception):
    """Raised when a report cannot be generated safely."""


@dataclass(frozen=True)
class BeanResult:
    bean: str
    status: str
    latency_seconds: float | None
    usage: Mapping[str, Any] | None
    error: str | None
    output_file: str | None
    preview: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "bean": self.bean,
            "status": self.status,
            "latency_seconds": self.latency_seconds,
            "usage": dict(self.usage) if self.usage else None,
            "tokens": format_usage(self.usage),
            "cost": format_cost(self.usage),
            "error": self.error,
            "output_file": self.output_file,
            "preview": self.preview,
        }


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    created_at: str
    output_dir: str
    order_file: str | None
    order_sha256: str | None
    manifest_path: str
    beans: tuple[BeanResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "output_dir": self.output_dir,
            "order_file": self.order_file,
            "order_sha256": self.order_sha256,
            "manifest_path": self.manifest_path,
            "beans": [bean.as_dict() for bean in self.beans],
        }


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--max-preview-chars must be an integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("--max-preview-chars must be greater than zero")
    return number


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a draft Roastery report from local Cup Test manifests.",
    )
    parser.add_argument("--run-dir", required=True, help="Run directory or parent directory.")
    parser.add_argument("--output", default=None, help="Optional output file for the draft report.")
    parser.add_argument(
        "--include-previews",
        action="store_true",
        help="Include capped local-output excerpts from successful output files.",
    )
    parser.add_argument(
        "--max-preview-chars",
        type=positive_int,
        default=DEFAULT_MAX_PREVIEW_CHARS,
        help=f"Maximum preview characters. Default: {DEFAULT_MAX_PREVIEW_CHARS}.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON summary instead of Markdown.",
    )
    return parser.parse_args(argv)


def generate_report(
    run_dir: str | Path,
    *,
    include_previews: bool = False,
    max_preview_chars: int = DEFAULT_MAX_PREVIEW_CHARS,
) -> tuple[str, list[RunSummary]]:
    runs = load_runs(
        run_dir,
        include_previews=include_previews,
        max_preview_chars=max_preview_chars,
    )
    generated_at = timestamp()
    markdown = render_markdown_report(runs, generated_at, include_previews)
    return markdown, runs


def load_runs(
    run_dir: str | Path,
    *,
    include_previews: bool = False,
    max_preview_chars: int = DEFAULT_MAX_PREVIEW_CHARS,
) -> list[RunSummary]:
    root = validate_run_dir(run_dir)
    manifests = discover_manifests(root)
    return [
        load_run_summary(
            manifest,
            include_previews=include_previews,
            max_preview_chars=max_preview_chars,
        )
        for manifest in manifests
    ]


def validate_run_dir(run_dir: str | Path) -> Path:
    path = Path(run_dir).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ReportError(f"Run directory does not exist: {path}") from exc

    if not resolved.is_dir():
        raise ReportError(f"Run path is not a directory: {resolved}")
    if resolved.is_symlink():
        raise ReportError(f"Refusing symlinked run directory: {resolved}")
    return resolved


def discover_manifests(root: Path) -> list[Path]:
    manifest = root / "manifest.json"
    if manifest.is_file():
        return [manifest]

    child_dirs = sorted(
        child for child in root.iterdir()
        if child.is_dir() and not child.is_symlink()
    )
    if not child_dirs:
        raise ReportError(f"Manifest not found: {manifest}")

    manifests: list[Path] = []
    for child in child_dirs:
        child_manifest = child / "manifest.json"
        if not child_manifest.is_file():
            raise ReportError(f"Child run directory is missing manifest: {child}")
        manifests.append(child_manifest)
    return manifests


def load_run_summary(
    manifest_path: Path,
    *,
    include_previews: bool,
    max_preview_chars: int,
) -> RunSummary:
    manifest = load_manifest(manifest_path)
    run_dir = manifest_path.parent.resolve()

    beans = tuple(
        parse_bean_result(
            item,
            run_dir,
            include_previews=include_previews,
            max_preview_chars=max_preview_chars,
        )
        for item in manifest.get("beans", [])
    )
    if not beans:
        raise ReportError(f"Manifest has no Bean results: {manifest_path}")

    return RunSummary(
        run_id=str(manifest.get("run_id") or manifest_path.parent.name),
        created_at=str(manifest.get("created_at") or "unknown"),
        output_dir=str(manifest.get("output_dir") or run_dir),
        order_file=string_or_none(manifest.get("order_file")),
        order_sha256=string_or_none(manifest.get("order_sha256")),
        manifest_path=str(manifest_path),
        beans=beans,
    )


def load_manifest(manifest_path: Path) -> Mapping[str, Any]:
    if manifest_path.is_symlink():
        raise ReportError(f"Refusing symlinked manifest: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportError(f"Invalid manifest JSON: {manifest_path}") from exc
    except OSError as exc:
        raise ReportError(f"Could not read manifest: {manifest_path}") from exc
    if not isinstance(data, dict):
        raise ReportError(f"Manifest root must be a JSON object: {manifest_path}")
    return data


def parse_bean_result(
    data: Mapping[str, Any],
    run_dir: Path,
    *,
    include_previews: bool,
    max_preview_chars: int,
) -> BeanResult:
    usage = data.get("usage")
    if usage is not None and not isinstance(usage, dict):
        usage = None

    output_file = string_or_none(data.get("output_file"))
    preview = None
    if include_previews and output_file:
        preview = read_preview(output_file, run_dir, max_preview_chars)

    return BeanResult(
        bean=str(data.get("bean") or data.get("model") or "unknown"),
        status=str(data.get("status") or "unknown"),
        latency_seconds=number_or_none(data.get("latency_seconds")),
        usage=usage,
        error=string_or_none(data.get("error")),
        output_file=output_file,
        preview=preview,
    )


def read_preview(output_file: str, run_dir: Path, max_chars: int) -> str:
    path = resolve_output_file(output_file, run_dir)
    if path is None:
        return "[preview unavailable: output file is missing or outside the run directory]"

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "[preview unavailable: output file is not UTF-8 text]"
    except OSError:
        return "[preview unavailable: output file could not be read]"

    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return f"{compact[: max_chars - 3]}..."


def resolve_output_file(output_file: str, run_dir: Path) -> Path | None:
    raw = Path(output_file)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend(
            [
                Path.cwd() / raw,
                run_dir / raw,
                run_dir / raw.name,
            ]
        )

    run_root = run_dir.resolve()
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            continue
        if not resolved.is_file() or resolved.is_symlink():
            continue
        if is_within(resolved, run_root):
            return resolved
    return None


def render_markdown_report(
    runs: Sequence[RunSummary],
    generated_at: str,
    include_previews: bool,
) -> str:
    lines = [
        "# Roastery Report Draft",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a draft for human review. Do not treat it as final scored evidence until outputs are reviewed.",
        "",
        "## Run Summary",
        "",
        markdown_table(
            ["Run ID", "Created At", "Order File", "Output Dir", "OK", "Errors"],
            [
                [
                    run.run_id,
                    run.created_at,
                    run.order_file or "unknown",
                    run.output_dir,
                    str(count_status(run, "ok")),
                    str(count_errors(run)),
                ]
                for run in runs
            ],
        ),
        "",
        "## Per-Bean Results",
        "",
    ]

    for run in runs:
        lines.extend(
            [
                f"### Run: {run.run_id}",
                "",
                markdown_table(
                    ["Bean", "Status", "Latency", "Tokens", "Cost", "Output File", "Error"],
                    [
                        [
                            bean.bean,
                            bean.status,
                            format_latency(bean.latency_seconds),
                            format_usage(bean.usage),
                            format_cost(bean.usage),
                            bean.output_file or "",
                            bean.error or "",
                        ]
                        for bean in run.beans
                    ],
                ),
                "",
            ]
        )

    lines.extend(render_error_summary(runs))
    lines.extend(render_token_latency_summary(runs))
    lines.extend(render_local_output_notes(runs, include_previews))
    lines.extend(render_scoring_todo(runs))
    lines.extend(
        [
            "## Reminder",
            "",
            "Raw outputs are local-only and should not be committed. Review full local outputs before assigning quality scores.",
            "",
        ]
    )
    return "\n".join(lines)


def render_error_summary(runs: Sequence[RunSummary]) -> list[str]:
    lines = ["## Error Summary", ""]
    errors = [
        (run.run_id, bean.bean, bean.error)
        for run in runs
        for bean in run.beans
        if bean.error
    ]
    if not errors:
        lines.extend(["No Bean errors recorded in the manifest data.", ""])
        return lines

    lines.append(markdown_table(["Run ID", "Bean", "Error"], errors))
    lines.append("")
    return lines


def render_token_latency_summary(runs: Sequence[RunSummary]) -> list[str]:
    lines = ["## Token And Latency Summary", ""]
    rows = []
    for run in runs:
        known_tokens = [
            total_tokens(bean.usage)
            for bean in run.beans
            if total_tokens(bean.usage) is not None
        ]
        known_latencies = [
            bean.latency_seconds
            for bean in run.beans
            if bean.latency_seconds is not None
        ]
        rows.append(
            [
                run.run_id,
                str(sum(known_tokens)) if known_tokens else "unknown",
                format_latency(min(known_latencies)) if known_latencies else "unknown",
                format_latency(max(known_latencies)) if known_latencies else "unknown",
            ]
        )
    lines.append(markdown_table(["Run ID", "Known Total Tokens", "Fastest", "Slowest"], rows))
    lines.append("")
    return lines


def render_local_output_notes(runs: Sequence[RunSummary], include_previews: bool) -> list[str]:
    lines = ["## Local Output Notes", ""]
    lines.append("Successful output files are local artifacts. Keep them out of commits.")
    lines.append("")
    if not include_previews:
        lines.append("Previews omitted by default. Re-run with `--include-previews` for capped local-output excerpts.")
        lines.append("")
        return lines

    lines.append("Preview excerpts below are capped local-output excerpts, not full raw outputs.")
    lines.append("")
    for run in runs:
        lines.append(f"### Local-output excerpts: {run.run_id}")
        lines.append("")
        for bean in run.beans:
            if bean.preview is None:
                continue
            lines.extend(
                [
                    f"#### {bean.bean}",
                    "",
                    bean.preview,
                    "",
                ]
            )
    return lines


def render_scoring_todo(runs: Sequence[RunSummary]) -> list[str]:
    lines = ["## Human Scoring TODO", ""]
    rows = []
    for run in runs:
        for bean in run.beans:
            rows.append(
                [
                    run.run_id,
                    bean.bean,
                    "yes/no",
                    "TODO",
                    "TODO",
                    "TODO",
                    "TODO",
                    "yes/no",
                ]
            )
    lines.append(
        markdown_table(
            [
                "Run ID",
                "Bean",
                "Full Output Reviewed?",
                "Quality Score",
                "Strengths",
                "Weaknesses",
                "Human Fixes Needed",
                "Use Again?",
            ],
            rows,
        )
    )
    lines.append("")
    return lines


def render_json_summary(runs: Sequence[RunSummary], generated_at: str) -> str:
    payload = {
        "generated_at": generated_at,
        "run_count": len(runs),
        "runs": [run.as_dict() for run in runs],
    }
    return json.dumps(payload, indent=2)


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(escape_table_cell(value) for value in row) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def escape_table_cell(value: Any) -> str:
    text = str(value)
    return text.replace("\n", " ").replace("|", "\\|")


def format_latency(latency_seconds: float | None) -> str:
    if latency_seconds is None:
        return "unknown"
    return f"{latency_seconds:.2f}s"


def format_usage(usage: Mapping[str, Any] | None) -> str:
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


def format_cost(usage: Mapping[str, Any] | None) -> str:
    if not usage or "cost" not in usage:
        return "unknown"
    return f"{usage.get('cost')} reported"


def total_tokens(usage: Mapping[str, Any] | None) -> int | None:
    if not usage:
        return None
    total = usage.get("total_tokens")
    return total if isinstance(total, int) else None


def count_status(run: RunSummary, status: str) -> int:
    return sum(1 for bean in run.beans if bean.status == status)


def count_errors(run: RunSummary) -> int:
    return sum(1 for bean in run.beans if bean.error)


def number_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except ValueError:
        return False
    return True


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_forbidden_output_path(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    return len(parts) >= 2 and parts[-2:] == ["roastery", "tasting_notes.md"]


def write_output(path: str | Path, content: str) -> None:
    output_path = Path(path).expanduser()
    if is_forbidden_output_path(output_path):
        raise ReportError("Refusing to write directly to roastery/tasting_notes.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    args = parse_args(argv)

    try:
        runs = load_runs(
            args.run_dir,
            include_previews=args.include_previews,
            max_preview_chars=args.max_preview_chars,
        )
        generated_at = timestamp()
        if args.json:
            report = render_json_summary(runs, generated_at)
        else:
            report = render_markdown_report(runs, generated_at, args.include_previews)

        if args.output:
            write_output(args.output, report)
        else:
            print(report, file=output)
    except ReportError as exc:
        print(f"Error: {exc}", file=errors)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
