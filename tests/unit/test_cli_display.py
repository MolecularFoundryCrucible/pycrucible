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


def test_table_fits_terminal_and_preserves_protected_identifiers(monkeypatch, capsys):
    slug = 'i' * 25
    monkeypatch.setattr(term, '_table_output_width', lambda: 80)

    term.table(
        [(
            'A long instrument display name',
            slug,
            MFID,
            'A long owner display name',
            'maintenance',
        )],
        ['Name', 'Instrument ID', 'MFID', 'Owner', 'Status'],
        max_widths=[24, 25, 26, 25, 12],
        min_widths=[4, 25, 26, 5, 6],
    )

    lines = capsys.readouterr().out.splitlines()
    assert all(term._dlen(line) <= 80 for line in lines)
    assert slug in lines[1]
    assert MFID in lines[1]


def test_table_preserves_full_username_when_space_permits(monkeypatch, capsys):
    username = 'u' * 24
    monkeypatch.setattr(term, '_table_output_width', lambda: 80)

    term.table(
        [(username, 'A long user display name', MFID)],
        ['Username', 'Name', 'ID'],
        max_widths=[24, 25, 26],
        min_widths=[24, 4, 26],
    )

    lines = capsys.readouterr().out.splitlines()
    assert all(term._dlen(line) <= 80 for line in lines)
    assert username in lines[1]
    assert MFID in lines[1]


def test_table_truncates_protected_columns_only_when_required(monkeypatch, capsys):
    monkeypatch.setattr(term, '_table_output_width', lambda: 50)

    term.table(
        [('A long name', 'instrument-identifier-25', MFID, 'Owner', 'active')],
        ['Name', 'Instrument ID', 'MFID', 'Owner', 'Status'],
        max_widths=[24, 25, 26, 25, 12],
        min_widths=[4, 25, 26, 5, 6],
    )

    lines = capsys.readouterr().out.splitlines()
    assert all(term._dlen(line) <= 50 for line in lines)
    assert '…' in lines[1]


def test_table_without_minimums_remains_responsive(monkeypatch, capsys):
    monkeypatch.setattr(term, '_table_output_width', lambda: 30)

    term.table(
        [('A long descriptive value', 'Another long value')],
        ['First', 'Second'],
        max_widths=[30, 30],
    )

    assert all(
        term._dlen(line) <= 30
        for line in capsys.readouterr().out.splitlines()
    )


def test_table_preserves_hyperlink_sequences_when_truncating(monkeypatch, capsys):
    monkeypatch.setattr(term, '_table_output_width', lambda: 24)
    monkeypatch.setattr(term, '_tty', lambda stream=None: True)
    url = 'https://example.org/resource'
    linked = term.hyperlink(term.cyan('a-very-long-resource-name'), url)

    term.table(
        [(linked, 'complete')],
        ['Resource', 'Status'],
        max_widths=[30, 10],
    )

    output = capsys.readouterr().out
    assert f'\033]8;;{url}\007' in output
    assert '\033]8;;\007' in output
    assert all(term._dlen(line) <= 24 for line in output.splitlines())


def test_redirected_table_width_is_deterministic(monkeypatch):
    monkeypatch.setattr(
        term.sys,
        'stdout',
        SimpleNamespace(isatty=lambda: False),
    )

    assert term._table_output_width() == 100


def test_interactive_table_width_uses_terminal_size(monkeypatch):
    monkeypatch.setattr(
        term.sys,
        'stdout',
        SimpleNamespace(isatty=lambda: True),
    )
    monkeypatch.setattr(
        term.shutil,
        'get_terminal_size',
        lambda fallback: SimpleNamespace(columns=72),
    )

    assert term._table_output_width() == 72
