"""Unit coverage for canonical CLI flags and compatibility aliases."""

import argparse
from unittest.mock import MagicMock

import pytest

from crucible.cli import dataset, file as file_cli, project, sample, upload


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


def test_dataset_create_accepts_no_input():
    args = make_parser(dataset).parse_args([
        'dataset', 'create', '--project-id', 'project-one', '--name', 'Planned experiment',
    ])

    assert args.input is None


@pytest.mark.parametrize('flag', ['--yes', '-y'])
def test_file_delete_accepts_confirmation_flag(flag):
    args = make_parser(file_cli).parse_args([
        'file', 'delete', '0tf7evvtg5wb90005k1j97ak94', flag,
    ])

    assert args.yes is True


@pytest.mark.parametrize(
    'option',
    [
        ['--type', 'lammps'],
        ['--ingestor', 'ExampleIngestor'],
        ['--no-upload'],
        ['--backend', 'globus'],
        ['--access-note', 'Shared path'],
    ],
)
def test_dataset_create_rejects_file_options_without_input(option, caplog):
    args = make_parser(dataset).parse_args([
        'dataset', 'create', '--project-id', 'project-one', *option,
    ])

    with pytest.raises(SystemExit) as exit_info:
        args.func(args)

    assert exit_info.value.code == 1
    assert 'require --input FILE' in caplog.text


def test_dataset_create_without_files_uses_direct_client(monkeypatch):
    client = MagicMock()
    client.projects.get.return_value = {'project_id': 'project-one'}
    client.datasets.create.return_value = {'created_record': {}}
    monkeypatch.setattr('crucible.client.CrucibleClient', lambda: client)
    args = make_parser(dataset).parse_args([
        'dataset', 'create', '--project-id', 'project-one', '--name', 'Planned experiment',
        '--metadata', '{"temperature": 300}', '--keywords', 'planned,draft',
    ])

    args.func(args)

    created_dataset = client.datasets.create.call_args.args[0]
    assert created_dataset.dataset_name == 'Planned experiment'
    assert created_dataset.project_id == 'project-one'
    client.datasets.create.assert_called_once_with(
        created_dataset,
        scientific_metadata={'temperature': 300},
        keywords=['planned', 'draft'],
        files=[],
    )


def test_dataset_add_thumbnail_dispatches_local_image(monkeypatch, tmp_path, capsys):
    image_path = tmp_path / 'preview.png'
    image_path.write_bytes(b'png bytes')
    client = MagicMock()
    monkeypatch.setattr('crucible.client.CrucibleClient', lambda: client)
    args = make_parser(dataset).parse_args([
        'dataset', 'add-thumbnail',
        '0tkn2knjast3h0008nyq9zps2c', str(image_path),
        '--name', 'overview.png',
    ])

    args.func(args)

    client.datasets.add_thumbnail.assert_called_once_with(
        '0tkn2knjast3h0008nyq9zps2c',
        str(image_path),
        thumbnail_name='overview.png',
    )
    assert 'Added thumbnail overview.png' in capsys.readouterr().out


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
