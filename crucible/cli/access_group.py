#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Access group join-request subcommand.

Lets a user request to join an access group (currently only projects) and
lets admins/leads review the request. Accessible as both
'crucible access-group' and 'crucible ag'.
"""

import sys
import logging
from . import term

logger = logging.getLogger(__name__)


def register_subcommand(subparsers):
    for name in ('access-group', 'ag'):
        parser = subparsers.add_parser(
            name,
            help='Request and review access-group join requests',
            description='Request to join an access group (project), and review pending requests.',
        )
        ag_subparsers = parser.add_subparsers(dest='ag_command', metavar='COMMAND')
        ag_subparsers.required = True

        _register_request(ag_subparsers)
        _register_list(ag_subparsers)
        _register_mine(ag_subparsers)
        _register_approve(ag_subparsers)
        _register_reject(ag_subparsers)


def _status_label(status):
    if status == 'pending':
        return term.yellow(status)
    if status == 'approved':
        return term.green(status)
    if status == 'rejected':
        return term.red(status)
    return status


def _show_join_request(record, client=None):
    """Print a JoinRequest record."""
    from .helpers import resolve_usernames
    names = resolve_usernames(client, [record.get('requester_id'), record.get('reviewer_id')])
    _p = term.field_printer(16)
    term.header("Join Request")
    _p("Request ID", record.get('id'))
    _p("Group",      record.get('group_name'))
    _p("Status",     _status_label(record.get('status')))
    _p("Reason",     record.get('reason'))
    _p("Requested",  term.fmt_ts(record.get('request_time')))
    _p("Requester",  names.get(record.get('requester_id'), record.get('requester_id')))
    if record.get('reviewer_notes') or record.get('review_time'):
        _p("Review Time",  term.fmt_ts(record.get('review_time')))
        _p("Reviewer",     names.get(record.get('reviewer_id'), record.get('reviewer_id')))
        _p("Review Notes", record.get('reviewer_notes'))


def _table_rows(records, client=None):
    from .helpers import resolve_usernames
    names = resolve_usernames(client, [r.get('requester_id') for r in records])
    rows = []
    for r in records:
        rows.append((
            str(r.get('id', '-')),
            r.get('group_name') or '-',
            _status_label(r.get('status') or '-'),
            names.get(r.get('requester_id'), r.get('requester_id')) or '-',
            term.fmt_date(r.get('request_time')),
        ))
    return rows


# ── request ───────────────────────────────────────────────────────────────────

def _register_request(subparsers):
    parser = subparsers.add_parser(
        'request',
        help='Request to join an access group',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible ag request my-project
    crucible ag request my-project --reason "Need access for XRD analysis"
""",
    )
    parser.add_argument('group_name', metavar='GROUP', help='Access group name (project ID)')
    parser.add_argument('--reason', metavar='TEXT', default=None,
                        help='Optional explanation for the request')
    parser.set_defaults(func=_execute_request)


def _execute_request(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        record = client.access_groups.request_join(args.group_name, reason=args.reason)
        logger.info("✓ Join request submitted")
        _show_join_request(record, client=client)
    except Exception as e:
        logger.error(f"Error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ── list ──────────────────────────────────────────────────────────────────────

def _register_list(subparsers):
    parser = subparsers.add_parser(
        'list',
        help='List join requests (admin, or lead of the given group)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible ag list --group my-project
    crucible ag list --group my-project --status pending
    crucible ag list --status pending
""",
    )
    parser.add_argument('--group', dest='group_name', metavar='GROUP', default=None,
                        help='Filter to one group. Required for a non-admin lead.')
    parser.add_argument('--status', choices=['pending', 'approved', 'rejected'], default=None,
                        help='Filter by status')
    parser.add_argument('--requester', dest='requester_id', metavar='ORCID', default=None,
                        help='Filter to one user\'s requests (admin use)')
    parser.add_argument('--limit', type=int, default=100, metavar='N')
    parser.set_defaults(func=_execute_list)


def _execute_list(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        records = client.access_groups.list_join_requests(
            group_name=args.group_name, status=args.status,
            requester_id=args.requester_id, limit=args.limit,
        )
        term.header(f"Join Requests ({len(records)})")
        if not records:
            print(f"  {term.dim('None found.')}")
            return
        term.table(_table_rows(records, client=client),
                  ['ID', 'Group', 'Status', 'Requester', 'Requested'],
                  max_widths=[6, 20, 10, 20, 12])
    except Exception as e:
        logger.error(f"Error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ── mine ──────────────────────────────────────────────────────────────────────

def _register_mine(subparsers):
    parser = subparsers.add_parser(
        'mine',
        help='List your own join requests',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible ag mine
    crucible ag mine --status pending
""",
    )
    parser.add_argument('--status', choices=['pending', 'approved', 'rejected'], default=None,
                        help='Filter by status')
    parser.add_argument('--limit', type=int, default=100, metavar='N')
    parser.set_defaults(func=_execute_mine)


def _execute_mine(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        records = client.account.join_requests(status=args.status, limit=args.limit)
        term.header(f"My Join Requests ({len(records)})")
        if not records:
            print(f"  {term.dim('None found.')}")
            return
        term.table(_table_rows(records, client=client),
                  ['ID', 'Group', 'Status', 'Requester', 'Requested'],
                  max_widths=[6, 20, 10, 20, 12])
    except Exception as e:
        logger.error(f"Error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ── approve / reject ───────────────────────────────────────────────────────────

def _register_approve(subparsers):
    parser = subparsers.add_parser(
        'approve',
        help='Approve a pending join request (admin or group lead)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible ag approve 42
    crucible ag approve 42 -m "Welcome aboard"
""",
    )
    parser.add_argument('request_id', type=int, metavar='REQUEST_ID', help='Join request ID')
    parser.add_argument('-m', '--message', dest='reviewer_notes', metavar='TEXT', default=None,
                        help='Optional reviewer notes')
    parser.set_defaults(func=_execute_approve)


def _execute_approve(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        record = client.access_groups.approve_join_request(args.request_id,
                                                            reviewer_notes=args.reviewer_notes)
        logger.info(f"✓ Join request {args.request_id} approved")
        _show_join_request(record, client=client)
    except Exception as e:
        logger.error(f"Error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _register_reject(subparsers):
    parser = subparsers.add_parser(
        'reject',
        help='Reject a pending join request (admin or group lead)',
        formatter_class=term.ColorHelpFormatter,
        epilog="""
Examples:
    crucible ag reject 42
    crucible ag reject 42 -m "Not currently accepting new members"
""",
    )
    parser.add_argument('request_id', type=int, metavar='REQUEST_ID', help='Join request ID')
    parser.add_argument('-m', '--message', dest='reviewer_notes', metavar='TEXT', default=None,
                        help='Optional reviewer notes')
    parser.set_defaults(func=_execute_reject)


def _execute_reject(args):
    from crucible.client import CrucibleClient
    try:
        client = CrucibleClient()
        record = client.access_groups.reject_join_request(args.request_id,
                                                           reviewer_notes=args.reviewer_notes)
        logger.info(f"✓ Join request {args.request_id} rejected")
        _show_join_request(record, client=client)
    except Exception as e:
        logger.error(f"Error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)
