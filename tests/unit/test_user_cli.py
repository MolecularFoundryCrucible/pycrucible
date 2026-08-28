"""Unit coverage for user CLI presentation."""

from crucible.cli.user import _show_user


BASE_USER = {
    'unique_id': '0000-0001-6402-3752',
    'username': 'roncofaber',
    'first_name': 'Fabrice',
    'last_name': 'Roncoroni',
}


def test_omitted_email_is_reported_as_not_disclosed(capsys):
    _show_user(dict(BASE_USER))

    assert '(not disclosed)' in capsys.readouterr().out


def test_explicit_null_email_is_reported_as_not_set(capsys):
    _show_user({**BASE_USER, 'email': None})

    assert '(not set)' in capsys.readouterr().out


def test_authorized_email_is_displayed(capsys):
    _show_user({**BASE_USER, 'email': 'roncoroni@lbl.gov'})

    assert 'roncoroni@lbl.gov' in capsys.readouterr().out
