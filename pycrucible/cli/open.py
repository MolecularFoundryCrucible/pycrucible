#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Open subcommand for opening Crucible resources in the browser.

Opens datasets, samples, or projects in the Crucible Graph Explorer.
"""

import sys
import webbrowser


# Mapping from dtype to URL extension
DTYPE_TO_EXT = {
    "sample": "sample-graph",
    "dataset": "dataset",
    "main": "",
}


def register_subcommand(subparsers):
    """Register the open subcommand."""
    parser = subparsers.add_parser(
        'open',
        help='Open a Crucible resource in the browser',
        description='Open datasets, samples, projects, or the Graph Explorer in the browser',
        formatter_class=lambda prog: __import__('argparse').RawDescriptionHelpFormatter(prog, max_help_position=35),
        epilog="""
Examples:
    # Open the Graph Explorer home page
    crucible open

    # Open a specific project
    crucible open -pid 10k_perovskites

    # Open a sample in a project
    crucible open 0tcbwt4cp9x1z000bazhkv5gkg -pid 10k_perovskites

    # Open with explicit type
    crucible open abc123xyz -pid my-project -t dataset

    # Just print the URL instead of opening
    crucible open 0tcbwt4cp9x1z000bazhkv5gkg -pid my-project --print-url
"""
    )

    # mfid (optional now)
    parser.add_argument(
        'mfid',
        nargs='?',  # Make it optional
        default=None,
        help='Unique identifier (mfid) of the resource to open (optional)'
    )

    # Project ID (optional, uses config default)
    parser.add_argument(
        '-pid', '--project-id',
        default=None,
        metavar='ID',
        help='Project ID (uses config if not specified)'
    )

    # Resource type
    parser.add_argument(
        '-t', '--type',
        dest='dtype',
        choices=['sample', 'dataset', 'main'],
        default='sample',
        help='Resource type (default: sample)'
    )

    # Print URL instead of opening
    parser.add_argument(
        '--print-url',
        action='store_true',
        help='Print the URL instead of opening in browser'
    )

    parser.set_defaults(func=execute)


def execute(args):
    """Execute the open command."""
    from pycrucible.config import config

    mfid = args.mfid
    project_id = args.project_id
    dtype = args.dtype

    # Get graph explorer URL from config
    graph_explorer_url = config.graph_explorer_url.rstrip('/')

    # Case 1: No mfid, no project_id -> open graph explorer home
    if mfid is None and project_id is None:
        url = graph_explorer_url

    # Case 2: No mfid, but project_id given -> open project page
    elif mfid is None and project_id is not None:
        url = f"{graph_explorer_url}/{project_id}"

    # Case 3: Both mfid and project_id -> open specific resource
    elif mfid is not None and project_id is not None:
        ext = DTYPE_TO_EXT.get(dtype, "")
        if ext:
            url = f"{graph_explorer_url}/{project_id}/{ext}/{mfid}"
        else:
            url = f"{graph_explorer_url}/{project_id}/{mfid}"

    # Case 4: mfid given but no project_id -> error
    else:
        print("Error: Project ID required when opening a specific resource.", file=sys.stderr)
        print("Example: crucible open <mfid> -pid 10k_perovskites", file=sys.stderr)
        sys.exit(1)

    if args.print_url:
        # Just print the URL
        print(url)
    else:
        # Open in browser
        print(f"Opening in browser: {url}")
        try:
            webbrowser.open(url)
            print("✓ Opened in browser")
        except Exception as e:
            print(f"Error opening browser: {e}", file=sys.stderr)
            print(f"URL: {url}", file=sys.stderr)
            sys.exit(1)
