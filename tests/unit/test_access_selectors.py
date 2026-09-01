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
