"""Unified Project Coffee CLI.

This wrapper delegates common Project Coffee commands to the existing local
tools. It keeps the command surface convenient without reimplementing tool
logic or changing their safety boundaries.
"""

from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Callable, Sequence, TextIO


VERSION = "Project Coffee CLI v0.1"
REPO_ROOT = Path(__file__).resolve().parents[1]


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
ScriptExists = Callable[[Path], bool]


@dataclass(frozen=True)
class Delegation:
    script: Path
    args: list[str]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run common Project Coffee tools through one command.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=VERSION,
        help="Print the Project Coffee CLI version.",
    )

    subcommands = parser.add_subparsers(dest="command", required=True)

    dashboard = subcommands.add_parser("dashboard", help="Run the Coffee Dashboard.")
    dashboard.add_argument("--root", default=".", help="Project Coffee root. Default: current directory.")
    dashboard.add_argument("--json", action="store_true", help="Print JSON output.")
    dashboard.add_argument("--section", help="Dashboard section to print.")
    dashboard.add_argument("--fail-on-missing", action="store_true", help="Exit nonzero when required files are missing.")

    doctor = subcommands.add_parser("doctor", help="Run Coffee Doctor.")
    doctor.add_argument("--root", default=".", help="Project root. Default: current directory.")
    doctor.add_argument("--json", action="store_true", help="Print JSON output.")
    doctor.add_argument("--section", help="Doctor section to run.")
    doctor.add_argument("--fail-on-issue", action="store_true", help="Exit nonzero when fail findings are present.")

    pantry_search = subcommands.add_parser("pantry-search", help="Search local Markdown Pantry files.")
    pantry_search.add_argument("--root", default="knowledge", help="Root directory to search. Default: knowledge.")
    pantry_search.add_argument("--query", required=True, help="Search query text.")
    pantry_search.add_argument("--max-results", type=int, help="Maximum results to print.")
    pantry_search.add_argument("--json", action="store_true", help="Print JSON output.")

    roastery_report = subcommands.add_parser("roastery-report", help="Generate a draft Roastery report.")
    roastery_report.add_argument("--run-dir", required=True, help="Run directory or parent directory.")
    roastery_report.add_argument("--json", action="store_true", help="Print JSON output.")
    roastery_report.add_argument("--output", help="Optional output path for the draft report.")

    install_template = subcommands.add_parser("install-template", help="Install the Project Coffee template pack.")
    install_template.add_argument("--target", required=True, help="Target project root.")
    install_template.add_argument("--template", help="Template root. Defaults to templates/project-coffee.")
    install_template.add_argument("--apply", action="store_true", help="Write missing files.")
    install_template.add_argument("--force", action="store_true", help="Overwrite existing files when used with --apply.")

    check_onboarding = subcommands.add_parser("check-onboarding", help="Check Project Coffee onboarding files.")
    check_onboarding.add_argument("--target", required=True, help="Target project root.")
    check_onboarding.add_argument("--template", help="Template root. Defaults to templates/project-coffee.")

    ledger_summary = subcommands.add_parser("ledger-summary", help="Summarize Project Coffee Ledger evidence.")
    ledger_summary.add_argument("--root", default=".", help="Project root. Default: current directory.")
    ledger_summary.add_argument("--ledger", help="Ledger markdown path. Default: ledger/cost_log.md under root.")
    ledger_summary.add_argument("--json", action="store_true", help="Print JSON output.")
    ledger_summary.add_argument("--from", dest="from_date", help="Include entries on or after YYYY-MM-DD.")
    ledger_summary.add_argument("--to", dest="to_date", help="Include entries on or before YYYY-MM-DD.")
    ledger_summary.add_argument("--max-entries", type=int, help="Maximum recent entries to print.")
    ledger_summary.add_argument("--output", help="Optional Markdown report output path.")

    return parser


def build_delegation(args: argparse.Namespace) -> Delegation:
    if args.command == "dashboard":
        return Delegation(
            script=REPO_ROOT / "tools" / "coffee_dashboard.py",
            args=dashboard_args(args),
        )
    if args.command == "doctor":
        return Delegation(
            script=REPO_ROOT / "tools" / "coffee_doctor.py",
            args=doctor_args(args),
        )
    if args.command == "pantry-search":
        return Delegation(
            script=REPO_ROOT / "tools" / "pantry_search.py",
            args=pantry_search_args(args),
        )
    if args.command == "roastery-report":
        return Delegation(
            script=REPO_ROOT / "tools" / "roastery_report.py",
            args=roastery_report_args(args),
        )
    if args.command == "install-template":
        return Delegation(
            script=REPO_ROOT / "tools" / "install_project_coffee_template.py",
            args=install_template_args(args),
        )
    if args.command == "check-onboarding":
        return Delegation(
            script=REPO_ROOT / "tools" / "install_project_coffee_template.py",
            args=check_onboarding_args(args),
        )
    if args.command == "ledger-summary":
        return Delegation(
            script=REPO_ROOT / "tools" / "ledger_summary.py",
            args=ledger_summary_args(args),
        )
    raise ValueError(f"Unsupported command: {args.command}")


def dashboard_args(args: argparse.Namespace) -> list[str]:
    forwarded = ["--root", args.root]
    append_optional(forwarded, "--section", args.section)
    append_flag(forwarded, "--json", args.json)
    append_flag(forwarded, "--fail-on-missing", args.fail_on_missing)
    return forwarded


def doctor_args(args: argparse.Namespace) -> list[str]:
    forwarded = ["--root", args.root]
    append_optional(forwarded, "--section", args.section)
    append_flag(forwarded, "--json", args.json)
    append_flag(forwarded, "--fail-on-issue", args.fail_on_issue)
    return forwarded


def pantry_search_args(args: argparse.Namespace) -> list[str]:
    forwarded = ["--root", args.root, "--query", args.query]
    append_optional(forwarded, "--max-results", args.max_results)
    append_flag(forwarded, "--json", args.json)
    return forwarded


def roastery_report_args(args: argparse.Namespace) -> list[str]:
    forwarded = ["--run-dir", args.run_dir]
    append_optional(forwarded, "--output", args.output)
    append_flag(forwarded, "--json", args.json)
    return forwarded


def install_template_args(args: argparse.Namespace) -> list[str]:
    forwarded = ["--target", args.target]
    append_optional(forwarded, "--template", args.template)
    append_flag(forwarded, "--apply", args.apply)
    append_flag(forwarded, "--force", args.force)
    return forwarded


def check_onboarding_args(args: argparse.Namespace) -> list[str]:
    forwarded = ["--target", args.target]
    append_optional(forwarded, "--template", args.template)
    forwarded.append("--check")
    return forwarded


def ledger_summary_args(args: argparse.Namespace) -> list[str]:
    forwarded = ["--root", args.root]
    append_optional(forwarded, "--ledger", args.ledger)
    append_optional(forwarded, "--from", args.from_date)
    append_optional(forwarded, "--to", args.to_date)
    append_optional(forwarded, "--max-entries", args.max_entries)
    append_optional(forwarded, "--output", args.output)
    append_flag(forwarded, "--json", args.json)
    return forwarded


def append_optional(forwarded: list[str], flag: str, value: object | None) -> None:
    if value is not None:
        forwarded.extend([flag, str(value)])


def append_flag(forwarded: list[str], flag: str, enabled: bool) -> None:
    if enabled:
        forwarded.append(flag)


def run(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner = subprocess.run,
    script_exists: ScriptExists | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_parser()

    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            args = parser.parse_args(argv)
        except SystemExit as exc:
            return int(exc.code)

    delegation = build_delegation(args)
    exists = script_exists or Path.is_file
    if not exists(delegation.script):
        print(f"Delegated tool is missing: {delegation.script}", file=err)
        return 1

    completed = runner([sys.executable, str(delegation.script), *delegation.args])
    return int(completed.returncode)


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
