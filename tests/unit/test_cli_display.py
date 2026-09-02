"""Unit coverage for shared CLI resource presentation."""

from types import SimpleNamespace

import pytest

from crucible.cli import access_group as access_group_cli
from crucible.cli import dataset as dataset_cli
from crucible.cli import deletion as deletion_cli
from crucible.cli import helpers
from crucible.cli import instrument as instrument_cli
from crucible.cli import project as project_cli
from crucible.cli import sample as sample_cli
from crucible.cli import service_account as service_account_cli
from crucible.cli import shell as shell_cli
from crucible.cli import term


MFID = '0tkn2knjast3h0008nyq9zps2c'


@pytest.mark.parametrize(('execute', 'args', 'expected'), [
    (
        project_cli._execute_list_join_requests,
        SimpleNamespace(project_id='project-slug', status=None, limit=100),
        'No join requests found.',
    ),
    (
        access_group_cli._execute_list,
        SimpleNamespace(status='pending', group_name=None, requester_id=None, limit=100),
        'No join requests found.',
    ),
    (
        access_group_cli._execute_mine,
        SimpleNamespace(status='pending', limit=100),
        'No join requests found.',
    ),
    (
        service_account_cli._execute_list,
        SimpleNamespace(limit=100, json=False),
        'No service accounts found.',
    ),
    (
        deletion_cli._execute_list_deleted,
        SimpleNamespace(resource_id=None, requester_id=None, reviewer_id=None, limit=100),
        'No deleted resources found.',
    ),
])
def test_empty_listings_name_their_subject(execute, args, expected, monkeypatch, capsys):
    client = SimpleNamespace(
        projects=SimpleNamespace(list_join_requests=lambda *args, **kwargs: []),
        access_groups=SimpleNamespace(list_join_requests=lambda **kwargs: []),
        account=SimpleNamespace(join_requests=lambda **kwargs: []),
        service_accounts=SimpleNamespace(list=lambda **kwargs: []),
        deletions=SimpleNamespace(list_deleted=lambda **kwargs: []),
    )
    monkeypatch.setattr('crucible.client.CrucibleClient', lambda: client)

    execute(args)

    output = capsys.readouterr().out
    assert expected in output
    assert 'None found.' not in output
    assert 'No records found.' not in output


@pytest.mark.parametrize(('value', 'expected'), [
    (True, 'yes'),
    (False, 'no'),
    (None, '-'),
])
def test_nullable_boolean_formatting(value, expected):
    assert term.fmt_bool(value) == expected


def test_success_message_uses_text_and_respects_json(monkeypatch, capsys):
    monkeypatch.setattr(term, '_tty', lambda stream=None: True)

    term.success('Project created')
    term.success('Hidden', SimpleNamespace(json=True))

    output = capsys.readouterr().out
    assert '\033[32mSuccess:\033[0m Project created' in output
    assert 'Hidden' not in output


@pytest.mark.parametrize(('status', 'expected'), [
    ('success', 'OK'),
    ('warning', 'WARNING'),
    ('error', 'ERROR'),
    ('info', 'INFO'),
])
def test_status_markers_use_words_when_redirected(status, expected, monkeypatch):
    monkeypatch.setattr(term, '_interactive', lambda stream=None: False)

    assert term.status_marker(status) == expected


def test_status_markers_use_symbols_in_interactive_output(monkeypatch):
    monkeypatch.setattr(term, '_interactive', lambda stream=None: True)

    assert term.status_marker('success') == '✓'
    assert term.status_marker('error') == '×'


def test_project_members_sort_by_role_then_name():
    members = [
        {'username': 'zoe', 'first_name': 'Zoe', 'role': 'viewer'},
        {'username': 'amy', 'first_name': 'Amy', 'role': 'editor'},
        {'username': 'ben', 'first_name': 'Ben', 'role': 'admin'},
        {'username': 'ann', 'first_name': 'Ann', 'role': 'admin'},
        {'username': 'lee', 'first_name': 'Lee', 'role': 'owner'},
        {'username': 'cal', 'first_name': 'Cal', 'role': 'contributor'},
    ]

    ordered = helpers.sort_members(members)

    assert [(member['role'], member['username']) for member in ordered] == [
        ('owner', 'lee'),
        ('admin', 'ann'),
        ('admin', 'ben'),
        ('editor', 'amy'),
        ('contributor', 'cal'),
        ('viewer', 'zoe'),
    ]


@pytest.mark.parametrize(('role', 'code'), [
    ('owner', '38;5;220'),
    ('admin', '31'),
    ('editor', '34'),
    ('contributor', '36'),
    ('viewer', '90'),
])
def test_project_role_labels_have_distinct_colors(role, code, monkeypatch):
    monkeypatch.setattr(term, '_tty', lambda stream=None: True)

    display_role = 'lead' if role == 'owner' else role
    assert term.role_label(role) == f'\033[{code}m{display_role}\033[0m'


def test_project_role_labels_remain_plain_when_redirected(monkeypatch):
    monkeypatch.setattr(term, '_tty', lambda stream=None: False)

    assert term.role_label('admin') == 'admin'


def test_shell_toolbar_restores_context_symbols(monkeypatch):
    from prompt_toolkit.formatted_text import fragment_list_to_text, to_formatted_text

    shell = shell_cli.CrucibleShell.__new__(shell_cli.CrucibleShell)
    shell.state = {
        'project': 'example-project',
        'session': '',
        'user_label': 'Test User',
        'api_label': 'api: testapi-staging',
        'debug': False,
    }
    app = SimpleNamespace(output=SimpleNamespace(
        get_size=lambda: SimpleNamespace(columns=100)))
    monkeypatch.setattr('prompt_toolkit.application.get_app', lambda: app)

    rendered = fragment_list_to_text(to_formatted_text(shell._toolbar()))

    assert '🔬 example-project' in rendered
    assert '🧸 Test User' in rendered
    assert '🔗 api: testapi-staging' in rendered


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


def test_project_detail_sorts_and_colors_member_roles(monkeypatch, capsys):
    monkeypatch.setattr(term, '_tty', lambda stream=None: True)

    project_cli._show_project({
        'unique_id': MFID,
        'project_id': 'project-slug',
        'members': [
            {'username': 'viewer-user', 'first_name': 'Viewer', 'role': 'viewer'},
            {'username': 'lead-user', 'first_name': 'Lead', 'role': 'owner'},
            {'username': 'admin-user', 'first_name': 'Admin', 'role': 'admin'},
        ],
    }, include_members=True)

    output = capsys.readouterr().out
    assert output.index('lead-user') < output.index('admin-user') < output.index('viewer-user')
    assert '\033[38;5;220mlead\033[0m' in output
    assert '\033[31madmin\033[0m' in output
    assert '\033[90mviewer\033[0m' in output


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
