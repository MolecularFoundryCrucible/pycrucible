#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Account resource operations — self-service endpoints for the authenticated caller.

All methods operate on the caller's own account via Bearer token.
For admin operations on other users, use UserOperations (client.users).
"""

import logging
from typing import Dict

from .base import BaseResource

logger = logging.getLogger(__name__)


class AccountOperations(BaseResource):
    """Self-service account operations.

    Access via: client.account.profile(), client.account.api_key(), etc.
    All methods require a valid API key but do not require admin permissions.
    """

    def whoami(self) -> Dict:
        """Return full auth context for the current API key.

        Returns ORCID, access group list, and user profile in one response.
        For just the user profile use account.profile().

        Returns:
            Dict: user_unique_id, access_group_ids, user_info (UserRead)
        """
        result = self._request('get', '/account')
        # Normalize field renames from API v2 transition so callers work against
        # both API versions without separate handling.
        user_info = result.get('user_info') or {}
        is_service = user_info.get('is_service_account', False)
        if not is_service and 'orcid' not in user_info and 'unique_id' in user_info:
            user_info['orcid'] = user_info['unique_id']
        if 'user_unique_id' in result and 'access_group_name' not in result:
            result['access_group_name'] = result['user_unique_id']
        return result

    def profile(self) -> Dict:
        """Return the authenticated caller's own user profile.

        Returns:
            Dict: UserRead — includes username, first_name, last_name, email, orcid
        """
        return self._request('get', '/account/profile')

    def update_profile(self, **kwargs) -> Dict:
        """Partially update the authenticated caller's own profile.

        Accepted fields: first_name, last_name, email, username.
        Pass username=None to clear the username.
        Note: is_service_account is admin-only — use client.users.update() instead.

        Returns:
            Dict: Updated UserRead profile
        """
        kwargs.pop('is_service_account', None)
        return self._request('patch', '/account/profile', json=kwargs)

    def api_key(self) -> str:
        """Return the caller's own API key.

        Raises:
            HTTPError 404: No API key exists for this account yet.

        Returns:
            str: The caller's API key
        """
        result = self._request('get', '/account/apikey')
        return result['api_key']

    def verify(self) -> Dict:
        """Return the validity and expiry info for the caller's API key.

        Returns:
            Dict: {valid: bool, created_at: str, expires_at: str}
        """
        return self._request('get', '/account/verify')
