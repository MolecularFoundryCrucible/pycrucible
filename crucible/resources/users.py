#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User resource operations for Crucible API.

Provides organized access to user-related API endpoints.
"""

import logging
from typing import Optional, Dict, List
from .base import BaseResource
from ..constants import DEFAULT_LIMIT
from ..utils.deprecation import _deprecated
from ..utils.identifiers import (
    classify_user_reference,
    collapse_exact_lookup,
    is_mfid,
    is_orcid,
    require_canonical_identifier,
)

logger = logging.getLogger(__name__)


class UserOperations(BaseResource):
    """User-related API operations.

    Access via: client.users.get(), client.users.create(), etc.
    """

    def get(self, user_ref: Optional[str] = None,
            email: Optional[str] = None, username: Optional[str] = None,
            *, orcid: Optional[str] = None,
            user_unique_id: Optional[str] = None) -> Dict:
        """Get a user by canonical unique ID, username, or email.

        Username and email references use exact collection filters and return
        the matching public-safe representation without a second request.
        ``orcid``, ``email``, and ``username`` remain supported keyword forms.

        Args:
            user_ref (str, optional): ORCID, service-account MFID, username, or email
            email (str, optional): User's email address
            username (str, optional): User's username
            orcid (str, optional): Explicit person ORCID
            user_unique_id (str, optional): Explicit ORCID or service-account MFID

        Returns:
            Dict: UserRead for a canonical lookup or the exact collection item

        Raises:
            ValueError: If no identifier or multiple identifiers are provided
        """
        provided = [
            value for value in (user_ref, email, username, orcid, user_unique_id)
            if value is not None
        ]
        if len(provided) != 1:
            raise ValueError("Provide exactly one user reference.")
        if user_unique_id is not None:
            return self._get_by_unique_id(user_unique_id)
        if orcid is not None:
            return self._get_by_unique_id(orcid)
        if username is not None:
            return self._get_by_username(username)
        if email is not None:
            return self._get_by_email(email)

        reference_kind, normalized = classify_user_reference(user_ref)
        if reference_kind == 'unique_id':
            return self._get_by_unique_id(normalized)
        if reference_kind == 'username':
            return self._get_by_username(normalized)
        return self._get_by_email(normalized)

    def _get_by_unique_id(self, unique_id: str) -> Dict:
        """Get a person by ORCID or a service account by MFID."""
        if not is_orcid(unique_id) and not is_mfid(unique_id):
            raise ValueError("unique_id must be an ORCID or service-account MFID.")
        raw = self._request('get', f'/users/{unique_id}')
        return require_canonical_identifier(raw, 'user')

    def _get_by_username(self, username: str) -> Dict:
        """Resolve an exact username through the user collection route."""
        reference_kind, normalized = classify_user_reference(username)
        if reference_kind != 'username':
            raise ValueError("username must be a valid 3-to-24-character username.")
        raw = self._request(
            'get',
            '/users',
            params={'username': normalized, 'limit': 2},
        )
        return collapse_exact_lookup(raw, 'user', username)

    def _get_by_email(self, email: str) -> Dict:
        """Resolve an exact email through the user collection route."""
        reference_kind, normalized = classify_user_reference(email)
        if reference_kind != 'email':
            raise ValueError("email must contain '@'.")
        raw = self._request(
            'get',
            '/users',
            params={'email': normalized, 'limit': 2},
        )
        return collapse_exact_lookup(raw, 'user', email)

    def search(self, q: str, limit: int = 20) -> List[Dict]:
        """Search for users by name or username. Available to all authenticated users.

        Matches the query term against username, first name, and last name
        simultaneously (case-insensitive). Returns UserPublicRead — no email
        exposed. Hard-capped at 50 results.

        Use client.users.list() for admin-level field-specific filtering.

        Args:
            q: Search term (e.g. "fabrice", "ron")

        Returns:
            List[Dict]: Matching users (username, first_name, last_name, orcid)
        """
        result = self._request('get', '/users/search', params={'q': q, 'limit': limit})
        return result.get('items', result) if isinstance(result, dict) else result

    @_deprecated("client.account.profile()")
    def me(self) -> Dict:
        """Deprecated: use client.account.profile() instead."""
        return self._client.account.profile()

    @_deprecated("client.account.update_profile()")
    def update_me(self, **kwargs) -> Dict:
        """Deprecated: use client.account.update_profile() instead."""
        return self._client.account.update_profile(**kwargs)

    def verify_api_key(self, orcid: str) -> Dict:
        """Verify the API key for any user. Admin only.

        Args:
            orcid: User's ORCID identifier

        Returns:
            Dict: {valid: bool, created_at: str, expires_at: str}
        """
        return self._request('get', f'/users/{orcid}/apikey/verify')

    def resolve(self, orcids: Optional[List[str]] = None,
                usernames: Optional[List[str]] = None,
                emails: Optional[List[str]] = None) -> Dict:
        """Batch-resolve users by any mix of ORCIDs, usernames, or emails.

        Open to all authenticated users. Returns public profiles (no email).

        Args:
            orcids: List of ORCID strings
            usernames: List of username strings
            emails: List of email strings

        Returns:
            Dict: Mapping of ORCID → UserPublicRead. Unresolved identifiers map to null.
        """
        body = {}
        if orcids:
            body['orcids'] = orcids
        if usernames:
            body['usernames'] = usernames
        if emails:
            body['emails'] = emails
        return self._request('post', '/users/resolve', json=body)

    def list(self, limit: int = DEFAULT_LIMIT, offset: int = 0, **kwargs) -> List[Dict]:
        """List all users in the system.

        **Requires admin permissions.**

        Args:
            limit (int): Maximum number of results to return (default: 100)
            offset (int): Starting position in the full result set (default: 0)
            **kwargs: Additional query parameters for filtering

        Returns:
            List[Dict]: List of user objects with unique_id, name, email, is_service_account

        Example:
            >>> users = client.users.list(limit=50)
            >>> for user in users:
            ...     print(f"{user['first_name']} {user['last_name']} ({user['orcid']})")
        """
        params = {k: v for k, v in kwargs.items() if v is not None}
        users = self._paginate('/users', params, limit, offset)
        return sorted(users, key=lambda u: u.get('id') or 0)

    def create(self, user, project_ids=None) -> Dict:
        """Add or update a user in the system (upsert by ORCID).

        If a user with the given ORCID already exists their record is updated.
        Project memberships and access groups are always re-applied.

        **Requires admin permissions.**

        Args:
            user: User model or dict with user information.
                  Required fields: first_name, last_name, orcid.
                  Optional: email, is_service_account.
                  If a dict, may include a 'projects' key (list of project IDs)
                  as an alternative to the project_ids parameter.
            project_ids (list, optional): Project IDs to associate with the user.

        Returns:
            Dict: Created or updated user object

        Example:
            >>> from crucible.models import User
            >>> user = User(first_name="Jane", last_name="Doe", orcid="0000-0000-0000-0000")
            >>> new_user = client.users.create(user, project_ids=["project1"])
        """
        from ..models import User
        if isinstance(user, User):
            user_data = user.model_dump(exclude_none=True, exclude={'id'})
            user_projects = project_ids or []
        else:
            user_data = dict(user)
            user_projects = user_data.pop("projects", project_ids or [])

        # API expects 'orcid', not 'unique_id'
        if 'unique_id' in user_data:
            user_data['orcid'] = user_data.pop('unique_id')

        return self._request('post', "/users", json={"user_info": user_data, "project_ids": user_projects})

    def list_datasets(self, orcid: str) -> List[str]:
        """List dataset IDs accessible to a user.

        **Requires admin permissions.**

        Args:
            orcid (str): User ORCID identifier

        Returns:
            List[str]: Dataset unique IDs the user has access to
        """
        return self._request('get', f'/users/{orcid}/datasets')

    def check_dataset_access(self, orcid: str, dsid: str) -> Dict:
        """Check a user's read/write access to a specific dataset.

        **Requires admin permissions.**

        Args:
            orcid (str): User ORCID identifier
            dsid (str): Dataset unique identifier

        Returns:
            Dict: Permissions dict with 'read' and 'write' boolean keys
        """
        return self._request('get', f'/users/{orcid}/datasets/{dsid}')

    def list_access_groups(self, orcid: str) -> List[str]:
        """List access group names for a user.

        Args:
            orcid (str): User ORCID identifier

        Returns:
            List[str]: Access group names the user belongs to
        """
        return self._request('get', f'/users/{orcid}/access_groups')

    def add_to_access_group(self, orcid: str, group_name: str) -> Dict:
        """Add a user to an access group.

        **Requires admin permissions.**

        Args:
            orcid (str): User ORCID identifier
            group_name (str): Name of the access group

        Returns:
            Dict: Updated access group object
        """
        return self._request('post', f'/users/{orcid}/access_groups/{group_name}')

    def get_projects(self, orcid: str, limit: int = DEFAULT_LIMIT, offset: int = 0) -> List[Dict]:
        """List projects associated with a user.

        Args:
            orcid (str): User ORCID identifier
            limit (int): Maximum number of results to return (default: 100)
            offset (int): Starting position in the full result set (default: 0)

        Returns:
            List[Dict]: Project objects the user is associated with
        """
        return self._paginate(f'/users/{orcid}/projects', {}, limit, offset)

    def update(self, orcid: str, **kwargs) -> Dict:
        """Partially update a user record.

        **Requires admin permissions.**

        Args:
            orcid (str): User ORCID identifier
            **kwargs: Fields to update. Accepted: first_name, last_name,
                      email, is_service_account.

        Returns:
            Dict: Updated user object
        """
        return self._request('patch', f'/users/{orcid}', json=kwargs)

    @_deprecated("client.account.api_key()")
    def get_api_key(self) -> str:
        """Deprecated: use client.account.api_key() instead."""
        return self._client.account.api_key()

    def remove_from_access_group(self, orcid: str, group_name: str) -> Dict:
        """Remove a user from an access group.

        **Requires admin permissions.**

        Args:
            orcid (str): User ORCID identifier
            group_name (str): Name of the access group

        Returns:
            Dict: Response message
        """
        return self._request('delete', f'/users/{orcid}/access_groups/{group_name}')
