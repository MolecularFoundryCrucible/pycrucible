#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models for Crucible API request and response objects.
"""

from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Optional

#%% Base model

class CrucibleResource(BaseModel):
    """Shared fields common to all Crucible resources."""

    unique_id: Optional[str] = None
    public: Optional[bool] = False
    creation_time: Optional[str] = None
    modification_time: Optional[str] = None
    resource_type: Optional[str] = None
    scientific_metadata: Optional[Dict] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra='allow')


#%% Models

class Sample(CrucibleResource):
    sample_name: Optional[str] = None
    sample_type: Optional[str] = None
    owner_orcid: Optional[str] = None
    project_id: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[str] = None
    datasets: Optional[List[Dict]] = None
    deletion_request: Optional[Dict] = None
    links: Optional[List[Dict]] = None


class Dataset(CrucibleResource):
    dataset_name: Optional[str] = None
    owner_orcid: Optional[str] = None
    project_id: Optional[str] = None
    instrument_name: Optional[str] = None
    measurement: Optional[str] = None
    data_type: Optional[str] = None
    session_name: Optional[str] = None
    data_format: Optional[str] = None
    size: Optional[int] = None
    timestamp: Optional[str] = None
    deletion_request: Optional[Dict] = None
    links: Optional[List[Dict]] = None


class Instrument(CrucibleResource):
    instrument_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    owner: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    instrument_type: Optional[str] = None
    other_id: Optional[str] = None
    other_id_source: Optional[str] = None


class Project(BaseModel):
    project_id: str
    organization: str
    lead: Optional[Dict] = None
    project_lead_orcid: Optional[str] = None
    project_lead_email: Optional[str] = None
    project_lead_username: Optional[str] = None
    status: Optional[str] = None
    title: Optional[str] = None
    scientific_metadata: Optional[Dict] = None
    creation_time: Optional[str] = None
    modification_time: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra='allow')


class User(BaseModel):
    orcid: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    is_service_account: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AssociatedFile(BaseModel):
    '''A file attached to a dataset.'''

    mfid: Optional[str] = None
    dataset_mfid: Optional[str] = None
    filename: Optional[str] = None
    storage_path: Optional[str] = None
    size: Optional[int] = None
    sha256_hash: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra='allow')


class DeletionRequest(BaseModel):
    '''A pending or resolved request to delete a resource.'''

    id: Optional[int] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    project_id: Optional[str] = None
    requester_id: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None          # "pending" | "approved" | "rejected"
    request_time: Optional[str] = None
    review_time: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra='allow')


class DeletionAuditLog(BaseModel):
    '''Permanent record of a hard-deleted resource. Written before deletion; survives it.'''

    id: Optional[int] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None
    project_id: Optional[str] = None
    requester_id: Optional[str] = None
    reason: Optional[str] = None
    request_time: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    review_time: Optional[str] = None
    deleted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra='allow')


#%% Backward-compatibility aliases (deprecated)

def __getattr__(name: str):
    import warnings
    _aliases = {
        'BaseDataset': Dataset,
        'BaseSample':  Sample,
    }
    if name in _aliases:
        warnings.warn(
            f"'{name}' is deprecated; use '{_aliases[name].__name__}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _aliases[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
