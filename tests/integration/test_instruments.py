"""Integration tests for client.instruments.*"""

import pytest


def test_instrument_list(client):
    instruments = client.instruments.list(limit=5)
    assert isinstance(instruments, list)


def test_instrument_get(client):
    instruments = client.instruments.list(limit=1)
    if not instruments:
        pytest.skip("no instruments available")
    iid = instruments[0].get('unique_id')
    inst = client.instruments.get(instrument_id=iid)
    assert inst.get('unique_id') == iid


def test_instrument_search(client):
    results = client.instruments.search('micro', limit=5)
    assert isinstance(results, list)


def test_instrument_search_metadata(client):
    results = client.instruments.search_metadata('test', limit=5)
    assert isinstance(results, list)
