"""Read-only Project Coffee repository health doctor.

Coffee Doctor diagnoses common Project Coffee health issues and suggests safe
next actions. It checks only known safe paths and never modifies files, calls
models, calls external APIs, or inspects raw local output folders.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence, TextIO


SUPPORTED_SECTIONS = (
    "core",
    "docs",
    "tools",
    "roastery",
    "ledger",
    "pantry",
    "templates",
    "ignored-paths",
    "all",
)

SEVERITIES = ("OK", "INFO", "WARN", "FAIL")

CORE_FILES = (
    "AGENTS.md",
    "PROJECT_COFFEE.md",
    "brew-log/active_context.md",
    "brew-log/progress.md",
)

GUIDE_FILES = (
    "docs/guides/project-coffee-operating-manual.md",
    "docs/guides/project-coffee-setup-guide.md",
    "docs/guides/new-project-onboarding-guide.md",
    "docs/guides/template-pack-guide.md",
    "docs/guides/template-installer-guide.md",
    "docs/guides/pantry-search-guide.md",
    "docs/guides/pantry-intake-guide.md",
    "docs/guides/barista-handbook.md",
    "docs/guides/roastery-and-ledger-guide.md",
    "docs/guides/roastery-report-guide.md",
    "docs/guides/coffee-dashboard-guide.md",
    "docs/guides/coffee-doctor-guide.md",
    "docs/guides/model-routing-and-house-blend-guide.md",
)

TOOL_FILES = (
    "tools/install_project_coffee_template.py",
    "tools/pantry_search.py",
    "tools/roastery_report.py",
    "tools/coffee_dashboard.py",
    "roastery/run_cup_test.py",
)

ROASTERY_FILES = (
    "roastery/tasting_notes.md",
    "roastery/cup_tests/README.md",
)

TEMPLATE_FILES = (
    "TEMPLATES/project-coffee/README.md",
    "TEMPLATES/project-coffee/knowledge/00_index.md",
)

IGNORE_FILES = (
    ".gitignore",
    ".cursorignore",
    ".cursorindexingignore",
)

LOCAL_ARTIFACT_PATHS = (
    "roastery/local_cup_outputs",
    "roastery/local_reports",
)

SENSITIVE_PARTS = {
    ".env",
    ".git",
    ".ssh",
    ".aws",
    "secret",
    "secrets",
    "credential",
    "credentials",
    "token",
    "tokens",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "local_cup_outputs",
    "local_reports",
}

POLICY_MARKERS = (
    "git grep --cached",
    "-I -E",
)


class DoctorError(Exception):
    """Raised when Coffee Doctor cannot run safely."""


@dataclass(frozen=True)
class Finding:
    section: str
    severity: str
    code: str
    message: str
    suggestion: str
    path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "section": self.section,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
        }
        if self.path is not None:
            payload["path"] = self.path
        return payload


GitLsFilesFunc = Callable[[Path, Sequence[str]], list[str] | None]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose local Project Coffee repository health.",
    )
    parser.add_argument("--root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    parser.add_argument(
        "--section",
        choices=SUPPORTED_SECTIONS,
        default="all",
        help="Doctor section to run. Default: all.",
    )
    parser.add_argument(
        "--fail-on-issue",
        action="store_true",
        help="Exit nonzero when FAIL findings are present.",
    )
    return parser.parse_args(argv)


def build_doctor_report(
    root: str | Path,
    *,
    section: str = "all",
    git_ls_files_func: GitLsFilesFunc | None = None,
) -> dict[str, Any]:
    root_path = validate_root(root)
    selected = selected_sections(section)
    git_func = git_ls_files_func or git_ls_files

    findings: list[Finding] = []
    for selected_section in selected:
        if selected_section == "core":
            findings.extend(check_core(root_path))
        elif selected_section == "docs":
            findings.extend(check_docs(root_path))
        elif selected_section == "tools":
            findings.extend(check_tools(root_path))
        elif selected_section == "roastery":
            findings.extend(check_roastery(root_path, git_func))
        elif selected_section == "ledger":
            findings.extend(check_ledger(root_path))
        elif selected_section == "pantry":
            findings.extend(check_pantry(root_path))
        elif selected_section == "templates":
            findings.extend(check_templates(root_path))
        elif selected_section == "ignored-paths":
            findings.extend(check_ignored_paths(root_path))

    summary = summarize(findings)
    return {
        "root": str(root_path),
        "generated_at": timestamp(),
        "status": overall_status(summary),
        "findings": [finding.as_dict() for finding in findings],
        "summary": summary,
    }


def validate_root(root: str | Path) -> Path:
    path = Path(root).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise DoctorError(f"Root does not exist: {path}") from exc
    if not resolved.is_dir():
        raise DoctorError(f"Root is not a directory: {resolved}")
    return resolved


def selected_sections(section: str) -> tuple[str, ...]:
    if section == "all":
        return (
            "core",
            "docs",
            "tools",
            "roastery",
            "ledger",
            "pantry",
            "templates",
            "ignored-paths",
        )
    return (section,)


def check_core(root: Path) -> list[Finding]:
    return [
        file_finding(
            root,
            relative_path,
            section="core",
            missing_severity="FAIL",
            ok_message=f"{relative_path} is present.",
            missing_message=f"{relative_path} is missing.",
            suggestion=f"Restore {relative_path} from Project Coffee policy or template before continuing.",
        )
        for relative_path in CORE_FILES
    ]


def check_docs(root: Path) -> list[Finding]:
    findings = [
        file_finding(
            root,
            "docs/README.md",
            section="docs",
            missing_severity="FAIL",
            ok_message="Docs index is present.",
            missing_message="Docs index is missing.",
            suggestion="Restore docs/README.md so guides are discoverable.",
        )
    ]
    for relative_path in GUIDE_FILES:
        findings.append(
            file_finding(
                root,
                relative_path,
                section="docs",
                missing_severity="WARN",
                ok_message=f"{relative_path} is present.",
                missing_message=f"{relative_path} is missing.",
                suggestion=f"Add or restore {relative_path} when working on productized docs.",
            )
        )
    findings.extend(check_policy_markers(root))
    return findings


def check_policy_markers(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    docs_root = root / "docs"
    if not docs_root.is_dir():
        return findings
    for path in sorted(docs_root.rglob("*.md")):
        if not is_safe_read_path(root, path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            findings.append(
                Finding(
                    section="docs",
                    severity="WARN",
                    code="docs-unreadable",
                    message=f"Could not read {relative_display(root, path)} for policy marker check.",
                    path=relative_display(root, path),
                    suggestion="Review the file manually if it should be part of Project Coffee docs.",
                )
            )
            continue
        if all(marker in text for marker in POLICY_MARKERS):
            relative_path = relative_display(root, path)
            findings.append(
                Finding(
                    section="docs",
                    severity="WARN",
                    code="literal-secret-check-command",
                    message=f"{relative_path} appears to include the literal staged secret-check command.",
                    path=relative_path,
                    suggestion="Refer to the staged secret-pattern check from Project Coffee policy by name instead of embedding the command.",
                )
            )
    return findings


def check_tools(root: Path) -> list[Finding]:
    return [
        file_finding(
            root,
            relative_path,
            section="tools",
            missing_severity="FAIL",
            ok_message=f"{relative_path} is present.",
            missing_message=f"{relative_path} is missing.",
            suggestion=f"Restore {relative_path} before relying on Project Coffee local tooling.",
        )
        for relative_path in TOOL_FILES
    ]


def check_roastery(root: Path, git_ls_files_func: GitLsFilesFunc) -> list[Finding]:
    findings = [
        file_finding(
            root,
            "roastery/tasting_notes.md",
            section="roastery",
            missing_severity="FAIL",
            ok_message="Roastery tasting notes are present.",
            missing_message="Roastery tasting notes are missing.",
            suggestion="Restore roastery/tasting_notes.md before recording model or workflow evidence.",
        ),
        file_finding(
            root,
            "roastery/cup_tests/README.md",
            section="roastery",
            missing_severity="WARN",
            ok_message="Cup Test README is present.",
            missing_message="Cup Test README is missing.",
            suggestion="Restore roastery/cup_tests/README.md so benchmark Orders are discoverable.",
        ),
    ]

    tracked = git_ls_files_func(root, LOCAL_ARTIFACT_PATHS)
    if tracked:
        for relative_path in tracked:
            findings.append(
                Finding(
                    section="roastery",
                    severity="FAIL",
                    code="local-artifact-tracked",
                    message=f"Local Roastery artifact is tracked by Git: {relative_path}",
                    path=relative_path,
                    suggestion="Untrack local raw outputs or reports; keep only summarized evidence in tracked docs.",
                )
            )
    elif tracked is None:
        findings.append(
            Finding(
                section="roastery",
                severity="INFO",
                code="git-check-skipped",
                message="Git tracking check for local Roastery artifacts could not be completed.",
                suggestion="Run `git ls-files -- roastery/local_cup_outputs roastery/local_reports` manually if needed.",
            )
        )
    else:
        for relative_path in LOCAL_ARTIFACT_PATHS:
            path = root / relative_path
            if path.exists():
                findings.append(
                    Finding(
                        section="roastery",
                        severity="OK",
                        code="local-artifact-untracked",
                        message=f"{relative_path} exists and no tracked files were reported.",
                        path=relative_path,
                        suggestion="Keep the local artifact path ignored and do not commit raw outputs.",
                    )
                )
            else:
                findings.append(
                    Finding(
                        section="roastery",
                        severity="INFO",
                        code="local-artifact-absent",
                        message=f"{relative_path} is not present.",
                        path=relative_path,
                        suggestion="No action needed unless a captured local run creates this path.",
                    )
                )
    return findings


def check_ledger(root: Path) -> list[Finding]:
    return [
        file_finding(
            root,
            "ledger/cost_log.md",
            section="ledger",
            missing_severity="FAIL",
            ok_message="Ledger cost log is present.",
            missing_message="Ledger cost log is missing.",
            suggestion="Restore ledger/cost_log.md before recording cost or token evidence.",
        )
    ]


def check_pantry(root: Path) -> list[Finding]:
    onboarded = (root / "AGENTS.md").is_file() and (root / "PROJECT_COFFEE.md").is_file()
    if not onboarded:
        return [
            Finding(
                section="pantry",
                severity="INFO",
                code="pantry-not-required",
                message="Project Coffee onboarding markers were not both present; Pantry index check skipped.",
                suggestion="Add onboarding files first, then create knowledge/00_index.md.",
            )
        ]
    return [
        file_finding(
            root,
            "knowledge/00_index.md",
            section="pantry",
            missing_severity="WARN",
            ok_message="Pantry index is present.",
            missing_message="Pantry index is missing for an onboarded project.",
            suggestion="Add knowledge/00_index.md so local knowledge can be searched and maintained.",
        )
    ]


def check_templates(root: Path) -> list[Finding]:
    findings = [
        directory_finding(
            root,
            "TEMPLATES/project-coffee",
            section="templates",
            missing_severity="WARN",
            ok_message="Project Coffee template pack directory is present.",
            missing_message="Project Coffee template pack directory is missing.",
            suggestion="Restore TEMPLATES/project-coffee before onboarding more projects from templates.",
        )
    ]
    for relative_path in TEMPLATE_FILES:
        findings.append(
            file_finding(
                root,
                relative_path,
                section="templates",
                missing_severity="WARN",
                ok_message=f"{relative_path} is present.",
                missing_message=f"{relative_path} is missing.",
                suggestion=f"Restore {relative_path} so the template pack remains useful.",
            )
        )
    return findings


def check_ignored_paths(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for ignore_file in IGNORE_FILES:
        path = root / ignore_file
        if not path.is_file():
            findings.append(
                Finding(
                    section="ignored-paths",
                    severity="FAIL",
                    code="ignore-file-missing",
                    message=f"{ignore_file} is missing.",
                    path=ignore_file,
                    suggestion=f"Restore {ignore_file} before generating local outputs.",
                )
            )
            continue
        text = safe_read_text(root, ignore_file)
        for local_path in LOCAL_ARTIFACT_PATHS:
            pattern = f"{local_path}/"
            if pattern in text or local_path in text:
                findings.append(
                    Finding(
                        section="ignored-paths",
                        severity="OK",
                        code="ignore-pattern-present",
                        message=f"{ignore_file} ignores {local_path}.",
                        path=ignore_file,
                        suggestion="No action needed.",
                    )
                )
            else:
                findings.append(
                    Finding(
                        section="ignored-paths",
                        severity="FAIL",
                        code="ignore-pattern-missing",
                        message=f"{ignore_file} does not ignore {local_path}.",
                        path=ignore_file,
                        suggestion=f"Add {pattern} to {ignore_file} before generating local outputs.",
                    )
                )
    return findings


def file_finding(
    root: Path,
    relative_path: str,
    *,
    section: str,
    missing_severity: str,
    ok_message: str,
    missing_message: str,
    suggestion: str,
) -> Finding:
    path = root / relative_path
    if path.is_file() and not path.is_symlink():
        return Finding(section, "OK", "file-present", ok_message, "No action needed.", relative_path)
    return Finding(section, missing_severity, "file-missing", missing_message, suggestion, relative_path)


def directory_finding(
    root: Path,
    relative_path: str,
    *,
    section: str,
    missing_severity: str,
    ok_message: str,
    missing_message: str,
    suggestion: str,
) -> Finding:
    path = root / relative_path
    if path.is_dir() and not path.is_symlink():
        return Finding(section, "OK", "directory-present", ok_message, "No action needed.", relative_path)
    return Finding(section, missing_severity, "directory-missing", missing_message, suggestion, relative_path)


def safe_read_text(root: Path, relative_path: str) -> str:
    path = root / relative_path
    if not is_safe_read_path(root, path):
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def is_safe_read_path(root: Path, path: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        resolved_root = root.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
        resolved_path.relative_to(resolved_root)
    except (FileNotFoundError, ValueError):
        return False
    relative_parts = resolved_path.relative_to(resolved_root).parts
    return not any(part.lower() in SENSITIVE_PARTS for part in relative_parts)


def git_ls_files(root: Path, relative_paths: Sequence[str]) -> list[str] | None:
    command = ["git", "ls-files", "--", *relative_paths]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return [line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()]


def relative_display(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=True).relative_to(root.resolve(strict=True)).as_posix()
    except (FileNotFoundError, ValueError):
        return str(path)


def summarize(findings: Sequence[Finding]) -> dict[str, int]:
    summary = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        summary[finding.severity] += 1
    return summary


def overall_status(summary: Mapping[str, int]) -> str:
    if summary.get("FAIL", 0):
        return "FAIL"
    if summary.get("WARN", 0):
        return "WARN"
    return "OK"


def render_human_report(report: Mapping[str, Any]) -> str:
    lines = [
        "Project Coffee Doctor",
        f"Root: {report['root']}",
        f"Generated: {report['generated_at']}",
        f"Status: {report['status']}",
        "",
        "## Summary",
    ]
    summary = report["summary"]
    for severity in SEVERITIES:
        lines.append(f"- {severity}: {summary.get(severity, 0)}")
    lines.extend(["", "## Findings"])

    findings = report["findings"]
    if not findings:
        lines.append("No findings.")
    else:
        for index, finding in enumerate(findings, start=1):
            path = f" [{finding['path']}]" if "path" in finding else ""
            lines.append(f"{index}. {finding['severity']} {finding['section']} {finding['code']}{path}")
            lines.append(f"   Finding: {finding['message']}")
            lines.append(f"   Suggested safe next action: {finding['suggestion']}")
    lines.append("")
    return "\n".join(lines)


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
        report = build_doctor_report(args.root, section=args.section)
    except DoctorError as exc:
        print(f"Error: {exc}", file=errors)
        return 1

    if args.json:
        print(json.dumps(report, indent=2), file=output)
    else:
        print(render_human_report(report), file=output)

    if args.fail_on_issue and report["summary"].get("FAIL", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
