"""Unit coverage for shared interactive CLI prompts."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from crucible.cli import helpers
from crucible.cli import instrument as instrument_cli
from crucible.cli import project as project_cli
from crucible.cli import sample as sample_cli
from crucible.config import config
from crucible.utils.identifiers import IdentifierNotFoundError


def enable_interactive_stdin(monkeypatch):
    monkeypatch.setattr(helpers, '_interactive_stdin', lambda: True)


def test_required_prompt_retries_and_returns_validated_value(monkeypatch, capsys):
    enable_interactive_stdin(monkeypatch)
    answers = iter(['bad', 'VALID'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))

    def validate(value):
        if value != 'VALID':
            raise ValueError('Try again.')
        return value.lower()

    result = helpers.prompt_required(
        'Value',
        validator=validate,
    )

    assert result == 'valid'
    assert 'Invalid value' in capsys.readouterr().err


def test_optional_prompt_retries_instead_of_discarding_invalid_value(monkeypatch):
    enable_interactive_stdin(monkeypatch)
    answers = iter(['invalid', 'user@example.org'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))

    assert helpers.prompt_optional(
        'Email', validator=helpers.validate_email) == 'user@example.org'


def test_optional_prompt_returns_none_for_empty_input(monkeypatch):
    enable_interactive_stdin(monkeypatch)
    monkeypatch.setattr('builtins.input', lambda prompt: '')

    assert helpers.prompt_optional('Description') is None


def test_default_is_validated_when_input_is_empty(monkeypatch):
    enable_interactive_stdin(monkeypatch)
    monkeypatch.setattr('builtins.input', lambda prompt: '')

    assert helpers.prompt_optional(
        'Project ID', default='Default-Project', validator=str.lower) == 'default-project'


def test_required_prompt_fails_cleanly_without_interactive_stdin(monkeypatch, capsys):
    monkeypatch.setattr(helpers, '_interactive_stdin', lambda: False)

    with pytest.raises(SystemExit) as raised:
        helpers.prompt_required('Project ID', option='--project-id')

    assert raised.value.code == 2
    error = capsys.readouterr().err
    assert 'stdin is not interactive' in error
    assert '--project-id' in error


def test_optional_prompt_does_not_fail_without_interactive_stdin(monkeypatch):
    monkeypatch.setattr(helpers, '_interactive_stdin', lambda: False)

    assert helpers.prompt_optional('Description') is None


def test_invalid_default_fails_cleanly_without_interactive_stdin(monkeypatch, capsys):
    monkeypatch.setattr(helpers, '_interactive_stdin', lambda: False)

    def reject(value):
        raise ValueError('Configured project is invalid.')

    with pytest.raises(SystemExit) as raised:
        helpers.prompt_optional(
            'Project ID',
            default='invalid',
            validator=reject,
            option='--project-id',
        )

    assert raised.value.code == 2
    error = capsys.readouterr().err
    assert 'Configured project is invalid.' in error
    assert 'Provide --project-id' in error


def test_secret_prompt_uses_getpass(monkeypatch):
    enable_interactive_stdin(monkeypatch)
    monkeypatch.setattr('getpass.getpass', lambda prompt: 'secret-key')
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('input() exposed the secret'))

    assert helpers.prompt_secret('API Key') == 'secret-key'


def test_choice_prompt_retries_and_normalizes(monkeypatch):
    enable_interactive_stdin(monkeypatch)
    answers = iter(['owner', 'EDITOR'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))

    assert helpers.prompt_choice(
        'Role', ('viewer', 'contributor', 'editor', 'admin')) == 'editor'


def test_project_create_reprompts_for_invalid_required_values(monkeypatch):
    enable_interactive_stdin(monkeypatch)
    answers = iter(['-bad', 'valid-project', '', 'LBNL', 'x', 'alice', '', ''])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))
    client = SimpleNamespace(projects=SimpleNamespace())
    client.projects.create = MagicMock(return_value={
        'unique_id': '0tkn2knjast3h0008nyq9zps2c',
        'project_id': 'valid-project',
        'organization': 'LBNL',
    })
    monkeypatch.setattr('crucible.client.CrucibleClient', lambda: client)
    monkeypatch.setattr(project_cli, '_show_project', lambda project: None)

    project_cli._execute_create(SimpleNamespace(
        project_id=None,
        organization=None,
        project_lead=None,
        title=None,
        status=None,
        metadata=None,
        debug=False,
    ))

    project = client.projects.create.call_args.args[0]
    assert project.project_id == 'valid-project'
    assert project.organization == 'LBNL'
    assert project.project_lead == 'alice'


def test_instrument_create_reprompts_for_invalid_slug(monkeypatch):
    enable_interactive_stdin(monkeypatch)
    answers = iter(['-bad', 'valid-instrument', '', '', '', ''])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))
    client = SimpleNamespace(instruments=SimpleNamespace())
    client.instruments.create = MagicMock(return_value={
        'unique_id': '0tkn2knjast3h0008nyq9zps2c',
        'instrument_id': 'valid-instrument',
        'instrument_name': 'Instrument',
        'location': 'Building 67',
    })
    monkeypatch.setattr('crucible.client.CrucibleClient', lambda: client)
    monkeypatch.setattr(instrument_cli, '_show_instrument', lambda instrument: None)

    instrument_cli._execute_create(SimpleNamespace(
        instrument_name='Instrument',
        instrument_id=None,
        owner=None,
        location='Building 67',
        manufacturer=None,
        model=None,
        instrument_type=None,
        description=None,
        metadata=None,
        debug=False,
    ))

    instrument = client.instruments.create.call_args.args[0]
    assert instrument.instrument_id == 'valid-instrument'


def test_sample_create_reprompts_when_project_is_not_found(monkeypatch):
    enable_interactive_stdin(monkeypatch)
    answers = iter(['missing-project', 'valid-project', '', '', ''])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))
    monkeypatch.setattr(config, '_data', {**config._data, 'current_project': None})
    client = SimpleNamespace(projects=SimpleNamespace(), samples=SimpleNamespace())
    client.projects.get = MagicMock(side_effect=[
        IdentifierNotFoundError('Project not found: missing-project'),
        {'unique_id': '0tkn2knjast3h0008nyq9zps2c', 'project_id': 'valid-project'},
    ])
    client.samples.create = MagicMock(return_value={
        'unique_id': '0td7evvtg5wb90005k1j97ak94',
        'sample_name': 'Sample',
        'project_id': 'valid-project',
    })
    monkeypatch.setattr('crucible.client.CrucibleClient', lambda: client)
    monkeypatch.setattr(sample_cli, '_show_sample', lambda sample, client: None)

    sample_cli._execute_create(SimpleNamespace(
        name='Sample',
        project_id=None,
        description=None,
        sample_type=None,
        timestamp=None,
        metadata=None,
        public=False,
        debug=False,
    ))

    sample = client.samples.create.call_args.args[0]
    assert sample.project_id == 'valid-project'
    assert client.projects.get.call_count == 2
