"""Unit coverage for user CLI presentation."""

from crucible.cli.user import _show_user


BASE_USER = {
    'unique_id': '0000-0001-6402-3752',
    'username': 'roncofaber',
    'first_name': 'Fabrice',
    'last_name': 'Roncoroni',
}


def test_omitted_email_row_is_hidden(capsys):
    _show_user(dict(BASE_USER))

    output = capsys.readouterr().out
    assert 'Email' not in output
    assert '(not disclosed)' not in output


def test_explicit_null_email_is_reported_as_not_set(capsys):
    _show_user({**BASE_USER, 'email': None})

    output = capsys.readouterr().out
    assert 'Email' in output
    assert '(not set)' in output


def test_authorized_email_is_displayed(capsys):
    _show_user({**BASE_USER, 'email': 'roncoroni@lbl.gov'})

    assert 'roncoroni@lbl.gov' in capsys.readouterr().out
