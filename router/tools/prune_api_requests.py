"""CLI for pruning old `api_requests` rows (Brew 47 Section 2).

Manual only, never automatic - docs/design/openai-compat-endpoint-design.md's
resolved open question 3: automatic deletion of the only evidence this
router has for retry detection and shadow-mode pairs, on a schedule you
forget about, is how you discover your data is gone the day you want to
analyze it. Run this deliberately, when you actually want to prune.

Usage (run from the repository root):
    python router/tools/prune_api_requests.py --older-than 90d
    python router/tools/prune_api_requests.py --older-than 24h
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from router.app.sessions import SessionStore  # noqa: E402

DURATION_PATTERN = re.compile(r"^(\d+)(d|h|m)$")
DURATION_UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60}


class InvalidDurationError(Exception):
    """Raised when --older-than isn't a recognized duration string."""


def parse_duration_seconds(value: str) -> int:
    match = DURATION_PATTERN.match(value.strip())
    if not match:
        raise InvalidDurationError(
            f"Invalid --older-than value {value!r} - expected a number followed by "
            "d (days), h (hours), or m (minutes), e.g. '90d', '24h', '30m'."
        )
    amount, unit = match.groups()
    return int(amount) * DURATION_UNIT_SECONDS[unit]


def cmd_prune(store: SessionStore, older_than: str) -> int:
    try:
        seconds = parse_duration_seconds(older_than)
    except InvalidDurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    cutoff_iso = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat(timespec="microseconds")
    deleted = store.prune_api_requests_older_than(cutoff_iso)
    print(f"Deleted {deleted} api_requests row(s) created before {cutoff_iso} (older than {older_than}).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--older-than",
        required=True,
        help="Delete api_requests rows created before this long ago, e.g. '90d', '24h', '30m'. Required - no default, never automatic.",
    )
    args = parser.parse_args()

    store = SessionStore()
    return cmd_prune(store, args.older_than)


if __name__ == "__main__":
    raise SystemExit(main())
