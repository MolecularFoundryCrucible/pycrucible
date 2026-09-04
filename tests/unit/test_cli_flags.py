"""Unit coverage for canonical CLI flags and compatibility aliases."""

import argparse

import pytest

from crucible.cli import dataset, project, sample, upload


def make_parser(module):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='resource')
    module.register_subcommand(subparsers)
    return parser


@pytest.mark.parametrize('flag', ['--project-id', '-p'])
def test_dataset_search_accepts_canonical_project_flags(flag):
    args = make_parser(dataset).parse_args([
        'dataset', 'search', 'query', flag, 'project-one',
    ])

    assert args.project_id == 'project-one'


@pytest.mark.parametrize('flag', ['--project', '-pid'])
def test_dataset_search_warns_for_legacy_project_flags(flag, capsys):
    args = make_parser(dataset).parse_args([
        'dataset', 'search', 'query', flag, 'project-one',
    ])

    assert args.project_id == 'project-one'
    assert (
        f'Warning: {flag} is deprecated; use --project-id instead.'
        in capsys.readouterr().err
    )


def test_sample_create_uses_canonical_type_flag():
    args = make_parser(sample).parse_args([
        'sample', 'create', '--type', 'substrate',
    ])

    assert args.sample_type == 'substrate'


def test_sample_create_warns_for_legacy_type_flag(capsys):
    args = make_parser(sample).parse_args([
        'sample', 'create', '--sample-type', 'substrate',
    ])

    assert args.sample_type == 'substrate'
    assert (
        'Warning: --sample-type is deprecated; use --type instead.'
        in capsys.readouterr().err
    )


def test_project_create_uses_canonical_short_flag():
    args = make_parser(project).parse_args([
        'project', 'create', '-i', 'project-one',
    ])

    assert args.project_id == 'project-one'


def test_project_create_warns_for_legacy_short_flag(capsys):
    args = make_parser(project).parse_args([
        'project', 'create', '-id', 'project-one',
    ])

    assert args.project_id == 'project-one'
    assert (
        'Warning: -id is deprecated; use --project-id instead.'
        in capsys.readouterr().err
    )


def test_legacy_upload_project_flag_remains_compatible(capsys):
    args = make_parser(upload).parse_args([
        'upload', '-i', 'data.csv', '-pid', 'project-one',
    ])

    assert args.project_id == 'project-one'
    assert (
        'Warning: -pid is deprecated; use --project-id instead.'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize(
    ('module', 'command', 'visible', 'hidden'),
    [
        (dataset, ['dataset', 'search'], '--project-id ID, -p ID', '--project ID'),
        (sample, ['sample', 'create'], '--type TYPE, -t TYPE', '--sample-type TYPE'),
        (project, ['project', 'create'], '--project-id ID, -i ID', ', -id ID'),
    ],
)
def test_help_hides_legacy_flags(module, command, visible, hidden, capsys):
    with pytest.raises(SystemExit) as exit_info:
        make_parser(module).parse_args(command + ['--help'])

    assert exit_info.value.code == 0
    output = capsys.readouterr().out
    assert visible in output
    assert hidden not in output
