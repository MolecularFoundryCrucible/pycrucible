#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload subcommand for Crucible CLI.

Handles parsing and uploading datasets to Crucible.
"""

import sys
from pathlib import Path

try:
    import mfid
except ImportError:
    mfid = None

try:
    import argcomplete
    from argcomplete.completers import FilesCompleter
    ARGCOMPLETE_AVAILABLE = True
except ImportError:
    ARGCOMPLETE_AVAILABLE = False


def register_subcommand(subparsers):
    """
    Register the upload subcommand with the main parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    from pycrucible.parsers import PARSER_REGISTRY

    parser = subparsers.add_parser(
        'upload',
        help='Parse and upload datasets to Crucible',
        description='Parse dataset files and upload them to Crucible',
        formatter_class=lambda prog: __import__('argparse').RawDescriptionHelpFormatter(prog, max_help_position=35),
        epilog="""
Examples:
    # Parse only (no upload) - preview what will be uploaded
    crucible upload -i input.lmp -t lammps -pid my-project

    # Parse and upload with auto-generated mfid
    crucible upload -i input.lmp -t lammps -pid my-project -u

    # Upload with specific mfid (all aliases work: --mfid, --uuid, --unique-id, --id)
    crucible upload -i input.lmp -t lammps -pid my-project -u --mfid abc123xyz
    crucible upload -i input.lmp -t lammps -pid my-project -u --uuid abc123xyz

    # Upload with custom dataset name
    crucible upload -i input.lmp -t lammps -pid my-project -u -n "Water MD Simulation"
"""
    )

    # Input file(s)
    input_arg = parser.add_argument(
        '-i', '--input',
        nargs='+',
        required=True,
        metavar='FILE',
        help='Input file(s) to parse'
    )
    # Add file completion for input files
    if ARGCOMPLETE_AVAILABLE:
        input_arg.completer = FilesCompleter()

    # Dataset type
    available_types = ', '.join(sorted(set(PARSER_REGISTRY.keys())))
    type_arg = parser.add_argument(
        '-t', '--type',
        required=True,
        dest='dataset_type',
        metavar='TYPE',
        help=f'Dataset type. Available: {available_types}'
    )
    # Add choices completion for dataset types
    if ARGCOMPLETE_AVAILABLE:
        type_arg.completer = lambda **kwargs: sorted(set(PARSER_REGISTRY.keys()))

    # Project ID
    parser.add_argument(
        '-pid', '--project-id',
        required=True,
        metavar='ID',
        help='Crucible project ID'
    )

    # Upload flag
    parser.add_argument(
        '-u', '--upload',
        action='store_true',
        help='Upload to Crucible (default: parse only)'
    )

    # Unique ID / mfid (with multiple aliases)
    parser.add_argument(
        '--mfid', '--uuid', '--unique-id', '--id',
        dest='mfid',
        default=None,
        metavar='ID',
        help='Unique dataset ID (mfid). Auto-generated if not provided.'
    )

    # Dataset name (optional)
    parser.add_argument(
        '-n', '--name',
        dest='dataset_name',
        default=None,
        metavar='NAME',
        help='Human-readable dataset name (optional)'
    )

    # Owner ORCID (optional)
    parser.add_argument(
        '--orcid', '-oid',
        dest='owner_orcid',
        default=None,
        metavar='ORCID',
        help='Owner ORCID ID (optional)'
    )

    # Verbose output
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )

    # Set the function to execute for this subcommand
    parser.set_defaults(func=execute)


def execute(args):
    """
    Execute the upload subcommand.

    Args:
        args: Parsed command-line arguments from argparse
    """
    from pycrucible.parsers import get_parser

    # Validate input files exist
    input_files = [Path(f) for f in args.input]
    for input_file in input_files:
        if not input_file.exists():
            print(f"Error: Input file not found: {input_file}", file=sys.stderr)
            sys.exit(1)

    # Get the appropriate parser
    try:
        ParserClass = get_parser(args.dataset_type)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Use first input file (most parsers take a single primary input)
    primary_input = str(input_files[0])

    print(f"Parsing {args.dataset_type} dataset from: {primary_input}")

    # Initialize parser
    try:
        parser = ParserClass(primary_input, project_id=args.project_id)
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Display parsed metadata
    print("\n=== Parsed Metadata ===")
    print(f"Files to upload: {len(parser.files_to_upload)}")
    for f in parser.files_to_upload:
        print(f"  - {Path(f).name}")
    print(f"\nKeywords: {', '.join(parser.keywords)}")
    print(f"\nScientific Metadata:")
    for key, value in parser.scientific_metadata.items():
        if key == 'dump_files':
            print(f"  {key}: {len(value)} files")
        elif isinstance(value, (list, dict)) and len(str(value)) > 80:
            print(f"  {key}: <{type(value).__name__} with {len(value)} items>")
        else:
            print(f"  {key}: {value}")

    # Upload if requested
    if args.upload:
        print("\n=== Uploading to Crucible ===")

        # Generate mfid if not provided
        dataset_mfid = args.mfid
        if dataset_mfid is None:
            if mfid is None:
                print("Error: mfid package not installed. Install with 'pip install mfid' or provide --mfid", file=sys.stderr)
                sys.exit(1)
            dataset_mfid = mfid.mfid()[0]
            print(f"Generated mfid: {dataset_mfid}")
        else:
            print(f"Using provided mfid: {dataset_mfid}")

        try:
            result = parser.upload_dataset(
                mfid=dataset_mfid,
                project_id=args.project_id,
                owner_orcid=args.owner_orcid,
                dataset_name=args.dataset_name,
                verbose=args.verbose,
                wait_for_ingestion_response=True
            )

            print("\n✓ Upload successful!")
            print(f"Dataset ID: {result.get('created_record', {}).get('unique_id', 'N/A')}")

            if args.verbose and result:
                print("\nUpload result details:")
                for key, value in result.items():
                    print(f"  {key}: {value}")

        except Exception as e:
            print(f"\n✗ Upload failed: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    else:
        print("\n(Use -u/--upload flag to upload to Crucible)")

    print("\nDone!")
