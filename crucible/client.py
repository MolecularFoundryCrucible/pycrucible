#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main client for Crucible API.

Provides organized access to API endpoints.
"""

import time
import requests
import json
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, List, Dict, Any, Union
from .models import Dataset, Project
from .constants import DEFAULT_LIMIT
from .utils.deprecation import _deprecated, _removed

logger = logging.getLogger(__name__)

#%%

class CrucibleClient:
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the Crucible API client.

        Args:
            api_url: Base URL for the Crucible API (loads from config if not provided)
            api_key: API key for authentication (loads from config if not provided)

        Raises:
            ValueError: If api_url or api_key not provided and not found in config
        """
        # Load from config if not provided
        from .config import config as _config
        self._config = _config
        if api_url is None:
            api_url = _config.api_url
        if api_key is None:
            api_key = _config.api_key

        if not api_url:
            raise ValueError("api_url is required. Provide it directly or run 'crucible config init'")
        if not api_key:
            raise ValueError("api_key is required. Provide it directly or run 'crucible config init'")

        self.api_url = api_url.rstrip('/')
        self.api_key = api_key

        if '/api/v1' in self.api_url:
            import warnings
            from .config.config import Config as _Cfg
            warnings.warn(
                f"You are connected to Crucible API v1 which is deprecated. "
                f"Update with: crucible config set api_url {_Cfg.DEFAULT_API_URL}",
                DeprecationWarning,
                stacklevel=2,
            )

        # Session with automatic retry on transient server/network errors
        retry = Retry(
            total            = 3,
            backoff_factor   = 1,            # waits 1s, 2s, 4s between retries
            status_forcelist = {429, 502, 503, 504},
            allowed_methods  = False,        # retry all HTTP methods, including POST
            raise_on_status  = False,        # let raise_for_status() handle final failure
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}"})
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

        # Initialize resource operations
        from .resources import FileOperations, DatasetOperations, SampleOperations, \
        ProjectOperations, UserOperations, InstrumentOperations, DeletionOperations, \
        GraphOperations, AccountOperations, IngestionOperations

        self.files = FileOperations(self)
        self.datasets = DatasetOperations(self)
        self.samples = SampleOperations(self)
        self.projects = ProjectOperations(self)
        self.users = UserOperations(self)
        self.instruments = InstrumentOperations(self)
        self.deletions = DeletionOperations(self)
        self.graphs = GraphOperations(self)
        self.account = AccountOperations(self)
        self.ingestions = IngestionOperations(self)
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an HTTP request to the API.

        Args:
            method: HTTP method (get, post, put, delete)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            Parsed JSON response

        Raises:
            requests.exceptions.HTTPError: For HTTP errors (4xx, 5xx)
            requests.exceptions.ConnectionError: For connection failures
            requests.exceptions.Timeout: For timeout errors
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        logger.debug(f"{method.upper()} {url}")
        timeout = (self._config.connect_timeout, self._config.read_timeout)
        response = self._session.request(method, url, timeout=timeout, **kwargs)
        logger.debug(f"Status: {response.status_code}")
        logger.debug(f"Response: {response.text}")
        if not response.ok:
            # Try to surface the server's error detail from the response body
            detail = None
            try:
                body = response.json()
                detail = body.get("detail") or body.get("message") or body.get("error")
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
            if detail:
                raise requests.exceptions.HTTPError(
                    f"{response.status_code} {response.reason}: {detail}",
                    response=response,
                )
            response.raise_for_status()
        try:
            if response.content:
                return response.json()
            else:
                return None
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response from {url}: {e}")
            return response
    
    def _wait_for_request_completion(self, reqid: str, sleep_interval: int = 1) -> Dict:
        """Internal: delegate to client.ingestions.wait()."""
        return self.ingestions.wait(reqid, sleep_interval=sleep_interval)

    
    #%% GENERIC METHODS

    def live(self) -> Dict:
        """Check whether the API process is running (no DB check, no auth).

        Returns:
            Dict: {"status": "ok"}
        """
        import requests as _requests
        url = f"{self.api_url}/health/live"
        timeout = (self._config.connect_timeout, self._config.read_timeout)
        resp = _requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> Dict:
        """Check API and database health without requiring authentication.

        Returns:
            Dict: {"status": "ok"|"degraded", "db": "ok"|"error",
                   "db_ms": float|None, "version": str|None}
                  Raises requests.exceptions.ConnectionError if the host is unreachable.
        """
        import requests as _requests
        url = f"{self.api_url}/health/ready"
        timeout = (self._config.connect_timeout, self._config.read_timeout)
        resp = _requests.get(url, timeout=timeout)
        return resp.json()

    def whoami(self) -> Dict:
        """Return full auth context for the current API key.

        Delegates to client.account.whoami(). Kept here for backward compatibility
        and because it spans the account context rather than a specific resource.
        """
        return self.account.whoami()

    def get_resource_type(self, resource_id: str) -> str:
        """
        Determine the type of a resource.

        Args:
            resource_id (str): The unique identifier (mfid) of the resource

        Returns:
            str: resource_type
        """
        response = self._request('get', f"/resources/{resource_id}")
        return response['resource_type']

    def get(self, resource_id: str, resource_type: str = None,
            include_metadata: bool = False, include_links: bool = False,
            include_owner: bool = False) -> Dict:
        """
        Get a resource by ID with automatic type detection.

        Args:
            resource_id (str): The unique identifier (mfid) of the resource
            resource_type (str, optional): Resource type ('sample', 'dataset', 'instrument').
                                          If not provided, will be auto-detected.
            include_metadata (bool): Include scientific metadata
            include_links (bool): Include immediate parent/child/associated links
            include_owner (bool): Resolve owner_orcid into a full user object

        Returns:
            Dict: Resource data

        Raises:
            ValueError: If resource type is unknown or not supported
        """
        if resource_type is None:
            params = {}
            if include_links:
                params['include_links'] = True
            if include_metadata:
                params['include_metadata'] = True
            if include_owner:
                params['include_owner'] = True
            return self._request('get', f"/resources/{resource_id}", params=params or None)

        if resource_type == "sample":
            return self.samples.get(resource_id, include_links=include_links,
                                    include_metadata=include_metadata,
                                    include_owner=include_owner)
        elif resource_type == "dataset":
            return self.datasets.get(resource_id, include_metadata=include_metadata,
                                     include_links=include_links,
                                     include_owner=include_owner)
        elif resource_type == "instrument":
            return self.instruments.get(instrument_id=resource_id,
                                        include_metadata=include_metadata)
        else:
            raise ValueError(f"Unknown or unsupported resource type: {resource_type}")

    def get_links(self, resource_id: str) -> list:
        """Return immediate links for any resource (dataset or sample).

        Hits GET /resources/{id}/links and returns a flat list of link dicts:
            [{"unique_id": "...", "resource_type": "dataset|sample",
              "name": "...", "relationship": "parent|child|associated"}, ...]

        Args:
            resource_id (str): Dataset or sample unique identifier

        Returns:
            list: Link objects, or empty list if none
        """
        result = self._request('get', f"/resources/{resource_id}/links")
        return result or []

    def link(self, parent_id: str, child_id: str) -> Dict:
        """
        Link two resources with automatic type detection.

        Automatically determines resource types and creates appropriate link:
        - Both datasets: Creates parent-child dataset relationship
        - Both samples: Creates parent-child sample relationship
        - Dataset + sample: Links sample to dataset

        Args:
            parent_id (str): Parent resource unique identifier
            child_id (str): Child resource unique identifier

        Returns:
            Dict: Information about the created link

        Raises:
            ValueError: If resource types cannot be determined or combination is invalid

        Example:
            >>> # Link two datasets
            >>> client.link('parent_dataset_id', 'child_dataset_id')

            >>> # Link two samples
            >>> client.link('parent_sample_id', 'child_sample_id')

            >>> # Link sample to dataset
            >>> client.link('dataset_id', 'sample_id')
        """
        parent_type = self.get_resource_type(parent_id)
        child_type = self.get_resource_type(child_id)

        # Both are datasets
        if parent_type == "dataset" and child_type == "dataset":
            logger.info(f"Linking datasets: {parent_id} (parent) -> {child_id} (child)")
            return self.datasets.link_parent_child(parent_id, child_id)

        # Both are samples
        elif parent_type == "sample" and child_type == "sample":
            logger.info(f"Linking samples: {parent_id} (parent) -> {child_id} (child)")
            return self.samples.link(parent_id, child_id)

        # Mixed: dataset and sample
        elif parent_type == "dataset" and child_type == "sample":
            logger.info(f"Linking sample {child_id} to dataset {parent_id}")
            return self.datasets.add_sample(parent_id, child_id)

        elif parent_type == "sample" and child_type == "dataset":
            logger.info(f"Linking sample {parent_id} to dataset {child_id}")
            return self.datasets.add_sample(child_id, parent_id)

        else:
            raise ValueError(
                f"Cannot link resources: parent is {parent_type}, child is {child_type}. "
                f"Valid combinations: dataset-dataset, sample-sample, or dataset-sample."
            )

    def unlink(self, id_a: str, id_b: str) -> Dict:
        """Unlink two resources with automatic type detection.

        Automatically determines resource types and removes the appropriate link:
        - Both datasets: Removes parent-child dataset relationship
        - Both samples: Removes parent-child sample relationship
        - Dataset + sample: Removes dataset-sample link

        Args:
            id_a (str): First resource unique identifier (dataset or sample)
            id_b (str): Second resource unique identifier (dataset or sample)

        Returns:
            Dict: Deletion confirmation

        Raises:
            ValueError: If resource types cannot be determined or combination is invalid.
        """
        type_a = self.get_resource_type(id_a)
        type_b = self.get_resource_type(id_b)

        if type_a == "dataset" and type_b == "sample":
            logger.info(f"Unlinking sample {id_b} from dataset {id_a}")
            return self.datasets.remove_sample(id_a, id_b)

        elif type_a == "sample" and type_b == "dataset":
            logger.info(f"Unlinking sample {id_a} from dataset {id_b}")
            return self.datasets.remove_sample(id_b, id_a)

        elif type_a == "dataset" and type_b == "dataset":
            logger.info(f"Unlinking child dataset {id_b} from parent dataset {id_a}")
            return self.datasets.remove_child(id_a, id_b)

        elif type_a == "sample" and type_b == "sample":
            logger.info(f"Unlinking child sample {id_b} from parent sample {id_a}")
            return self.samples.remove_child(id_a, id_b)

        else:
            raise ValueError(
                f"Cannot unlink resources: {id_a} is {type_a}, {id_b} is {type_b}."
            )
    
    @_deprecated("client.datasets.download() or client.samples.download()")
    def download(self, resource_id: str, output_dir: str = 'crucible-downloads',
                 no_files: bool = False, no_record: bool = False,
                 overwrite_existing: bool = True,
                 include: Optional[List[str]] = None,
                 exclude: Optional[List[str]] = None) -> List[str]:
        """Deprecated: use client.datasets.download() or client.samples.download() instead."""
        resource_type = self.get_resource_type(resource_id)
        if resource_type == 'dataset':
            return self.datasets.download(resource_id, output_dir=output_dir,
                                          no_files=no_files, no_record=no_record,
                                          overwrite_existing=overwrite_existing,
                                          include=include, exclude=exclude)
        elif resource_type == 'sample':
            return self.samples.download(resource_id, output_dir=output_dir)
        else:
            raise ValueError(f"Cannot download resource of type: {resource_type}")