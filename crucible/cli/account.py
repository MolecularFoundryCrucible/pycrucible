#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Account subcommand — self-service profile management for the authenticated user.

These commands operate on the caller's own account (no admin required).
For admin operations on other users, see 'crucible user'.
"""

import sys
import logging

logger = logging.getLogger(__name__)

from . import term


def register_subcommand(subparsers):
    parser = subparsers.add_parser(
        'account',
        help='Manage your own account (show, edit, set-username, api-key)',
        description='Self-service account management. No admin required.',
    )
    sub = parser.add_subparsers(dest='account_command', metavar='COMMAND')
    sub.required = True

    _register_show(sub)
    _register_edit(sub)
    _register_set_username(sub)
    _register_api_key(sub)


def _register_show(subparsers):
    parser = subparsers.add_parser(
        'show',
        help='Show your profile',
        description='Display your account profile.',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible account show
    crucible account show --json
""",
    )
    parser.add_argument('--json', action='store_true', default=False, help='Output as JSON')
    parser.set_defaults(func=_execute_show)


def _register_edit(subparsers):
    parser = subparsers.add_parser(
        'edit',
        help='Edit your profile in $EDITOR',
        description='Open your profile in $EDITOR and update on save. '
                    'Editable fields: username, first_name, last_name, email.',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible account edit
    EDITOR=vim crucible account edit
""",
    )
    parser.set_defaults(func=_execute_edit)


def _register_set_username(subparsers):
    parser = subparsers.add_parser(
        'set-username',
        help='Set or clear your username',
        description='Set your username without opening an editor. '
                    'Format: lowercase letters, digits, hyphens, underscores; 3-32 chars.',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible account set-username fabrice
    crucible account set-username --clear
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('username', metavar='USERNAME', nargs='?', default=None,
                       help='New username')
    group.add_argument('--clear', action='store_true', default=False,
                       help='Remove your username')
    parser.set_defaults(func=_execute_set_username)


def _register_api_key(subparsers):
    parser = subparsers.add_parser(
        'api-key',
        help='Show your API key',
        description='Display the API key associated with your account.',
    )
    parser.set_defaults(func=_execute_api_key)


def _show_profile(user):
    _p = term.field_printer(12)
    term.header("Account")
    _p("Username", user.get('username') or term.dim('(not set)'))
    first = user.get('first_name') or ''
    last  = user.get('last_name') or ''
    _p("Name",  ' '.join(p for p in (first, last) if p) or None)
    uid = user.get('orcid') or user.get('unique_id')
    _p("ORCID",  term.orcid_link(uid))
    _p("Email",  user.get('email'))
    if user.get('is_service_account'):
        _p("Type", "service account")


def _execute_show(args):
    from crucible.client import CrucibleClient
    try:
        user = CrucibleClient().users.me()
        if user is None:
            logger.error("No user record found for the current API key - "
                         "the account may not be fully set up yet")
            sys.exit(1)
        if getattr(args, 'json', False):
            import json
            print(json.dumps(user, indent=2, default=str))
        else:
            _show_profile(user)
    except Exception as e:
        logger.error(f"Error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _execute_edit(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        user = client.users.me()
        if user is None:
            logger.error("No user record found for the current API key")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        sys.exit(1)

    editable = {
        'username':   user.get('username'),
        'first_name': user.get('first_name'),
        'last_name':  user.get('last_name'),
        'email':      user.get('email'),
    }

    try:
        edited = term.open_editor_json(editable)
    except (RuntimeError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)

    if edited is None:
        logger.info("No changes.")
        return

    changes = {k: v for k, v in edited.items() if v != editable.get(k)}
    if not changes:
        logger.info("No changes.")
        return

    try:
        result = client.users.update_me(**changes)
        term.header("Changes")
        term.diff(editable, {k: edited[k] for k in changes})
        _show_profile(result)
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _execute_set_username(args):
    from crucible.client import CrucibleClient
    try:
        username = None if args.clear else args.username
        result = CrucibleClient().users.update_me(username=username)
        if username:
            logger.info(f"Username set to: {username}")
        else:
            logger.info("Username cleared.")
        _show_profile(result)
    except Exception as e:
        logger.error(f"Error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _execute_api_key(args):
    import requests as _req
    from crucible.client import CrucibleClient
    try:
        key = CrucibleClient().users.get_api_key()
        _p = term.field_printer(8)
        term.header("API Key")
        _p("Key", key)
    except _req.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            logger.error("No API key found for this account. "
                         "Use the web interface to generate one.")
        else:
            logger.error(f"Error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)
