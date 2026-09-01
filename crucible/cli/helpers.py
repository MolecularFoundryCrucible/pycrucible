#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared CLI helper utilities.

Functions here are used across multiple CLI modules (dataset, sample, get,
shell, keybindings, etc.) and don't belong in term.py (display-only) or
shell.py (which would create circular imports).
"""

import json
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from ..utils.identifiers import MFID_PATTERN, classify_user_reference

logger = logging.getLogger(__name__)

_MFID_RE = MFID_PATTERN
_NO_DEFAULT = object()


def _error_details(error):
    response = getattr(error, 'response', None)
    if response is None:
        return None, None, []

    status = getattr(response, 'status_code', None)
    reason = getattr(response, 'reason', None)
    detail = None
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = payload.get('detail') or payload.get('message') or payload.get('error')
        elif payload:
            detail = payload
    except (ValueError, AttributeError):
        text = getattr(response, 'text', '').strip()
        detail = text or None

    items = detail if isinstance(detail, list) else [detail] if detail is not None else []
    details = []
    for item in items:
        if isinstance(item, dict):
            location = item.get('loc') or []
            if isinstance(location, (str, int)):
                location = [location]
            location = [str(part) for part in location if part not in ('body', 'query', 'path')]
            entry = {'message': str(item.get('msg') or item.get('message') or item)}
            if location:
                entry['field'] = '.'.join(location)
            if item.get('type'):
                entry['type'] = str(item['type'])
            details.append(entry)
        else:
            details.append({'message': str(item)})
    return status, reason, details


def format_cli_error(action: str, error: Exception) -> dict:
    import requests

    status, reason, details = _error_details(error)
    if status is not None:
        error_type = 'http_error'
    elif isinstance(error, requests.exceptions.Timeout):
        error_type = 'timeout'
        reason = 'Request timed out'
    elif isinstance(error, requests.exceptions.ConnectionError):
        error_type = 'connection_error'
        reason = 'Connection failed'
    else:
        error_type = type(error).__name__

    if not details and str(error):
        details = [{'message': str(error)}]

    result = {
        'type': error_type,
        'message': f"Failed while {action}." if action else 'Command failed.',
        'details': details,
    }
    if status is not None:
        result['status'] = status
    if reason:
        result['reason'] = str(reason)
    return result


def print_cli_error(data: dict, as_json: bool = False) -> None:
    from . import term

    if as_json:
        print(json.dumps({'error': data}, default=str), file=sys.stderr)
        return

    title = 'Error'
    if data.get('status') is not None:
        title += f" {data['status']}"
    if data.get('reason'):
        title += f" {data['reason']}"
    print(term.red(title, stream=sys.stderr), file=sys.stderr)
    print(data['message'], file=sys.stderr)

    details = data.get('details') or []
    if details:
        print(file=sys.stderr)
        field_width = max((len(item.get('field', '')) for item in details), default=0)
        for item in details:
            field = item.get('field')
            message = item.get('message', '')
            if field:
                label = term.bold(field.ljust(field_width), stream=sys.stderr)
                print(f"  {label}  {message}", file=sys.stderr)
            else:
                print(f"  {message}", file=sys.stderr)


def show_warning(message) -> None:
    from . import term

    print(term.yellow('Warning', stream=sys.stderr), file=sys.stderr)
    print(str(message), file=sys.stderr)


def _interactive_stdin() -> bool:
    return hasattr(sys.stdin, 'isatty') and sys.stdin.isatty()


def _prompt_unavailable(label: str, option: str = None) -> None:
    from . import term

    message = f"Cannot prompt for {label.lower()} because stdin is not interactive."
    if option:
        message += f" Provide {option}."
    print(term.red('Error', stream=sys.stderr), file=sys.stderr)
    print(message, file=sys.stderr)
    raise SystemExit(2)


def _prompt_value(label: str, *, optional: bool = False, default=_NO_DEFAULT,
                  validator=None, option: str = None, secret: bool = False,
                  hint: str = None):
    from . import term

    if not _interactive_stdin():
        if default is not _NO_DEFAULT:
            value = str(default)
            try:
                return validator(value) if validator else value
            except ValueError as error:
                print(term.red('Invalid value', stream=sys.stderr), file=sys.stderr)
                print(str(error), file=sys.stderr)
                if option:
                    print(f"Provide {option} to override the configured default.", file=sys.stderr)
                raise SystemExit(2)
        if optional:
            return None
        _prompt_unavailable(label, option)

    if default is not _NO_DEFAULT:
        suffix = term.dim(f" [{default}]")
    elif optional:
        detail = f"optional; {hint}" if hint else "optional"
        suffix = term.dim(f" ({detail})")
    else:
        suffix = term.dim(" (required)")
    if hint and not optional:
        suffix += term.dim(f" ({hint})")
    prompt = f"{term.bold(label)}{suffix}: "

    reader = input
    if secret:
        import getpass
        reader = getpass.getpass

    while True:
        try:
            value = reader(prompt).strip()
        except EOFError:
            _prompt_unavailable(label, option)
        if not value:
            if default is not _NO_DEFAULT:
                value = str(default)
            if optional:
                return None
            elif default is _NO_DEFAULT:
                error = ValueError(f"{label} is required.")
                print(term.red('Invalid value', stream=sys.stderr), file=sys.stderr)
                print(str(error), file=sys.stderr)
                continue
        if value:
            try:
                return validator(value) if validator else value
            except ValueError as validation_error:
                error = validation_error

        print(term.red('Invalid value', stream=sys.stderr), file=sys.stderr)
        print(str(error), file=sys.stderr)


def prompt_required(label: str, validator=None, option: str = None):
    return _prompt_value(label, validator=validator, option=option)


def prompt_optional(label: str, validator=None, default=_NO_DEFAULT,
                    option: str = None, hint: str = None):
    return _prompt_value(
        label,
        optional=default is _NO_DEFAULT,
        default=default,
        validator=validator,
        option=option,
        hint=hint,
    )


def prompt_secret(label: str, option: str = None) -> str:
    return _prompt_value(label, option=option, secret=True)


def prompt_choice(label: str, choices, default=_NO_DEFAULT, option: str = None) -> str:
    allowed = tuple(choices)

    def validate(value):
        normalized = value.lower()
        if normalized not in allowed:
            raise ValueError(f"{label} must be one of: {', '.join(allowed)}.")
        return normalized

    return _prompt_value(
        label,
        default=default,
        validator=validate,
        option=option,
        hint='/'.join(allowed),
    )


def prompt_username(label: str = 'Username') -> str:
    from ..utils.identifiers import validate_username

    return prompt_required(label, validator=validate_username, option='--username')


def validate_email(value: str) -> str:
    email = value.strip().lower()
    if not re.fullmatch(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email):
        raise ValueError("Email must be a valid address such as user@example.org.")
    return email


def validate_user_reference(value: str) -> str:
    _, normalized = classify_user_reference(value)
    return normalized


def validate_mfid(value: str) -> str:
    from ..utils.identifiers import validate_mfid as validate

    return validate(value)


def validate_orcid(value: str) -> str:
    from ..utils.identifiers import is_orcid

    if not is_orcid(value):
        raise ValueError("ORCID must use the canonical 0000-0000-0000-000X format.")
    return value


def validate_project_ids(value: str) -> str:
    from ..utils.identifiers import validate_slug

    project_ids = [item.strip() for item in value.split(',') if item.strip()]
    if not project_ids:
        raise ValueError("Provide at least one project ID.")
    for project_id in project_ids:
        validate_slug(project_id, 'project')
    return ','.join(project_ids)


def validate_http_url(value: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(value)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise ValueError("URL must be an absolute HTTP or HTTPS URL.")
    return value.rstrip('/')


def install_warning_formatter() -> None:
    import warnings

    def showwarning(message, category, filename, lineno, file=None, line=None):
        show_warning(message)

    warnings.showwarning = showwarning


def fail(action: str, error: Exception, args=None) -> None:
    """Display a structured CLI error and exit with status 1."""
    data = format_cli_error(action, error)
    as_json = not isinstance(args, bool) and getattr(args, 'json', False)
    print_cli_error(data, as_json=as_json)
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
