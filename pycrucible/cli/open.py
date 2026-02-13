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
        help='Project ID (uses config current_project if not specified for project pages; required for specific resources)'
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

    # Use current_project as fallback when not specified
    if project_id is None and (mfid is not None):
        # mfid provided but no project_id - try to use current_project from config
        project_id = config.current_project
        if project_id is None:
            print("Error: Project ID required when opening a specific resource.", file=sys.stderr)
            print("  Specify with -pid or set current_project in config:", file=sys.stderr)
            print("  crucible config set current_project YOUR_PROJECT_ID", file=sys.stderr)
            sys.exit(1)

    # Case 1: No mfid, no project_id (after fallback) -> open graph explorer home
    if mfid is None and project_id is None:
        url = graph_explorer_url

    # Case 2: No mfid, but project_id given/from config -> open project page
    elif mfid is None and project_id is not None:
        url = f"{graph_explorer_url}/{project_id}"

    # Case 3: Both mfid and project_id (possibly from config) -> open specific resource
    else:
        ext = DTYPE_TO_EXT.get(dtype, "")
        if ext:
            url = f"{graph_explorer_url}/{project_id}/{ext}/{mfid}"
        else:
            url = f"{graph_explorer_url}/{project_id}/{mfid}"

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
