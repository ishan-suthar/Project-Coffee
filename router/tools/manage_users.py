"""CLI for managing Coffee Core Router users (Brew 43).

The only way to create a user - there is no signup endpoint or page.
This is how a family adds members, not a public registration flow. See
docs/design/auth-projects-chat-management-design.md Section 3.2.

Usage (run from the repository root):
    python router/tools/manage_users.py add
    python router/tools/manage_users.py remove <username>
    python router/tools/manage_users.py list
    python router/tools/manage_users.py set-cap <username> <amount|clear>
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from router.app.auth import hash_password  # noqa: E402
from router.app.sessions import SessionStore, UsernameTakenError  # noqa: E402


def cmd_add(store: SessionStore) -> int:
    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.", file=sys.stderr)
        return 1
    display_name = input("Display name: ").strip() or username

    password = getpass.getpass("Password: ")
    if not password:
        print("Password cannot be empty.", file=sys.stderr)
        return 1
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords did not match.", file=sys.stderr)
        return 1

    try:
        user_id = store.create_user(username, hash_password(password), display_name)
    except UsernameTakenError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Created user {username!r} (id={user_id}, display_name={display_name!r}).")
    return 0


def cmd_remove(store: SessionStore, username: str) -> int:
    if store.delete_user(username):
        print(f"Removed user {username!r}.")
        return 0
    print(f"No such user {username!r}.", file=sys.stderr)
    return 1


def cmd_list(store: SessionStore) -> int:
    users = store.list_users()
    if not users:
        print("No users.")
        return 0
    for user in users:
        cap = "default" if user.daily_cost_cap_usd is None else f"${user.daily_cost_cap_usd:.2f}"
        print(f"{user.username}\t{user.display_name}\t{user.created_at}\tdaily_cost_cap={cap}")
    return 0


def cmd_set_cap(store: SessionStore, username: str, amount: str) -> int:
    if amount == "clear":
        cap: Optional[float] = None
    else:
        try:
            cap = float(amount)
        except ValueError:
            print(f"Invalid amount {amount!r} - expected a number or the literal 'clear'.", file=sys.stderr)
            return 1
        if cap < 0:
            print("Amount must not be negative.", file=sys.stderr)
            return 1

    if not store.set_user_daily_cost_cap(username, cap):
        print(f"No such user {username!r}.", file=sys.stderr)
        return 1

    label = "cleared (uses the settings.yaml default)" if cap is None else f"${cap:.2f}/day"
    print(f"Set {username!r}'s daily cost cap: {label}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("add", help="Prompt for username, display name, and password.")
    remove_parser = subparsers.add_parser("remove", help="Remove a user by username.")
    remove_parser.add_argument("username")
    subparsers.add_parser("list", help="List all users.")
    set_cap_parser = subparsers.add_parser(
        "set-cap", help="Set (or clear) a user's per-user daily cost cap override."
    )
    set_cap_parser.add_argument("username")
    set_cap_parser.add_argument("amount", help="A dollar amount (e.g. 2.50), or the literal 'clear'.")
    args = parser.parse_args()

    store = SessionStore()

    if args.command == "add":
        return cmd_add(store)
    if args.command == "remove":
        return cmd_remove(store, args.username)
    if args.command == "list":
        return cmd_list(store)
    if args.command == "set-cap":
        return cmd_set_cap(store, args.username, args.amount)
    parser.error(f"Unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
