"""Local Project Coffee dashboard CLI.

The dashboard reports known Project Coffee file health and current operating
status. It checks only known safe paths and never calls models, APIs, Git, or
credential-dependent tools.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence, TextIO


SUPPORTED_SECTIONS = (
    "overview",
    "brew-log",
    "docs",
    "tools",
    "roastery",
    "ledger",
    "house-blend",
    "all",
)

CORE_FILES = (
    "AGENTS.md",
    "PROJECT_COFFEE.md",
    "brew-log/active_context.md",
    "brew-log/progress.md",
    "config/house_blend.md",
    "roastery/tasting_notes.md",
    "ledger/cost_log.md",
    "docs/README.md",
)

TOOL_FILES = (
    "tools/install_project_coffee_template.py",
    "tools/pantry_search.py",
    "tools/roastery_report.py",
    "roastery/run_cup_test.py",
)

GUIDE_FILES = (
    "docs/guides/project-coffee-operating-manual.md",
    "docs/guides/project-coffee-setup-guide.md",
    "docs/guides/new-project-onboarding-guide.md",
    "docs/guides/template-pack-guide.md",
    "docs/guides/barista-handbook.md",
    "docs/guides/roastery-and-ledger-guide.md",
    "docs/guides/model-routing-and-house-blend-guide.md",
    "docs/guides/pantry-search-guide.md",
    "docs/guides/pantry-intake-guide.md",
    "docs/guides/roastery-report-guide.md",
)

SAFE_READ_FILES = {
    "brew-log/active_context.md",
    "brew-log/progress.md",
    "config/house_blend.md",
}


class DashboardError(Exception):
    """Raised when the dashboard cannot run safely."""


@dataclass(frozen=True)
class FileCheck:
    path: str
    present: bool
    required: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "present": self.present,
            "required": self.required,
        }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show local Project Coffee dashboard health.",
    )
    parser.add_argument("--root", default=".", help="Project Coffee root. Default: current directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    parser.add_argument(
        "--section",
        choices=SUPPORTED_SECTIONS,
        default="all",
        help="Dashboard section to print. Default: all.",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit nonzero when required core files are missing.",
    )
    return parser.parse_args(argv)


def build_dashboard(
    root: str | Path,
    *,
    section: str = "all",
    fail_on_missing: bool = False,
) -> dict[str, Any]:
    root_path = validate_root(root)
    selected = selected_sections(section)

    core_checks = check_paths(root_path, CORE_FILES, required=True)
    tool_checks = check_paths(root_path, TOOL_FILES, required=False)
    guide_checks = check_paths(root_path, GUIDE_FILES, required=False)

    missing_core = [check.path for check in core_checks if not check.present]
    missing_expected = [
        check.path
        for check in (*tool_checks, *guide_checks)
        if not check.present
    ]

    warnings: list[str] = []
    if missing_core:
        warnings.append("Required core files are missing.")
    if missing_expected:
        warnings.append("Expected tool or guide files are missing.")

    status = compute_status(missing_core, missing_expected, fail_on_missing)
    context = read_context(root_path)

    sections: dict[str, Any] = {}
    if "overview" in selected:
        sections["overview"] = {
            "status": "OK" if not missing_core else "WARN",
            "current_milestone": context.get("current_milestone"),
            "active_shot": context.get("active_shot"),
            "next_action": context.get("next_action"),
        }
    if "brew-log" in selected:
        sections["brew-log"] = brew_log_section(root_path)
    if "docs" in selected:
        sections["docs"] = {
            "status": "OK" if all(check.present for check in guide_checks) else "WARN",
            "files": [check.as_dict() for check in guide_checks],
        }
    if "tools" in selected:
        sections["tools"] = {
            "status": "OK" if all(check.present for check in tool_checks) else "WARN",
            "files": [check.as_dict() for check in tool_checks],
        }
    if "roastery" in selected:
        sections["roastery"] = roastery_section(root_path)
    if "ledger" in selected:
        sections["ledger"] = ledger_section(root_path)
    if "house-blend" in selected:
        sections["house-blend"] = house_blend_section(root_path)

    return {
        "root": str(root_path),
        "generated_at": timestamp(),
        "status": status,
        "sections": sections,
        "missing": {
            "core": missing_core,
            "expected": missing_expected,
        },
        "warnings": warnings,
    }


def validate_root(root: str | Path) -> Path:
    path = Path(root).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise DashboardError(f"Root does not exist: {path}") from exc
    if not resolved.is_dir():
        raise DashboardError(f"Root is not a directory: {resolved}")
    return resolved


def selected_sections(section: str) -> tuple[str, ...]:
    if section == "all":
        return (
            "overview",
            "brew-log",
            "docs",
            "tools",
            "roastery",
            "ledger",
            "house-blend",
        )
    return (section,)


def check_paths(root: Path, paths: Sequence[str], *, required: bool) -> tuple[FileCheck, ...]:
    return tuple(
        FileCheck(path=relative_path, present=(root / relative_path).is_file(), required=required)
        for relative_path in paths
    )


def compute_status(
    missing_core: Sequence[str],
    missing_expected: Sequence[str],
    fail_on_missing: bool,
) -> str:
    if missing_core and fail_on_missing:
        return "INCOMPLETE"
    if missing_core or missing_expected:
        return "WARN"
    return "OK"


def read_context(root: Path) -> dict[str, str | None]:
    active_context = safe_read_known_file(root, "brew-log/active_context.md")
    progress = safe_read_known_file(root, "brew-log/progress.md")
    return {
        "current_milestone": extract_section_value(active_context, "Current milestone"),
        "active_shot": extract_active_shot(progress),
        "next_action": extract_next_action(active_context),
    }


def brew_log_section(root: Path) -> dict[str, Any]:
    files = check_paths(
        root,
        ("brew-log/active_context.md", "brew-log/progress.md"),
        required=True,
    )
    return {
        "status": "OK" if all(check.present for check in files) else "WARN",
        "files": [check.as_dict() for check in files],
    }


def roastery_section(root: Path) -> dict[str, Any]:
    paths = (
        "roastery/tasting_notes.md",
        "roastery/run_cup_test.py",
        "roastery/cup_tests/README.md",
    )
    files = check_paths(root, paths, required=False)
    return {
        "status": "OK" if (root / "roastery/tasting_notes.md").is_file() else "WARN",
        "files": [check.as_dict() for check in files],
        "local_outputs": "not inspected",
        "local_reports": "not inspected",
    }


def ledger_section(root: Path) -> dict[str, Any]:
    files = check_paths(root, ("ledger/cost_log.md",), required=True)
    return {
        "status": "OK" if files[0].present else "WARN",
        "files": [check.as_dict() for check in files],
    }


def house_blend_section(root: Path) -> dict[str, Any]:
    path = root / "config/house_blend.md"
    summary = []
    if path.is_file():
        text = safe_read_known_file(root, "config/house_blend.md")
        summary = extract_house_blend_rows(text)
    return {
        "status": "OK" if path.is_file() else "WARN",
        "file": "config/house_blend.md",
        "present": path.is_file(),
        "summary": summary,
    }


def safe_read_known_file(root: Path, relative_path: str) -> str:
    if relative_path not in SAFE_READ_FILES:
        return ""
    path = root / relative_path
    if not path.is_file() or path.is_symlink():
        return ""
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except ValueError:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def extract_section_value(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    target = f"## {heading}".lower()
    for index, line in enumerate(lines):
        if line.strip().lower() != target:
            continue
        for value in lines[index + 1:]:
            stripped = value.strip()
            if not stripped:
                continue
            if stripped.startswith("## "):
                return None
            return stripped
    return None


def extract_next_action(text: str) -> str | None:
    section = extract_section_lines(text, "Next actions")
    for line in section:
        stripped = line.strip()
        if not stripped:
            continue
        return re.sub(r"^\d+\.\s*", "", stripped)
    return None


def extract_active_shot(text: str) -> str | None:
    value = extract_section_value(text, "Current shot")
    if not value:
        return None
    value = re.sub(r"^Current status:\s*", "", value)
    value = re.sub(r"\s+Next active work:.*$", "", value)
    return value


def extract_section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    target = f"## {heading}".lower()
    for index, line in enumerate(lines):
        if line.strip().lower() != target:
            continue
        result: list[str] = []
        for value in lines[index + 1:]:
            if value.strip().startswith("## "):
                break
            result.append(value)
        return result
    return []


def extract_house_blend_rows(text: str) -> list[str]:
    rows = []
    in_current_blend = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if stripped.lower() == "## current blend":
                in_current_blend = True
                continue
            if in_current_blend:
                break
        if not in_current_blend:
            continue
        if not stripped.startswith("|"):
            continue
        if stripped.startswith("| Route ") or stripped.startswith("| ---"):
            continue
        rows.append(stripped)
    return rows[:4]


def render_human_dashboard(dashboard: Mapping[str, Any]) -> str:
    lines = [
        "Project Coffee Dashboard",
        f"Root: {dashboard['root']}",
        f"Generated: {dashboard['generated_at']}",
        f"Status: {dashboard['status']}",
        "",
    ]

    sections = dashboard["sections"]
    overview = sections.get("overview")
    if overview:
        lines.extend(
            [
                "## Overview",
                f"Current milestone: {overview.get('current_milestone') or 'unknown'}",
                f"Active shot: {overview.get('active_shot') or 'unknown'}",
                f"Next action: {overview.get('next_action') or 'unknown'}",
                "",
            ]
        )

    for name, title in (
        ("brew-log", "Brew Log"),
        ("docs", "Docs"),
        ("tools", "Tools"),
        ("roastery", "Roastery"),
        ("ledger", "Ledger"),
        ("house-blend", "House Blend"),
    ):
        section = sections.get(name)
        if not section:
            continue
        lines.extend(render_section(title, section))

    missing = dashboard["missing"]
    lines.append("## Missing")
    if missing["core"]:
        lines.append("Required core files:")
        lines.extend(f"- {path}" for path in missing["core"])
    if missing["expected"]:
        lines.append("Expected tool/guide files:")
        lines.extend(f"- {path}" for path in missing["expected"])
    if not missing["core"] and not missing["expected"]:
        lines.append("None")
    lines.append("")

    lines.append("## Warnings")
    warnings = dashboard["warnings"]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("None")
    lines.append("")
    return "\n".join(lines)


def render_section(title: str, section: Mapping[str, Any]) -> list[str]:
    lines = [f"## {title}", f"Status: {section.get('status', 'unknown')}"]

    files = section.get("files")
    if files:
        for item in files:
            marker = "OK" if item["present"] else "MISSING"
            lines.append(f"- {marker}: {item['path']}")

    if title == "House Blend":
        if section.get("present"):
            lines.append("- OK: config/house_blend.md")
        else:
            lines.append("- MISSING: config/house_blend.md")
        summary = section.get("summary") or []
        if summary:
            lines.append("Summary:")
            lines.extend(f"- {row}" for row in summary)

    if title == "Roastery":
        lines.append(f"- Local outputs: {section.get('local_outputs')}")
        lines.append(f"- Local reports: {section.get('local_reports')}")

    lines.append("")
    return lines


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        dashboard = build_dashboard(
            args.root,
            section=args.section,
            fail_on_missing=args.fail_on_missing,
        )
    except DashboardError as exc:
        print(f"Error: {exc}", file=errors)
        return 1

    if args.json:
        print(json.dumps(dashboard, indent=2), file=output)
    else:
        print(render_human_dashboard(dashboard), file=output)

    if dashboard["status"] == "INCOMPLETE":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
