"""Unit coverage for project CLI argument compatibility."""

import argparse

import pytest

from crucible.cli.project import _register_get


def parse_project_get(*arguments):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    _register_get(subparsers)
    return parser.parse_args(['get'] + list(arguments))


def test_include_members_is_canonical_without_warning():
    args = parse_project_get('example-project', '--include-members')

    assert args.include_members is True


def test_members_alias_warns_and_remains_supported():
    with pytest.warns(DeprecationWarning, match='--include-members'):
        args = parse_project_get('example-project', '--members')

    assert args.include_members is True
