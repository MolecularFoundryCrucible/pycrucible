#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Status subcommand — check API reachability, database health, and authentication.
"""

import sys
import time
import threading
import itertools
import logging

logger = logging.getLogger(__name__)

from . import term

_SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']


def _readiness_fields(health):
    """Return version, database status, latency, and contract detection."""
    if not isinstance(health, dict):
        return None, None, None, False

    database = health.get("database")
    if isinstance(database, dict):
        build = health.get("build")
        version = build.get("api_version") if isinstance(build, dict) else None
        return version, database.get("status"), database.get("latency_ms"), True

    if "db" in health:
        return health.get("version"), health.get("db"), health.get("db_ms"), True

    return None, None, None, False


def _spin(stop_event, message):
    """Animate a spinner on the current line until stop_event is set."""
    for frame in itertools.cycle(_SPINNER_FRAMES):
        if stop_event.is_set():
            break
        sys.stdout.write(f'\r  {message}  {frame}')
        sys.stdout.flush()
        time.sleep(0.08)
    sys.stdout.write('\r' + ' ' * (len(message) + 6) + '\r')
    sys.stdout.flush()


def _check(stop_event, is_tty, fn):
    """Run *fn* while optionally animating a spinner. Returns (result, elapsed_ms)."""
    if is_tty:
        t = threading.Thread(target=_spin, args=(stop_event, 'Checking...'), daemon=True)
        t.start()
    t0 = time.monotonic()
    try:
        result = fn()
        elapsed = (time.monotonic() - t0) * 1000
        return result, elapsed, None
    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return None, elapsed, e
    finally:
        stop_event.set()
        if is_tty:
            t.join()
        stop_event.clear()


def register_subcommand(subparsers):
    """Register the status subcommand."""
    parser = subparsers.add_parser(
        'status',
        help='Check API connectivity, database health, and authentication',
        description='Verify the API is reachable, the database is up, and the current API key is accepted',
    )
    parser.set_defaults(func=execute)


def execute(args):
    """Execute the status command."""
    import requests
    from crucible.config import config

    api_url = config.api_url
    api_key  = config.api_key

    if not api_url:
        logger.error("API URL is not configured. Run: crucible config set api_url URL")
        sys.exit(1)

    from urllib.parse import urlparse
    host = urlparse(api_url).netloc or api_url
    is_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    stop = threading.Event()

    term.header("Status")
    print()

    # ── 1. Reachability + DB health (/health/ready, no auth) ─────────────────
    def _health():
        resp = requests.get(
            f"{api_url.rstrip('/')}/health/ready",
            timeout=(5, 15),
        )
        return resp.status_code, resp.json()

    health_result, elapsed_ms, err = _check(stop, is_tty, _health)

    if err is not None:
        print(f'  {term.status_marker("error")}  {term.bold(host)}  {term.dim("unreachable")}')
        print(f'\n     {err}')
        sys.exit(1)

    http_status, health = health_result
    version_str, db_status, db_ms, readiness_detected = _readiness_fields(health)
    ver_label   = f"  {term.dim(version_str)}" if version_str else ""
    print(f'  {term.status_marker("success")}  {term.bold(host)}  {term.dim(f"{elapsed_ms:.0f}ms")}{ver_label}')

    if readiness_detected:
        db_ok = db_status == "ok"
        db_latency = f"  {term.dim(f'{db_ms:.0f}ms')}" if db_ms is not None else ""
        if db_ok:
            print(f'  {term.status_marker("success")}  Database reachable{db_latency}')
        else:
            print(f'  {term.status_marker("error")}  Database unreachable')
    else:
        db_ok = True  # can't determine; don't block auth check
        print(f'  {term.status_marker("info")}  Health endpoint not yet deployed  {term.dim(f"(HTTP {http_status})")}')


    # ── 2. Authentication (/account, requires API key) ────────────────────────
    print()
    if not api_key:
        print(f'  {term.status_marker("info")}  No API key configured')
        print(f'       Run: crucible config set api_key KEY')
        sys.exit(0 if db_ok else 1)

    def _whoami():
        from crucible.client import CrucibleClient
        return CrucibleClient().whoami()

    info, _, err = _check(stop, is_tty, _whoami)

    if err is not None:
        print(f'  {term.status_marker("error")}  Authentication failed')
        print(f'\n     {err}')
        sys.exit(1)

    user  = info.get('user_info', {})
    first = user.get('first_name', '')
    last  = user.get('last_name', '')
    name  = f'{first} {last}'.strip() or None

    if name:
        print(f'  {term.status_marker("success")}  Authenticated as  {name}')
    else:
        print(f'  {term.status_marker("success")}  Authenticated')

    print()
    sys.exit(0 if db_ok else 1)
