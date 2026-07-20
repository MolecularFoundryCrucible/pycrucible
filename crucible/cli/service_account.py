#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service account subcommand — create and manage non-human API users.

Accessible as both 'crucible service-account' and 'crucible sa'.
All operations require admin permissions.
"""

import sys
import logging
from . import term

logger = logging.getLogger(__name__)

_EDITABLE = ('username', 'first_name', 'last_name')


def register_subcommand(subparsers):
    for name in ('service-account', 'sa'):
        parser = subparsers.add_parser(
            name,
            help='Manage service accounts (admin only)',
            description='Create and manage non-human API users with API key authentication.',
        )
        sa_subparsers = parser.add_subparsers(dest='sa_command', metavar='COMMAND')
        sa_subparsers.required = True

        _register_create(sa_subparsers)
        _register_rotate_key(sa_subparsers)
        _register_get(sa_subparsers)
        _register_list(sa_subparsers)
        _register_edit(sa_subparsers)
        _register_update(sa_subparsers)


def _show_sa(sa, key=None):
    """Display a service account record."""
    _p = term.field_printer(14)
    term.header("Service Account")
    _p("MFID",     sa.get('unique_id'))
    _p("Username", sa.get('username'))
    if sa.get('first_name') or sa.get('last_name'):
        name = ' '.join(filter(None, [sa.get('first_name'), sa.get('last_name')]))
        _p("Name", name)
    if key:
        print()
        print(f"  {term.yellow('API Key')}  {term.bold(key)}")
        print(f"  {term.dim('Store this now — it will not be shown again.')}")


def _resolve_sa(client, unique_id=None, username=None):
    """Resolve a service account by unique_id or username, return the record."""
    sa = client.service_accounts.get(unique_id=unique_id, username=username)
    if sa is None:
        logger.error("Service account not found")
        sys.exit(1)
    return sa


def _register_create(subparsers):
    parser = subparsers.add_parser(
        'create',
        help='Create a new service account',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible sa create --username nirvana-sa
    crucible sa create --username nirvana-sa --unique-id 0th7...
""",
    )
    parser.add_argument('--username', '-u', required=True, metavar='USERNAME',
                        help='Unique username (lowercase, letters/digits/hyphens/underscores)')
    parser.add_argument('--unique-id', metavar='MFID',
                        help='Optional MFID — server generates one if omitted')
    parser.set_defaults(func=_execute_create)


def _execute_create(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        result = client.service_accounts.create(
            username=args.username,
            unique_id=getattr(args, 'unique_id', None),
        )
        _show_sa(result, key=result.get('api_key'))
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def _register_rotate_key(subparsers):
    parser = subparsers.add_parser(
        'rotate-key',
        help='Generate a new API key, invalidating the old one',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible sa rotate-key --unique-id 0th7...
    crucible sa rotate-key --username nirvana-sa
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--unique-id', '-o', metavar='MFID',     help='Service account MFID')
    group.add_argument('--username',  '-u', metavar='USERNAME',  help='Service account username')
    parser.set_defaults(func=_execute_rotate_key)


def _execute_rotate_key(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        uid = getattr(args, 'unique_id', None)
        if not uid:
            sa = _resolve_sa(client, username=args.username)
            uid = sa.get('unique_id')
        result = client.service_accounts.rotate_key(uid)
        _show_sa(result, key=result.get('api_key'))
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def _register_get(subparsers):
    parser = subparsers.add_parser(
        'get',
        help='Show a service account',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible sa get --unique-id 0th7...
    crucible sa get --username nirvana-sa
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--unique-id', '-o', metavar='MFID',    help='Service account MFID')
    group.add_argument('--username',  '-u', metavar='USERNAME', help='Service account username')
    parser.set_defaults(func=_execute_get)


def _execute_get(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        sa = _resolve_sa(client, unique_id=getattr(args, 'unique_id', None),
                         username=getattr(args, 'username', None))
        _show_sa(sa)
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def _register_list(subparsers):
    parser = subparsers.add_parser(
        'list',
        help='List all service accounts',
        formatter_class=term.ColorHelpFormatter,
    )
    parser.add_argument('--limit', type=int, default=100, metavar='N')
    parser.set_defaults(func=_execute_list)


def _execute_list(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        accounts = client.service_accounts.list(limit=args.limit)
        term.header(f"Service Accounts ({len(accounts)})")
        if not accounts:
            print(f"  {term.dim('None found.')}")
            return
        rows = []
        for sa in accounts:
            rows.append((sa.get('username') or '-', sa.get('unique_id') or '-'))
        term.table(rows, ['Username', 'MFID'], max_widths=[30, 30])
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def _register_edit(subparsers):
    parser = subparsers.add_parser(
        'edit',
        help='Edit a service account in your editor',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible sa edit --unique-id 0th7...
    crucible sa edit --username nirvana-sa
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--unique-id', '-o', metavar='MFID',    help='Service account MFID')
    group.add_argument('--username',  '-u', metavar='USERNAME', help='Service account username')
    parser.set_defaults(func=_execute_edit)


def _execute_edit(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        sa = _resolve_sa(client, unique_id=getattr(args, 'unique_id', None),
                         username=getattr(args, 'username', None))
        uid = sa.get('unique_id')
        original = {k: sa.get(k) for k in _EDITABLE}

        try:
            edited = term.open_editor_json(original)
        except (RuntimeError, ValueError) as e:
            logger.error(str(e))
            sys.exit(1)

        if edited is None:
            logger.info("No changes.")
            return

        changes = {k: v for k, v in edited.items() if k in _EDITABLE and v != original.get(k)}
        if not changes:
            logger.info("No changes.")
            return

        result = client.service_accounts.update(uid, **changes)
        term.header("Changes")
        term.diff(original, {k: result.get(k) for k in changes})

    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def _register_update(subparsers):
    parser = subparsers.add_parser(
        'update',
        help='Update a service account with named flags',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible sa update --username nirvana-sa --new-username nirvana-v2
    crucible sa update --unique-id 0th7... --first-name Nirvana
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--unique-id', '-o', metavar='MFID',    help='Service account MFID')
    group.add_argument('--username',  '-u', metavar='USERNAME', help='Service account username')
    parser.add_argument('--new-username',  dest='new_username',  metavar='USERNAME', help='New username')
    parser.add_argument('--first-name',    dest='first_name',    metavar='NAME',     help='First name')
    parser.add_argument('--last-name',     dest='last_name',     metavar='NAME',     help='Last name')
    parser.set_defaults(func=_execute_update)


def _execute_update(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        sa = _resolve_sa(client, unique_id=getattr(args, 'unique_id', None),
                         username=getattr(args, 'username', None))
        uid = sa.get('unique_id')

        fields = {k: v for k, v in {
            'username':   getattr(args, 'new_username', None),
            'first_name': getattr(args, 'first_name', None),
            'last_name':  getattr(args, 'last_name', None),
        }.items() if v is not None}

        if not fields:
            logger.error("No fields to update.")
            sys.exit(1)

        result = client.service_accounts.update(uid, **fields)
        _show_sa(result)

    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
