"""Read-only Project Coffee release packaging checklist.

The release check summarizes whether the repository looks ready for a local
Project Coffee release. It checks only known safe files, uses Git metadata for
repository state, and never creates tags, stages files, commits, calls models,
or inspects local raw Roastery outputs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Sequence, TextIO


SUPPORTED_SECTIONS = (
    "repo",
    "docs",
    "tools",
    "templates",
    "safety",
    "evidence",
    "tags",
    "all",
)

SEVERITIES = ("OK", "INFO", "WARN", "BLOCKER")

CORE_GUIDES = (
    "docs/guides/project-coffee-operating-manual.md",
    "docs/guides/project-coffee-setup-guide.md",
    "docs/guides/new-project-onboarding-guide.md",
    "docs/guides/template-pack-guide.md",
    "docs/guides/template-installer-guide.md",
    "docs/guides/pantry-search-guide.md",
    "docs/guides/pantry-intake-guide.md",
    "docs/guides/barista-handbook.md",
    "docs/guides/roastery-and-ledger-guide.md",
    "docs/guides/ledger-summary-guide.md",
    "docs/guides/roastery-report-guide.md",
    "docs/guides/coffee-dashboard-guide.md",
    "docs/guides/coffee-doctor-guide.md",
    "docs/guides/unified-coffee-cli-guide.md",
    "docs/guides/model-routing-and-house-blend-guide.md",
    "docs/guides/release-packaging-guide.md",
)

TOOL_FILES = (
    "tools/coffee.py",
    "tools/coffee_dashboard.py",
    "tools/coffee_doctor.py",
    "tools/ledger_summary.py",
    "tools/pantry_search.py",
    "tools/roastery_report.py",
    "tools/install_project_coffee_template.py",
    "tools/release_check.py",
)

TEMPLATE_PATHS = (
    "TEMPLATES/project-coffee",
    "TEMPLATES/project-coffee/README.md",
    "TEMPLATES/project-coffee/knowledge/00_index.md",
)

SAFETY_FILES = (
    "AGENTS.md",
    "PROJECT_COFFEE.md",
    ".gitignore",
    ".cursorignore",
    ".cursorindexingignore",
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

REQUIRED_IGNORE_PATTERNS = (
    "roastery/local_cup_outputs/",
    "roastery/local_reports/",
)

EVIDENCE_FILES = (
    "brew-log/active_context.md",
    "brew-log/progress.md",
    "roastery/tasting_notes.md",
    "ledger/cost_log.md",
)

EXPECTED_RELEASE_TAGS = (
    "v0.1",
    "v0.1-proven",
    "v0.1-certified",
)


class ReleaseCheckError(Exception):
    """Raised when the release check cannot run safely."""


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


GitStatusFunc = Callable[[Path], list[str] | None]
GitTagFunc = Callable[[Path], list[str] | None]
GitLsFilesFunc = Callable[[Path, Sequence[str]], list[str] | None]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the read-only Project Coffee release packaging checklist.",
    )
    parser.add_argument("--root", default=".", help="Project Coffee root. Default: current directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    parser.add_argument(
        "--section",
        choices=SUPPORTED_SECTIONS,
        default="all",
        help="Checklist section to run. Default: all.",
    )
    parser.add_argument(
        "--fail-on-blocker",
        action="store_true",
        help="Exit nonzero when BLOCKER findings are present.",
    )
    return parser.parse_args(argv)


def build_release_report(
    root: str | Path,
    *,
    section: str = "all",
    git_status_func: GitStatusFunc | None = None,
    git_tag_func: GitTagFunc | None = None,
    git_ls_files_func: GitLsFilesFunc | None = None,
) -> dict[str, Any]:
    root_path = validate_root(root)
    selected = selected_sections(section)
    status_func = git_status_func or git_status
    tag_func = git_tag_func or git_tags
    ls_files_func = git_ls_files_func or git_ls_files

    findings: list[Finding] = []
    for selected_section in selected:
        if selected_section == "repo":
            findings.extend(check_repo(root_path, status_func))
        elif selected_section == "docs":
            findings.extend(check_docs(root_path))
        elif selected_section == "tools":
            findings.extend(check_tools(root_path))
        elif selected_section == "templates":
            findings.extend(check_templates(root_path))
        elif selected_section == "safety":
            findings.extend(check_safety(root_path, ls_files_func))
        elif selected_section == "evidence":
            findings.extend(check_evidence(root_path))
        elif selected_section == "tags":
            findings.extend(check_tags(root_path, tag_func))

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
        raise ReleaseCheckError(f"Root does not exist: {path}") from exc
    if not resolved.is_dir():
        raise ReleaseCheckError(f"Root is not a directory: {resolved}")
    return resolved


def selected_sections(section: str) -> tuple[str, ...]:
    if section == "all":
        return ("repo", "docs", "tools", "templates", "safety", "evidence", "tags")
    return (section,)


def check_repo(root: Path, git_status_func: GitStatusFunc) -> list[Finding]:
    status_lines = git_status_func(root)
    if status_lines is None:
        return [
            Finding(
                section="repo",
                severity="INFO",
                code="git-status-unavailable",
                message="Git status could not be read, possibly because Git is unavailable or this is not a Git repository.",
                suggestion="Run git status --short manually before release packaging.",
            )
        ]
    if status_lines:
        return [
            Finding(
                section="repo",
                severity="WARN",
                code="working-tree-dirty",
                message=f"Working tree has {len(status_lines)} changed or untracked path(s).",
                suggestion="Review the diff and commit or intentionally leave local-only files before release tagging.",
            )
        ]
    return [
        Finding(
            section="repo",
            severity="OK",
            code="working-tree-clean",
            message="Working tree is clean according to git status --short.",
            suggestion="Continue release packaging checks.",
        )
    ]


def check_docs(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    docs_readme = root / "docs" / "README.md"
    if docs_readme.is_file():
        findings.append(
            Finding(
                section="docs",
                severity="OK",
                code="docs-index-present",
                message="Docs index is present.",
                suggestion="Keep it linked to release-facing guides.",
                path="docs/README.md",
            )
        )
        docs_text = safe_read_text(docs_readme)
        missing_links = [guide for guide in CORE_GUIDES if guide.replace("docs/", "") not in docs_text]
        if missing_links:
            findings.append(
                Finding(
                    section="docs",
                    severity="WARN",
                    code="docs-index-links-missing",
                    message="Docs index may be missing guide links: " + ", ".join(missing_links),
                    suggestion="Add guide links to docs/README.md before release.",
                    path="docs/README.md",
                )
            )
        else:
            findings.append(
                Finding(
                    section="docs",
                    severity="OK",
                    code="docs-index-links-current",
                    message="Docs index links the expected release-facing guides.",
                    suggestion="Continue release packaging checks.",
                    path="docs/README.md",
                )
            )
    else:
        findings.append(
            Finding(
                section="docs",
                severity="BLOCKER",
                code="docs-index-missing",
                message="Docs index is missing.",
                suggestion="Create docs/README.md before packaging a release.",
                path="docs/README.md",
            )
        )

    missing_guides = [guide for guide in CORE_GUIDES if not (root / guide).is_file()]
    if missing_guides:
        findings.append(
            Finding(
                section="docs",
                severity="WARN",
                code="guide-files-missing",
                message="Expected guide file(s) are missing: " + ", ".join(missing_guides),
                suggestion="Add missing guides or document why they are out of scope for this release.",
            )
        )
    else:
        findings.append(
            Finding(
                section="docs",
                severity="OK",
                code="guide-files-present",
                message="Expected release-facing guide files are present.",
                suggestion="Review guide quality before tagging.",
            )
        )
    return findings


def check_tools(root: Path) -> list[Finding]:
    missing = [path for path in TOOL_FILES if not (root / path).is_file()]
    if missing:
        return [
            Finding(
                section="tools",
                severity="BLOCKER",
                code="tool-files-missing",
                message="Required release-facing tool file(s) are missing: " + ", ".join(missing),
                suggestion="Restore or finish the missing tool files before packaging a release.",
            )
        ]
    return [
        Finding(
            section="tools",
            severity="OK",
            code="tool-files-present",
            message="Required release-facing tool files are present: " + ", ".join(TOOL_FILES),
            suggestion="Run focused tests and compile checks before tagging.",
        )
    ]


def check_templates(root: Path) -> list[Finding]:
    missing = [path for path in TEMPLATE_PATHS if not (root / path).exists()]
    if missing:
        return [
            Finding(
                section="templates",
                severity="BLOCKER",
                code="template-pack-incomplete",
                message="Project Coffee template pack path(s) are missing: " + ", ".join(missing),
                suggestion="Restore the template pack before packaging a repeatable release.",
            )
        ]
    return [
        Finding(
            section="templates",
            severity="OK",
            code="template-pack-present",
            message="Project Coffee template pack, README, and Pantry index are present.",
            suggestion="Run the template installer smoke workflow before release if it has not been dogfooded recently.",
        )
    ]


def check_safety(root: Path, git_ls_files_func: GitLsFilesFunc) -> list[Finding]:
    findings: list[Finding] = []
    missing_safety = [path for path in SAFETY_FILES if not (root / path).is_file()]
    if missing_safety:
        findings.append(
            Finding(
                section="safety",
                severity="BLOCKER",
                code="safety-files-missing",
                message="Safety file(s) are missing: " + ", ".join(missing_safety),
                suggestion="Restore Project Coffee safety files before release packaging.",
            )
        )
    else:
        findings.append(
            Finding(
                section="safety",
                severity="OK",
                code="safety-files-present",
                message="Project Coffee safety files are present: " + ", ".join(SAFETY_FILES),
                suggestion="Keep approval gates and Spill Guard rules in place through release.",
            )
        )

    missing_ignore_patterns: list[str] = []
    for ignore_file in IGNORE_FILES:
        ignore_path = root / ignore_file
        if not ignore_path.is_file():
            continue
        ignore_text = safe_read_text(ignore_path)
        for pattern in REQUIRED_IGNORE_PATTERNS:
            if pattern not in ignore_text:
                missing_ignore_patterns.append(f"{ignore_file}: {pattern}")
    if missing_ignore_patterns:
        findings.append(
            Finding(
                section="safety",
                severity="BLOCKER",
                code="local-artifact-ignore-missing",
                message="Ignored local output pattern(s) are missing: " + ", ".join(missing_ignore_patterns),
                suggestion="Add local raw-output/report paths to Git and Cursor ignore files before release.",
            )
        )
    elif all((root / ignore_file).is_file() for ignore_file in IGNORE_FILES):
        findings.append(
            Finding(
                section="safety",
                severity="OK",
                code="local-artifact-ignores-present",
                message="Local raw-output and report paths are ignored by Git and Cursor ignore files.",
                suggestion="Keep generated raw outputs and local reports out of commits.",
            )
        )

    tracked_artifacts = git_ls_files_func(root, LOCAL_ARTIFACT_PATHS)
    if tracked_artifacts is None:
        findings.append(
            Finding(
                section="safety",
                severity="INFO",
                code="tracked-artifact-check-unavailable",
                message="Could not check whether local Roastery output/report paths are tracked by Git.",
                suggestion="Run git ls-files -- roastery/local_cup_outputs roastery/local_reports manually before release.",
            )
        )
    elif tracked_artifacts:
        findings.append(
            Finding(
                section="safety",
                severity="BLOCKER",
                code="local-artifact-tracked",
                message=f"Local raw-output/report path(s) are tracked by Git: {len(tracked_artifacts)} path(s).",
                suggestion="Remove tracked local artifacts from version control before release.",
            )
        )
    else:
        findings.append(
            Finding(
                section="safety",
                severity="OK",
                code="local-artifacts-untracked",
                message="Git does not track known local Roastery output/report paths.",
                suggestion="Continue keeping raw outputs and generated reports local-only.",
            )
        )
    return findings


def check_evidence(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    missing = [path for path in EVIDENCE_FILES if not (root / path).is_file()]
    if missing:
        findings.append(
            Finding(
                section="evidence",
                severity="BLOCKER",
                code="evidence-files-missing",
                message="Evidence/status file(s) are missing: " + ", ".join(missing),
                suggestion="Restore Brew Log, Roastery, and Ledger evidence before release packaging.",
            )
        )
    else:
        findings.append(
            Finding(
                section="evidence",
                severity="OK",
                code="evidence-files-present",
                message="Brew Log, Roastery, and Ledger evidence files are present.",
                suggestion="Review evidence notes for the release candidate.",
            )
        )

    ledger_path = root / "ledger" / "cost_log.md"
    if ledger_path.is_file():
        ledger_text = safe_read_text(ledger_path)
        if "Brew 19" in ledger_text or "Brew 20" in ledger_text:
            findings.append(
                Finding(
                    section="evidence",
                    severity="OK",
                    code="recent-ledger-evidence-present",
                    message="Ledger includes recent Brew 19 or Brew 20 evidence.",
                    suggestion="Keep release packaging evidence honest and local-first.",
                    path="ledger/cost_log.md",
                )
            )
        else:
            findings.append(
                Finding(
                    section="evidence",
                    severity="WARN",
                    code="recent-ledger-evidence-missing",
                    message="Ledger does not appear to mention Brew 19 or Brew 20.",
                    suggestion="Add an honest Ledger entry for recent release work if relevant.",
                    path="ledger/cost_log.md",
                )
            )
    return findings


def check_tags(root: Path, git_tag_func: GitTagFunc) -> list[Finding]:
    tags = git_tag_func(root)
    if tags is None:
        return [
            Finding(
                section="tags",
                severity="INFO",
                code="git-tags-unavailable",
                message="Git tags could not be read, possibly because Git is unavailable or this is not a Git repository.",
                suggestion="Run git tag -l manually before deciding on a release tag.",
            )
        ]
    findings: list[Finding] = []
    tag_set = set(tags)
    for expected_tag in EXPECTED_RELEASE_TAGS:
        if expected_tag in tag_set:
            findings.append(
                Finding(
                    section="tags",
                    severity="OK",
                    code="expected-tag-present",
                    message=f"Expected release tag exists: {expected_tag}",
                    suggestion="Do not recreate existing release tags.",
                )
            )
        else:
            findings.append(
                Finding(
                    section="tags",
                    severity="INFO",
                    code="expected-tag-absent",
                    message=f"Expected release tag is not present: {expected_tag}",
                    suggestion="Create tags only after human review, validation, and the staged secret-pattern check from Project Coffee policy.",
                )
            )
    return findings


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def git_status(root: Path) -> list[str] | None:
    try:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.splitlines()


def git_tags(root: Path) -> list[str] | None:
    try:
        completed = subprocess.run(
            ["git", "tag", "-l"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.splitlines()


def git_ls_files(root: Path, paths: Sequence[str]) -> list[str] | None:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "--", *paths],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.splitlines()


def summarize(findings: Sequence[Finding]) -> dict[str, int]:
    return {severity: sum(1 for finding in findings if finding.severity == severity) for severity in SEVERITIES}


def overall_status(summary: dict[str, int]) -> str:
    if summary["BLOCKER"]:
        return "BLOCKER"
    if summary["WARN"]:
        return "WARN"
    return "OK"


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def render_human(report: dict[str, Any]) -> str:
    lines = [
        "Project Coffee Release Check",
        f"Root: {report['root']}",
        f"Generated: {report['generated_at']}",
        f"Release readiness status: {report['status']}",
        "",
        "Summary:",
    ]
    summary = report["summary"]
    for severity in SEVERITIES:
        lines.append(f"- {severity}: {summary[severity]}")

    lines.extend(["", "Findings:"])
    for index, finding in enumerate(report["findings"], start=1):
        path = f" [{finding['path']}]" if "path" in finding else ""
        lines.append(
            f"{index}. {finding['severity']} {finding['section']}::{finding['code']}{path}"
        )
        lines.append(f"   {finding['message']}")
        lines.append(f"   Next: {finding['suggestion']}")
    return "\n".join(lines)


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    git_status_func: GitStatusFunc | None = None,
    git_tag_func: GitTagFunc | None = None,
    git_ls_files_func: GitLsFilesFunc | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    args = parse_args(argv)
    try:
        report = build_release_report(
            args.root,
            section=args.section,
            git_status_func=git_status_func,
            git_tag_func=git_tag_func,
            git_ls_files_func=git_ls_files_func,
        )
    except ReleaseCheckError as exc:
        print(f"Release check failed: {exc}", file=err)
        return 2

    if args.json:
        json.dump(report, out, indent=2)
        out.write("\n")
    else:
        print(render_human(report), file=out)

    if args.fail_on_blocker and report["summary"]["BLOCKER"]:
        return 1
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
