"""Read-only Project Coffee fleet registry status tool.

Fleet Status reads a local JSON registry of onboarded projects and can run safe
file-existence checks for Project Coffee onboarding markers. It does not scan
repositories, run Git, call models, call external APIs, or inspect secrets/raw
local outputs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence, TextIO


SEVERITIES = ("OK", "INFO", "WARN", "FAIL")

REQUIRED_PROJECT_FIELDS = ("id", "name", "path", "type", "status")

PROJECT_CHECK_FILES = (
    "AGENTS.md",
    "PROJECT_COFFEE.md",
    "brew-log/active_context.md",
    "brew-log/progress.md",
    "ledger/cost_log.md",
    "roastery/tasting_notes.md",
)

ONBOARDED_MARKERS = (
    "AGENTS.md",
    "PROJECT_COFFEE.md",
    "brew-log/active_context.md",
    "brew-log/progress.md",
)

KNOWLEDGE_INDEX = "knowledge/00_index.md"

UNSAFE_EXACT_PARTS = {
    ".env",
    ".git",
    ".ssh",
    ".aws",
    ".azure",
    ".gcp",
    ".config",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "local_cup_outputs",
    "local_reports",
}

UNSAFE_SUBSTRINGS = (
    "secret",
    "secrets",
    "credential",
    "credentials",
    "token",
    "tokens",
)


class FleetStatusError(Exception):
    """Raised when Fleet Status cannot run safely."""


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    suggestion: str
    project_id: str | None = None
    path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
        }
        if self.project_id is not None:
            payload["project_id"] = self.project_id
        if self.path is not None:
            payload["path"] = self.path
        return payload


@dataclass
class ProjectRecord:
    id: str
    name: str
    path: str
    type: str
    status: str
    notes: str | None
    resolved_path: Path
    check_status: str = "not-run"
    checks: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "resolved_path": str(self.resolved_path),
            "type": self.type,
            "status": self.status,
            "check_status": self.check_status,
        }
        if self.notes:
            payload["notes"] = self.notes
        if self.checks:
            payload["checks"] = self.checks
        return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect a local Project Coffee fleet registry.",
    )
    parser.add_argument("--root", default=".", help="Project Coffee root. Default: current directory.")
    parser.add_argument(
        "--registry",
        help="Registry JSON path. Default: fleet/projects.json under root.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    parser.add_argument("--list", action="store_true", help="List registered projects without checks.")
    parser.add_argument("--project", help="Filter to one project id.")
    parser.add_argument("--check", action="store_true", help="Run safe Project Coffee onboarding existence checks.")
    parser.add_argument(
        "--fail-on-issue",
        action="store_true",
        help="Exit nonzero when FAIL findings are present.",
    )
    return parser.parse_args(argv)


def build_fleet_report(
    root: str | Path,
    *,
    registry: str | Path | None = None,
    list_only: bool = False,
    project_id: str | None = None,
    check: bool = False,
) -> dict[str, Any]:
    root_path = validate_root(root)
    registry_path = resolve_registry_path(root_path, registry)

    findings: list[Finding] = []
    projects: list[ProjectRecord] = []
    registry_status = "missing"

    unsafe_registry_reason = unsafe_path_reason(registry_path)
    if unsafe_registry_reason:
        registry_status = "unsafe"
        findings.append(
            Finding(
                "FAIL",
                "unsafe-registry-path",
                f"Registry path is unsafe: {unsafe_registry_reason}",
                "Choose a registry path outside hidden credential, secret, dependency, or local-output folders.",
                path=display_path(root_path, registry_path),
            )
        )
    elif not registry_path.exists():
        findings.append(
            Finding(
                "INFO",
                "registry-missing",
                "Fleet registry is not present.",
                "Copy fleet/projects.example.json to fleet/projects.json and edit it locally when ready.",
                path=display_path(root_path, registry_path),
            )
        )
    else:
        registry_status = "loaded"
        loaded_projects, registry_findings = load_registry(root_path, registry_path)
        projects.extend(loaded_projects)
        findings.extend(registry_findings)

    if project_id and projects:
        matched = [project for project in projects if project.id == project_id]
        if not matched:
            findings.append(
                Finding(
                    "FAIL",
                    "project-not-found",
                    f"Project id is not registered: {project_id}",
                    "Run fleet-status --list to see registered project ids.",
                )
            )
            projects = []
        else:
            projects = matched

    if check and projects:
        for project in projects:
            findings.extend(check_project(root_path, project))

    summary = summarize(findings, len(projects))
    return {
        "root": str(root_path),
        "registry_path": str(registry_path),
        "generated_at": timestamp(),
        "status": overall_status(summary),
        "registry_status": registry_status,
        "projects": [project.as_dict() for project in projects],
        "findings": [finding.as_dict() for finding in findings],
        "summary": summary,
        "list_only": list_only,
        "check": bool(check),
    }


def validate_root(root: str | Path) -> Path:
    path = Path(root).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FleetStatusError(f"Root does not exist: {path}") from exc
    if not resolved.is_dir():
        raise FleetStatusError(f"Root is not a directory: {resolved}")
    reason = unsafe_path_reason(resolved)
    if reason:
        raise FleetStatusError(f"Root path is unsafe: {reason}")
    return resolved


def resolve_registry_path(root: Path, registry: str | Path | None) -> Path:
    candidate = Path(registry).expanduser() if registry is not None else root / "fleet" / "projects.json"
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve(strict=False)


def load_registry(root: Path, registry_path: Path) -> tuple[list[ProjectRecord], list[Finding]]:
    findings: list[Finding] = []
    projects: list[ProjectRecord] = []

    try:
        raw = registry_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return (
            [],
            [
                Finding(
                    "FAIL",
                    "invalid-json",
                    f"Registry JSON could not be parsed: {exc.msg} at line {exc.lineno}, column {exc.colno}.",
                    "Fix the JSON syntax before running fleet checks.",
                    path=display_path(root, registry_path),
                )
            ],
        )
    except OSError as exc:
        return (
            [],
            [
                Finding(
                    "FAIL",
                    "registry-read-failed",
                    f"Registry could not be read: {exc}",
                    "Check file permissions and use a safe local registry path.",
                    path=display_path(root, registry_path),
                )
            ],
        )

    if not isinstance(payload, Mapping):
        return (
            [],
            [
                Finding(
                    "FAIL",
                    "invalid-registry-format",
                    "Registry root must be a JSON object.",
                    "Use fleet/projects.example.json as the starting shape.",
                    path=display_path(root, registry_path),
                )
            ],
        )

    registry_projects = payload.get("projects")
    if not isinstance(registry_projects, list):
        findings.append(
            Finding(
                "FAIL",
                "invalid-projects-list",
                "Registry must contain a projects list.",
                "Use fleet/projects.example.json as the starting shape.",
                path=display_path(root, registry_path),
            )
        )
        return [], findings

    seen_ids: set[str] = set()
    for index, item in enumerate(registry_projects):
        if not isinstance(item, Mapping):
            findings.append(
                Finding(
                    "FAIL",
                    "invalid-project-entry",
                    f"Project entry at index {index} must be an object.",
                    "Replace the entry with an object containing id, name, path, type, and status.",
                    path=display_path(root, registry_path),
                )
            )
            continue

        missing = [field_name for field_name in REQUIRED_PROJECT_FIELDS if not item.get(field_name)]
        project_id = str(item.get("id", f"index-{index}"))
        if missing:
            findings.append(
                Finding(
                    "FAIL",
                    "missing-project-field",
                    f"Project {project_id} is missing required field(s): {', '.join(missing)}.",
                    "Fill in id, name, path, type, and status for each project.",
                    project_id=project_id,
                    path=display_path(root, registry_path),
                )
            )
            continue

        if project_id in seen_ids:
            findings.append(
                Finding(
                    "FAIL",
                    "duplicate-project-id",
                    f"Duplicate project id found: {project_id}",
                    "Use stable unique project ids in the fleet registry.",
                    project_id=project_id,
                    path=display_path(root, registry_path),
                )
            )
            continue
        seen_ids.add(project_id)

        raw_path = str(item["path"])
        resolved_path = resolve_project_path(root, raw_path)
        unsafe_reason = unsafe_path_reason(resolved_path, raw_path=raw_path)
        if unsafe_reason:
            findings.append(
                Finding(
                    "FAIL",
                    "unsafe-project-path",
                    f"Project {project_id} has an unsafe path: {unsafe_reason}",
                    "Move the project path outside hidden credential, secret, dependency, or local-output folders.",
                    project_id=project_id,
                    path=raw_path,
                )
            )

        projects.append(
            ProjectRecord(
                id=project_id,
                name=str(item["name"]),
                path=raw_path,
                type=str(item["type"]),
                status=str(item["status"]),
                notes=str(item["notes"]) if item.get("notes") else None,
                resolved_path=resolved_path,
            )
        )

    if not findings:
        findings.append(
            Finding(
                "OK",
                "registry-loaded",
                f"Fleet registry loaded with {len(projects)} project(s).",
                "Use --check when you want safe onboarding marker checks.",
                path=display_path(root, registry_path),
            )
        )
    return projects, findings


def resolve_project_path(root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve(strict=False)


def check_project(root: Path, project: ProjectRecord) -> list[Finding]:
    findings: list[Finding] = []
    checks: list[dict[str, Any]] = []
    project_path = project.resolved_path
    unsafe_reason = unsafe_path_reason(project_path, raw_path=project.path)

    if unsafe_reason:
        project.check_status = "FAIL"
        checks.append({"path": project.path, "status": "FAIL", "reason": unsafe_reason})
        project.checks = checks
        return findings

    if not project_path.exists():
        project.check_status = "FAIL"
        checks.append({"path": project.path, "status": "FAIL", "reason": "project path missing"})
        project.checks = checks
        findings.append(
            Finding(
                "FAIL",
                "project-path-missing",
                f"Project path does not exist: {project.path}",
                "Fix the path in fleet/projects.json or remove the stale project entry.",
                project_id=project.id,
                path=project.path,
            )
        )
        return findings

    if not project_path.is_dir():
        project.check_status = "FAIL"
        checks.append({"path": project.path, "status": "FAIL", "reason": "project path is not a directory"})
        project.checks = checks
        findings.append(
            Finding(
                "FAIL",
                "project-path-not-directory",
                f"Project path is not a directory: {project.path}",
                "Point the registry entry at the project root directory.",
                project_id=project.id,
                path=project.path,
            )
        )
        return findings

    findings.append(
        Finding(
            "OK",
            "project-path-present",
            f"Project path exists: {project.path}",
            "No action needed.",
            project_id=project.id,
            path=project.path,
        )
    )

    missing_count = 0
    for relative_path in PROJECT_CHECK_FILES:
        if check_file_exists(project_path, relative_path):
            checks.append({"path": relative_path, "status": "OK"})
        else:
            missing_count += 1
            checks.append({"path": relative_path, "status": "FAIL", "reason": "missing"})
            findings.append(
                Finding(
                    "FAIL",
                    "project-onboarding-file-missing",
                    f"{project.id} is missing {relative_path}.",
                    "Add the minimal Project Coffee onboarding skeleton or run the template installer after approval.",
                    project_id=project.id,
                    path=relative_path,
                )
            )

    if has_onboarded_markers(project_path):
        if check_file_exists(project_path, KNOWLEDGE_INDEX):
            checks.append({"path": KNOWLEDGE_INDEX, "status": "OK"})
        else:
            missing_count += 1
            checks.append({"path": KNOWLEDGE_INDEX, "status": "FAIL", "reason": "missing"})
            findings.append(
                Finding(
                    "FAIL",
                    "project-knowledge-index-missing",
                    f"{project.id} has onboarding markers but is missing {KNOWLEDGE_INDEX}.",
                    "Add the Pantry index from the Project Coffee template pack.",
                    project_id=project.id,
                    path=KNOWLEDGE_INDEX,
                )
            )

    project.checks = checks
    project.check_status = "FAIL" if missing_count else "OK"
    if missing_count == 0:
        findings.append(
            Finding(
                "OK",
                "project-onboarding-complete",
                f"{project.id} has the checked Project Coffee onboarding markers.",
                "No action needed.",
                project_id=project.id,
                path=project.path,
            )
        )
    return findings


def has_onboarded_markers(project_path: Path) -> bool:
    return any(check_file_exists(project_path, marker) for marker in ONBOARDED_MARKERS)


def check_file_exists(project_path: Path, relative_path: str) -> bool:
    candidate = (project_path / relative_path).resolve(strict=False)
    reason = unsafe_path_reason(candidate, raw_path=relative_path)
    if reason:
        return False
    return candidate.is_file()


def unsafe_path_reason(path: Path, *, raw_path: str | None = None) -> str | None:
    parts = list(path.parts)
    if raw_path:
        parts.extend(Path(raw_path).parts)
    lowered = [part.lower() for part in parts if part]
    for part in lowered:
        if part in UNSAFE_EXACT_PARTS:
            return f"path contains {part}"
        if part.startswith(".") and part in UNSAFE_EXACT_PARTS:
            return f"path contains {part}"
        for marker in UNSAFE_SUBSTRINGS:
            if marker in part:
                return f"path contains {part}"
    return None


def summarize(findings: Sequence[Finding], project_count: int) -> dict[str, int]:
    summary = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        summary[finding.severity] += 1
    summary["total"] = len(findings)
    summary["project_count"] = project_count
    return summary


def overall_status(summary: Mapping[str, int]) -> str:
    if summary.get("FAIL", 0):
        return "FAIL"
    if summary.get("WARN", 0):
        return "WARN"
    if summary.get("INFO", 0):
        return "INFO"
    return "OK"


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def display_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def print_human(report: Mapping[str, Any], stdout: TextIO) -> None:
    print("Project Coffee Fleet Status", file=stdout)
    print(f"Root: {report['root']}", file=stdout)
    print(f"Registry: {report['registry_path']}", file=stdout)
    print(f"Generated: {report['generated_at']}", file=stdout)
    print(f"Status: {report['status']}", file=stdout)
    print(f"Registry status: {report['registry_status']}", file=stdout)
    print(f"Project count: {report['summary']['project_count']}", file=stdout)

    print("\nProjects:", file=stdout)
    projects = report["projects"]
    if not projects:
        print("- None registered.", file=stdout)
    else:
        print("| ID | Name | Type | Status | Path | Check |", file=stdout)
        print("| --- | --- | --- | --- | --- | --- |", file=stdout)
        for project in projects:
            print(
                f"| {project['id']} | {project['name']} | {project['type']} | "
                f"{project['status']} | {project['path']} | {project['check_status']} |",
                file=stdout,
            )

    print("\nFindings:", file=stdout)
    findings = report["findings"]
    if not findings:
        print("- None.", file=stdout)
    else:
        for index, finding in enumerate(findings, start=1):
            label = f"{finding['severity']} {finding['code']}"
            if finding.get("project_id"):
                label += f" [{finding['project_id']}]"
            if finding.get("path"):
                label += f" ({finding['path']})"
            print(f"{index}. {label}", file=stdout)
            print(f"   Finding: {finding['message']}", file=stdout)
            print(f"   Suggested safe next action: {finding['suggestion']}", file=stdout)

    print("\nSuggested safe next actions:", file=stdout)
    suggestions = []
    for finding in findings:
        suggestion = finding["suggestion"]
        if suggestion not in suggestions:
            suggestions.append(suggestion)
    if not suggestions:
        suggestions.append("No action needed.")
    for suggestion in suggestions:
        print(f"- {suggestion}", file=stdout)


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    args = parse_args(argv)

    try:
        report = build_fleet_report(
            args.root,
            registry=args.registry,
            list_only=args.list,
            project_id=args.project,
            check=args.check and not args.list,
        )
    except FleetStatusError as exc:
        print(f"Fleet Status error: {exc}", file=err)
        return 1

    if args.json:
        print(json.dumps(report, indent=2), file=out)
    else:
        print_human(report, out)

    if args.fail_on_issue and report["summary"]["FAIL"]:
        return 1
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
