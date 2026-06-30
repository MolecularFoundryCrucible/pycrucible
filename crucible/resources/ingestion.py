#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ingestion request operations for the Crucible API.

Access via: client.ingestion.list(), client.ingestion.get(), etc.
"""

import logging
from typing import Dict, List, Optional

from .base import BaseResource
from ..constants import DEFAULT_LIMIT

logger = logging.getLogger(__name__)


class IngestionOperations(BaseResource):
    """Operations on ingestion requests (/ingestion_requests endpoints).

    Access via: client.ingestion.list(), client.ingestion.get(), etc.
    """

    def list(self, dsid: Optional[str] = None,
             file_id: Optional[str] = None,
             limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """List ingestion requests, optionally filtered by dataset or file.

        Args:
            dsid: Filter by dataset ID
            file_id: Filter by file MFID
            limit: Maximum number of results

        Returns:
            List[Dict]: IngestionRequest records
        """
        params = {}
        if dsid:
            params['dataset_id'] = dsid
        if file_id:
            params['file_id'] = file_id
        return self._request('get', '/ingestion_requests', params=params or None)

    def get(self, request_id: str) -> Dict:
        """Get the status of a single ingestion request.

        Args:
            request_id: Ingestion request ID

        Returns:
            Dict: IngestionRequest record (id, status, ...)
        """
        return self._request('get', f'/ingestion_requests/{request_id}')

    def update(self, request_id: str, status: str,
               ingestion_githash: Optional[str] = None,
               ingestion_class: Optional[str] = None,
               timezone: str = "America/Los_Angeles") -> Dict:
        """Update the status of an ingestion request. Admin only.

        Args:
            request_id: Ingestion request ID
            status: New status ('complete', 'in_progress', 'failed')
            ingestion_githash: Git hash of the ingestion worker version
            ingestion_class: Ingestion class used
            timezone: Timezone for the completion timestamp

        Returns:
            Dict: Updated IngestionRequest record
        """
        from ..utils import get_tz_isoformat

        patch_json = {
            'id': request_id,
            'status': status,
            'ingestion_githash': ingestion_githash,
            'ingestion_class': ingestion_class,
        }
        if status == "complete":
            patch_json["time_completed"] = get_tz_isoformat(timezone)

        return self._request('patch', f'/ingestion_requests/{request_id}', json=patch_json)
