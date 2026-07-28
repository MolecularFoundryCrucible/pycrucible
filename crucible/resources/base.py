#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base resource class for Crucible API operations.

Provides shared functionality for all resource operation classes.
"""

# typing
from typing import Optional, List, Dict, Tuple

# internal modules
from ..constants import DEFAULT_LIMIT
from ..utils.deprecation import _deprecated

class BaseResource:
    """Base class for resource-specific operations.

    All resource classes inherit from this and get access to the
    parent client's _request method for making API calls.
    """

    def __init__(self, client):
        """
        Initialize resource operations.

        Args:
            client: Parent CrucibleClient instance
        """
        self._client = client
        self._request = client._request  # Delegate HTTP requests to main client

    def _paginate(self, endpoint: str, params: dict,
                  limit: int = DEFAULT_LIMIT, offset: int = 0) -> list:
        """Fetch all matching records from a paginated envelope endpoint.

        Supports both pagination styles transparently, detected from the first
        response:

        * Keyset (cursor) pagination — used by '/datasets' and '/samples'. The
          response carries a 'next_cursor' token; pages are followed
          sequentially until the cursor is exhausted.
        * Offset pagination — every other endpoint. The first response carries
          'total'; remaining pages are fetched in parallel by offset.

        Args:
            endpoint: API path (e.g. '/datasets')
            params:   Query parameters (must NOT include 'limit', 'offset', or 'cursor')
            limit:    Maximum number of records to return. Pass None to fetch all.
            offset:   Starting position in the full result set. Ignored by keyset
                      endpoints, which no longer accept an offset.

        Returns:
            list: Raw item dicts, up to limit items (or all items if limit is None)
        """
        from concurrent.futures import ThreadPoolExecutor
        from ..constants import API_PAGE_MAX

        page_size = API_PAGE_MAX
        first_params = {**params, 'limit': page_size}
        if offset:
            first_params['offset'] = offset
        first = self._request('get', endpoint, params=first_params)
        items = list(first['items'])

        # Keyset (cursor) pagination — '/datasets' and '/samples'.
        if 'next_cursor' in first:
            cursor = first.get('next_cursor')
            page_len = len(items)
            while (cursor and page_len >= page_size
                   and (limit is None or len(items) < limit)):
                resp = self._request('get', endpoint,
                                     params={**params, 'limit': page_size, 'cursor': cursor})
                page = resp['items']
                items.extend(page)
                cursor = resp.get('next_cursor')
                page_len = len(page)
            return items if limit is None else items[:limit]

        # Offset pagination — all other endpoints.
        total = first['total']
        need = total - offset if limit is None else min(total - offset, limit)
        if len(items) >= need:
            return items[:need]

        remaining_offsets = range(offset + page_size, offset + need, API_PAGE_MAX)

        def _fetch(off):
            r = self._request('get', endpoint,
                              params={**params, 'limit': API_PAGE_MAX, 'offset': off})
            return r['items']

        with ThreadPoolExecutor(max_workers=min(len(remaining_offsets), 8)) as pool:
            for page in pool.map(_fetch, remaining_offsets):
                items.extend(page)

        return items[:need]

    def search_metadata(self, q: str, limit: int = 20) -> list:
        """Full-text search across scientific metadata of all accessible resources.

        Results are ranked by relevance (rank field) and include resource_type, name,
        owner_orcid, creation_time, modification_time, and scientific_metadata.
        Resources with pending or approved deletion requests are excluded.

        Args:
            q: Plain-text search query (English-language stemmed).
            limit: Max results to return (default 20, max 50).

        Returns:
            List of result dicts with unique_id, resource_type, name, owner_orcid,
            creation_time, modification_time, rank, and scientific_metadata.
        """
        resp = self._request('get', '/resources/metadata/search',
                             params={"q": q, "limit": limit})
        if isinstance(resp, dict) and 'items' in resp:
            return resp['items']
        return resp or []

    @_deprecated("search_metadata()")
    def search_scientific_metadata(self, q: str, limit: int = 50) -> list:
        """Deprecated: use search_metadata() instead."""
        return self.search_metadata(q, limit=limit)

    def get_scientific_metadata(self, resource_id: str) -> dict:
        """Get scientific metadata for a resource."""
        return self._request('get', f'/resources/{resource_id}/metadata')

    def replace_scientific_metadata(self, resource_id: str, metadata: dict) -> dict:
        """Create new scientific metadata entry for a resource."""
        # this is kind of redundant with API but its better here? #TODO
        return self._request('post', f'/resources/{resource_id}/metadata', json=metadata, params = {'overwrite': True})

    def update_scientific_metadata(self, resource_id: str, metadata: dict,
                                   overwrite: bool = False) -> dict:
        """Add or Update scientific metadata for a resource.

        Args:
            overwrite: If True, replace all metadata (POST); if False, merge with existing (PATCH)
        """
        if overwrite:
            return self._request('post', f'/resources/{resource_id}/metadata', json=metadata, params = {'overwrite':overwrite})
        return self._request('patch', f'/resources/{resource_id}/metadata', json=metadata)


#%% access group methods

    def get_access_groups(self, mfid: str) -> List[str]:
        """Get list of access groups for a dataset.

        **Requires admin permissions.**

        Args:
            dsid (str): Dataset unique identifier

        Returns:
            List[str]: Access group names
        """
        groups = self._request('get', f'/resources/{mfid}/access_groups')
        return [group['group_name'] for group in groups]

    def add_access_group(self, mfid: str, group_name: str,
                         read: bool = True, write: bool = False) -> Dict:
        """Add an access group to a dataset.

        **Requires admin permissions.**

        Args:
            dsid (str): Dataset unique identifier
            group_name (str): Name of the access group to add
            read (bool): Grant read access (default: True)
            write (bool): Grant write access (default: False)

        Returns:
            Dict: Created ACL entry
        """
        params = {"group_name": group_name, "read": read, "write": write}
        return self._request('post', f'/resources/{mfid}/access_groups', params=params)