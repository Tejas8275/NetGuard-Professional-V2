"""Reset an existing NetGuard local Administrator password.

Run this only while signed into the same Windows account that owns the
NetGuard local data. The new password is requested without echoing it and is
never accepted as a command-line argument.
"""
import argparse
import getpass
import sys

from core.recovery import AdminRecoveryError, administrator_usernames, reset_admin_password
from core.storage import load_users, save_users


def main():
    parser = argparse.ArgumentParser(description='Reset an existing local NetGuard Administrator password.')
    parser.add_argument('--username', help='Administrator username. Required when multiple administrators exist.')
    parser.add_argument(
        '--promote-existing', action='store_true',
        help='Explicitly promote an existing local user when no Administrator account exists.',
    )
    args = parser.parse_args()

    users = load_users()
    administrators = administrator_usernames(users)
    if not administrators:
        if not args.promote_existing:
            print(
                'No local Administrator account was found. Re-run with --username <existing-user> --promote-existing '
                'to recover local administration.',
                file=sys.stderr,
            )
            return 1
        if not args.username:
            print('Specify the existing local user with --username when using --promote-existing.', file=sys.stderr)
            return 1

    username = args.username
    if not username:
        if len(administrators) != 1:
            print('Multiple Administrator accounts exist. Re-run with --username <administrator-name>.', file=sys.stderr)
            return 1
        username = administrators[0]

    password = getpass.getpass('New administrator password: ')
    confirmation = getpass.getpass('Confirm new administrator password: ')
    if password != confirmation:
        print('Passwords do not match. No changes were made.', file=sys.stderr)
        return 1

    was_administrator = str(users.get(str(username).strip().lower(), {}).get('role', '')).strip().lower() == 'admin'
    try:
        updated = reset_admin_password(users, username, password, promote_existing=args.promote_existing)
    except AdminRecoveryError as error:
        print(f'Password reset failed: {error}', file=sys.stderr)
        return 1

    save_users(users)
    action = 'promoted and reset' if not was_administrator else 'reset'
    print(f'Password {action} successfully for Administrator account "{updated.get("username", username)}".')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
