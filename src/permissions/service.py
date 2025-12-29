"""Business logic for Permissions System module.

Service layer - all business logic, validation, and orchestration.
No HTTP concerns, no database queries (uses repository).
"""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.permissions.models import Role
from src.permissions.repository import RoleRepository
from src.permissions.schemas import (
    RoleListQuery,
    RoleRead,
    RoleListItem,
)
from src.permissions.exceptions import (
    RoleNotFound,
    InvalidSortField,
    InvalidSortOrder,
)
from src.permissions.constants import (
    VALID_SORT_FIELDS,
    VALID_SORT_ORDERS,
)
from src.pagination import PagedCollection
from src.config import settings
from src.permissions.utils import generate_etag
from fastapi.responses import Response as FastAPIResponse
from fastapi import status


class RoleService:
    """Service for role management business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = RoleRepository(session)

    def _validate_sort_field(self, sort_by: str) -> None:
        """Validate sort field."""
        if sort_by not in VALID_SORT_FIELDS:
            raise InvalidSortField(sort_by, VALID_SORT_FIELDS)

    def _validate_sort_order(self, sort_order: str) -> None:
        """Validate sort order."""
        if sort_order not in VALID_SORT_ORDERS:
            raise InvalidSortOrder(sort_order)

    async def list_roles(
        self, query: RoleListQuery, if_none_match: Optional[str] = None
    ) -> PagedCollection[RoleListItem] | FastAPIResponse:
        """List roles with pagination, filtering, and sorting with ETag support.
        
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        # Validate inputs
        self._validate_sort_field(query.sort_by)
        self._validate_sort_order(query.sort_order)

        # Get roles from repository
        items, total = await self.repository.list_with_pagination(
            page=query.page,
            page_size=query.page_size,
            code=query.code,
            name=query.name,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )

        # Generate ETag based on most recent role's updated_at (if any)
        # For empty results, use a fixed ETag
        if items:
            # Get the most recent updated_at from the result set
            # Since we're sorting, the first item should have the latest timestamp
            most_recent_updated_at = items[0].updated_at
            etag = generate_etag(most_recent_updated_at)
        else:
            # Empty result set - use a fixed ETag
            etag = generate_etag(datetime.now(timezone.utc))

        # Check If-None-Match header for conditional request
        if if_none_match and if_none_match == etag:
            # Resource hasn't changed - return 304 Not Modified
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)

        # Convert to response schemas
        role_items = [RoleListItem.model_validate(item) for item in items]

        # Calculate pagination metadata
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0

        # Build pagination URLs
        base_path = f"/api{settings.api_prefix}/roles"

        next_page = None
        prev_page = None

        if query.page < total_pages:
            # Build next_page URL with all query parameters
            next_params = []
            if query.page_size != 20:
                next_params.append(f"page_size={query.page_size}")
            if query.code is not None:
                next_params.append(f"code={query.code}")
            if query.name is not None:
                next_params.append(f"name={query.name}")
            if query.sort_by != "created_at":
                next_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                next_params.append(f"sort_order={query.sort_order}")
            next_params.append(f"page={query.page + 1}")
            next_page = f"{base_path}?{'&'.join(next_params)}"

        if query.page > 1:
            # Build prev_page URL with all query parameters
            prev_params = []
            if query.page_size != 20:
                prev_params.append(f"page_size={query.page_size}")
            if query.code is not None:
                prev_params.append(f"code={query.code}")
            if query.name is not None:
                prev_params.append(f"name={query.name}")
            if query.sort_by != "created_at":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"

        result = PagedCollection(
            items=role_items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )
        
        # Attach ETag metadata for router to set header
        result._etag = etag
        if items:
            result._last_modified = items[0].updated_at
        
        return result

    async def get_role_by_id(
        self, role_id: UUID, if_none_match: Optional[str] = None
    ) -> RoleRead | FastAPIResponse:
        """Get role by ID with ETag support.
        
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise RoleNotFound(str(role_id))

        # Generate ETag in service (business logic)
        etag = generate_etag(role.updated_at)

        # Check If-None-Match header for conditional request
        if if_none_match and if_none_match == etag:
            # Resource hasn't changed - return 304 Not Modified
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)

        # Return role with ETag metadata
        result = RoleRead.model_validate(role)
        result._etag = etag
        result._last_modified = role.updated_at
        
        return result
