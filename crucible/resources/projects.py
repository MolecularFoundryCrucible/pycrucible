#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project resource operations for Crucible API.

Provides organized access to project-related API endpoints.
"""

import logging
from typing import Optional, List, Dict, Union
from .base import BaseResource
from ..constants import DEFAULT_LIMIT
from ..models import Project, ProjectMember

logger = logging.getLogger(__name__)


def _build_project_from_args(project_id, organization, project_lead_orcid):
    """Default function to build project info from arguments."""
    return {
        "project_id": project_id,
        "organization": organization,
        "project_lead_orcid": project_lead_orcid,
    }


class ProjectOperations(BaseResource):
    """Project-related API operations.

    Access via: client.projects.get(), client.projects.list(), etc.
    """

    def get(self, project_id: str, include_metadata: bool = False,
            include_members: bool = False) -> Dict:
        """Get details of a specific project. Readable by any authenticated user.

        The response always includes project_id, organization, status, title.

        The ``lead`` field's shape depends on membership: members and admins
        get the full user record (includes email); non-members get a public
        record (unique_id, username, first_name, last_name — no email).

        ``scientific_metadata`` is only ever populated for members/admins —
        include_metadata is silently ignored for non-members. Same gating
        applies to ``members`` (list of {unique_id, username, first_name,
        last_name, role}) with include_members - non-members always get
        ``members: None`` regardless of the flag.

        Args:
            project_id (str): Unique project identifier
            include_metadata (bool): Whether to include scientific metadata
                                      (members/admins only)
            include_members (bool): Whether to include the member list
                                     (members/admins only)

        Returns:
            Dict: Project information, with membership-gated fields as described above
        """
        params = {}
        if include_metadata:
            params['include_metadata'] = True
        if include_members:
            params['include_members'] = True
        return self._request('get', f'/projects/{project_id}', params=params or None)

    def list(self, orcid: Optional[str] = None, include_metadata: bool = False,
             limit: int = DEFAULT_LIMIT, offset: int = 0) -> List[Dict]:
        """List all accessible projects.

        Each project dict includes a ``lead`` key with the project lead's full
        user record (orcid, first_name, last_name, email, lbl_email).

        Args:
            orcid (str, optional): Filter projects by those associated with a certain user
            include_metadata (bool): Include scientific metadata in results
            limit (int): Maximum number of results to return (default: 100)
            offset (int): Starting position in the full result set (default: 0)

        Returns:
            List[Dict]: Project metadata including project_id, title, organization, lead
        """
        params = {'include_metadata': True} if include_metadata else {}
        endpoint = f'/users/{orcid}/projects' if orcid else '/projects'
        return self._paginate(endpoint, params, limit, offset)

    def create(self, project: Union[Project, Dict],
               scientific_metadata: Optional[Dict] = None) -> Dict:
        """Create a new project.

        **Requires admin permissions.**

        Args:
            project: A Project model instance or a dict with project_id,
                     organization, and project_lead_email. Alternatively, pass
                     a flexible `project_lead` field (ORCID, username, or
                     email - resolved server-side) instead of the three
                     explicit `project_lead_orcid`/`project_lead_email`/
                     `project_lead_username` fields; providing both is a 400,
                     as is providing neither.
            scientific_metadata (Dict, optional): Scientific metadata to attach after creation.

        Returns:
            Dict: Created project object

        Example:
            >>> from crucible.models import Project
            >>> project = Project(
            ...     project_id="my-project",
            ...     organization="Molecular Foundry",
            ...     project_lead_email="lead@lbl.gov"
            ... )
            >>> result = client.projects.create(project)
        """
        if isinstance(project, Project):
            project_details = project.model_dump(exclude_none=True)
        else:
            project_details = dict(project)

        result = self._request('post', "/projects", json=project_details)
        if scientific_metadata:
            self.update_scientific_metadata(result['project_id'], scientific_metadata)
        return result

    def get_users(self, project_id: str, limit: int = DEFAULT_LIMIT,
                  offset: int = 0) -> List[ProjectMember]:
        """Get users associated with a project.

        **Requires admin permissions.**

        Args:
            project_id (str): Unique project identifier
            limit (int): Maximum number of results to return (default: 100)
            offset (int): Starting position in the full result set (default: 0)

        Returns:
            List[ProjectMember]: Project team members (excludes project lead)
        """
        raw = self._paginate(f'/projects/{project_id}/users', {}, limit, offset)
        return [ProjectMember.model_validate(m) for m in raw]

    def update(self, proj_id: str, **kwargs) -> Dict:
        """Partially update a project record.

        **Requires admin permissions.**

        Leadership changes are not accepted here (422) - use
        transfer_ownership() instead, which moves owner standing and the
        denormalized lead pointer atomically.

        Note the identifying parameter is named `proj_id`, not `project_id` -
        `project_id` is itself now a valid field in `**kwargs` (it renames the
        project), and the two would collide if both were named the same.

        Args:
            proj_id (str): Unique project identifier
            **kwargs: Fields to update. Accepted: project_id (renames the
                      project), organization, status, title.

        Returns:
            Dict: Updated project object
        """
        return self._request('patch', f'/projects/{proj_id}', json=kwargs)

    def remove_user(self, project_id: str, orcid: Optional[str] = None,
                    email: Optional[str] = None, username: Optional[str] = None) -> Dict:
        """Remove a user from a project.

        **Requires admin permissions.**

        Provide one of ``orcid``, ``email``, or ``username`` to identify the user.

        Args:
            project_id (str): Unique project identifier
            orcid (str, optional): User's ORCID identifier
            email (str, optional): User's email address
            username (str, optional): User's username

        Returns:
            Dict: Response message
        """
        if not orcid and not email and not username:
            raise ValueError("provide orcid, email, or username")
        if not orcid:
            params = {}
            if email:
                params['email'] = email
            if username:
                params['username'] = username
            return self._request('delete', f'/projects/{project_id}/users/me', params=params)
        return self._request('delete', f'/projects/{project_id}/users/{orcid}')

    def add_user(self, orcid: Optional[str] = None, project_id: str = None,
                email: Optional[str] = None, username: Optional[str] = None,
                role: Optional[str] = None) -> List[ProjectMember]:
        """Add a user to a project.

        **Requires editor or above in the project.** You may only grant a role
        at or below your own - an editor can seat a contributor but never an
        admin. Cannot seat someone as owner (use transfer_ownership() instead).

        Provide one of ``orcid``, ``email``, or ``username`` to identify the user.

        Args:
            orcid (str, optional): User's ORCID identifier
            project_id (str): Unique project identifier
            email (str, optional): User's email address
            username (str, optional): User's username
            role (str, optional): Role to grant (default: contributor)

        Returns:
            List[ProjectMember]: Updated list of project users
        """
        if not orcid and not email and not username:
            raise ValueError("provide orcid, email, or username")
        if not orcid:
            params = {}
            if email:
                params['email'] = email
            if username:
                params['username'] = username
            if role:
                params['role'] = role
            return self._request('post', f'/projects/{project_id}/users/me', params=params)
        params = {'role': role} if role else {}
        raw = self._request('post', f'/projects/{project_id}/users/{orcid}', params=params)
        return [ProjectMember.model_validate(m) for m in raw]

    def update_user_role(self, project_id: str, orcid: str, role: str) -> List[ProjectMember]:
        """Change a member's role in a project.

        **Requires editor or above in the project.** The cap binds on both
        ends: you may not grant a role above your own, nor change a member who
        already holds one above your own. Cannot touch owner standing at all
        (use transfer_ownership() instead).

        Args:
            project_id (str): Unique project identifier
            orcid (str): User's ORCID identifier
            role (str): New role to grant

        Returns:
            List[ProjectMember]: Updated list of project users
        """
        raw = self._request('patch', f'/projects/{project_id}/users/{orcid}', params={'role': role})
        return [ProjectMember.model_validate(m) for m in raw]

    def search(self, q: str, limit: int = 20) -> List[Dict]:
        """Fuzzy search across all projects (not just the caller's). Available
        to all authenticated users — supports project discovery ahead of
        request_join().

        Matches against both title and project_id. Results never include
        lead or scientific_metadata, regardless of membership.

        Args:
            q: Search term (min 3 chars). Typo-tolerant.
            limit: Max results (default 20, max 50).

        Returns:
            List[Dict]: Matching ProjectRead records, ranked by relevance.
        """
        result = self._request('get', '/projects/search', params={'q': q, 'limit': limit})
        return result.get('items', result) if isinstance(result, dict) else result

    def request_join(self, project_id: str, reason: Optional[str] = None) -> Dict:
        """Request to join this project. Any authenticated user.

        Delegates to client.access_groups.request_join() — see there for full
        list/approve/reject operations on join requests.

        Args:
            project_id: Unique project identifier.
            reason: Optional explanation for the request.

        Returns:
            Dict: The created JoinRequest record (status will be "pending").

        Raises:
            HTTPError 404: Project doesn't exist.
            HTTPError 409: Already a member, or already has a pending request.
        """
        return self._client.access_groups.request_join(project_id, reason=reason)

    def list_join_requests(self, project_id: str, status: Optional[str] = None,
                           limit: int = DEFAULT_LIMIT, offset: int = 0) -> List[Dict]:
        """List join requests for this project. Admin or the project lead only.

        Delegates to client.access_groups.list_join_requests(group_name=project_id).

        Args:
            project_id: Unique project identifier.
            status: Filter by "pending", "approved", or "rejected".
            limit: Maximum number of results.
            offset: Starting position in the full result set.

        Returns:
            List[Dict]: Matching JoinRequest records, most recent first.
        """
        return self._client.access_groups.list_join_requests(
            group_name=project_id, status=status, limit=limit, offset=offset)

    def get_or_create(self, project_id: str, get_project_info_function=_build_project_from_args,
                     **kwargs) -> Dict:
        """Deprecated: use create() instead.

        .. deprecated::
            Use :meth:`create` with a :class:`~crucible.models.Project` model.
            ``create()`` now checks for an existing project before posting.
        """
        import warnings
        warnings.warn(
            "get_or_create() is deprecated; use create() instead — "
            "it now checks for an existing project automatically.",
            DeprecationWarning, stacklevel=2,
        )
        project_info = get_project_info_function(project_id=project_id, **kwargs)
        return self.create(project_info)
