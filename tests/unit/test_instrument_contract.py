"""Unit coverage for instrument API and CLI contract alignment."""

import argparse
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from crucible.cli import instrument as instrument_cli
from crucible.cli import term
from crucible.models import Instrument
from crucible.resources.instruments import InstrumentOperations


MFID = '0tkn2knjast3h0008nyq9zps2c'
USER_MFID = '0tkvpezyz1zzf00076nahf85j4'


def make_ops():
    return InstrumentOperations(MagicMock())


def make_parser(register):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    register(subparsers)
    return parser


def test_list_preserves_positional_limit_and_offset():
    operations = make_ops()
    operations._paginate = MagicMock(return_value=[])

    operations.list(False, 5, 2)

    operations._paginate.assert_called_once_with('/instruments', {}, 5, 2)


def test_list_requests_owner_and_status_filters():
    operations = make_ops()
    operations._paginate = MagicMock(return_value=[{
        'unique_id': MFID,
        'instrument_id': 'team-i',
        'owner_orcid': USER_MFID,
    }])

    result = operations.list(
        include_metadata=True,
        include_owner=True,
        status='maintenance',
        limit=7,
    )

    operations._paginate.assert_called_once_with(
        '/instruments',
        {
            'include_metadata': True,
            'include_owner': True,
            'status': 'maintenance',
        },
        7,
        0,
    )
    assert result[0]['owner_orcid'] == USER_MFID


def test_list_rejects_unknown_status():
    with pytest.raises(ValueError, match='status must be one of'):
        make_ops().list(status='retired')


def test_search_can_request_expanded_owners():
    operations = make_ops()
    operations._request = MagicMock(return_value={'items': [{'unique_id': MFID}]})

    operations.search('team', limit=4, include_owner=True)

    operations._request.assert_called_once_with(
        'get', '/instruments/search',
        params={'q': 'team', 'limit': 4, 'include_owner': True},
    )


def test_update_rejects_owner_fields_locally():
    operations = make_ops()
    operations._request = MagicMock()

    with pytest.raises(ValueError, match='transfer_ownership'):
        operations.update(MFID, owner='another-user')

    operations._request.assert_not_called()


def test_create_rejects_expanded_owner_object():
    operations = make_ops()

    with pytest.raises(ValueError, match='must be a string identifier'):
        operations.create(Instrument(
            instrument_id='team-i',
            instrument_name='TEAM I',
            location='72-150',
            owner={
                'unique_id': USER_MFID,
                'username': 'test-user-one',
                'first_name': 'Test',
                'last_name': 'User One',
            },
        ))


def test_create_warns_for_legacy_owner_orcid():
    operations = make_ops()
    operations._request = MagicMock(side_effect=[
        {'total': 0, 'items': []},
        {'unique_id': MFID, 'owner_orcid': USER_MFID},
    ])

    with pytest.warns(DeprecationWarning, match='Instrument.owner_orcid'):
        operations.create(Instrument(
            instrument_id='team-i',
            instrument_name='TEAM I',
            location='72-150',
            owner_orcid=USER_MFID,
        ))

    assert operations._request.call_args.kwargs['json']['owner_orcid'] == USER_MFID


def test_mfid_backed_owner_is_not_linked_to_orcid(monkeypatch):
    monkeypatch.setattr(term, '_tty', lambda: True)
    rendered = term.fmt_owner({
        'owner_orcid': USER_MFID,
        'owner': {
            'unique_id': USER_MFID,
            'username': 'test-user-one',
            'first_name': 'Test',
            'last_name': 'User One',
        },
    })

    assert 'Test User One (@test-user-one)' in rendered
    assert 'orcid.org' not in rendered


def test_list_parser_exposes_status_and_json():
    args = make_parser(instrument_cli._register_list).parse_args([
        'list', '--status', 'maintenance', '--json',
    ])

    assert args.status == 'maintenance'
    assert args.json is True


def test_create_parser_leaves_owner_optional():
    args = make_parser(instrument_cli._register_create).parse_args([
        'create', '--instrument-id', 'team-i', '--name', 'TEAM I',
        '--location', '72-150',
    ])

    assert args.owner is None


def test_update_parser_no_longer_accepts_owner():
    parser = make_parser(instrument_cli._register_update)

    with pytest.raises(SystemExit):
        parser.parse_args(['update', MFID, '--owner', 'another-user'])


def test_transfer_parser_defaults_to_preview():
    args = make_parser(instrument_cli._register_transfer_ownership).parse_args([
        'transfer-ownership', MFID, 'new-owner',
    ])

    assert args.instrument_mfid == MFID
    assert args.new_owner == 'new-owner'
    assert args.confirm is False


def test_cli_list_requests_owners_and_formats_public_owner(monkeypatch, capsys):
    client = SimpleNamespace(instruments=SimpleNamespace())
    client.instruments.list = MagicMock(return_value=[{
        'unique_id': MFID,
        'instrument_id': 'team-i',
        'instrument_name': 'TEAM I',
        'owner_orcid': USER_MFID,
        'owner': {
            'unique_id': USER_MFID,
            'username': 'test-user-one',
            'first_name': 'Test',
            'last_name': 'User One',
        },
        'status': 'active',
    }])
    monkeypatch.setattr('crucible.client.CrucibleClient', lambda: client)
    args = SimpleNamespace(
        limit=10,
        include_metadata=False,
        status=None,
        json=False,
        debug=False,
    )

    instrument_cli._execute_list(args)

    client.instruments.list.assert_called_once_with(
        limit=10,
        include_metadata=False,
        include_owner=True,
        status=None,
    )
    output = capsys.readouterr().out
    assert 'Test User One' in output
    assert "{'unique_id'" not in output
