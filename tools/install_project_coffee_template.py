"""Install the Project Coffee onboarding template into a target project.

The installer is intentionally narrow: it copies only the known onboarding
manifest and never scans the target project for content.
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path


ONBOARDING_FILES = (
    "AGENTS.md",
    "PROJECT_COFFEE.md",
    ".cursorignore",
    ".cursorindexingignore",
    "brew-log/projectbrief.md",
    "brew-log/active_context.md",
    "brew-log/progress.md",
    "knowledge/00_index.md",
    "roastery/tasting_notes.md",
    "ledger/cost_log.md",
)

DOCTOR_FILES = (
    "AGENTS.md",
    "PROJECT_COFFEE.md",
    ".cursorignore",
    ".cursorindexingignore",
    "brew-log/active_context.md",
    "brew-log/progress.md",
    "knowledge/00_index.md",
    "roastery/tasting_notes.md",
    "ledger/cost_log.md",
)


@dataclass(frozen=True)
class InstallPlan:
    mode: str
    target: Path
    template: Path
    to_create: tuple[str, ...]
    to_skip: tuple[str, ...]
    would_overwrite: tuple[str, ...]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_template_path() -> Path:
    root = project_root()
    preferred = root / "templates" / "project-coffee"
    if preferred.exists():
        return preferred

    # The historical repository path is uppercase on disk. Keep the CLI default
    # documented as templates/project-coffee while still working locally.
    existing = root / "TEMPLATES" / "project-coffee"
    if existing.exists():
        return existing

    return preferred


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely install the Project Coffee onboarding template.",
    )
    parser.add_argument("--target", required=True, help="Target project root.")
    parser.add_argument(
        "--template",
        default=None,
        help="Template root. Defaults to templates/project-coffee.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print the plan only.")
    mode.add_argument("--apply", action="store_true", help="Write missing files.")
    mode.add_argument(
        "--check",
        action="store_true",
        help="Doctor mode: check required onboarding files without writing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing onboarding files when used with --apply.",
    )
    return parser.parse_args(argv)


def resolved_child(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Unsafe path escapes root: {relative_path}") from exc
    return candidate


def validate_roots(target: Path, template: Path) -> list[str]:
    errors: list[str] = []
    if not target.exists():
        errors.append(f"Target does not exist: {target}")
    elif not target.is_dir():
        errors.append(f"Target is not a directory: {target}")

    if not template.exists():
        errors.append(f"Template does not exist: {template}")
    elif not template.is_dir():
        errors.append(f"Template is not a directory: {template}")

    return errors


def check_onboarding(target: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    found: list[str] = []
    missing: list[str] = []

    for relative_path in DOCTOR_FILES:
        destination = resolved_child(target, relative_path)
        if destination.is_file():
            found.append(relative_path)
        else:
            missing.append(relative_path)

    return tuple(found), tuple(missing)


def build_plan(target: Path, template: Path, *, apply: bool, force: bool) -> InstallPlan:
    to_create: list[str] = []
    to_skip: list[str] = []
    would_overwrite: list[str] = []

    for relative_path in ONBOARDING_FILES:
        source = resolved_child(template, relative_path)
        destination = resolved_child(target, relative_path)

        if not source.exists():
            raise FileNotFoundError(f"Template file is missing: {relative_path}")
        if not source.is_file():
            raise ValueError(f"Template path is not a file: {relative_path}")
        if source.is_symlink():
            raise ValueError(f"Template path is a symlink: {relative_path}")

        if destination.exists():
            if not destination.is_file():
                raise ValueError(f"Target path exists but is not a file: {relative_path}")
            if destination.is_symlink():
                raise ValueError(f"Target path is a symlink: {relative_path}")
            if force:
                would_overwrite.append(relative_path)
            else:
                to_skip.append(relative_path)
        else:
            to_create.append(relative_path)

    mode = "apply" if apply else "dry-run"
    if apply and force:
        mode = "apply --force"

    return InstallPlan(
        mode=mode,
        target=target,
        template=template,
        to_create=tuple(to_create),
        to_skip=tuple(to_skip),
        would_overwrite=tuple(would_overwrite),
    )


def print_list(title: str, items: tuple[str, ...]) -> None:
    print(title)
    if items:
        for item in items:
            print(f"  - {item}")
    else:
        print("  - None")


def print_plan(plan: InstallPlan, result: str) -> None:
    print("Mode")
    print(f"  {plan.mode}")
    print("Target")
    print(f"  {plan.target}")
    print("Template")
    print(f"  {plan.template}")
    print_list("Files to create", plan.to_create)
    print_list("Files to skip", plan.to_skip)
    print_list("Files that would overwrite only with --force", plan.would_overwrite)
    print("Result")
    print(f"  {result}")


def print_check_result(target: Path, found: tuple[str, ...], missing: tuple[str, ...]) -> None:
    print("Mode")
    print("  check")
    print("Target")
    print(f"  {target}")
    print_list("FOUND files", found)
    print_list("MISSING files", missing)
    print("status")
    print("  COMPLETE" if not missing else "  INCOMPLETE")


def apply_plan(plan: InstallPlan) -> None:
    for relative_path in plan.to_create + plan.would_overwrite:
        source = resolved_child(plan.template, relative_path)
        destination = resolved_child(plan.target, relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = Path(args.target).expanduser().resolve()
    template = (
        Path(args.template).expanduser().resolve()
        if args.template
        else default_template_path().resolve()
    )
    apply = bool(args.apply)
    force = bool(args.force)

    if args.check:
        if not target.exists():
            print("Mode")
            print("  check")
            print("Target")
            print(f"  {target}")
            print("Result")
            print(f"  ERROR: Target does not exist: {target}")
            return 1
        if not target.is_dir():
            print("Mode")
            print("  check")
            print("Target")
            print(f"  {target}")
            print("Result")
            print(f"  ERROR: Target is not a directory: {target}")
            return 1

        found, missing = check_onboarding(target)
        print_check_result(target, found, missing)
        return 0 if not missing else 2

    errors = validate_roots(target, template)
    if errors:
        print("Mode")
        print("  dry-run" if not apply else "  apply")
        print("Target")
        print(f"  {target}")
        print("Template")
        print(f"  {template}")
        print("Result")
        for error in errors:
            print(f"  ERROR: {error}")
        return 1

    try:
        plan = build_plan(target, template, apply=apply, force=force)
    except (FileNotFoundError, ValueError) as exc:
        print("Mode")
        print("  dry-run" if not apply else "  apply")
        print("Target")
        print(f"  {target}")
        print("Template")
        print(f"  {template}")
        print("Result")
        print(f"  ERROR: {exc}")
        return 1

    if not apply:
        print_plan(plan, "Dry-run complete. No files were written.")
        return 0

    try:
        apply_plan(plan)
    except OSError as exc:
        print_plan(plan, f"ERROR: apply failed: {exc}")
        return 1

    print_plan(plan, "Apply complete.")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
