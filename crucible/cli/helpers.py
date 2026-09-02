#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared CLI helper utilities.

Functions here are used across multiple CLI modules (dataset, sample, get,
shell, keybindings, etc.) and don't belong in term.py (display-only) or
shell.py (which would create circular imports).
"""

import re
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from ..utils.identifiers import MFID_PATTERN, classify_user_reference

logger = logging.getLogger(__name__)

_MFID_RE = MFID_PATTERN


def fail(action: str, error: Exception, args=None) -> None:
    """Log a CLI error and exit(1), printing a traceback if --debug was passed.

    `action` is the same trailing text every _execute_* function already
    writes by hand, e.g. fail("deleting dataset", e, args) logs
    "Error deleting dataset: <e>". Pass action="" for the bare "Error: <e>" form.

    `args` may be an argparse Namespace (checks args.debug) or a plain bool
    (some helpers like _edit_dataset take a bare `debug` flag, not the full
    Namespace) — pass whichever is in scope at the call site.

    Never returns — exits the process, same as every call site did manually.
    """
    logger.error(f"Error {action}: {error}" if action else f"Error: {error}")
    debug = args if isinstance(args, bool) else getattr(args, 'debug', False)
    if debug:
        import traceback
        traceback.print_exc()
    sys.exit(1)


def parse_user_ref(value: str) -> dict:
    """Sniff a user identifier's format and return a kwargs dict for users.get()/users.resolve().

    Uses the shared API-contract classifier. Canonical person and service-account
    identifiers are returned under the legacy ``orcid`` keyword for compatibility.
    """
    reference_kind, normalized = classify_user_reference(value)
    if reference_kind == 'unique_id':
        return {'orcid': normalized}
    return {reference_kind: normalized}


def parse_sa_ref(value: str) -> dict:
    """Sniff a service account identifier's format for service_accounts.get().

    Matches the MFID pattern (26-char Crockford base32) -> unique_id. Otherwise -> username.
    """
    if _MFID_RE.match(value):
        return {'unique_id': value}
    return {'username': value}


def resolve_user_id(client, value: str) -> str:
    """Resolve a user reference to its canonical ORCID or MFID.

    Returns a canonical ORCID or MFID unchanged without an API call.
    Raises ValueError if the identifier doesn't resolve to a user.
    """
    reference_kind, normalized = classify_user_reference(value)
    if reference_kind == 'unique_id':
        return normalized
    user = client.users.get(normalized)
    return user.get('unique_id')


def resolve_sa_id(client, value: str) -> str:
    """Resolve a service account identifier (MFID or username) to its MFID.

    A username could coincidentally match the MFID shape (usernames allow the
    same charset), so an MFID-shaped value that isn't found is retried as a
    username before giving up.
    Raises ValueError if the identifier doesn't resolve to a service account.
    """
    ref = parse_sa_ref(value)
    sa = client.service_accounts.get(**ref)
    if sa is None and 'unique_id' in ref:
        sa = client.service_accounts.get(username=value)
    if sa is None:
        raise ValueError(f"Service account not found: {value}")
    return sa.get('unique_id')


def fetch_projects(client):
    """Return [(project_id, title), ...] for all accessible projects."""
    try:
        return [(p.get('project_id', ''), p.get('title') or '-')
                for p in client.projects.list() if p.get('project_id')]
    except Exception:
        return []


def fetch_deletions(client):
    """Return pending deletion requests, or None if the user lacks permission."""
    try:
        return client.deletions.list(status='pending')
    except Exception:
        return None


def fetch_join_requests(client):
    """Return pending join requests, or None if the user lacks permission."""
    try:
        return client.access_groups.list_join_requests(status='pending')
    except Exception:
        return None


def fetch_service_accounts(client):
    """Return all service accounts, or None if the user lacks permission."""
    try:
        return client.service_accounts.list()
    except Exception:
        return None


def fetch_instruments(client):
    """Return [(instrument_id, instrument_name, unique_id), ...] for instruments.

    Instruments are a small, globally-readable set (not admin-gated),
    so fetch-all-once is appropriate here rather than live search.
    """
    try:
        return [
            (
                i.get('instrument_id') or '',
                i.get('instrument_name') or '',
                i.get('unique_id') or '',
            )
            for i in client.instruments.list()
            if i.get('instrument_id') and i.get('unique_id')
        ]
    except Exception:
        return []


def resolve_usernames(client, orcids):
    """Batch-resolve ORCIDs to usernames. Returns {orcid: username_or_orcid}."""
    orcids = sorted({o for o in orcids if o})
    if not orcids or client is None:
        return {}
    try:
        resolved = client.users.resolve(orcids=orcids)
    except Exception:
        return {}
    return {orcid: (info.get('username') or orcid) if info else orcid
            for orcid, info in resolved.items()}


def fetch_user_label(client, whoami_info=None):
    """Return a display name for the authenticated user.

    Pass whoami_info to skip a redundant API call when the caller already
    has the result of client.whoami().
    """
    from . import term
    try:
        info = whoami_info if whoami_info is not None else client.whoami()
        user = info.get('user_info', {})
        return term.fmt_name(user, default=info.get('user_unique_id') or '?')
    except Exception:
        return '?'


def fetch_current_project():
    """Return the current project ID from config, or a placeholder."""
    try:
        from crucible.config import config
        return config.current_project or '(no project set)'
    except Exception:
        return '?'


def fetch_current_session():
    """Return the current session name from config, or empty string."""
    try:
        from crucible.config import config
        return config.current_session or ''
    except Exception:
        return ''


def fetch_api_label():
    """Return 'api: <last-path-segment>' derived from the configured api_url."""
    try:
        from urllib.parse import urlparse
        from crucible.config import config
        parsed = urlparse(config.api_url or '')
        parts  = [p for p in parsed.path.split('/') if p]
        label  = parts[-1] if parts else (parsed.netloc or '?')
        return f"api: {label}"
    except Exception:
        return 'api: ?'


def explorer_url(resource_id: str, project_id: str, resource_type: str) -> str:
    """Build a graph explorer URL for a dataset or sample.

    Returns None if the graph_explorer_url is not configured or any argument is missing.
    """
    try:
        from crucible.config import config
        base = (config.graph_explorer_url or '').rstrip('/')
    except Exception:
        return None
    if not base or not resource_id or not project_id:
        return None
    dtype = 'samples' if resource_type == 'sample' else 'datasets'
    return f"{base}/{project_id}/{dtype}/{resource_id}"


def cast_value(value: str):
    """Auto-cast a string value to int, float, bool, or string."""
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def load_metadata(value: str) -> dict:
    """Parse a metadata arg: JSON string or path to a JSON file.

    Args:
        value: Raw string from --metadata CLI argument.

    Returns:
        dict: Parsed metadata.

    Raises:
        ValueError: If the string is not valid JSON and no such file exists.
    """
    import json
    from pathlib import Path
    p = Path(value)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {p}: {e}") from e
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise ValueError(f"'{value}' is not valid JSON and no such file exists.")


def show_scientific_metadata(sci_md):
    """Display scientific metadata dict under a subheader."""
    from . import term
    term.subheader(f"Scientific Metadata ({len(sci_md) if sci_md else 0} fields)")
    if not sci_md:
        print(f"  {term.dim('(none)')}")
        return
    max_key = max(len(k) for k in sci_md)
    for k, v in sorted(sci_md.items()):
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in sorted(v.items()):
                print(f"    {kk}: {vv}")
        elif isinstance(v, list) and len(v) > 8:
            print(f"  {k:<{max_key}}  <list with {len(v)} items>")
        else:
            print(f"  {k:<{max_key}}  {v}")


def cache_resource(shell_state, client, data, rtype, resource_id, **flags):
    """Cache a fetched resource in the shell state and start background prefetches.

    For datasets, prefetches links, keywords, associated files, and download
    links in parallel so Alt+V / Alt+G can re-render without extra API calls.
    For samples, only links are prefetched.

    Args:
        shell_state: The shell's mutable state dict (args._shell_state), or
                     None when running outside the interactive shell.
        client:      CrucibleClient instance.
        data:        The fetched resource dict.
        rtype:       Resource type string, 'dataset' or 'sample'.
        resource_id: MFID of the resource.
        **flags:     Additional keys stored in last_resource (verbose, graph,
                     include_metadata, etc.).
    """
    if shell_state is None:
        return

    # Track recently visited MFIDs for shell tab completion.
    recent = shell_state.get('recent_mfids')
    if recent is not None:
        name_key = {'dataset': 'dataset_name', 'sample': 'sample_name',
                    'instrument': 'instrument_name'}.get(rtype, 'name')
        name = data.get(name_key) or ''
        for i, (uid, _, _) in enumerate(recent):
            if uid == resource_id:
                del recent[i]
                break
        recent.appendleft((resource_id, name, rtype))

    if rtype == 'dataset':
        pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='prefetch')
        futures = {
            '_keywords_future': pool.submit(client.datasets.get_keywords, resource_id),
            '_files_future':    pool.submit(client.datasets.list_files, resource_id),
            '_dl_links_future': pool.submit(client.datasets.get_download_links, resource_id),
        }
        if not data.get('links'):
            futures['_links_future'] = pool.submit(client.get_links, resource_id)
    elif rtype == 'sample':
        futures = {}
        if not data.get('links'):
            pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='prefetch')
            futures['_links_future'] = pool.submit(client.get_links, resource_id)
    else:
        futures = {}

    if futures:
        pool.shutdown(wait=False)
    shell_state['last_resource'] = {
        'data': data, 'type': rtype, **futures, **flags
    }


def show_transfer_ownership(result, confirm: bool) -> None:
    """Print the preview or outcome of a BaseResource.transfer_ownership() call."""
    from . import term
    prev = result.previous_owner
    prev_name = term.fmt_name(prev.model_dump(), default=prev.unique_id) if prev else '-'
    new_name = term.fmt_name(result.new_owner.model_dump(), default=result.new_owner.unique_id)
    if confirm:
        logger.info(f"✓ Ownership of {result.resource_id} transferred: {prev_name} -> {new_name}")
    else:
        logger.info(f"Preview: ownership of {result.resource_id} would transfer from {prev_name} to {new_name}")
        logger.info("Re-run with --confirm to execute.")


_ROLE_RANK = {'owner': 5, 'admin': 4, 'editor': 3, 'contributor': 2, 'viewer': 1}


def sort_members(members) -> list:
    """Sort a list of ProjectMember objects (or user/role dicts) by role rank
    (owner first, per the VIEWER < CONTRIBUTOR < EDITOR < ADMIN < OWNER
    hierarchy), then alphabetically by name/username. Unrecognized roles sort last.
    """
    from . import term

    def key(m):
        d = m.model_dump() if hasattr(m, 'model_dump') else m
        rank = _ROLE_RANK.get((d.get('role') or '').lower(), 0)
        name = term.fmt_name(d, default='') or ''
        return (-rank, name.lower())

    return sorted(members, key=key)


def show_reassign_project(result, confirm: bool) -> None:
    """Print the preview or outcome of a BaseResource.reassign_project() call."""
    prev = result.previous_project_id or '-'
    if confirm:
        logger.info(f"✓ {result.resource_id} moved from project '{prev}' to '{result.new_project_id}'")
    else:
        logger.info(f"Preview: {result.resource_id} would move from project '{prev}' to '{result.new_project_id}'")
        logger.info("Re-run with --confirm to execute.")
