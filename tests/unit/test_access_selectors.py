"""Unit coverage for typed resource access selectors."""

from unittest.mock import MagicMock

import pytest

from crucible.resources.datasets import DatasetOperations
from crucible.resources.projects import ProjectOperations
from crucible.resources.samples import SampleOperations


@pytest.mark.parametrize(
    ('operations_class', 'endpoint'),
    [
        (DatasetOperations, '/datasets'),
        (SampleOperations, '/samples'),
        (ProjectOperations, '/projects'),
    ],
)
def test_lists_with_repeated_user_and_project_selectors(operations_class, endpoint):
    client = MagicMock()
    operations = operations_class(client)
    operations._request = MagicMock(return_value={
        'total': 0,
        'limit': 5,
        'offset': 0,
        'items': [],
    })

    operations.list(
        accessible_to_user=['alice', 'bob'],
        accessible_to_project=['project-a'],
        limit=5,
    )

    operations._request.assert_called_once_with(
        'get',
        endpoint,
        params={
            'accessible_to_user': ['alice', 'bob'],
            'accessible_to_project': ['project-a'],
            'limit': 5,
        },
    )


def test_rejects_more_than_ten_selectors():
    operations = DatasetOperations(MagicMock())

    with pytest.raises(ValueError, match='At most 10'):
        operations.list(accessible_to_user=[str(i) for i in range(11)])


def test_rejects_selectors_on_nested_collection():
    operations = SampleOperations(MagicMock())

    with pytest.raises(ValueError, match='top-level sample list'):
        operations.list(dataset_mfid='dataset', accessible_to_user='alice')


def test_dataset_list_filters_by_instrument_mfid():
    operations = DatasetOperations(MagicMock())
    operations._request = MagicMock(return_value={
        'total': 0,
        'limit': 5,
        'offset': 0,
        'items': [],
    })

    operations.list(instrument_mfid='0tkn2knjast3h0008nyq9zps2c', limit=5)

    operations._request.assert_called_once_with(
        'get',
        '/datasets',
        params={
            'instrument_mfid': '0tkn2knjast3h0008nyq9zps2c',
            'limit': 5,
        },
    )


def test_rejects_instrument_filter_on_nested_dataset_collection():
    operations = DatasetOperations(MagicMock())

    with pytest.raises(ValueError, match='top-level dataset list'):
        operations.list(
            sample_mfid='0tkn2knjast3h0008nyq9zps2c',
            instrument_mfid='0tk8pf1me0h3h0003fp91vr037',
        )
