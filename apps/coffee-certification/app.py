"""Command-line entry point for the Brew 7 certification checklist."""

import argparse
from typing import Iterable, Optional

from src.certifier import (
    REQUIRED_WORKFLOW_STEPS,
    certify_workflow,
    format_markdown_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check Project Coffee workflow certification steps."
    )
    parser.add_argument(
        "--completed",
        action="append",
        default=[],
        metavar="STEP",
        help="Workflow step completed. Repeat this flag for multiple steps.",
    )
    parser.add_argument(
        "--list-required",
        action="store_true",
        help="Print the required workflow steps and exit.",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_required:
        for step in REQUIRED_WORKFLOW_STEPS:
            print(step)
        return 0

    result = certify_workflow(args.completed)
    print(format_markdown_report(result))
    return 0 if result.is_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
