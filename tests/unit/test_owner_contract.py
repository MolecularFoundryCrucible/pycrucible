"""Unit coverage for dataset and sample owner request and response contracts."""

import warnings
from unittest.mock import MagicMock

import pytest

from crucible.models import Dataset, PublicUser, Sample
from crucible.resources.datasets import DatasetOperations
from crucible.resources.samples import SampleOperations


MFID = '0tkn2knjast3h0008nyq9zps2c'
ORCID = '0000-0001-6402-3752'
PUBLIC_OWNER = {
    'unique_id': ORCID,
    'username': 'roncofaber',
    'first_name': 'Fabrice',
    'last_name': 'Roncoroni',
}


def make_ops(operations_class, response):
    client = MagicMock()
    operations = operations_class(client)
    operations._request = MagicMock(return_value=response)
    return operations


@pytest.mark.parametrize('model', [Dataset, Sample])
def test_owner_response_uses_public_user_model(model):
    resource = model.model_validate({
        'unique_id': MFID,
        'owner_orcid': ORCID,
        'owner': PUBLIC_OWNER,
    })

    assert isinstance(resource.owner, PublicUser)
    assert resource.model_dump()['owner'] == PUBLIC_OWNER


@pytest.mark.parametrize(
    ('operations_class', 'resource_name'),
    [(DatasetOperations, 'datasets'), (SampleOperations, 'samples')],
)
def test_get_requests_and_preserves_public_owner(operations_class, resource_name):
    response = {'unique_id': MFID, 'owner_orcid': ORCID, 'owner': PUBLIC_OWNER}
    operations = make_ops(operations_class, response)

    result = operations.get(MFID, include_owner=True)

    operations._request.assert_called_once_with(
        'get',
        f'/{resource_name}/{MFID}',
        params={'include_owner': True},
    )
    assert result['owner'] == PUBLIC_OWNER


def test_dataset_create_warns_for_owner_orcid_and_preserves_payload():
    operations = make_ops(DatasetOperations, {'unique_id': MFID})

    with pytest.warns(DeprecationWarning, match='Dataset.owner_orcid'):
        operations.create(Dataset(unique_id=MFID, dataset_name='test', owner_orcid=ORCID))

    assert operations._request.call_args.kwargs['json']['owner_orcid'] == ORCID


def test_sample_create_warns_for_owner_orcid_and_preserves_payload():
    operations = make_ops(SampleOperations, {'unique_id': MFID})

    with pytest.warns(DeprecationWarning, match='Sample.owner_orcid'):
        operations.create(Sample(unique_id=MFID, sample_name='test', owner_orcid=ORCID))

    assert operations._request.call_args.kwargs['json']['owner_orcid'] == ORCID


@pytest.mark.parametrize(
    ('operations_class', 'resource'),
    [
        (DatasetOperations, Dataset(unique_id=MFID, dataset_name='test', owner='roncofaber')),
        (SampleOperations, Sample(unique_id=MFID, sample_name='test', owner='roncofaber')),
    ],
)
def test_create_prefers_flexible_owner_without_warning(operations_class, resource):
    operations = make_ops(operations_class, {'unique_id': MFID})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        operations.create(resource)

    assert not caught
    assert operations._request.call_args.kwargs['json']['owner'] == 'roncofaber'


@pytest.mark.parametrize(
    ('operations_class', 'resource'),
    [
        (DatasetOperations, Dataset(unique_id=MFID, dataset_name='test', owner=PUBLIC_OWNER)),
        (SampleOperations, Sample(unique_id=MFID, sample_name='test', owner=PUBLIC_OWNER)),
    ],
)
def test_create_rejects_expanded_owner_record(operations_class, resource):
    operations = make_ops(operations_class, {'unique_id': MFID})

    with pytest.raises(ValueError, match='string identifier'):
        operations.create(resource)

    operations._request.assert_not_called()
