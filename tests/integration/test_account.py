"""Integration tests for client.account.* and client.whoami()."""


def test_whoami(client):
    info = client.whoami()
    assert info is not None


def test_account_profile(client):
    p = client.account.profile()
    assert p is not None
    assert p.get('unique_id') or p.get('orcid')


def test_account_api_key(client):
    key = client.account.api_key()
    assert isinstance(key, str) and len(key) > 0


def test_account_verify(client):
    info = client.account.verify()
    assert 'valid' in info
    assert info['valid'] is True
