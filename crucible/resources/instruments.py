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
from ..utils.identifiers import (
    IdentifierNotFoundError,
    classify_slug_reference,
    collapse_exact_lookup,
    is_mfid,
    require_canonical_identifier,
    validate_slug,
)

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

    def get(self, instrument_ref: Optional[str] = None,
            instrument_id: Optional[str] = None,
            include_metadata: bool = False,
            *, instrument_mfid: Optional[str] = None,
            instrument_name: Optional[str] = None) -> Dict:
        """Get an instrument by canonical MFID or human-readable slug.

        ``instrument_id`` explicitly selects the human-readable API identifier.
        An MFID-shaped value remains temporarily compatible with its former
        meaning and emits a deprecation warning.

        Args:
            instrument_ref (str, optional): Instrument MFID or slug
            instrument_id (str, optional): Explicit instrument slug
            include_metadata (bool): Whether to include scientific metadata
            instrument_mfid (str, optional): Explicit instrument MFID
            instrument_name (str, optional): Deprecated display-name lookup

        Returns:
            Dict or None: Instrument information if found, None otherwise

        Raises:
            ValueError: If no reference or multiple references are provided
        """
        provided = [
            value for value in
            (instrument_ref, instrument_id, instrument_mfid, instrument_name)
            if value is not None
        ]
        if len(provided) != 1:
            raise ValueError("Provide exactly one instrument reference.")

        if instrument_name is not None:
            import warnings
            warnings.warn(
                "instrument_name lookup is deprecated because display names are not unique; "
                "pass an instrument MFID or instrument_id slug instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return self._get_by_name(instrument_name, include_metadata=include_metadata)
        if instrument_id is not None:
            if is_mfid(instrument_id):
                import warnings
                warnings.warn(
                    "Passing an MFID as instrument_id is deprecated; use instrument_mfid instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return self._get_by_mfid(instrument_id, include_metadata=include_metadata)
            return self._get_by_instrument_id(instrument_id, include_metadata=include_metadata)
        if instrument_mfid is not None:
            return self._get_by_mfid(instrument_mfid, include_metadata=include_metadata)

        reference_kind = classify_slug_reference(instrument_ref, 'instrument')
        if reference_kind == 'mfid':
            return self._get_by_mfid(instrument_ref, include_metadata=include_metadata)
        return self._get_by_instrument_id(instrument_ref, include_metadata=include_metadata)

    def _get_by_mfid(self, instrument_mfid: str,
                     include_metadata: bool = False) -> Dict:
        """Get an instrument through its canonical single-resource route."""
        if not is_mfid(instrument_mfid):
            raise ValueError("instrument_mfid must be an exact 26-character MFID.")
        params = {'include_metadata': True} if include_metadata else None
        raw = self._request('get', f'/instruments/{instrument_mfid}', params=params)
        return require_canonical_identifier(raw, 'instrument')

    def _get_by_instrument_id(self, instrument_id: str,
                              include_metadata: bool = False) -> Dict:
        """Resolve an exact instrument slug through the collection route."""
        if not isinstance(instrument_id, str) or not instrument_id:
            raise ValueError("instrument_id must be a non-empty string.")
        params = {'instrument_id': instrument_id, 'limit': 2}
        if include_metadata:
            params['include_metadata'] = True
        raw = self._request('get', '/instruments', params=params)
        return collapse_exact_lookup(raw, 'instrument', instrument_id)

    def _get_by_name(self, instrument_name: str,
                     include_metadata: bool = False) -> Dict:
        """Compatibility lookup for a non-unique instrument display name."""
        params = {'instrument_name': instrument_name, 'limit': 2}
        if include_metadata:
            params['include_metadata'] = True
        raw = self._request('get', '/instruments', params=params)
        return collapse_exact_lookup(raw, 'instrument', instrument_name)

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
        validate_slug(payload['instrument_id'], 'instrument')

        try:
            existing = self._get_by_instrument_id(payload['instrument_id'])
        except IdentifierNotFoundError:
            existing = None
        if existing:
            warnings.warn(
                f"Instrument '{payload['instrument_id']}' already exists; returning existing record.",
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
        if kwargs.get('instrument_id') is not None:
            validate_slug(kwargs['instrument_id'], 'instrument')
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
