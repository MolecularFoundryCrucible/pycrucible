"""Unit coverage for shared CLI resource presentation."""

from types import SimpleNamespace

import pytest

from crucible.cli import dataset as dataset_cli
from crucible.cli import instrument as instrument_cli
from crucible.cli import project as project_cli
from crucible.cli import sample as sample_cli
from crucible.cli import term


MFID = '0tkn2knjast3h0008nyq9zps2c'


@pytest.mark.parametrize(('value', 'expected'), [
    (True, 'yes'),
    (False, 'no'),
    (None, '-'),
])
def test_nullable_boolean_formatting(value, expected):
    assert term.fmt_bool(value) == expected


def test_project_detail_distinguishes_slug_and_mfid_and_shows_empty_members(capsys):
    project_cli._show_project({
        'unique_id': MFID,
        'project_id': 'project-slug',
        'title': 'Project',
        'organization': 'LBNL',
        'status': 'active',
        'creation_time': '2026-09-01T12:00:00+00:00',
        'modification_time': '2026-09-01T13:00:00+00:00',
        'members': [],
    }, include_members=True)

    output = capsys.readouterr().out
    assert 'Project ID' in output
    assert 'project-slug' in output
    assert 'MFID' in output
    assert MFID in output
    assert 'Created' in output
    assert 'Modified' in output
    assert 'Members (0)' in output
    assert 'No members found.' in output


def test_instrument_detail_distinguishes_slug_and_mfid(capsys):
    instrument_cli._show_instrument({
        'unique_id': MFID,
        'instrument_id': 'instrument-slug',
        'instrument_name': 'Instrument',
        'status': 'maintenance',
    })

    output = capsys.readouterr().out
    assert 'Instrument ID' in output
    assert 'instrument-slug' in output
    assert 'MFID' in output
    assert MFID in output
    assert 'maintenance' in output


@pytest.mark.parametrize(('show', 'record'), [
    (
        lambda record: dataset_cli._show_dataset(
            record,
            SimpleNamespace(),
            prefetched={'keywords': [], 'af_list': [], 'link_map': {}},
        ),
        {'unique_id': MFID, 'dataset_name': 'Dataset', 'public': None},
    ),
    (
        lambda record: sample_cli._show_sample(record, SimpleNamespace()),
        {'unique_id': MFID, 'sample_name': 'Sample', 'public': None},
    ),
])
def test_missing_public_value_is_not_rendered_as_false(show, record, capsys):
    show(record)

    public_line = next(
        line for line in capsys.readouterr().out.splitlines() if 'Public' in line)
    assert public_line.rstrip().endswith('-')
