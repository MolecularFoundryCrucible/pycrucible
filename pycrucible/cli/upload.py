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
    # Generic upload (no parsing) - upload any files
    crucible upload -i file1.dat file2.csv -pid my-project -u

    # Generic upload with metadata and keywords
    crucible upload -i data.csv -pid my-project -u \\
        --metadata '{"temperature": 300, "pressure": 1.0}' \\
        --keywords "experiment,thermal" -m "thermal_analysis"

    # Generic upload with metadata from JSON file
    crucible upload -i data.csv -pid my-project -u --metadata metadata.json

    # Parse and upload LAMMPS simulation
    crucible upload -i input.lmp -t lammps -pid my-project -u

    # Upload with specific mfid (all aliases work: --mfid, --uuid, --unique-id, --id)
    crucible upload -i input.lmp -t lammps -pid my-project -u --mfid abc123xyz

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

    # Dataset type (optional - if not provided, uses generic upload)
    available_types = ', '.join(sorted(set(PARSER_REGISTRY.keys())))
    type_arg = parser.add_argument(
        '-t', '--type',
        required=False,
        default=None,
        dest='dataset_type',
        metavar='TYPE',
        help=f'Dataset type (optional). Available: {available_types}. If not specified, files are uploaded without parsing.'
    )
    # Add choices completion for dataset types
    if ARGCOMPLETE_AVAILABLE:
        type_arg.completer = lambda **kwargs: sorted(set(PARSER_REGISTRY.keys()))

    # Project ID
    parser.add_argument(
        '-pid', '--project-id',
        required=False,
        default=None,
        metavar='ID',
        help='Crucible project ID (uses config current_project if not specified)'
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
        help='Owner ORCID ID (uses config if not specified)'
    )

    # Verbose output
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )

    # Measurement type (for generic uploads without parser)
    parser.add_argument(
        '-m', '--measurement',
        dest='measurement',
        default=None,
        metavar='TYPE',
        help='Measurement type (optional, for generic uploads)'
    )

    # Scientific metadata JSON (for generic uploads without parser)
    parser.add_argument(
        '--metadata',
        dest='metadata',
        default=None,
        metavar='JSON',
        help='Scientific metadata as JSON string or path to JSON file (optional, for generic uploads)'
    )

    # Keywords (for generic uploads without parser)
    parser.add_argument(
        '-k', '--keywords',
        dest='keywords',
        default=None,
        metavar='WORDS',
        help='Comma-separated keywords (optional, for generic uploads)'
    )

    # Set the function to execute for this subcommand
    parser.set_defaults(func=execute)


def execute(args):
    """
    Execute the upload subcommand.

    Args:
        args: Parsed command-line arguments from argparse
    """
    import json
    from pycrucible.parsers import get_parser, BaseParser
    from pycrucible.config import config

    # Get project_id - use flag if provided, otherwise fall back to config
    project_id = args.project_id
    project_from_config = False
    if project_id is None:
        project_id = config.current_project
        project_from_config = True
        if project_id is None:
            print("Error: Project ID required. Specify with -pid or set current_project in config.", file=sys.stderr)
            print("  Set default: crucible config set current_project YOUR_PROJECT_ID", file=sys.stderr)
            sys.exit(1)

    # Show which project is being used
    if project_from_config:
        print(f"Project: {project_id} (from config)")
    else:
        print(f"Project: {project_id}")

    # Validate input files exist
    input_files = [Path(f) for f in args.input]
    for input_file in input_files:
        if not input_file.exists():
            print(f"Error: Input file not found: {input_file}", file=sys.stderr)
            sys.exit(1)

    # Parse metadata early (before mode announcement) - support JSON string or file
    metadata_dict = None
    if args.metadata:
        metadata_input = args.metadata
        # Check if it's a file path
        if Path(metadata_input).exists():
            try:
                with open(metadata_input, 'r') as f:
                    metadata_dict = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in file {metadata_input}: {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"Error reading metadata file {metadata_input}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # It's a JSON string
            try:
                metadata_dict = json.loads(metadata_input)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in --metadata: {e}", file=sys.stderr)
                sys.exit(1)

    # Case 1: Generic upload (no dataset type specified)
    if args.dataset_type is None:
        print(f"Parser: BaseParser (generic upload, no parsing)")

        # Create a BaseParser instance
        parser = BaseParser(
            files_to_upload=[str(f) for f in input_files],
            project_id=project_id
        )

        # Add metadata if provided
        if metadata_dict:
            parser.scientific_metadata = metadata_dict
            print(f"  Metadata: {len(parser.scientific_metadata)} fields")

        # Add keywords if provided
        if args.keywords:
            parser.keywords = [k.strip() for k in args.keywords.split(',')]
            print(f"  Keywords: {', '.join(parser.keywords)}")

        # Measurement type for generic uploads
        measurement_type = args.measurement or "generic"

    # Case 2: Use specific parser for dataset type
    else:
        # Get the appropriate parser
        try:
            ParserClass = get_parser(args.dataset_type)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Use first input file (most parsers take a single primary input)
        primary_input = str(input_files[0])

        print(f"Parser: {ParserClass.__name__}")
        print(f"Input: {primary_input}")

        # Initialize parser
        try:
            parser = ParserClass(primary_input, project_id=project_id)
        except Exception as e:
            print(f"Error parsing file: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        # Measurement type comes from parser (e.g., "LAMMPS")
        measurement_type = args.measurement  # Will be set by parser in upload_dataset

    # Display metadata (if not generic upload or if metadata provided)
    if args.dataset_type is not None or args.metadata or args.keywords:
        print("\n=== Dataset Information ===")
        print(f"Files to upload: {len(parser.files_to_upload)}")
        for f in parser.files_to_upload:
            print(f"  - {Path(f).name}")

        if parser.keywords:
            print(f"\nKeywords: {', '.join(parser.keywords)}")

        if parser.scientific_metadata:
            print(f"\nScientific Metadata:")
            for key, value in parser.scientific_metadata.items():
                if key == 'dump_files':
                    print(f"  {key}: {len(value)} files")
                elif isinstance(value, (list, dict)) and len(str(value)) > 80:
                    print(f"  {key}: <{type(value).__name__} with {len(value)} items>")
                else:
                    print(f"  {key}: {value}")
    else:
        print("\n=== Files to Upload ===")
        for f in parser.files_to_upload:
            print(f"  - {Path(f).name}")

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

        # Get ORCID - use flag if provided, otherwise fall back to config
        owner_orcid = args.owner_orcid
        if owner_orcid is None:
            owner_orcid = config.orcid_id
            if owner_orcid and args.verbose:
                print(f"Using ORCID from config: {owner_orcid}")

        try:
            # For generic uploads, pass measurement type; for specific parsers, they handle it
            upload_kwargs = {
                'mfid': dataset_mfid,
                'project_id': project_id,
                'owner_orcid': owner_orcid,
                'dataset_name': args.dataset_name,
                'verbose': args.verbose,
                'wait_for_ingestion_response': True
            }

            # Only pass measurement if it's a generic upload
            if args.dataset_type is None:
                upload_kwargs['measurement'] = measurement_type

            result = parser.upload_dataset(**upload_kwargs)

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
