#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dataset resource operations for Crucible API.

Provides organized access to dataset-related API endpoints.
"""

import os
import re
import logging
import requests
from typing import Optional, List, Dict

import mfid

# internal modules
from .base import BaseResource
from ..constants import DEFAULT_LIMIT
from ..utils.deprecation import _deprecated

# upload/download
from .gcs.upload import upload_file_gcs

# set up logging
logger = logging.getLogger(__name__)


class DatasetOperations(BaseResource):
    """Dataset-related API operations.

    Access via: client.datasets.get(), client.datasets.list(), etc.
    """

    @staticmethod
    def _parse(raw: Dict) -> Dict:
        """Validate a raw API response dict through the Dataset Pydantic model.

        Normalises field aliases (e.g. creation_date → timestamp) and preserves
        any extra fields returned by the server (keywords, scientific_metadata, …).
        """
        from ..models import Dataset
        return Dataset.model_validate(raw).model_dump()

    def get(self, dsid: str, include_metadata: bool = False,
            include_links: bool = False) -> Dict:
        """Get dataset details, optionally including scientific metadata and links.

        Args:
            dsid (str): Dataset unique identifier
            include_metadata (bool): Whether to include scientific metadata
            include_links (bool): Whether to include immediate parent/child/associated links

        Returns:
            Dict: Dataset object with optional metadata and links
        """
        params = {}
        if include_links:
            params['include_links'] = True

        if include_metadata:
            params['include_metadata'] = True

        raw = self._request('get', f'/datasets/{dsid}', params=params or None)
        if raw is None:
            return None

        return self._parse(raw)


    def list(self, sample_id: Optional[str] = None, include_metadata: bool = False,
             include_links: bool = False, limit: int = DEFAULT_LIMIT,
             offset: int = 0, **kwargs) -> List[Dict]:
        """List datasets with optional filtering and automatic pagination.

        Args:
            sample_id (str, optional): If provided, returns datasets for this sample
            limit (int): Maximum total results to return (default: 100). Larger
                         requests are handled transparently by following the
                         server's keyset cursor. Pass None to fetch all matches.
            offset (int): Deprecated for the top-level /datasets endpoint, which now
                          uses keyset pagination and ignores offset. Still honored
                          for the sample_id sub-listing.
            include_metadata (bool): Include scientific metadata in results
            include_links (bool): Include linked resources (parents, children, associated) per dataset
            **kwargs (Any): Query parameters for filtering. Supported fields include:
                keyword, unique_id, public, dataset_name, owner_orcid, project_id,
                instrument_name, timestamp, size, data_format, data_type, measurement,
                session_name. Filters expect exact matches (case sensitive) except for
                keywords, which are case insensitive and match substrings.

        Returns:
            List[Dict]: Dataset objects matching filter criteria
        """
        params = {k: v for k, v in kwargs.items() if v is not None}
        if include_metadata:
            params['include_metadata'] = True
        if include_links:
            params['include_links'] = True
        if sample_id:
            if limit:
                params['limit'] = limit
            raw = self._request('get', f'/samples/{sample_id}/datasets', params=params) 
        else:
            if offset:
                import warnings
                warnings.warn(
                    "'offset' is ignored by /datasets, which now uses keyset "
                    "pagination; results start from the newest dataset.",
                    DeprecationWarning, stacklevel=2,
                )
            raw = self._paginate('/datasets', params, limit, offset)
        return [self._parse(d) for d in raw]

    def count(self, **kwargs) -> int:
        """Return the total number of datasets matching the given filters without fetching items."""
        params = {k: v for k, v in kwargs.items() if v is not None}
        result = self._request('get', '/datasets', params={**params, 'limit': 1})
        return result['total']


    def create(self, dataset, scientific_metadata: Optional[Dict] = None,
               keywords: Optional[List[str]] = None,
               files_to_upload: Optional[List[str]] = None,
               ingestor: Optional[str] = None,
               verbose: bool = False,
               wait_for_ingestion_response: bool = False) -> Dict:
        """Create a new dataset record with scientific metadata and keywords.

        Args:
            dataset (Dataset): Dataset object with dataset details
            scientific_metadata (dict, optional): Scientific metadata
            keywords (list, optional): Keywords to associate with dataset
        Returns:
            Dict: created_record, scientific_metadata_record, dsid
        """
        if scientific_metadata is None:
            scientific_metadata = {}

        if keywords is None:
            keywords = []
        if files_to_upload is None:
            files_to_upload = []

        dataset_details = dataset.model_dump()

        if not dataset_details.get('unique_id'):
            dataset_details['unique_id'] = mfid.mfid()[0]

        logger.debug('Creating new dataset record...')

        clean_dataset = {k: v for k, v in dataset_details.items() if v is not None}
        new_ds_record = self._request('post', '/datasets', json=clean_dataset)
        dsid = new_ds_record['unique_id']

        # add scientific metadata
        scimd = None
        if scientific_metadata:
            logger.debug(f'Adding scientific metadata record for {dsid}')
            scimd = self.update_scientific_metadata(dsid, scientific_metadata)

            
        # add keywords
        if keywords:
            logger.debug(f'Adding keywords to dataset {dsid}: {keywords}')
            for kw in keywords:
                self.add_keyword(dsid, kw)

        for file in files_to_upload:
            logger.debug(f'Adding {file} to dataset {dsid}')
            self.add_file(dsid, file, ingestion_class=ingestor, wait_for_ingestion_response=wait_for_ingestion_response)

        result = {"created_record": new_ds_record, "scientific_metadata_record": scimd, "dsid": dsid}
        return result

    def update(self, dsid: str, **updates) -> Dict:
        """Update an existing dataset with new field values.

        Args:
            dsid (str): Dataset unique identifier
            **updates (Any): Fields to update (e.g., dataset_name="New Name", public=True)

        Returns:
            Dict: Updated dataset object

        Example:
            >>> client.datasets.update("my-dataset-id", dataset_name="Updated Name", public=True)
        """
        return self._request('patch', f'/datasets/{dsid}', json=updates)

    def list_files(self, dsid: str) -> List[Dict]:
        """List files attached to a dataset.

        Args:
            dsid: Dataset unique identifier

        Returns:
            List[Dict]: File records (mfid, filename, storage_path, size, sha256_hash, dataset_mfid).
                storage_path is null until the file has been ingested.
        """
        return self._request('get', f'/datasets/{dsid}/files')

    def search(self, q: str, project_id: Optional[str] = None,
               limit: int = 20) -> List[Dict]:
        """Fuzzy name search across datasets. Available to all authenticated users.

        Matches against dataset_name. Returns datasets the caller can read.
        For scientific metadata search use search_metadata().

        Args:
            q: Search term (min 3 chars). Typo-tolerant — "pero" finds "perovskite".
            project_id: Optional project to scope results to.
            limit: Max results (default 20, max 50).

        Returns:
            List[Dict]: Matching DatasetResponse records, ranked by relevance.
        """
        params = {'q': q, 'limit': limit}
        if project_id:
            params['project_id'] = project_id
        result = self._request('get', '/datasets/search', params=params)
        return result.get('items', result) if isinstance(result, dict) else result

    # Keyword Methods
    def get_keywords(self, dsid: Optional[str] = None, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """List keywords, optionally filtered by dataset.

        Args:
            dsid (str, optional): Dataset unique identifier to filter keywords
            limit (int): Maximum number of results to return

        Returns:
            List[Dict]: Keyword objects with keyword text and num_datasets counts
        """
        return self._request('get', f'/datasets/{dsid}/keywords')

    def add_keyword(self, dsid: str, keyword: str) -> Dict:
        """Add a keyword to a dataset.

        Args:
            dsid (str): Dataset unique identifier
            keyword (str): Keyword/tag to associate with dataset

        Returns:
            Dict: Keyword object with updated usage count
        """
        return self._request('post', f'/datasets/{dsid}/keywords', params={'keyword': keyword})

    # Dataset Linking Methods
    def add_sample(self, dataset_id: str, sample_id: str) -> Dict:
        """Link a sample to a dataset.

        Args:
            dataset_id (str): Dataset unique identifier
            sample_id (str): Sample unique identifier

        Returns:
            Dict: Information about the created link
        """
        return self._request('post', f"/datasets/{dataset_id}/samples/{sample_id}")

    def remove_sample(self, dataset_id: str, sample_id: str) -> Dict:
        """Remove the link between a dataset and a sample.

        **Requires admin permissions.**

        Args:
            dataset_id (str): Dataset unique identifier
            sample_id (str): Sample unique identifier

        Returns:
            Dict: Deletion confirmation
        """
        return self._request('delete', f"/datasets/{dataset_id}/samples/{sample_id}")

    def remove_child(self, parent_dataset_id: str, child_dataset_id: str) -> Dict:
        """Remove the parent-child link between two datasets.

        Args:
            parent_dataset_id (str): The unique ID of the parent dataset
            child_dataset_id (str): The unique ID of the child dataset

        Returns:
            Dict: Deletion confirmation
        """
        return self._request('delete', f"/datasets/{parent_dataset_id}/children/{child_dataset_id}")

    def link_parent_child(self, parent_dataset_id: str, child_dataset_id: str) -> Dict:
        """Link a derived dataset to a parent dataset.

        Args:
            parent_dataset_id (str): The unique ID for the parent dataset
            child_dataset_id (str): The unique ID for the derived dataset

        Returns:
            Dict: Information about the created link
        """
        new_link = self._request('post', f"/datasets/{parent_dataset_id}/children/{child_dataset_id}")
        return new_link

    def list_children(self, parent_dataset_id: str, limit: int = DEFAULT_LIMIT,
                      offset: int = 0, **kwargs) -> List[Dict]:
        """List the children of a given dataset with optional filtering.

        Args:
            parent_dataset_id (str): The unique ID of the dataset for which you want to find the children
            limit (int): Maximum number of results to return
            offset (int): Starting position in the full result set (default: 0)
            **kwargs (Any): Query parameters for filtering datasets

        Returns:
            List[Dict]: Children datasets
        """
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._paginate(f"/datasets/{parent_dataset_id}/children", params, limit, offset)

    def list_parents(self, child_dataset_id: str, limit: int = DEFAULT_LIMIT,
                     offset: int = 0, **kwargs) -> List[Dict]:
        """List the parents of a given dataset with optional filtering.

        Args:
            child_dataset_id (str): The unique ID of the dataset for which you want to find the parents
            limit (int): Maximum number of results to return
            offset (int): Starting position in the full result set (default: 0)
            **kwargs (Any): Query parameters for filtering datasets

        Returns:
            List[Dict]: Parent datasets
        """
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._paginate(f"/datasets/{child_dataset_id}/parents", params, limit, offset)

    # Special Processing Methods
    def request_carrier_segmentation(self, dsid: str) -> Dict:
        """Request carrier segmentation for a dataset.

        Args:
            dsid (str): Dataset unique identifier

        Returns:
            Dict: Carrier segmentation request information
        """
        result = self._request('post', f"/datasets/{dsid}/carrier_segmentation")
        return result

    def request_insitu_aggregation(self, dsid: str) -> Dict:
        """Request insitu spectroscopy data aggregation for a dataset.

        Args:
            dsid (str): Dataset unique identifier

        Returns:
            Dict: Data processing request information
        """
        result = self._request('post', f"/datasets/{dsid}/insitu_spec_aggregation")
        return result

    def request_rga_analysis(self, dsid: str) -> Dict:
        """Request RGA analysis for a dataset.

        Args:
            dsid (str): Dataset unique identifier

        Returns:
            Dict: RGA analysis request information
        """
        result = self._request('post', f"/datasets/{dsid}/rga_analysis")
        return result

    @_deprecated("client.graphs.get")
    def graph(self, dataset_id: str, recursive: bool = False, as_networkx: bool = False):
        return self._client.graphs.get(dataset_id, recursive=recursive, as_networkx=as_networkx)

    #%% Upload Methods

    def add_file(self, dsid: str, file_path: str,
                            ingestion_class: Optional[str] = None,
                            wait_for_ingestion_response: bool = False,
                            multipart: bool = True,
                            chunk_size_mb: Optional[int] = None,
                            max_workers: Optional[int] = None) -> Dict:
        """Upload a file to a dataset and request ingestion.

        Args:
            dsid: Dataset unique identifier
            file_path: Local path to the file
            ingestion_class: Ingestion class for the worker (e.g. 'lammps', 'nexus').
                Defaults to the server-side default if omitted.
            wait_for_ingestion_response: Block until ingestion completes.
            multipart: Use parallel multipart upload (default: True). Set to False to
                use the sequential resumable upload (slower but simpler).
            chunk_size_mb: Override chunk size in MiB (uses config/default if None).
            max_workers: Override number of upload threads (uses config/default if None).

        Returns:
            Dict: {'associated_file': AssociatedFileRead, 'ingestion_request': IngestionRequest}
        """
        file_size = os.path.getsize(file_path)
        filename  = os.path.basename(file_path)

        file_record, was_existing = upload_file_gcs(self._client, dsid, file_path,
                                                    multipart=multipart,
                                                    chunk_size_mb=chunk_size_mb,
                                                    max_workers=max_workers)

        stored_filename = file_record.get('filename', filename)
        file_id         = file_record.get('mfid')

        if was_existing:
            logger.info(f"{stored_filename} already exists in dataset {dsid}, skipping ingestion")
            return {'associated_file': file_record, 'ingestion_request': None}

        ingestion_request = self._client.files.request_ingestion(
            file_id,
            ingestion_class=ingestion_class,
            wait_for_response=wait_for_ingestion_response,
        )
        return {'associated_file': file_record, 'ingestion_request': ingestion_request}

    @_deprecated("client.datasets.add_file")
    def add_file_to_dataset(self, dsid: str, file_path: str,
                            ingestion_class: Optional[str] = None,
                            wait_for_ingestion_response: bool = False,
                            multipart: bool = True,
                            chunk_size_mb: Optional[int] = None,
                            max_workers: Optional[int] = None) -> Dict:
        return self.add_file(dsid=dsid, file_path=file_path,
                             ingestion_class=ingestion_class,
                             wait_for_ingestion_response=wait_for_ingestion_response,
                             multipart=multipart,
                             chunk_size_mb=chunk_size_mb,
                             max_workers=max_workers)


    #%% Download Methods

    def get_download_links(self, dsid: str) -> Dict:
        """Get signed download URLs for all ingested files in a dataset.

        Returns:
            Dict: Mapping of file MFID → signed URL. Empty dict if no ingested files.
        """
        try:
            return self._request('get', f"/datasets/{dsid}/download_links")
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    logger.debug(f"No ingested files in storage for dataset {dsid}")
                    return {}
                if e.response.status_code in (502, 503, 504):
                    logger.warning(f"Could not retrieve download links for {dsid}: "
                                   f"{e.response.status_code} {e.response.reason}.")
                    return {}
            raise

    def _fetch_files(self, dsid: str, output_dir: str,
                     overwrite_existing: bool = True,
                     include: Optional[List[str]] = None,
                     exclude: Optional[List[str]] = None) -> List[str]:
        """Download ingested files for a dataset. Returns list of downloaded paths."""
        from .gcs.download import download_dataset_files
        return download_dataset_files(
            self._client, dsid, output_dir,
            link_map=self.get_download_links(dsid),
            all_files=self.list_files(dsid),
            overwrite_existing=overwrite_existing,
            include=include, exclude=exclude,
        )

    def download(self, dsid: str, file_name: Optional[str] = None,
                 output_dir: str = 'crucible-downloads',
                 no_files: bool = False,
                 no_record: bool = False,
                 overwrite_existing: bool = True,
                 include: Optional[List[str]] = None,
                 exclude: Optional[List[str]] = None) -> List[str]:
        """Download a dataset's files and optionally save its record as JSON.

        Args:
            dsid: Dataset unique identifier
            file_name: Deprecated. Use include=['pattern'] with glob syntax.
            output_dir: Directory to save files (default: 'crucible-downloads/')
            no_files: Skip file download, save record.json only.
            no_record: Skip saving record.json, just download files.
            overwrite_existing: Overwrite existing files (default: True)
            include: Glob patterns - only download matching files
            exclude: Glob patterns - skip matching files

        Returns:
            List[str]: Paths of all downloaded items (record.json + data files)
        """
        if file_name is not None:
            import warnings
            warnings.warn(
                "The 'file_name' parameter is deprecated. Use include=['pattern'] instead.",
                DeprecationWarning, stacklevel=2,
            )
            matched = [os.path.basename(f.get('storage_path') or f.get('filename', ''))
                       for f in self.list_files(dsid)
                       if re.fullmatch(fr"({file_name})",
                                       os.path.basename(f.get('storage_path') or f.get('filename', '')))]
            include = matched

        os.makedirs(output_dir, exist_ok=True)
        downloaded = []

        if not no_record:
            record      = self.get(dsid, include_metadata=True)
            record_dir  = os.path.join(output_dir, dsid)
            os.makedirs(record_dir, exist_ok=True)
            json_path   = os.path.join(record_dir, 'record.json')
            with open(json_path, 'w') as fh:
                import json as _json
                _json.dump(record, fh, indent=2)
            logger.info(f"Saved record to {json_path}")
            downloaded.append(json_path)

        if not no_files:
            dest = os.path.join(output_dir, dsid)
            os.makedirs(dest, exist_ok=True)
            files = self._fetch_files(dsid, output_dir=dest,
                                      overwrite_existing=overwrite_existing,
                                      include=include, exclude=exclude)
            downloaded.extend(files)
            if files:
                logger.info(f"Downloaded {len(files)} file(s) to {dest}")

        return downloaded

    #%% Thumbnail Methods

    def get_thumbnails(self, dsid: str, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """Get thumbnails for a dataset."""
        return self._request('get', f'/datasets/{dsid}/thumbnails')

    def add_thumbnail(self, dsid: str, image, thumbnail_name: Optional[str] = None) -> Dict:
        """Add a thumbnail to a dataset."""
        import base64
        from ..utils import data2thumbnail, is_base64

        if is_base64(image):
            thumbnail_data = {
                'thumbnail_name': thumbnail_name or f"{dsid}_thumbnail",
                'thumbnail_b64str': image,
            }
            return self._request('post', f'/datasets/{dsid}/thumbnails', json=thumbnail_data)

        png_path = data2thumbnail(image)
        if thumbnail_name is None:
            thumbnail_name = os.path.basename(png_path)

        with open(png_path, 'rb') as f:
            thumbnail_b64str = base64.b64encode(f.read()).decode('utf-8')

        thumbnail_data = {'thumbnail_name': thumbnail_name, 'thumbnail_b64str': thumbnail_b64str}
        return self._request('post', f'/datasets/{dsid}/thumbnails', json=thumbnail_data)

    def delete_thumbnail(self, dsid: str, thumbnail_id: int) -> Dict:
        """Delete a thumbnail from a dataset."""
        return self._request('delete', f'/datasets/{dsid}/thumbnails/{thumbnail_id}')

    #%% Ingestion Methods — deprecated, use client.ingestions.*

    @_deprecated("client.ingestions.list(dsid=dsid, file_id=file_id)")
    def get_ingestion_requests(self, dsid: Optional[str] = None,
                               file_id: Optional[str] = None,
                               limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """Deprecated: use client.ingestions.list() instead."""
        return self._client.ingestions.list(dsid=dsid, file_id=file_id, limit=limit)

    @_deprecated("client.ingestions.get(reqid)")
    def get_request_status(self, reqid: str) -> Dict:
        """Deprecated: use client.ingestions.get() instead."""
        return self._client.ingestions.get(reqid)

    @_deprecated("client.ingestions.update(reqid, status)")
    def update_ingestion_status(self, reqid: str, status: str,
                                ingestion_githash: str = None,
                                ingestion_class: str = None,
                                timezone: str = "America/Los_Angeles") -> Dict:
        """Deprecated: use client.ingestions.update() instead."""
        return self._client.ingestions.update(reqid, status,
                                             ingestion_githash=ingestion_githash,
                                             ingestion_class=ingestion_class,
                                             timezone=timezone)
