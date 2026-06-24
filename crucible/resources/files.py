#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File resource operations — scoped to a single file MFID (/files/* endpoints).

For dataset-scoped file operations (upload, download, thumbnails, ingestion)
see DatasetOperations (client.datasets.*).
"""

import logging
from typing import Optional, List, Dict

from .base import BaseResource
from ..constants import DEFAULT_LIMIT

logger = logging.getLogger(__name__)


class FileOperations(BaseResource):
    """Operations on individual files by MFID.

    Access via: client.files.get(), client.files.list(), etc.
    """

    def get(self, file_id: str) -> Dict:
        """Get metadata for a single file by its MFID.

        Args:
            file_id: File MFID

        Returns:
            Dict: File record (mfid, filename, storage_path, size, sha256_hash, dataset_mfid)
        """
        return self._request('get', f'/files/{file_id}')

    def list(self, limit: int = DEFAULT_LIMIT,
             sha256_hash: Optional[str] = None) -> List[Dict]:
        """List files across all accessible datasets.

        Args:
            limit: Maximum number of results
            sha256_hash: Filter by SHA-256 hex digest

        Returns:
            List[Dict]: File records (mfid, filename, storage_path, size, sha256_hash, dataset_mfid)
        """
        params = {}
        if sha256_hash:
            params['sha256_hash'] = sha256_hash
        return self._paginate('/files', params, limit=limit)

    def get_download_link(self, file_id: str) -> str:
        """Get a signed download URL for a single file.

        Args:
            file_id: File MFID

        Returns:
            str: Signed URL valid for 1 hour, no auth required.

        Raises:
            HTTPError 404: File has not been ingested yet.
        """
        result = self._request('get', f'/files/{file_id}/download_link')
        return result['url']
