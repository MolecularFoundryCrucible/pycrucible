#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instrument resource operations for Crucible API.

Provides organized access to instrument-related API endpoints.
"""

import logging
from typing import Optional, List, Dict
from .base import BaseResource
from .capabilities import AccessControlMixin
from ..constants import DEFAULT_LIMIT

logger = logging.getLogger(__name__)


class InstrumentOperations(AccessControlMixin, BaseResource):
    """Instrument-related API operations.

    Access via: client.instruments.get(), client.instruments.list(), etc.
    """

    def list(self, include_metadata: bool = False, limit: int = DEFAULT_LIMIT,
             offset: int = 0) -> List[Dict]:
        """List all available instruments.

        Args:
            include_metadata (bool): Include scientific metadata in results
            limit (int): Maximum number of results to return
            offset (int): Starting position in the full result set (default: 0)

        Returns:
            List[Dict]: Instrument objects with specifications and metadata
        """
        params = {}
        if include_metadata:
            params['include_metadata'] = True
        return self._paginate('/instruments', params, limit, offset)

    def get(self, instrument_name: Optional[str] = None, instrument_id: Optional[str] = None,
            include_metadata: bool = False) -> Dict:
        """Get instrument information by name or ID.

        Note: despite the name, the `instrument_id` parameter here is the
        instrument's MFID (unique_id) - not the `instrument_id` slug field on
        the Instrument model/API (a separate, user-chosen identifier).

        Args:
            instrument_name (str, optional): Name of the instrument
            instrument_id (str, optional): MFID of the instrument
            include_metadata (bool): Whether to include scientific metadata

        Returns:
            Dict or None: Instrument information if found, None otherwise

        Raises:
            ValueError: If neither parameter is provided
        """
        if not instrument_name and not instrument_id:
            raise ValueError("Either instrument_name or instrument_id must be provided")

        if instrument_id:
            params = {}
            if include_metadata:
                params['include_metadata'] = True
            return self._request('get', f'/instruments/{instrument_id}', params=params or None)

        params = {"instrument_name": instrument_name}
        if include_metadata:
            params['include_metadata'] = True
        results = self._paginate('/instruments', params, limit=1)
        return results[0] if results else None

    def create(self, instrument, scientific_metadata: Optional[Dict] = None) -> Dict:
        """Create a new instrument, returning the existing one if it already exists.

        **Requires admin permissions.**

        Args:
            instrument: Instrument model or dict with instrument details.
                        Required fields: instrument_id, instrument_name, owner, location.
            scientific_metadata (Dict, optional): Scientific metadata to attach after creation.

        Returns:
            Dict: Created (or existing) instrument object

        Raises:
            ValueError: If instrument_id is missing
        """
        import warnings
        from ..models import Instrument
        if isinstance(instrument, Instrument):
            payload = instrument.model_dump(exclude_none=True, exclude={'id', 'unique_id'})
        else:
            payload = dict(instrument)

        if not payload.get('instrument_id'):
            raise ValueError(
                "instrument_id is required (a unique slug identifying the instrument, "
                "distinct from its auto-assigned MFID)."
            )

        instrument_name = payload.get('instrument_name')
        if instrument_name:
            existing = self.get(instrument_name=instrument_name)
            if existing:
                warnings.warn(
                    f"Instrument '{instrument_name}' already exists; returning existing record.",
                    UserWarning, stacklevel=2,
                )
                return existing

        result = self._request('post', '/instruments', json=payload)
        if scientific_metadata:
            self.update_scientific_metadata(result['unique_id'], scientific_metadata)
        return result

    def update(self, unique_id: str, **kwargs) -> Dict:
        """Partially update an instrument record.

        **Requires admin permissions.**

        Args:
            unique_id (str): Instrument unique identifier (MFID)
            **kwargs: Fields to update. Accepted: instrument_id, instrument_name, owner,
                      location, manufacturer, model, instrument_type, description,
                      other_id, other_id_source.

        Returns:
            Dict: Updated instrument object
        """
        return self._request('patch', f'/instruments/{unique_id}', json=kwargs)

    def bind_service_account(self, instrument_mfid: str, sa_unique_id: str) -> List['ProjectMember']:
        """Bind a service account as an operator of an instrument.

        **Requires admin permissions.**

        Args:
            instrument_mfid (str): Instrument unique identifier (MFID)
            sa_unique_id (str): Service account unique identifier (MFID)

        Returns:
            List[ProjectMember]: The instrument's operator group members
        """
        from ..models import ProjectMember
        raw = self._request('post', f'/instruments/{instrument_mfid}/service_accounts/{sa_unique_id}')
        return [ProjectMember.model_validate(m) for m in raw]

    def unbind_service_account(self, instrument_mfid: str, sa_unique_id: str) -> List['ProjectMember']:
        """Remove a service account as an operator of an instrument.

        **Requires admin permissions.**

        Args:
            instrument_mfid (str): Instrument unique identifier (MFID)
            sa_unique_id (str): Service account unique identifier (MFID)

        Returns:
            List[ProjectMember]: The instrument's operator group members
        """
        from ..models import ProjectMember
        raw = self._request('delete', f'/instruments/{instrument_mfid}/service_accounts/{sa_unique_id}')
        return [ProjectMember.model_validate(m) for m in raw]

    def search(self, q: str, limit: int = 20) -> List[Dict]:
        """Fuzzy search across instruments. Available to all authenticated users.

        Matches against instrument_name, instrument_type, and manufacturer
        (best score across the three).

        Args:
            q: Search term (min 3 chars). Typo-tolerant.
            limit: Max results (default 20, max 50).

        Returns:
            List[Dict]: Matching instrument records, ranked by relevance.
        """
        result = self._request('get', '/instruments/search', params={'q': q, 'limit': limit})
        return result.get('items', result) if isinstance(result, dict) else result

    def get_or_create(self, instrument_name: str, location: Optional[str] = None,
                     instrument_owner: Optional[str] = None) -> Dict:
        """Deprecated: use create() instead.

        .. deprecated::
            Use :meth:`create` with an :class:`~crucible.models.Instrument` model.
            ``create()`` now checks for an existing instrument before posting.
        """
        import warnings
        warnings.warn(
            "get_or_create() is deprecated; use create() instead — "
            "it now checks for an existing instrument automatically.",
            DeprecationWarning, stacklevel=2,
        )
        from ..models import Instrument
        return self.create(Instrument(
            instrument_name=instrument_name,
            location=location,
            owner=instrument_owner,
        ))
