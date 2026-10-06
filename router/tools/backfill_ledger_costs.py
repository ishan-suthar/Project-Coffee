"""CLI to backfill real cost_usd for Ledger rows whose cost is genuinely
unknown (cost-inconsistency fix - resolved the gap flagged in Brew 47's
Tasting Note where every paid-Bean row wrote cost_usd=None).

Manual only, opt-in - never runs automatically, same precedent as
prune_api_requests.py. A historical row's real OpenRouter-reported cost
was never captured (usage.cost wasn't retained before this Brew), so
backfill can only recover a computed (beans.yaml token math) cost, never
a reported one - see router/app/ledger.py's resolve_cost() and this
module's COST CONTRACT docstring. Rows that still can't be priced
(unparseable tokens, an unknown bean alias, or a bean with no configured
pricing) are left untouched and reported as still-unknown.

Usage (run from the repository root):
    python router/tools/backfill_ledger_costs.py --dry-run
    python router/tools/backfill_ledger_costs.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from router.app.aliases import BeanRegistry  # noqa: E402
from router.app.ledger import RouterLedger  # noqa: E402


def run(ledger: RouterLedger, bean_registry: BeanRegistry, *, apply: bool) -> int:
    changed = ledger.backfill_missing_costs(bean_registry, apply=apply)

    if not changed:
        print("No rows to backfill - every row already has a known cost_source, or none are priceable.")
        return 0

    for row in changed:
        old = row["_old_cost_usd"] or "unknown"
        print(
            f"request_id={row['request_id']} bean_alias={row['bean_alias']} "
            f"cost_usd: {old} -> {row['cost_usd']} (cost_source=computed)"
        )

    mode = "Applied" if apply else "Would apply (dry run, nothing written)"
    print(f"\n{mode}: {len(changed)} row(s) backfilled.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Print what would change; write nothing.")
    group.add_argument("--apply", action="store_true", help="Actually rewrite the Ledger with backfilled costs.")
    args = parser.parse_args()

    bean_registry = BeanRegistry.from_yaml()
    ledger = RouterLedger()
    return run(ledger, bean_registry, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
