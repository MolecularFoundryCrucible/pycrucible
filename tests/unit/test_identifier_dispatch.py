"""Unit coverage for canonical identifier dispatch and exact lookups."""

from unittest.mock import MagicMock

import pytest

from crucible.resources.datasets import DatasetOperations
from crucible.resources.graphs import GraphOperations
from crucible.resources.instruments import InstrumentOperations
from crucible.resources.projects import ProjectOperations
from crucible.resources.samples import SampleOperations
from crucible.resources.users import UserOperations
from crucible.utils.deprecation import _deprecated_parameter
from crucible.utils.identifiers import (
    IdentifierIntegrityError,
    IdentifierNotFoundError,
    classify_slug_reference,
    classify_user_reference,
    collapse_exact_lookup,
)


MFID = '0tkn2knjast3h0008nyq9zps2c'
SECOND_MFID = '0td7evvtg5wb90005k1j97ak94'
ORCID = '0000-0002-1825-0097'


def make_ops(operations_class):
    client = MagicMock()
    return operations_class(client)


class TestClassification:
    def test_mfid_and_slug_are_disjoint(self):
        assert classify_slug_reference(MFID, 'project') == 'mfid'
        assert classify_slug_reference('abc', 'project') == 'slug'
        assert classify_slug_reference('a' * 25, 'project') == 'slug'

    @pytest.mark.parametrize('value', ['', None])
    def test_invalid_general_slug_reference(self, value):
        with pytest.raises(ValueError):
            classify_slug_reference(value, 'project')

    @pytest.mark.parametrize('value', ['ab', 'i' * 26, 'has spaces', 'legacy-' * 10])
    def test_legacy_slug_reference_remains_readable(self, value):
        assert classify_slug_reference(value, 'project') == 'slug'

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [
            (ORCID, ('unique_id', ORCID)),
            (MFID, ('unique_id', MFID)),
            ('Alice_User', ('username', 'alice_user')),
            ('Alice@Example.org', ('email', 'alice@example.org')),
        ],
    )
    def test_user_dispatch(self, value, expected):
        assert classify_user_reference(value) == expected


class TestExactLookupCollapse:
    def test_zero_matches_is_not_found(self):
        with pytest.raises(IdentifierNotFoundError):
            collapse_exact_lookup({'total': 0, 'items': []}, 'project', 'missing')

    def test_multiple_matches_is_integrity_error(self):
        with pytest.raises(IdentifierIntegrityError):
            collapse_exact_lookup(
                {'total': 2, 'items': [{'unique_id': MFID}, {'unique_id': SECOND_MFID}]},
                'project',
                'duplicate',
            )

    def test_unique_id_is_required(self):
        with pytest.raises(IdentifierIntegrityError):
            collapse_exact_lookup({'total': 1, 'items': [{'project_id': 'example'}]}, 'project', 'example')


class TestProjectDispatch:
    def test_mfid_uses_canonical_route(self):
        ops = make_ops(ProjectOperations)
        ops._request = MagicMock(return_value={'unique_id': MFID, 'project_id': 'example'})

        result = ops.get(MFID)

        ops._request.assert_called_once_with('get', f'/projects/{MFID}', params=None)
        assert result['unique_id'] == MFID

    def test_slug_uses_one_exact_collection_request(self):
        ops = make_ops(ProjectOperations)
        ops._request = MagicMock(return_value={
            'total': 1,
            'items': [{'unique_id': MFID, 'project_id': 'example'}],
        })

        result = ops.get('example', include_members=True)

        ops._request.assert_called_once_with(
            'get',
            '/projects',
            params={'project_id': 'example', 'limit': 2, 'include_members': True},
        )
        assert result['unique_id'] == MFID

    def test_explicit_slug_handles_mfid_shaped_legacy_value(self):
        ops = make_ops(ProjectOperations)
        ops._request = MagicMock(return_value={
            'total': 1,
            'items': [{'unique_id': SECOND_MFID, 'project_id': MFID}],
        })

        ops.get(project_id=MFID)

        ops._request.assert_called_once_with(
            'get',
            '/projects',
            params={'project_id': MFID, 'limit': 2},
        )


class TestInstrumentDispatch:
    def test_slug_lookup_does_not_add_status_filter(self):
        ops = make_ops(InstrumentOperations)
        ops._request = MagicMock(return_value={
            'total': 1,
            'items': [{'unique_id': MFID, 'instrument_id': 'beamline-1'}],
        })

        ops.get('beamline-1')

        ops._request.assert_called_once_with(
            'get',
            '/instruments',
            params={'instrument_id': 'beamline-1', 'limit': 2},
        )

    def test_explicit_mfid_keyword_uses_canonical_route(self):
        ops = make_ops(InstrumentOperations)
        ops._request = MagicMock(return_value={'unique_id': MFID, 'instrument_id': 'beamline-1'})

        ops.get(instrument_mfid=MFID)

        ops._request.assert_called_once_with('get', f'/instruments/{MFID}', params=None)

    def test_legacy_mfid_as_instrument_id_warns_and_remains_compatible(self):
        ops = make_ops(InstrumentOperations)
        ops._request = MagicMock(return_value={'unique_id': MFID, 'instrument_id': 'beamline-1'})

        with pytest.warns(DeprecationWarning, match='instrument_mfid'):
            ops.get(instrument_id=MFID)

        ops._request.assert_called_once_with('get', f'/instruments/{MFID}', params=None)


class TestUserDispatch:
    def test_orcid_uses_canonical_route(self):
        ops = make_ops(UserOperations)
        ops._request = MagicMock(return_value={'unique_id': ORCID, 'username': 'alice'})

        ops.get(ORCID)

        ops._request.assert_called_once_with('get', f'/users/{ORCID}')

    @pytest.mark.parametrize(
        ('reference', 'params'),
        [
            ('Alice_User', {'username': 'alice_user', 'limit': 2}),
            ('Alice@Example.org', {'email': 'alice@example.org', 'limit': 2}),
        ],
    )
    def test_human_identifier_uses_one_exact_collection_request(self, reference, params):
        ops = make_ops(UserOperations)
        ops._request = MagicMock(return_value={
            'total': 1,
            'items': [{'unique_id': ORCID, 'username': 'alice_user'}],
        })

        result = ops.get(reference)

        ops._request.assert_called_once_with('get', '/users', params=params)
        assert result['unique_id'] == ORCID


class TestMfidOnlyResources:
    @pytest.mark.parametrize('operations_class', [DatasetOperations, SampleOperations])
    def test_display_names_are_not_dispatched(self, operations_class):
        ops = make_ops(operations_class)

        with pytest.raises(ValueError):
            ops.get('display-name')

        ops._request.assert_not_called()

    @pytest.mark.parametrize(
        ('operations_class', 'legacy_keyword'),
        [(DatasetOperations, 'dsid'), (SampleOperations, 'sample_id')],
    )
    def test_legacy_mfid_keyword_warns(self, operations_class, legacy_keyword):
        ops = make_ops(operations_class)
        ops._request = MagicMock(return_value={'unique_id': MFID})

        with pytest.warns(DeprecationWarning, match='mfid'):
            ops.get(**{legacy_keyword: MFID})

        resource = 'datasets' if operations_class is DatasetOperations else 'samples'
        ops._request.assert_called_once_with('get', f'/{resource}/{MFID}', params=None)


class TestDeprecatedParameterCompatibility:
    def test_decorator_maps_old_keyword_and_rejects_both(self):
        @_deprecated_parameter('old_id', 'resource_mfid')
        def operation(resource_mfid):
            return resource_mfid

        with pytest.warns(DeprecationWarning, match='resource_mfid'):
            assert operation(old_id=MFID) == MFID
        with pytest.raises(TypeError, match='either'):
            operation(resource_mfid=MFID, old_id=SECOND_MFID)

    def test_dataset_sample_link_uses_mfid_parameters(self):
        ops = make_ops(DatasetOperations)
        ops._request = MagicMock(return_value={'dataset_id': MFID, 'sample_id': SECOND_MFID})

        ops.add_sample(dataset_mfid=MFID, sample_mfid=SECOND_MFID)

        ops._request.assert_called_once_with(
            'post', f'/datasets/{MFID}/samples/{SECOND_MFID}')

    def test_dataset_sample_link_preserves_old_keywords(self):
        ops = make_ops(DatasetOperations)
        ops._request = MagicMock(return_value={})

        with pytest.warns(DeprecationWarning) as warnings:
            ops.add_sample(dataset_id=MFID, sample_id=SECOND_MFID)

        assert len(warnings) == 2
        ops._request.assert_called_once_with(
            'post', f'/datasets/{MFID}/samples/{SECOND_MFID}')

    def test_sample_dataset_filter_preserves_old_keyword(self):
        ops = make_ops(SampleOperations)
        ops._paginate = MagicMock(return_value=[])

        with pytest.warns(DeprecationWarning, match='dataset_mfid'):
            ops.list(dataset_id=MFID)

        ops._paginate.assert_called_once_with(
            f'/datasets/{MFID}/samples', {}, 100, 0)

    @pytest.mark.parametrize(
        ('operations_class', 'method_name', 'resource'),
        [
            (DatasetOperations, 'link_parent_child', 'datasets'),
            (SampleOperations, 'link', 'samples'),
        ],
    )
    def test_relationship_methods_use_role_mfid_parameters(
            self, operations_class, method_name, resource):
        ops = make_ops(operations_class)
        ops._request = MagicMock(return_value={})

        getattr(ops, method_name)(parent_mfid=MFID, child_mfid=SECOND_MFID)

        ops._request.assert_called_once_with(
            'post', f'/{resource}/{MFID}/children/{SECOND_MFID}')

    @pytest.mark.parametrize(
        ('operations_class', 'method_name', 'parent_keyword', 'child_keyword', 'resource'),
        [
            (
                DatasetOperations,
                'link_parent_child',
                'parent_dataset_id',
                'child_dataset_id',
                'datasets',
            ),
            (
                DatasetOperations,
                'link_parent_child',
                'parent_dataset_mfid',
                'child_dataset_mfid',
                'datasets',
            ),
            (
                SampleOperations,
                'link',
                'parent_id',
                'child_id',
                'samples',
            ),
            (
                SampleOperations,
                'link',
                'parent_sample_mfid',
                'child_sample_mfid',
                'samples',
            ),
        ],
    )
    def test_deprecated_relationship_keywords_remain_compatible(
            self, operations_class, method_name, parent_keyword,
            child_keyword, resource):
        ops = make_ops(operations_class)
        ops._request = MagicMock(return_value={})

        with pytest.warns(DeprecationWarning) as warnings:
            getattr(ops, method_name)(**{
                parent_keyword: MFID,
                child_keyword: SECOND_MFID,
            })

        assert len(warnings) == 2
        ops._request.assert_called_once_with(
            'post', f'/{resource}/{MFID}/children/{SECOND_MFID}')

    def test_sample_update_preserves_unique_id_keyword(self):
        ops = make_ops(SampleOperations)
        ops._request = MagicMock(return_value={'unique_id': MFID})

        with pytest.warns(DeprecationWarning, match='sample_mfid'):
            ops.update(unique_id=MFID, sample_name='updated')

        ops._request.assert_called_once_with(
            'patch', f'/samples/{MFID}', json={'sample_name': 'updated'})

    def test_graph_preserves_entity_id_keyword(self):
        ops = make_ops(GraphOperations)
        ops._request = MagicMock(return_value={'nodes': [], 'links': []})

        with pytest.warns(DeprecationWarning, match='resource_mfid'):
            ops.get(entity_id=MFID)

        ops._request.assert_called_once_with(
            'get', f'/entity_graph_cte/{MFID}', params={})
