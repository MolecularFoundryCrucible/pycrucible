"""Unit tests for the permission-system overhaul - mocked, no live API.

Targets the `feat/permission-roles` crucible-api branch (see
crucible-api/docs/permission_system_api_changes.md), not yet universally
deployed - see tests/unit/ vs tests/integration/ split in CLAUDE.md.
"""

import pytest
from unittest.mock import MagicMock

from crucible.models import (
    AccessGrant,
    EffectiveResourceAccess,
    Instrument,
    OwnershipTransfer,
    ProjectMember,
    ProjectReassignment,
)
from crucible.resources.datasets import DatasetOperations
from crucible.resources.instruments import InstrumentOperations
from crucible.resources.projects import ProjectOperations
from crucible.resources.users import UserOperations


@pytest.fixture
def dataset_ops():
    client = MagicMock()
    ops = DatasetOperations(client)
    ops._client = client
    return ops


@pytest.fixture
def instrument_ops():
    client = MagicMock()
    ops = InstrumentOperations(client)
    ops._client = client
    return ops


@pytest.fixture
def project_ops():
    client = MagicMock()
    ops = ProjectOperations(client)
    ops._client = client
    return ops


@pytest.fixture
def user_ops():
    client = MagicMock()
    ops = UserOperations(client)
    ops._client = client
    return ops


class TestListAccess:
    def test_parses_access_grants(self, dataset_ops):
        dataset_ops._request = MagicMock(return_value=[
            {'principal_id': '0000-0001', 'principal_type': 'user', 'permission': 'viewer',
             'display_name': 'A User'},
        ])

        result = dataset_ops.list_access('ds-1')

        dataset_ops._request.assert_called_once_with('get', '/resources/ds-1/access')
        assert isinstance(result[0], AccessGrant)
        assert result[0].principal_type == 'user'
        assert result[0].permission == 'viewer'
        assert result[0].kind == 'user'
        assert result[0].effective_permission == 'viewer'


class TestSetAccess:
    def test_sends_correct_route_and_body(self, dataset_ops):
        dataset_ops._request = MagicMock(return_value={
            'principal_id': 'project-mfid', 'principal_type': 'project',
            'permission': 'editor', 'slug': 'proj-1',
        })

        result = dataset_ops.set_access('ds-1', 'projects', 'proj-1', 'editor')

        dataset_ops._request.assert_called_once_with(
            'put', '/resources/ds-1/access/projects/proj-1',
            json={'permission': 'editor'})
        assert isinstance(result, AccessGrant)
        assert result.principal_id == 'project-mfid'
        assert result.slug == 'proj-1'


class TestRevokeAccess:
    def test_sends_correct_route(self, dataset_ops):
        dataset_ops._request = MagicMock(return_value=None)

        dataset_ops.revoke_access('ds-1', 'users', '0000-0001')

        dataset_ops._request.assert_called_once_with(
            'delete', '/resources/ds-1/access/users/0000-0001')


class TestPublicAccess:
    def test_set_public_no_permission_param(self, dataset_ops):
        dataset_ops._request = MagicMock(return_value={
            'principal_id': 'public',
            'principal_type': 'public',
            'permission': 'viewer',
        })

        dataset_ops.set_public('ds-1')

        dataset_ops._request.assert_called_once_with('put', '/resources/ds-1/access/public')

    def test_unset_public(self, dataset_ops):
        dataset_ops._request = MagicMock(return_value=None)

        dataset_ops.unset_public('ds-1')

        dataset_ops._request.assert_called_once_with('delete', '/resources/ds-1/access/public')


class TestEffectiveDatasetAccess:
    def test_parses_effective_access(self, user_ops):
        user_ops._request = MagicMock(return_value={
            'resource_mfid': 'ds-1',
            'user_id': '0000-0001',
            'effective_access': 'editor',
        })

        result = user_ops.check_dataset_access('alice', 'ds-1')

        user_ops._request.assert_called_once_with(
            'get', '/users/alice/datasets/ds-1')
        assert isinstance(result, EffectiveResourceAccess)
        assert result.effective_access == 'editor'


class TestTransferOwnership:
    def test_preview_by_default(self, dataset_ops):
        dataset_ops._request = MagicMock(return_value={
            'resource_id': 'ds-1',
            'previous_owner': {'unique_id': 'u1', 'username': 'old'},
            'new_owner': {'unique_id': 'u2', 'username': 'new'},
        })

        result = dataset_ops.transfer_ownership('ds-1', 'new')

        dataset_ops._request.assert_called_once_with(
            'post', '/resources/ds-1/transfer_ownership',
            params={'confirm': False}, json={'new_owner': 'new'})
        assert isinstance(result, OwnershipTransfer)
        assert result.new_owner.username == 'new'

    def test_confirm_true_passed_through(self, dataset_ops):
        dataset_ops._request = MagicMock(return_value={
            'resource_id': 'ds-1', 'previous_owner': None,
            'new_owner': {'unique_id': 'u2', 'username': 'new'},
        })

        dataset_ops.transfer_ownership('ds-1', 'new', confirm=True)

        assert dataset_ops._request.call_args.kwargs['params'] == {'confirm': True}


class TestReassignProject:
    def test_sends_correct_route_and_body(self, dataset_ops):
        dataset_ops._request = MagicMock(return_value={
            'resource_id': 'ds-1', 'previous_project_id': 'old-proj', 'new_project_id': 'new-proj',
        })

        result = dataset_ops.reassign_project('ds-1', 'new-proj', confirm=True)

        dataset_ops._request.assert_called_once_with(
            'post', '/resources/ds-1/project',
            params={'confirm': True}, json={'project_id': 'new-proj'})
        assert isinstance(result, ProjectReassignment)
        assert result.new_project_id == 'new-proj'


class TestInstrumentCreateRequiresInstrumentId:
    def test_raises_when_missing(self, instrument_ops):
        instrument = Instrument(instrument_name='titan', owner='mf', location='B67')

        with pytest.raises(ValueError):
            instrument_ops.create(instrument)

    def test_passes_through_when_present(self, instrument_ops):
        instrument_ops._request = MagicMock(side_effect=[
            {'total': 0, 'items': []},
            {'unique_id': 'mf-1', 'instrument_id': 'titan'},
        ])
        instrument = Instrument(instrument_name='titan', instrument_id='titan', owner='mf', location='B67')

        result = instrument_ops.create(instrument)

        assert instrument_ops._request.call_count == 2
        _, endpoint = instrument_ops._request.call_args.args
        assert endpoint == '/instruments'
        assert instrument_ops._request.call_args.kwargs['json']['instrument_id'] == 'titan'
        assert result['instrument_id'] == 'titan'


class TestBindServiceAccount:
    def test_bind(self, instrument_ops):
        instrument_ops._request = MagicMock(return_value=[
            {'unique_id': 'sa-1', 'username': 'sa', 'role': 'operator'},
        ])

        result = instrument_ops.bind_service_account('mf-1', 'sa-1')

        instrument_ops._request.assert_called_once_with(
            'post', '/instruments/mf-1/service_accounts/sa-1')
        assert isinstance(result[0], ProjectMember)
        assert result[0].role == 'operator'

    def test_unbind(self, instrument_ops):
        instrument_ops._request = MagicMock(return_value=[])

        instrument_ops.unbind_service_account('mf-1', 'sa-1')

        instrument_ops._request.assert_called_once_with(
            'delete', '/instruments/mf-1/service_accounts/sa-1')


class TestProjectAddUserRole:
    def test_role_passed_as_query_param(self, project_ops):
        project_ops._request = MagicMock(return_value=[
            {'unique_id': 'u1', 'username': 'alice', 'role': 'editor'},
        ])

        result = project_ops.add_user(orcid='0000-0001', project_id='proj-1', role='editor')

        project_ops._request.assert_called_once_with(
            'post', '/projects/proj-1/users/0000-0001', params={'role': 'editor'})
        assert isinstance(result[0], ProjectMember)
        assert result[0].role == 'editor'

    def test_role_omitted_when_not_given(self, project_ops):
        project_ops._request = MagicMock(return_value=[])

        project_ops.add_user(orcid='0000-0001', project_id='proj-1')

        project_ops._request.assert_called_once_with(
            'post', '/projects/proj-1/users/0000-0001', params={})


class TestProjectUpdateUserRole:
    def test_sends_correct_route_and_param(self, project_ops):
        project_ops._request = MagicMock(return_value=[
            {'unique_id': 'u1', 'username': 'alice', 'role': 'admin'},
        ])

        result = project_ops.update_user_role('proj-1', '0000-0001', 'admin')

        project_ops._request.assert_called_once_with(
            'patch', '/projects/proj-1/users/0000-0001', params={'role': 'admin'})
        assert result[0].role == 'admin'


class TestProjectGetIncludeMembers:
    def test_include_members_sets_param(self, project_ops):
        project_ops._request = MagicMock(return_value={
            'total': 1,
            'items': [{'unique_id': '0tkn2knjast3h0008nyq9zps2c', 'project_id': 'proj-1', 'members': []}],
        })

        project_ops.get('proj-1', include_members=True)

        project_ops._request.assert_called_once_with(
            'get', '/projects',
            params={'project_id': 'proj-1', 'limit': 2, 'include_members': True})

    def test_no_flags_sends_no_params(self, project_ops):
        project_ops._request = MagicMock(return_value={
            'total': 1,
            'items': [{'unique_id': '0tkn2knjast3h0008nyq9zps2c', 'project_id': 'proj-1'}],
        })

        project_ops.get('proj-1')

        project_ops._request.assert_called_once_with(
            'get', '/projects', params={'project_id': 'proj-1', 'limit': 2})

    def test_both_flags_combine(self, project_ops):
        project_ops._request = MagicMock(return_value={
            'total': 1,
            'items': [{'unique_id': '0tkn2knjast3h0008nyq9zps2c', 'project_id': 'proj-1'}],
        })

        project_ops.get('proj-1', include_metadata=True, include_members=True)

        project_ops._request.assert_called_once_with(
            'get', '/projects', params={
                'project_id': 'proj-1',
                'limit': 2,
                'include_metadata': True,
                'include_members': True,
            })


class TestProjectUpdateNoIdentifierCollision:
    def test_project_id_field_and_identifier_coexist(self, project_ops):
        project_ops._request = MagicMock(return_value={'project_id': 'new-slug'})

        result = project_ops.update('old-slug', project_id='new-slug')

        project_ops._request.assert_called_once_with(
            'patch', '/projects/old-slug', json={'project_id': 'new-slug'})
        assert result['project_id'] == 'new-slug'
