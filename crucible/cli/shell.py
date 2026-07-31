#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive shell for the Crucible CLI.

Starts when `crucible` is invoked with no arguments.
Uses prompt_toolkit if available, falls back to readline + input().
"""

import os
import sys
import re as _re
import time
import html as _html
import shlex
import shutil
import threading
import itertools
import logging
from collections import deque
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from . import term

logger = logging.getLogger(__name__)

_PROMPT = "crucible> "


def _get_subparser_map(parser):
    """Return {name: subparser} for a parser's subcommands, or {} if none."""
    for action in parser._actions:
        if hasattr(action, 'choices') and isinstance(action.choices, dict):
            return action.choices or {}
    return {}


def _vlen(s):
    """Visual (terminal column) width of s; falls back to len() if wcwidth unavailable."""
    try:
        from wcwidth import wcswidth
        w = wcswidth(s)
        return w if w >= 0 else len(s)
    except ImportError:
        return len(s)


_ENTITY_ICONS = {
    'dataset':    '<ansired><b>[ds]</b></ansired>',
    'sample':     '<ansimagenta><b>[s]</b></ansimagenta>',
    'instrument': '<ansicyan><b>[i]</b></ansicyan>',
}


try:
    from prompt_toolkit.completion     import Completer, Completion
    from prompt_toolkit.formatted_text import HTML as _HTML

    class _CrucibleCompleter(Completer):
        """Three-level argparse completer: resource -> subcommand -> flags."""

        def __init__(self, parser, client=None, projects=None, deletions=None,
                     join_requests=None, service_accounts=None, instruments=None, state=None):
            self._top               = _get_subparser_map(parser)
            self._client            = client
            self._projects          = projects  or []
            self._deletions         = deletions or []
            self._join_requests     = join_requests or []
            self._service_accounts  = service_accounts or []
            self._instruments       = instruments or []
            self._unlink_cache      = {}  # mfid -> [(uid, name, entity_type), ...]
            self._user_search_cache = {}  # query -> [(username, name, orcid), ...]
            self._entity_search_cache = {}  # (entity_type, project_id, query) -> [(uid, name), ...]
            self._state             = state or {}

        def _lazy_projects(self):
            if not self._projects and self._client is not None:
                from .helpers import fetch_projects
                self._projects = fetch_projects(self._client)
            return self._projects

        def _lazy_instruments(self):
            if not self._instruments and self._client is not None:
                from .helpers import fetch_instruments
                self._instruments = fetch_instruments(self._client)
            return self._instruments

        def _search_users(self, query):
            """Search users by name/username via the public search endpoint (no admin required).

            Cached per exact query string for the session — cheap and avoids
            re-hitting the API on every keystroke once a prefix was searched.

            Returns [(identifier, name, orcid), ...] where identifier is the
            username if set, else the ORCID (always present, server-assigned) —
            so a matched user is never silently dropped just for lacking a
            username. Callers can tell which case they're in: identifier ==
            orcid means there's no username.
            """
            if query in self._user_search_cache:
                return self._user_search_cache[query]
            results = []
            if self._client is not None:
                try:
                    for u in self._client.users.search(query):
                        orcid = u.get('unique_id') or ''
                        if not orcid:
                            continue
                        identifier = u.get('username') or orcid
                        name = term.fmt_name(u, default='', fallback_username=False)
                        results.append((identifier, name, orcid))
                except Exception:
                    pass
            self._user_search_cache[query] = results
            return results

        def _yield_user_completions(self, prefix):
            """Yield completions for a user-identifier argument: username where
            set, ORCID as a fallback for users without one.

            Requires 3+ characters (matches the `crucible user search` minimum)
            since this hits the live search endpoint rather than a local cache.
            The API does fuzzy/typo-tolerant matching server-side (e.g. "faber"
            -> "roncofaber"), so results aren't re-filtered by prefix here.
            """
            if len(prefix) < 3:
                return
            for identifier, name, orcid in self._search_users(prefix):
                meta = f'{name}  ' if name else ''
                # Only show the ORCID as metadata when it's not already the
                # completion value itself (i.e. the user has a real username).
                meta_orcid = orcid if identifier != orcid else ''
                yield Completion(
                    identifier + ' ',
                    start_position=-len(prefix),
                    display=_HTML(f'<b>{_html.escape(identifier)}</b>'),
                    display_meta=_HTML(f'<ansibrightblack>{_html.escape(meta)}{_html.escape(meta_orcid)}</ansibrightblack>'),
                )

        def _search_entities(self, entity_type, query, project_id=None):
            """Search datasets or samples by name via the public search endpoint.

            Cached per (entity_type, project_id, query) for the session.
            Returns [(unique_id, name), ...].
            """
            key = (entity_type, project_id, query)
            if key in self._entity_search_cache:
                return self._entity_search_cache[key]
            results = []
            if self._client is not None:
                try:
                    resource   = getattr(self._client, entity_type)  # 'datasets' or 'samples'
                    name_field = 'dataset_name' if entity_type == 'datasets' else 'sample_name'
                    for r in resource.search(query, project_id=project_id):
                        uid = r.get('unique_id') or ''
                        if uid:
                            results.append((uid, r.get(name_field) or '(unnamed)'))
                except Exception:
                    pass
            self._entity_search_cache[key] = results
            return results

        def _yield_entity_completions(self, entity_type, arg_text, query, icon):
            """Yield MFID completions (displayed by name) for a dataset/sample name argument.

            Below the 3-char search minimum, falls back to recently-viewed
            entities of this type from session history instead of live search.
            """
            if len(query) < 3:
                for uid, name, rtype in self._state.get('recent_mfids', []):
                    if rtype == entity_type.rstrip('s') and query.lower() in name.lower():
                        yield Completion(
                            uid + ' ',
                            start_position=-len(arg_text),
                            display=_HTML(f'<b>{_html.escape(uid)}</b>'),
                            display_meta=_HTML(f'{icon} <ansibrightblack>{_html.escape(name)}</ansibrightblack>'),
                        )
                return
            project_id = self._state.get('project')
            for uid, name in self._search_entities(entity_type, query, project_id=project_id):
                yield Completion(
                    uid + ' ',
                    start_position=-len(arg_text),
                    display=_HTML(f'<b>{_html.escape(uid)}</b>'),
                    display_meta=_HTML(f'{icon} <ansibrightblack>{_html.escape(name)}</ansibrightblack>'),
                )

        @staticmethod
        def _multiword_arg(text, num_preceding_words):
            """Extract the raw text typed for a positional argument that may
            contain spaces (e.g. an instrument or dataset name), given the
            number of complete words before it (resource + subcommand, etc).

            Returns (arg_text, query): arg_text is the exact trailing text
            (used for start_position so a Completion replaces it precisely),
            query is arg_text with trailing whitespace stripped (what to
            search for). Returns None if that argument hasn't been reached
            yet, or if a flag (a token starting with '-') appears in it,
            meaning the positional was already completed and a flag started.
            """
            parts = text.split(' ', num_preceding_words)
            if len(parts) <= num_preceding_words:
                return None
            arg_text = parts[num_preceding_words]
            if any(tok.startswith('-') for tok in arg_text.split(' ') if tok):
                return None
            return arg_text, arg_text.rstrip()

        def _unlink_neighbors(self, mfid):
            """Return [(uid, name, entity_type)] of entities directly linked to mfid (cached)."""
            if mfid in self._unlink_cache:
                return self._unlink_cache[mfid]
            try:
                graph  = self._client.graphs.get(mfid, recursive=False)
                result = [
                    (node['id'], node.get('name') or '', node.get('entity_type') or '')
                    for node in graph.get('nodes', [])
                    if node.get('id') != mfid
                ]
                self._unlink_cache[mfid] = result
            except Exception:
                result = []
            return result

        # Dispatch table for get_completions(): resource name(s) -> handler method
        # name. Each handler is a generator that yields Completions and returns
        # True if it fully handled the request, or False to fall through to the
        # next matching handler and eventually the generic subcommand/flag
        # completion in _complete_generic(). Order matters only in that a
        # resource name should appear in exactly one entry (verified: no overlaps).
        _RESOURCE_HANDLERS = {
            'debug':           '_complete_debug',
            'use':             '_complete_use',
            'deletion':        '_complete_deletion',
            'ag':              '_complete_access_group',
            'access-group':    '_complete_access_group',
            'sa':              '_complete_service_account',
            'service-account': '_complete_service_account',
            'unlink':          '_complete_unlink',
            'get':             '_complete_recent_mfid',
            'edit':            '_complete_recent_mfid',
            'open':            '_complete_recent_mfid',
            'tree':            '_complete_recent_mfid',
            'user':            '_complete_user',
            'project':         '_complete_project',
            'instrument':      '_complete_instrument',
            'dataset':         '_complete_dataset_or_sample',
            'sample':          '_complete_dataset_or_sample',
            'cast':            '_complete_path',
            'cd':              '_complete_path',
            'ls':              '_complete_path',
        }

        def get_completions(self, document, complete_event):
            text           = document.text_before_cursor
            words          = text.split()
            trailing_space = text.endswith(' ')

            if not words or (len(words) == 1 and not trailing_space):
                prefix = words[0] if words else ''
                candidates = list(self._top) + ['use', 'unuse', 'refresh', 'reload', 'debug', 'cd', 'ls', 'pwd']
                for name in candidates:
                    if name.startswith(prefix):
                        yield Completion(name + ' ', start_position=-len(prefix))
                return

            resource = words[0]
            ctx = (text, words, trailing_space, resource)

            handler_name = self._RESOURCE_HANDLERS.get(resource)
            if handler_name:
                handled = yield from getattr(self, handler_name)(ctx)
                if handled:
                    return

            yield from self._complete_generic(ctx)

        def _complete_debug(self, ctx):
            text, words, trailing_space, resource = ctx
            if len(words) > 2:
                return True
            prefix = words[1] if len(words) == 2 and not trailing_space else ''
            for choice in ('on', 'off'):
                if choice.startswith(prefix):
                    yield Completion(choice + ' ', start_position=-len(prefix))
            return True

        def _complete_use(self, ctx):
            text, words, trailing_space, resource = ctx
            if len(words) > 2 or (trailing_space and len(words) == 2):
                return True
            prefix = words[1] if len(words) == 2 else ''
            for pid, title in self._lazy_projects():
                if pid.startswith(prefix):
                    yield Completion(pid + ' ', start_position=-len(prefix),
                                     display=_HTML(f'<b>{pid}</b>'),
                                     display_meta=_HTML(f'<ansibrightblack>{_html.escape(title)}</ansibrightblack>'))
            return True

        def _complete_deletion(self, ctx):
            text, words, trailing_space, resource = ctx
            if not (len(words) >= 2 and words[1] in ('approve', 'reject', 'get')):
                return False
            already = set(words[2:]) if trailing_space else set(words[2:-1])
            prefix  = '' if trailing_space else words[-1]
            for d in self._deletions:
                did = str(d.get('id', ''))
                if did in already or not did.startswith(prefix):
                    continue
                rtype  = d.get('resource_type') or ''
                name   = (d.get('resource_name') or '')[:15]
                reason = (d.get('reason') or '')[:24]
                parts  = []
                if rtype:
                    parts.append(f'{rtype}')
                if name:
                    parts.append(f'<b>{_html.escape(name)}</b>')
                if reason:
                    parts.append(f'<ansibrightblack>{_html.escape(reason)}</ansibrightblack>')
                yield Completion(
                    did + ' ',
                    start_position=-len(prefix),
                    display=_HTML(f'<b>{did}</b>'),
                    display_meta=_HTML(' | '.join(parts)),
                )
            return True

        def _complete_access_group(self, ctx):
            text, words, trailing_space, resource = ctx
            if len(words) >= 2 and words[1] in ('approve', 'reject', 'get'):
                already = set(words[2:]) if trailing_space else set(words[2:-1])
                prefix  = '' if trailing_space else words[-1]
                for jr in self._join_requests:
                    jid = str(jr.get('id', ''))
                    if jid in already or not jid.startswith(prefix):
                        continue
                    group  = jr.get('group_name') or ''
                    reason = (jr.get('reason') or '')[:24]
                    parts  = []
                    if group:
                        parts.append(f'<b>{_html.escape(group)}</b>')
                    if reason:
                        parts.append(f'<ansibrightblack>{_html.escape(reason)}</ansibrightblack>')
                    yield Completion(
                        jid + ' ',
                        start_position=-len(prefix),
                        display=_HTML(f'<b>{jid}</b>'),
                        display_meta=_HTML(' | '.join(parts)),
                    )
                return True

            if len(words) >= 2 and words[1] == 'request':
                # Complete the GROUP positional (currently always a project_id).
                if trailing_space and len(words) == 2:
                    prefix = ''
                elif not trailing_space and len(words) == 3 and not words[2].startswith('-'):
                    prefix = words[2]
                else:
                    return True  # GROUP already filled
                for pid, title in self._lazy_projects():
                    if pid.startswith(prefix):
                        yield Completion(
                            pid + ' ',
                            start_position=-len(prefix),
                            display=_HTML(f'<b>{pid}</b>'),
                            display_meta=_HTML(f'<ansibrightblack>{_html.escape(title)}</ansibrightblack>'),
                        )
                return True

            return False

        def _complete_service_account(self, ctx):
            text, words, trailing_space, resource = ctx
            if len(words) < 2:
                return False
            # Complete the SA positional (MFID or username) for subcommands that take one.
            _SA_SUBS = {'get', 'rotate-key', 'edit', 'update', 'list-access-groups',
                        'add-access-group', 'remove-access-group'}
            if words[1] not in _SA_SUBS:
                return False
            if trailing_space and len(words) == 2:
                prefix = ''
            elif not trailing_space and len(words) == 3 and not words[2].startswith('-'):
                prefix = words[2]
            else:
                return True  # SA already filled
            prefix_lower = prefix.lower()
            for sa in self._service_accounts:
                username = sa.get('username') or ''
                if not username.lower().startswith(prefix_lower):
                    continue
                name = term.fmt_name(sa, default='', fallback_username=False)
                yield Completion(
                    username + ' ',
                    start_position=-len(prefix),
                    display=_HTML(f'<b>{_html.escape(username)}</b>'),
                    display_meta=_HTML(f'<ansibrightblack>{_html.escape(name)}</ansibrightblack>'),
                )
            return True

        def _complete_unlink(self, ctx):
            text, words, trailing_space, resource = ctx
            if self._client is None:
                return False
            # Positional form: unlink MFID1 MFID2
            # Complete MFID2 from the graph neighbors of MFID1.
            first = None
            prefix = ''
            if trailing_space and len(words) == 2 and not words[1].startswith('-'):
                first, prefix = words[1], ''
            elif not trailing_space and len(words) == 3 \
                    and not words[1].startswith('-') and not words[2].startswith('-'):
                first, prefix = words[1], words[2]
            if not first:
                return False
            for uid, name, etype in self._unlink_neighbors(first):
                if uid.startswith(prefix):
                    icon_html = _ENTITY_ICONS.get(etype, '<ansibrightblack>[?]</ansibrightblack>')
                    meta = f'{icon_html} <ansibrightblack>{_html.escape(name)}</ansibrightblack>'
                    yield Completion(
                        uid + ' ',
                        start_position=-len(prefix),
                        display=_HTML(f'<b>{_html.escape(uid)}</b>'),
                        display_meta=_HTML(meta),
                    )
            return True

        def _complete_recent_mfid(self, ctx):
            text, words, trailing_space, resource = ctx
            # Complete the first positional MFID from recently visited resources.
            if trailing_space and len(words) == 1:
                prefix = ''
                for uid, name, rtype in self._state.get('recent_mfids', []):
                    if uid.startswith(prefix):
                        icon = _ENTITY_ICONS.get(rtype, '<ansibrightblack>[?]</ansibrightblack>')
                        yield Completion(
                            uid + ' ',
                            start_position=-len(prefix),
                            display=_HTML(f'<b>{_html.escape(uid)}</b>'),
                            display_meta=_HTML(f'{icon} <ansibrightblack>{_html.escape(name)}</ansibrightblack>'),
                        )
                return True
            elif not trailing_space and len(words) == 2 and not words[1].startswith('-'):
                prefix = words[1]
                for uid, name, rtype in self._state.get('recent_mfids', []):
                    if uid.startswith(prefix):
                        icon = _ENTITY_ICONS.get(rtype, '<ansibrightblack>[?]</ansibrightblack>')
                        yield Completion(
                            uid + ' ',
                            start_position=-len(prefix),
                            display=_HTML(f'<b>{_html.escape(uid)}</b>'),
                            display_meta=_HTML(f'{icon} <ansibrightblack>{_html.escape(name)}</ansibrightblack>'),
                        )
                return True
            # ID already filled — complete flags from the top-level parser
            parser = self._top.get(resource)
            if parser:
                current_word = '' if trailing_space else words[-1]
                for flag in parser._option_string_actions:
                    if flag.startswith(current_word):
                        yield Completion(flag + ' ', start_position=-len(current_word))
            return True

        def _complete_user(self, ctx):
            text, words, trailing_space, resource = ctx
            if len(words) < 2:
                return False
            # Complete the USER positional (ORCID/username/email) by username search.
            # 'search' is included too — TERM is free text, but showing live
            # matches while typing is useful preview, not just identifier lookup.
            _USER_SUBS = {'get', 'update', 'edit', 'add-access-group', 'remove-access-group',
                          'list-datasets', 'check-access', 'list-access-groups', 'list-projects',
                          'search'}
            if words[1] not in _USER_SUBS:
                return False
            if trailing_space and len(words) == 2:
                prefix = ''
            elif not trailing_space and len(words) == 3 and not words[2].startswith('-'):
                prefix = words[2]
            else:
                return True  # USER already filled
            yield from self._yield_user_completions(prefix)
            return True

        def _complete_project(self, ctx):
            text, words, trailing_space, resource = ctx
            if len(words) < 2:
                return False
            # Complete the PROJECT_ID positional for subcommands that take one.
            _PID_SUBS = {'get', 'update', 'list-users', 'add-user', 'remove-user',
                         'request-join', 'list-join-requests'}
            if words[1] not in _PID_SUBS:
                return False
            if trailing_space and len(words) == 2:
                prefix = ''
            elif not trailing_space and len(words) == 3 and not words[2].startswith('-'):
                prefix = words[2]
            else:
                return True  # project ID already filled
            for pid, title in self._lazy_projects():
                if pid.startswith(prefix):
                    yield Completion(
                        pid + ' ',
                        start_position=-len(prefix),
                        display=_HTML(f'<b>{pid}</b>'),
                        display_meta=_HTML(f'<ansibrightblack>{_html.escape(title)}</ansibrightblack>'),
                    )
            return True

        def _complete_instrument(self, ctx):
            text, words, trailing_space, resource = ctx
            if not (len(words) >= 2 and words[1] == 'get'):
                return False
            # Complete the NAME_OR_ID positional (instrument names may contain spaces).
            span = self._multiword_arg(text, 2)
            if span is None:
                return True  # already past the positional (a flag was typed)
            arg_text, query = span
            query_lower = query.lower()
            for name, uid in self._lazy_instruments():
                if query_lower not in name.lower():
                    continue
                yield Completion(
                    name + ' ',
                    start_position=-len(arg_text),
                    display=_HTML(f'<b>{_html.escape(name)}</b>'),
                    display_meta=_HTML(f'<ansibrightblack>{_html.escape(uid)}</ansibrightblack>'),
                )
            return True

        def _complete_dataset_or_sample(self, ctx):
            text, words, trailing_space, resource = ctx
            if len(words) < 2:
                return False
            # Complete the ID positional (by name, resolving to MFID) for
            # every subcommand except the handful that don't take one.
            _NO_ID_SUBS = {'list', 'create', 'search', 'search-metadata', 'search-md',
                           'parsers', 'ingestors'}
            if words[1] in _NO_ID_SUBS:
                return False
            span = self._multiword_arg(text, 2)
            if span is None:
                # Positional already filled (a flag followed) — fall through
                # to flag completion in _complete_generic().
                return False
            arg_text, query = span
            entity_type = 'datasets' if resource == 'dataset' else 'samples'
            icon = _ENTITY_ICONS.get(resource, '')
            yield from self._yield_entity_completions(entity_type, arg_text, query, icon)
            return True

        def _complete_path(self, ctx):
            text, words, trailing_space, resource = ctx
            current = (words[1] if len(words) == 2 and not trailing_space else
                       '' if trailing_space and len(words) == 1 else None)
            if current is not None and not current.startswith('-'):
                expanded   = os.path.expanduser(current)
                search_dir = os.path.dirname(expanded) or '.'
                prefix     = os.path.basename(expanded)

                results = []

                # For cd: always offer '..' when at a directory boundary
                if resource == 'cd' and '..'.startswith(prefix):
                    remaining = '..'[len(prefix):]
                    results.append((False, '', Completion(
                        remaining + '/',
                        start_position=0,
                        display=_HTML('<ansiblue><b>../</b></ansiblue>'),
                    )))

                try:
                    scan = os.scandir(search_dir)
                except (PermissionError, FileNotFoundError):
                    return True

                with scan:
                    for entry in scan:
                        if not entry.name.startswith(prefix):
                            continue
                        is_dir    = entry.is_dir(follow_symlinks=True)
                        is_hidden = entry.name.startswith('.')
                        is_crux   = entry.name.endswith('.crux')

                        if resource == 'cd'   and not is_dir:   continue
                        if resource == 'cast' and not (is_dir or is_crux): continue

                        display_name    = entry.name + ('/' if is_dir else '')
                        completion_text = entry.name[len(prefix):] + ('/' if is_dir else '')
                        esc = _html.escape(display_name)

                        if is_dir:
                            disp = f'<ansiblue><b>{esc}</b></ansiblue>'
                        elif is_crux:
                            disp = f'<ansiyellow><b>{esc}</b></ansiyellow>'
                        elif is_hidden:
                            disp = f'<ansibrightblack>{esc}</ansibrightblack>'
                        else:
                            disp = esc

                        results.append((is_hidden, display_name.lower(), Completion(
                            completion_text,
                            start_position=0,
                            display=_HTML(disp),
                        )))

                results.sort(key=lambda x: (x[0], x[1]))
                yield from (c for _, _, c in results)
                return True

            # Flag completion for cast
            if resource == 'cast':
                current_word = '' if trailing_space else words[-1]
                if current_word.startswith('-'):
                    cast_parser = self._top.get('cast')
                    if cast_parser:
                        for flag in cast_parser._option_string_actions:
                            if flag.startswith(current_word):
                                yield Completion(flag + ' ', start_position=-len(current_word))
            return True

        def _complete_generic(self, ctx):
            """Fallback completion shared by every resource: subcommand names,
            then (for dataset/sample/user flag values) dynamic flag values,
            then plain flag names from the matched subparser.
            """
            text, words, trailing_space, resource = ctx

            sub_map = _get_subparser_map(self._top.get(resource)) \
                      if resource in self._top else {}

            if len(words) == 1 or (len(words) == 2 and not trailing_space):
                prefix = words[1] if len(words) == 2 else ''
                for name in sub_map:
                    if name.startswith(prefix):
                        yield Completion(name + ' ', start_position=-len(prefix))
                return

            subcommand = words[1]

            if resource == 'config' and subcommand == 'set':
                try:
                    from crucible.config.config import Config as _Cfg
                    config_keys = list(_Cfg._CONFIG_MAP)
                except Exception:
                    return
                if not (len(words) == 3 and trailing_space) and len(words) <= 3:
                    prefix = words[2] if len(words) == 3 else ''
                    for key in config_keys:
                        if key.startswith(prefix):
                            yield Completion(key + ' ', start_position=-len(prefix))
                elif len(words) >= 3 and words[2] == 'current_project':
                    prefix = words[3] if len(words) == 4 and not trailing_space else ''
                    for pid, title in self._lazy_projects():
                        if pid.startswith(prefix):
                            yield Completion(pid + ' ', start_position=-len(prefix),
                                             display=_HTML(f'<b>{pid}</b>'),
                                             display_meta=_HTML(f'<ansibrightblack>{_html.escape(title)}</ansibrightblack>'))
                return

            sub_parser  = sub_map.get(subcommand)
            if sub_parser is None:
                return

            current_word = '' if trailing_space else words[-1]
            prev = (words[-1] if trailing_space else words[-2]) if len(words) >= 2 else ''

            _PROJECT_FLAGS = ('--project', '-pid', '--project-id')
            # Flags whose value is a dataset or sample MFID, by resource context.
            # Values here can't contain unquoted spaces (argparse flag values are
            # single tokens), so completion is a plain prefix/substring search
            # rather than the multi-word span logic used for positionals.
            _ENTITY_FLAGS = {
                'dataset': {'-s': 'samples', '--sample': 'samples', '-c': 'datasets', '--child': 'datasets'},
                'sample':  {'-d': 'datasets', '--dataset': 'datasets', '-c': 'samples', '--child': 'samples'},
            }.get(resource, {})

            if current_word and not current_word.startswith('-'):
                # Mid-typing a flag value.
                if prev == '--orcid':
                    yield from self._yield_user_completions(current_word)
                elif prev in _PROJECT_FLAGS:
                    for pid, title in self._lazy_projects():
                        if pid.startswith(current_word):
                            yield Completion(
                                pid + ' ', start_position=-len(current_word),
                                display=_HTML(f'<b>{pid}</b>'),
                                display_meta=_HTML(f'<ansibrightblack>{_html.escape(title)}</ansibrightblack>'),
                            )
                elif prev in _ENTITY_FLAGS:
                    entity_type = _ENTITY_FLAGS[prev]
                    icon = _ENTITY_ICONS.get(entity_type.rstrip('s'), '')
                    yield from self._yield_entity_completions(entity_type, current_word, current_word, icon)
                return

            if not current_word and prev == '--orcid':
                yield from self._yield_user_completions('')
                return

            if not current_word and prev in _PROJECT_FLAGS:
                for pid, title in self._lazy_projects():
                    yield Completion(
                        pid + ' ', start_position=0,
                        display=_HTML(f'<b>{pid}</b>'),
                        display_meta=_HTML(f'<ansibrightblack>{_html.escape(title)}</ansibrightblack>'),
                    )
                return

            if not current_word and prev in _ENTITY_FLAGS:
                entity_type = _ENTITY_FLAGS[prev]
                icon = _ENTITY_ICONS.get(entity_type.rstrip('s'), '')
                yield from self._yield_entity_completions(entity_type, '', '', icon)
                return

            for flag in sub_parser._option_string_actions:
                if flag.startswith(current_word):
                    yield Completion(flag + ' ', start_position=-len(current_word))

except ImportError:
    _CrucibleCompleter = None


class CrucibleShell:
    """Interactive Crucible shell.

    Owns one CrucibleClient instance (self.client), shared mutable state
    (self.state), and the prompt_toolkit completer (self.completer).
    """

    _SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self, parser):
        self.parser    = parser
        self.client    = None
        self.state     = {}
        self.completer = None
        self.is_admin  = False
        self._session  = None         # prompt_toolkit PromptSession
        self._clock_stop = threading.Event()

    def run(self):
        """Start the interactive shell."""
        if _CrucibleCompleter:
            self._run_prompt_toolkit()
        else:
            self._run_readline()

    def _verify_connection(self):
        """Spinner + whoami. Sets self.client. Exits on failure."""
        from crucible.client import CrucibleClient

        _spin_state = {'msg': 'Connecting to Crucible'}
        _stop       = threading.Event()
        _is_tty     = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        _RETRY_RE   = _re.compile(r'Retry\(total=(\d+)')

        def _spin():
            for frame in itertools.cycle(self._SPINNER_FRAMES):
                if _stop.is_set():
                    break
                sys.stdout.write(f'\r  {_spin_state["msg"]}  {frame}')
                sys.stdout.flush()
                time.sleep(0.08)
            sys.stdout.write('\r\033[2K')
            sys.stdout.flush()

        class _RetryToSpinner(logging.Filter):
            def filter(self, record):
                msg = record.getMessage()
                if 'Retrying' not in msg:
                    return True
                m = _RETRY_RE.search(msg)
                n = m.group(1) if m else '?'
                _spin_state['msg'] = f'Retrying... ({n} left)'
                return False

        _filt = _RetryToSpinner()
        for _h in logging.getLogger().handlers:
            _h.addFilter(_filt)

        if _is_tty:
            _spin_thread = threading.Thread(target=_spin, daemon=True)
            _spin_thread.start()
        else:
            print('  Connecting to Crucible...')

        try:
            self.client = CrucibleClient()
            info = self.client.whoami()
        except Exception as e:
            _stop.set()
            if _is_tty:
                _spin_thread.join()
            for _h in logging.getLogger().handlers:
                _h.removeFilter(_filt)
            logger.error(f"Cannot connect to Crucible: {e}")
            sys.exit(1)

        _stop.set()
        if _is_tty:
            _spin_thread.join()
        for _h in logging.getLogger().handlers:
            _h.removeFilter(_filt)

        return info

    def _init_state(self, whoami_info):
        """Populate self.state from startup data."""
        from .helpers import (
            fetch_projects, fetch_deletions, fetch_join_requests, fetch_service_accounts,
            fetch_user_label, fetch_current_project, fetch_current_session, fetch_api_label,
        )
        deletions     = fetch_deletions(self.client)
        join_requests = fetch_join_requests(self.client)
        self.is_admin = deletions is not None
        service_accounts = fetch_service_accounts(self.client) if self.is_admin else None

        self.state = {
            'user_label':        fetch_user_label(self.client, whoami_info),
            'projects':          fetch_projects(self.client),
            'project':           fetch_current_project(),
            'session':           fetch_current_session(),
            'api_label':         fetch_api_label(),
            'debug':             False,
            'deletions':         deletions or [],
            'join_requests':     join_requests or [],
            'service_accounts':  service_accounts or [],
            'recent_mfids':      deque(maxlen=15),
        }

    def refresh(self):
        """Re-fetch projects, user info, deletions, join requests, and service accounts. Updates state + completer."""
        from .helpers import (
            fetch_projects, fetch_deletions, fetch_join_requests, fetch_service_accounts,
            fetch_user_label, fetch_current_project, fetch_current_session, fetch_api_label,
        )
        with ThreadPoolExecutor(max_workers=4) as pool:
            proj_f = pool.submit(fetch_projects,      self.client)
            del_f  = pool.submit(fetch_deletions,     self.client)
            jr_f   = pool.submit(fetch_join_requests, self.client)
            sa_f   = pool.submit(fetch_service_accounts, self.client)
            new_projects         = proj_f.result()
            new_deletions        = del_f.result()
            new_join_requests    = jr_f.result()
            new_service_accounts = sa_f.result()
        self.is_admin = new_deletions is not None
        self.state['projects']         = new_projects
        self.state['user_label']       = fetch_user_label(self.client)
        self.state['project']          = fetch_current_project()
        self.state['session']          = fetch_current_session()
        self.state['api_label']        = fetch_api_label()
        self.state['deletions']        = new_deletions or []
        self.state['join_requests']    = new_join_requests or []
        self.state['service_accounts'] = new_service_accounts or []
        if self.completer is not None:
            self.completer._projects         = new_projects
            self.completer._deletions        = new_deletions
            self.completer._join_requests    = new_join_requests
            self.completer._service_accounts = new_service_accounts
        print(f"Refreshed: {len(new_projects)} projects, user info reloaded.")

    def _toolbar(self):
        from prompt_toolkit.application import get_app
        proj  = self.state.get('project', '')
        sess  = self.state.get('session', '')
        label = f'{proj} / {sess}' if sess else proj
        if len(label) > 22:
            label = label[:21] + '…'
        proj_content = f'🔬 {label}'.ljust(25)
        clock        = datetime.now().strftime('%H:%M')

        left_str  = f' {proj_content} '
        mid_str   = f' 🧸 {self.state.get("user_label", "?")} '
        right_str = f' 🔗 {self.state.get("api_label", "?")}  │  {clock} '
        debug_str = ' DEBUG ' if self.state.get('debug') else ''

        try:
            term_width = get_app().output.get_size().columns
        except Exception:
            term_width = 80

        from prompt_toolkit.formatted_text import HTML
        pad = ' ' * max(0, term_width - _vlen(left_str) - _vlen(mid_str)
                        - len(debug_str) - _vlen(right_str))
        return HTML(
            f'<tb-project>{left_str}</tb-project>'
            f'{mid_str}{pad}'
            f'<tb-debug>{debug_str}</tb-debug>'
            f'<tb-clock>{right_str}</tb-clock>'
        )

    def _clock_tick(self):
        """Background thread: invalidate toolbar once per minute."""
        secs_to_next = 60 - datetime.now().second
        if self._clock_stop.wait(timeout=secs_to_next):
            return
        while not self._clock_stop.is_set():
            try:
                self._session.app.invalidate()
            except Exception:
                pass
            self._clock_stop.wait(timeout=60)

    def _resolve_future(self, last, key, default=None):
        """Resolve a named future from last_resource, returning default on failure."""
        future = last.get(key)
        if future is None:
            return default
        try:
            return future.result(timeout=15)
        except Exception:
            return default

    def _render_resource(self, last):
        """Re-render the cached resource with current verbose/graph flags."""
        try:
            rtype = last['type']
            data  = last['data']
            if not last.get('graph'):
                links = None
            elif '_links_future' in last:
                links = self._resolve_future(last, '_links_future', None)
            else:
                links = data.get('links')
            if rtype == 'dataset':
                from .dataset import _show_dataset
                prefetched = {
                    'keywords': self._resolve_future(last, '_keywords_future', []),
                    'af_list':  self._resolve_future(last, '_files_future', []),
                    'link_map': self._resolve_future(last, '_dl_links_future', {}),
                }
                _show_dataset(data, self.client, verbose=last['verbose'],
                              graph=last['graph'],
                              include_metadata=last.get('include_metadata', False),
                              links=links, prefetched=prefetched)
            elif rtype == 'sample':
                from .sample import _show_sample
                _show_sample(data, self.client, verbose=last['verbose'],
                             graph=last['graph'],
                             include_metadata=last.get('include_metadata', False),
                             links=links)
        except Exception as e:
            logger.error(f"Error rendering resource: {e}")

    def _dispatch(self, line):
        """Parse and execute one command line. Returns False to signal exit."""
        from . import _remap_deprecated, setup_logging

        line = line.strip()
        if not line:
            return True
        if line in ('exit', 'quit'):
            return False
        if line == 'help':
            self.parser.print_help()
            _W = 18
            print()
            term.header("Shell commands")
            for _cmd, _desc in [
                ('use PROJECT',   'switch active project'),
                ('unuse',         'clear active project'),
                ('refresh',       're-fetch projects, user info, deletions'),
                ('reload',        'restart the shell process'),
                ('debug on|off',  'toggle debug logging'),
                ('v',             'toggle verbose view for last fetched resource'),
                ('! CMD',         'run a shell command'),
                ('ls [PATH]',     'list directory'),
                ('cd [PATH]',     'change directory'),
                ('pwd',           'print working directory'),
                ('exit / quit',   'exit the shell'),
            ]:
                print(f"  {term.cyan(_cmd)}{' ' * (_W - len(_cmd))} {_desc}")
            if _CrucibleCompleter:
                print()
                term.header("Keyboard shortcuts")
                for _key, _desc in [
                    ('Alt+V',  'toggle verbose view for last fetched resource'),
                    ('Alt+G',  'toggle graph view for last fetched resource'),
                    ('Alt+R',  'refresh projects, user info, and deletions'),
                    ('Alt+P',  'project picker (type a number or filter text)'),
                    ('Alt+O',  'open last resource in Graph Explorer'),
                    ('Ctrl+L', 'clear screen'),
                ]:
                    print(f"  {term.bold(_key)}{' ' * (_W - len(_key))} {_desc}")
            print()
            return True

        if line.startswith('use ') or line == 'use':
            parts = line.split(None, 1)
            if len(parts) < 2 or not parts[1].strip():
                print("Usage: use <project_id>")
                return True
            project_id = parts[1].strip()
            try:
                import requests as _req
                from crucible.client import CrucibleClient
                project = CrucibleClient().projects.get(project_id)
                if project is None:
                    logger.error(f"Project not found: {project_id}")
                    return True
            except _req.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code in (403, 404):
                    logger.error(f"Project '{project_id}' not found or not accessible")
                else:
                    logger.error(f"Cannot access project '{project_id}': {e}")
                return True
            except Exception as e:
                logger.error(f"Cannot access project '{project_id}': {e}")
                return True
            try:
                from crucible.cli.config import set_config_value
                set_config_value('current_project', project_id)
                set_config_value('current_session', '')
                title = project.get('title') or ''
                label = f"{project_id} - {title}" if title else project_id
                print(f"Switched to project: {label}")
                self.state['project'] = project_id
                self.state['session'] = ''
            except Exception as e:
                logger.error(f"Error switching project: {e}")
            return True

        if line == 'unuse':
            try:
                from crucible.cli.config import set_config_value
                set_config_value('current_project', '')
                set_config_value('current_session', '')
                print("Cleared current project and session.")
                self.state['project'] = '(no project set)'
                self.state['session'] = ''
            except Exception as e:
                logger.error(f"Error clearing project: {e}")
            return True

        if line == 'refresh':
            try:
                from crucible.config import config as _cfg
                _cfg.reload()
            except Exception:
                pass
            self.refresh()
            return True

        if line == 'reload':
            print('\033[2J\033[H', end='', flush=True)
            os.execv(sys.executable, [sys.executable] + sys.argv)

        if line.startswith('!'):
            import subprocess
            cmd = line[1:].strip()
            if cmd:
                subprocess.run(cmd, shell=True)
            return True

        if line == 'pwd':
            print(os.getcwd())
            return True

        if line.startswith('ls') and (len(line) == 2 or line[2] == ' '):
            parts = line.split(None, 1)
            path  = os.path.expanduser(parts[1].strip()) if len(parts) > 1 else '.'
            try:
                entries = sorted(os.scandir(path), key=lambda e: (e.name.startswith('.'), e.name.lower()))
            except (FileNotFoundError, NotADirectoryError) as exc:
                print(f"ls: {exc}")
                return True
            col_width = max((len(e.name) for e in entries), default=0) + 3
            term_width = shutil.get_terminal_size().columns
            cols = max(1, term_width // col_width)
            for i, entry in enumerate(entries):
                display = entry.name + ('/' if entry.is_dir() else '')
                if entry.is_dir():
                    label = term.cyan(display)
                elif entry.name.endswith('.crux'):
                    label = term.bold(display)
                elif entry.name.startswith('.'):
                    label = term.dim(display)
                else:
                    label = display
                pad = ' ' * (col_width - _vlen(display))
                end = '\n' if (i + 1) % cols == 0 or i == len(entries) - 1 else ''
                print(label + pad, end=end)
            return True

        if line.startswith('cd') and (len(line) == 2 or line[2] == ' '):
            parts = line.split(None, 1)
            arg   = parts[1].strip() if len(parts) > 1 else '~'
            if arg == '-':
                oldpwd = self.state.get('oldpwd')
                if not oldpwd:
                    print("cd: no previous directory")
                    return True
                path = oldpwd
            else:
                path = os.path.expanduser(arg)
            try:
                prev = os.getcwd()
                os.chdir(path)
                self.state['oldpwd'] = prev
                if arg == '-':
                    print(os.getcwd())
            except FileNotFoundError:
                print(f"cd: no such directory: {path}")
            except NotADirectoryError:
                print(f"cd: not a directory: {path}")
            return True

        if line == 'v':
            last = self.state.get('last_resource')
            if not last:
                print("No recent get to toggle. Run 'get <id>' first.")
                return True
            last['verbose'] = not last['verbose']
            self._render_resource(last)
            return True

        if line == 'debug' or line.startswith('debug '):
            parts   = line.split()
            current = self.state.get('debug', False)
            if len(parts) == 1:
                print(f"Debug is {'on' if current else 'off'}.")
                return True
            action = parts[1].lower()
            if action not in ('on', 'off'):
                print("Usage: debug on | debug off")
                return True
            on = (action == 'on')
            self.state['debug'] = on
            setup_logging(debug=on)
            print(f"Debug {'enabled' if on else 'disabled'}.")
            return True

        words = line.split()
        try:
            argv = _remap_deprecated(shlex.split(line))
            args = self.parser.parse_args(argv)
            setup_logging(debug=getattr(args, 'debug', False) or self.state.get('debug', False))
            if hasattr(args, 'func'):
                args._shell_state = self.state
                args.func(args)
            else:
                self.parser.print_help()
        except SystemExit:
            pass
        except KeyboardInterrupt:
            print("\nCancelled.")
        except Exception as e:
            logger.error(f"Error: {e}")

        # Re-fetch pending deletions after any deletion command (admin only)
        if (self.is_admin and len(words) >= 2
                and words[0] == 'deletion' and words[1] in ('approve', 'reject', 'request')):
            from .helpers import fetch_deletions
            new_deletions = fetch_deletions(self.client)
            self.state['deletions'] = new_deletions
            if self.completer is not None:
                self.completer._deletions = new_deletions

        # Re-fetch pending join requests after any ag/access-group command
        if (len(words) >= 2 and words[0] in ('ag', 'access-group')
                and words[1] in ('approve', 'reject', 'request')):
            from .helpers import fetch_join_requests
            new_join_requests = fetch_join_requests(self.client)
            self.state['join_requests'] = new_join_requests
            if self.completer is not None:
                self.completer._join_requests = new_join_requests

        # Re-fetch service accounts after any sa/service-account command that changes the list
        if (self.is_admin and len(words) >= 2 and words[0] in ('sa', 'service-account')
                and words[1] in ('create', 'update', 'rotate-key')):
            from .helpers import fetch_service_accounts
            new_service_accounts = fetch_service_accounts(self.client)
            self.state['service_accounts'] = new_service_accounts or []
            if self.completer is not None:
                self.completer._service_accounts = new_service_accounts or []

        # Reload client and full state after config set / config edit
        if len(words) >= 2 and words[0] == 'config' and words[1] in ('set', 'edit'):
            from crucible.config import config as _cfg
            from crucible.client import CrucibleClient
            try:
                _cfg.reload()
                self.client = CrucibleClient()
                if self.completer is not None:
                    self.completer._client       = self.client
                    self.completer._unlink_cache = {}
                    self.completer._users        = []
            except Exception:
                pass
            self.refresh()

        return True

    def _run_prompt_toolkit(self):
        from prompt_toolkit                import PromptSession
        from prompt_toolkit.history        import FileHistory
        from prompt_toolkit.auto_suggest   import AutoSuggestFromHistory
        from prompt_toolkit.styles         import Style
        from prompt_toolkit.key_binding    import KeyBindings
        from prompt_toolkit.completion     import ThreadedCompleter
        from platformdirs import user_data_dir

        history_path = os.path.join(user_data_dir('crucible'), 'shell_history')
        os.makedirs(os.path.dirname(history_path), exist_ok=True)

        print('\033[2J\033[H', end='', flush=True)

        info = self._verify_connection()
        self._init_state(info)

        _u     = info.get('user_info', {})
        _first = _u.get('first_name', '').strip() or \
                 _u.get('last_name', '').strip() or \
                 info.get('access_group_name') or 'there'
        print(f"\nWelcome to the Crucible interactive shell, {_first}.\n"
              "(type 'help' for commands, 'exit' to quit)")

        self.completer = _CrucibleCompleter(
            self.parser,
            client=self.client,
            projects=self.state['projects'],
            deletions=self.state['deletions'],
            join_requests=self.state['join_requests'],
            service_accounts=self.state['service_accounts'],
            state=self.state,
        )

        kb = KeyBindings()
        from .keybindings import register as _register_keybindings
        _register_keybindings(kb, self)

        self._session = PromptSession(
            history=FileHistory(history_path),
            auto_suggest=AutoSuggestFromHistory(),
            completer=ThreadedCompleter(self.completer),
            complete_while_typing=True,
            key_bindings=kb,
            bottom_toolbar=self._toolbar,
            style=Style.from_dict({
                'bottom-toolbar':      'noinherit bg:#1c9aad fg:#E8F4F7',
                'bottom-toolbar.text': 'noinherit bg:#1c9aad fg:#E8F4F7',
                'tb-project':          'noinherit bg:#A8C4CD fg:#0D2B35',
                'tb-clock':            'noinherit bg:#A8C4CD fg:#0D2B35',
                'tb-debug':            'noinherit bg:#E8820A fg:#1C1C1C bold',
            }),
        )

        threading.Thread(target=self._clock_tick, daemon=True).start()

        while True:
            try:
                line = self._session.prompt(_PROMPT)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                break
            if not self._dispatch(line):
                break
            print()

        self._clock_stop.set()

    def _run_readline(self):
        """Fallback shell using stdlib readline."""
        print("\nCrucible interactive shell  (type 'help' for commands, 'exit' to quit)")
        try:
            import readline  # noqa: F401
        except ImportError:
            pass

        while True:
            try:
                line = input(_PROMPT)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                break
            if not self._dispatch(line):
                break
            print()


def run(parser):
    """Start the interactive shell. Called from main() when no command given."""
    CrucibleShell(parser).run()
