"""CLI for managing Coffee Core Router users (Brew 43).

The only way to create a user - there is no signup endpoint or page.
This is how a family adds members, not a public registration flow. See
docs/design/auth-projects-chat-management-design.md Section 3.2.

Usage (run from the repository root):
    python router/tools/manage_users.py add
    python router/tools/manage_users.py remove <username>
    python router/tools/manage_users.py list
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

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
        print(f"{user.username}\t{user.display_name}\t{user.created_at}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("add", help="Prompt for username, display name, and password.")
    remove_parser = subparsers.add_parser("remove", help="Remove a user by username.")
    remove_parser.add_argument("username")
    subparsers.add_parser("list", help="List all users.")
    args = parser.parse_args()

    store = SessionStore()

    if args.command == "add":
        return cmd_add(store)
    if args.command == "remove":
        return cmd_remove(store, args.username)
    if args.command == "list":
        return cmd_list(store)
    parser.error(f"Unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
