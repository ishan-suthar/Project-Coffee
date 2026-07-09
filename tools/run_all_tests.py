"""Aggregate Project Coffee test suites from every known test root.

Running `python -m unittest discover` from the repository root silently
collects zero tests, because apps/coffee-status and apps/coffee-certification
contain hyphens, which are not valid Python module-name characters and break
unittest's dotted-module resolution during discovery from the repo root.

Running all four known test roots in a single process (one shared
unittest.TestLoader) does not work either: apps/coffee-status/src and
apps/coffee-certification/src are both top-level packages named `src`, and
once one is imported and cached in sys.modules the other's `src.<module>`
imports resolve to the wrong package.

This script instead runs each known test root as its own isolated
subprocess, exactly matching the `python -m unittest discover -s <dir>`
invocation already documented per test root, and aggregates the results so
a hyphenated app directory or a cross-app module-name collision can never
again cause a silent false pass.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TEST_ROOTS = [
    REPO_ROOT / "tests",
    REPO_ROOT / "roastery" / "tests",
    REPO_ROOT / "apps" / "coffee-status" / "tests",
    REPO_ROOT / "apps" / "coffee-certification" / "tests",
]

RAN_PATTERN = re.compile(r"Ran (\d+) tests?")


def main() -> int:
    total_run = 0
    any_failed = False
    missing_roots = []

    for start_dir in TEST_ROOTS:
        if not start_dir.is_dir():
            missing_roots.append(str(start_dir))
            continue

        print(f"\n=== {start_dir.relative_to(REPO_ROOT)} ===")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(start_dir)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        print(result.stdout, end="")
        print(result.stderr, end="")

        match = RAN_PATTERN.search(result.stderr) or RAN_PATTERN.search(result.stdout)
        ran = int(match.group(1)) if match else 0
        total_run += ran

        if result.returncode != 0:
            any_failed = True

    print("\n=== Summary ===")
    print(f"Test roots checked: {len(TEST_ROOTS)}")
    if missing_roots:
        print(f"Missing test roots (skipped): {missing_roots}")
    print(f"Total tests run: {total_run}")

    if total_run == 0:
        print("FAIL: zero tests were collected across all known test roots.")
        return 1
    if any_failed:
        print("FAIL: one or more test roots reported failures or errors.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
