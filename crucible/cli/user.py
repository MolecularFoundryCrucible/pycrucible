#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User subcommand for Crucible CLI.

Provides user-related operations: get, create.
"""

import sys
import logging
import json
import re

logger = logging.getLogger(__name__)

from . import term
from ..config import config as _config


def register_subcommand(subparsers):
    """
    Register the user subcommand with the main parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    parser = subparsers.add_parser(
        'user',
        help='User operations (get, create, list)',
        description='Manage Crucible users (requires admin permissions)',
    )

    # User subcommands
    user_subparsers = parser.add_subparsers(
        title='user commands',
        dest='user_command',
        help='Available user operations'
    )

    # Register individual user commands
    _register_get(user_subparsers)
    _register_search(user_subparsers)
    _register_create(user_subparsers)
    _register_update(user_subparsers)
    _register_edit(user_subparsers)
    _register_list(user_subparsers)
    _register_list_datasets(user_subparsers)
    _register_check_access(user_subparsers)
    _register_list_access_groups(user_subparsers)
    _register_add_access_group(user_subparsers)
    _register_remove_access_group(user_subparsers)
    _register_list_projects(user_subparsers)


def _register_get(subparsers):
    """Register the 'user get' subcommand."""
    parser = subparsers.add_parser(
        'get',
        help='Get user by ORCID, username, or email',
        description='Retrieve user information (requires admin permissions)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user get 0000-0002-1825-0097
    crucible user get fabrice
    crucible user get user@example.com
"""
    )

    parser.add_argument('user', metavar='USER', nargs='?', default=None,
                        help='ORCID, username, or email of the user')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--orcid',    metavar='ORCID',    help='(deprecated, use positional USER)')
    group.add_argument('-u', '--username', metavar='USERNAME',  help='(deprecated, use positional USER)')
    group.add_argument('--email',    metavar='EMAIL',     help='(deprecated, use positional USER)')

    parser.add_argument('--json', action='store_true', default=False, help='Output as JSON')

    parser.set_defaults(func=_execute_get)


def _register_search(subparsers):
    parser = subparsers.add_parser(
        'search',
        help='Search for users by name or username',
        description='Search users by name or username. Available to all authenticated users — '
                    'no admin required. Returns up to 50 results.',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user search fabrice
    crucible user search ron
""",
    )
    parser.add_argument('query', metavar='TERM', help='Search term')
    parser.set_defaults(func=_execute_search)


def _execute_search(args):
    """Execute 'user search'."""
    if len(args.query) < 3:
        logger.error("Search term must be at least 3 characters")
        sys.exit(1)
    from crucible.client import CrucibleClient
    try:
        users = CrucibleClient().users.search(args.query)

        term.header(f"Users matching '{args.query}' ({len(users)})")
        if not users:
            print(f"  {term.dim('No users found.')}")
            return

        rows = []
        for u in users:
            username = u.get('username') or '-'
            name  = term.fmt_name(u, default='-', fallback_username=False)
            orcid = term.orcid_link(u.get('unique_id')) or '-'
            rows.append((username, name, orcid))
        term.table(rows, ['Username', 'Name', 'ORCID'], max_widths=[20, 25, 19])

    except Exception as e:
        from .helpers import fail
        fail("", e, args)


def _register_create(subparsers):
    """Register the 'user create' subcommand."""
    parser = subparsers.add_parser(
        'create',
        help='Create a new user',
        description='Add a new user to Crucible (requires admin permissions)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    # Interactive mode (prompts for input)
    crucible user create

    # Command-line mode (all arguments provided)
    crucible user create --orcid 0000-0002-1825-0097 \\
        --first-name "Jane" --last-name "Doe" \\
        --email "jane@example.com" \\
        --projects project1,project2
"""
    )

    parser.add_argument('--orcid',                 metavar='ORCID',    help='User ORCID identifier. If not provided, will prompt interactively.')
    parser.add_argument('-f', '--first-name',  dest='first_name', metavar='NAME',     help='First name. If not provided, will prompt interactively.')
    parser.add_argument('-l', '--last-name',   dest='last_name',  metavar='NAME',     help='Last name. If not provided, will prompt interactively.')
    parser.add_argument('--email',                 metavar='EMAIL',    help='Email address (optional)')
    parser.add_argument('-u', '--username',         metavar='USERNAME', help='Username (optional, 3-32 chars: lowercase letters/digits/hyphens/underscores)')
    parser.add_argument('-p', '--projects',         metavar='IDS',      help='Comma-separated project IDs (optional)')

    parser.set_defaults(func=_execute_create)


def _register_list(subparsers):
    """Register the 'user list' subcommand."""
    parser = subparsers.add_parser(
        'list',
        help='List all users',
        description='List all users in the system (requires admin permissions)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user list
    crucible user list --limit 50
"""
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=_config.default_limit,
        metavar='N',
        help=f'Maximum number of users to return (default: {_config.default_limit})'
    )

    parser.add_argument('-u', '--username', metavar='USERNAME', default=None,
                        help='Filter by username (partial match)')

    parser.set_defaults(func=_execute_list)


def _show_user(user):
    """Display user fields."""
    _p = term.field_printer(16)

    full_name = term.fmt_name(user, fallback_username=False)
    uid = user.get('unique_id')

    term.header("User")
    _p("Username", user.get('username') or term.dim('(not set)'))
    _p("Name",     full_name)
    _p("ORCID",    term.orcid_link(uid))
    _p("Email",    user.get('email'))
    if user.get('is_service_account'):
        _p("Type", "service account")


def _execute_get(args):
    """Execute the 'user get' subcommand."""
    from crucible.client import CrucibleClient
    from .helpers import parse_user_ref
    import warnings

    orcid    = getattr(args, 'orcid', None)
    username = getattr(args, 'username', None)
    email    = getattr(args, 'email', None)
    user_ref = getattr(args, 'user', None)

    if orcid or username or email:
        warnings.warn(
            "--orcid/--username/--email are deprecated; pass the identifier "
            "positionally instead: crucible user get USER",
            DeprecationWarning, stacklevel=2,
        )
        ref_kwargs = {'orcid': orcid, 'username': username, 'email': email}
        identifier = orcid or username or email
    elif user_ref:
        ref_kwargs = parse_user_ref(user_ref)
        identifier = user_ref
    else:
        logger.error("Provide a user identifier: crucible user get USER")
        sys.exit(1)

    try:
        client = CrucibleClient()
        user = client.users.get(**ref_kwargs)

        if user is None:
            logger.error(f"User not found: {identifier}")
            sys.exit(1)

        if getattr(args, 'json', False):
            import json
            print(json.dumps(user, indent=2, default=str))
        else:
            _show_user(user)

    except Exception as e:
        from .helpers import fail
        fail("retrieving user", e, args)


def _execute_create(args):
    """Execute the 'user create' subcommand."""
    from crucible.client import CrucibleClient
    # Interactive mode if required arguments are missing
    orcid = args.orcid
    first_name = args.first_name
    last_name = args.last_name
    email = args.email
    projects = args.projects

    interactive = orcid is None or first_name is None or last_name is None
    if interactive:
        term.header("Create User")
        print("")

    # Prompt for ORCID
    if orcid is None:
        while True:
            orcid = input("ORCID (format: 0000-0000-0000-000X): ").strip()
            if orcid:
                if re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$', orcid):
                    break
                else:
                    logger.error("Invalid ORCID format. Expected: 0000-0000-0000-000X")
            else:
                logger.error("ORCID is required.")

    # Prompt for first name
    if first_name is None:
        while True:
            first_name = input("First name: ").strip()
            if first_name:
                break
            else:
                logger.error("First name is required.")

    # Prompt for last name
    if last_name is None:
        while True:
            last_name = input("Last name: ").strip()
            if last_name:
                break
            else:
                logger.error("Last name is required.")

    # Optional fields — only prompt in interactive mode
    if interactive:
        if email is None:
            email_input = input("Email (optional, press Enter to skip): ").strip()
            if email_input:
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_input):
                    email = email_input
                else:
                    logger.warning("Invalid email format. Skipping.")

        if projects is None:
            projects_input = input("Project IDs (comma-separated, optional, press Enter to skip): ").strip()
            if projects_input:
                projects = projects_input

    try:
        from crucible.models import User
        client = CrucibleClient()

        user = User(
            unique_id=orcid,
            username=getattr(args, 'username', None) or None,
            first_name=first_name,
            last_name=last_name,
            email=email or None,
        )
        project_ids = [p.strip() for p in projects.split(',')] if projects else []
        result = client.users.create(user, project_ids=project_ids)

        logger.info("✓ User created")
        _show_user(result)

    except Exception as e:
        from .helpers import fail
        fail("creating user", e, args)


def _register_update(subparsers):
    """Register the 'user update' subcommand."""
    parser = subparsers.add_parser(
        'update',
        help='Update a user record',
        description='Partially update a user record (requires admin permissions)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user update 0000-0002-1825-0097 --first-name Jane
    crucible user update fabrice --email jane@example.com --last-name Smith
"""
    )
    parser.add_argument('user', metavar='USER', help='ORCID, username, or email of the user to update')
    parser.add_argument('-f', '--first-name',  dest='first_name',    metavar='NAME',     help='First name')
    parser.add_argument('-l', '--last-name',   dest='last_name',     metavar='NAME',     help='Last name')
    parser.add_argument('--email',             dest='email',          metavar='EMAIL',    help='Email address')
    parser.add_argument('-u', '--username',    dest='username',       metavar='USERNAME', help='Username')
    parser.add_argument('--clear-username',    dest='clear_username', action='store_true',
                        help='Remove the username (set to null)')
    parser.add_argument('--service-account',    dest='is_service_account', action='store_true',
                        help='Mark as a service account')
    parser.add_argument('--no-service-account', dest='is_service_account', action='store_false',
                        help='Unmark as a service account')
    parser.set_defaults(func=_execute_update, is_service_account=None)


def _execute_update(args):
    """Execute the 'user update' subcommand."""
    from crucible.client import CrucibleClient
    from .helpers import resolve_orcid

    fields = {k: v for k, v in {
        'first_name':         args.first_name,
        'last_name':          args.last_name,
        'email':              args.email,
        'username':           args.username,
        'is_service_account': args.is_service_account,
    }.items() if v is not None}

    if getattr(args, 'clear_username', False):
        fields['username'] = None

    if not fields:
        logger.error("No fields to update. Provide at least one of: --first-name, --last-name, --email, --username, --clear-username, --service-account")
        sys.exit(1)

    try:
        client = CrucibleClient()
        orcid = resolve_orcid(client, args.user)
        result = client.users.update(orcid, **fields)
        logger.info("User updated")
        _show_user(result)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        sys.exit(1)




def _register_edit(subparsers):
    parser = subparsers.add_parser(
        'edit',
        help='Edit a user record in your editor',
        description='Open a user record in your editor and apply changes on save (requires admin permissions)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user edit 0000-0002-1825-0097
    crucible user edit fabrice
    crucible user edit user@lbl.gov
""",
    )
    parser.add_argument('user', metavar='USER', nargs='?', default=None,
                        help='ORCID, username, or email of the user')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--orcid',    '-o', metavar='ORCID',    help='(deprecated, use positional USER)')
    group.add_argument('--username', '-u', metavar='USERNAME', help='(deprecated, use positional USER)')
    group.add_argument('--email',    '-e', metavar='EMAIL',    help='(deprecated, use positional USER)')
    parser.set_defaults(func=_execute_edit)


def _execute_edit(args):
    """Execute the 'user edit' subcommand."""
    from crucible.client import CrucibleClient
    from .helpers import parse_user_ref
    import warnings

    orcid    = getattr(args, 'orcid', None)
    username = getattr(args, 'username', None)
    email    = getattr(args, 'email', None)
    user_ref = getattr(args, 'user', None)

    if orcid or username or email:
        warnings.warn(
            "--orcid/--username/--email are deprecated; pass the identifier "
            "positionally instead: crucible user edit USER",
            DeprecationWarning, stacklevel=2,
        )
        ref_kwargs = {'orcid': orcid, 'username': username, 'email': email}
    elif user_ref:
        ref_kwargs = parse_user_ref(user_ref)
    else:
        logger.error("Provide a user identifier: crucible user edit USER")
        sys.exit(1)

    try:
        client = CrucibleClient()
        user = client.users.get(**ref_kwargs)
        if user is None:
            logger.error("User not found")
            sys.exit(1)

        orcid = user.get('unique_id')
        if not orcid:
            logger.error("Could not determine user ORCID")
            sys.exit(1)

        _EDITABLE = ('first_name', 'last_name', 'email', 'username', 'is_service_account')
        original = {k: user.get(k) for k in _EDITABLE}

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

        result = client.users.update(orcid, **changes)
        term.header("Changes")
        term.diff(original, {k: result.get(k) for k in changes})

    except Exception as e:
        from .helpers import fail
        fail("", e, args)


def _register_add_access_group(subparsers):
    """Register the 'user add-access-group' subcommand."""
    parser = subparsers.add_parser(
        'add-access-group',
        help='Add a user to an access group',
        description='Add a user to an access group (requires admin permissions)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user add-access-group 0000-0002-1825-0097 my-group
    crucible user add-access-group fabrice my-group
""",
    )
    parser.add_argument('user',       metavar='USER',  help='ORCID, username, or email of the user')
    parser.add_argument('group_name', metavar='GROUP', help='Access group name')
    parser.set_defaults(func=_execute_add_access_group)


def _execute_add_access_group(args):
    """Execute the 'user add-access-group' subcommand."""
    from crucible.client import CrucibleClient
    from .helpers import resolve_orcid
    try:
        client = CrucibleClient()
        orcid = resolve_orcid(client, args.user)
        client.users.add_to_access_group(orcid, args.group_name)
        logger.info(f"Added {args.user} to access group '{args.group_name}'")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        from .helpers import fail
        fail("", e, args)


def _register_remove_access_group(subparsers):
    """Register the 'user remove-access-group' subcommand."""
    parser = subparsers.add_parser(
        'remove-access-group',
        help='Remove a user from an access group',
        description='Remove a user from an access group (requires admin permissions)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user remove-access-group 0000-0002-1825-0097 my-group
    crucible user remove-access-group fabrice my-group
"""
    )
    parser.add_argument('user',       metavar='USER',  help='ORCID, username, or email of the user')
    parser.add_argument('group_name', metavar='GROUP', help='Access group name')
    parser.set_defaults(func=_execute_remove_access_group)


def _execute_remove_access_group(args):
    """Execute the 'user remove-access-group' subcommand."""
    from crucible.client import CrucibleClient
    from .helpers import resolve_orcid
    try:
        client = CrucibleClient()
        orcid = resolve_orcid(client, args.user)
        client.users.remove_from_access_group(orcid, args.group_name)
        logger.info(f"Removed {args.user} from access group '{args.group_name}'")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error removing user from access group: {e}")
        sys.exit(1)


def _execute_list(args):
    """Execute the 'user list' subcommand."""
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        username_filter = getattr(args, 'username', None)
        kwargs = {'username': username_filter} if username_filter else {}
        users = client.users.list(limit=args.limit, **kwargs)

        term.header(f"Users ({len(users)})")

        if not users:
            print(f"  {term.dim('No users found.')}")
            return

        rows = []
        for user in users:
            name     = term.fmt_name(user, default='-', fallback_username=False)
            orcid    = term.orcid_link(user.get('unique_id')) or '-'
            email    = user.get('email') or '-'
            username = user.get('username') or '-'
            rows.append((username, name, orcid, email))
        term.table(rows, ['Username', 'Name', 'ORCID', 'Email'], max_widths=[20, 25, 19, 35])

    except Exception as e:
        from .helpers import fail
        fail("listing users", e, args)


def _register_list_datasets(subparsers):
    """Register the 'user list-datasets' subcommand."""
    parser = subparsers.add_parser(
        'list-datasets',
        help='List datasets accessible to a user',
        description=(
            'List dataset MFIDs accessible to a user. Inspecting another user '
            'requires platform-administrator permissions.'
        ),
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user list-datasets 0000-0002-1825-0097
    crucible user list-datasets fabrice
"""
    )
    parser.add_argument('user', metavar='USER', help='ORCID, username, or email of the user')
    parser.add_argument(
        '--limit', type=int, default=_config.default_limit, metavar='N',
        help=f'Maximum number of datasets to return (default: {_config.default_limit})',
    )
    parser.set_defaults(func=_execute_list_datasets)


def _register_check_access(subparsers):
    """Register the 'user check-access' subcommand."""
    parser = subparsers.add_parser(
        'check-access',
        help='Check user access to a dataset',
        description='Show a user\'s effective access role on a dataset',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user check-access 0000-0002-1825-0097 0tcbwt4cp9x1z000bazhkv5gkg
    crucible user check-access fabrice 0tcbwt4cp9x1z000bazhkv5gkg
"""
    )
    parser.add_argument('user', metavar='USER', help='ORCID, username, or email of the user')
    parser.add_argument('dataset_id', metavar='DATASET_MFID', help='Dataset MFID')
    parser.set_defaults(func=_execute_check_access)


def _register_list_access_groups(subparsers):
    """Register the 'user list-access-groups' subcommand."""
    import argparse
    parser = subparsers.add_parser(
        'list-access-groups',
        help='List access groups for a user',
        description="List the access groups a user belongs to",
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user list-access-groups 0000-0002-1825-0097
    crucible user list-access-groups fabrice
"""
    )
    parser.add_argument('user', metavar='USER', help='ORCID, username, or email of the user')
    parser.set_defaults(func=_execute_list_access_groups)


def _register_list_projects(subparsers):
    """Register the 'user list-projects' subcommand."""
    import argparse
    parser = subparsers.add_parser(
        'list-projects',
        help='List projects for a user',
        description='List projects a user is associated with',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible user list-projects 0000-0002-1825-0097
    crucible user list-projects fabrice
"""
    )
    parser.add_argument('user', metavar='USER', help='ORCID, username, or email of the user')
    parser.set_defaults(func=_execute_list_projects)


def _execute_list_datasets(args):
    """Execute the 'user list-datasets' subcommand."""
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        datasets = client.datasets.list(
            accessible_to_user=args.user,
            limit=args.limit,
        )
        dataset_ids = [dataset['unique_id'] for dataset in datasets]

        term.header(f"Datasets · {args.user} ({len(dataset_ids)})")
        if not dataset_ids:
            print(f"  {term.dim('No datasets found.')}")
            return
        for dsid in dataset_ids:
            print(f"  {term.cyan(dsid)}")

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        from .helpers import fail
        fail("listing user datasets", e, args)


def _execute_check_access(args):
    """Execute the 'user check-access' subcommand."""
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        access = client.users.check_dataset_access(args.user, args.dataset_id)

        _p = term.field_printer(14)

        term.header(f"Access · {args.dataset_id}")
        _p("User", access.user_id)
        _p("Effective", access.effective_access)

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        from .helpers import fail
        fail("checking access", e, args)


def _execute_list_access_groups(args):
    """Execute the 'user list-access-groups' subcommand."""
    from crucible.client import CrucibleClient
    from .helpers import resolve_orcid
    try:
        client = CrucibleClient()
        orcid = resolve_orcid(client, args.user)
        groups = client.users.list_access_groups(orcid)

        term.header(f"Access Groups · {args.user} ({len(groups)})")
        if not groups:
            print(f"  {term.dim('No access groups found.')}")
            return
        for g in groups:
            print(f"  {g}")

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        from .helpers import fail
        fail("retrieving access groups", e, args)


def _execute_list_projects(args):
    """Execute the 'user list-projects' subcommand."""
    from crucible.client import CrucibleClient
    from .helpers import resolve_orcid
    try:
        client = CrucibleClient()
        orcid = resolve_orcid(client, args.user)
        projects = client.users.get_projects(orcid)

        term.header(f"Projects · {args.user} ({len(projects)})")
        if not projects:
            print(f"  {term.dim('No projects found.')}")
            return

        rows = [
            (
                p.get('project_id') or '-',
                p.get('title') or '-',
                p.get('organization') or '-',
            )
            for p in projects
        ]
        term.table(rows, ['ID', 'Title', 'Organization'], max_widths=[20, 30, 20])

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        from .helpers import fail
        fail("retrieving user projects", e, args)
