"""Business logic for Permissions System module.

Service layer - all business logic, validation, and orchestration.
No HTTP concerns, no database queries (uses repository).
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from src.permissions.models import Role
from src.permissions.repository import RoleRepository
from src.permissions.schemas import (
    RoleListQuery,
    RoleCreate,
    RoleUpdate,
    RoleRead,
    RoleListItem,
)
from src.permissions.exceptions import (
    RoleNotFound,
    InvalidRoleCode,
    DuplicateRoleCode,
    DuplicateRoleName,
    InvalidSortField,
    InvalidSortOrder,
    CannotDeleteRoleInUse,
)
from src.permissions.constants import (
    VALID_ROLE_CODES,
    VALID_SORT_FIELDS,
    VALID_SORT_ORDERS,
)
from src.pagination import PagedCollection
from src.config import settings


class RoleService:
    """Service for role management business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = RoleRepository(session)

    def _validate_role_code(self, role_code: str) -> None:
        """Validate role code."""
        if role_code not in VALID_ROLE_CODES:
            raise InvalidRoleCode(role_code, VALID_ROLE_CODES)

    def _validate_sort_field(self, sort_by: str) -> None:
        """Validate sort field."""
        if sort_by not in VALID_SORT_FIELDS:
            raise InvalidSortField(sort_by, VALID_SORT_FIELDS)

    def _validate_sort_order(self, sort_order: str) -> None:
        """Validate sort order."""
        if sort_order not in VALID_SORT_ORDERS:
            raise InvalidSortOrder(sort_order)

    async def list_roles(self, query: RoleListQuery) -> PagedCollection[RoleListItem]:
        """List roles with pagination, filtering, and sorting."""
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

        return PagedCollection(
            items=role_items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def get_role_by_id(self, role_id: UUID) -> RoleRead:
        """Get role by ID."""
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise RoleNotFound(str(role_id))

        return RoleRead.model_validate(role)

    async def create_role(self, data: RoleCreate, created_by: Optional[UUID] = None) -> RoleRead:
        """Create a new role."""
        # Validate role code
        self._validate_role_code(data.code)

        # Check for duplicate code
        if await self.repository.check_code_exists(data.code):
            raise DuplicateRoleCode(data.code)

        # Check for duplicate name
        if await self.repository.check_name_exists(data.name):
            raise DuplicateRoleName(data.name)

        # Create role
        role = await self.repository.create(
            name=data.name,
            code=data.code,
            permissions=data.permissions,
            created_by=created_by,
        )

        return RoleRead.model_validate(role)

    async def update_role(
        self, role_id: UUID, data: RoleUpdate, updated_by: Optional[UUID] = None
    ) -> RoleRead:
        """Update a role."""
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise RoleNotFound(str(role_id))

        # Check for duplicate name if name is being updated
        if data.name is not None and data.name != role.name:
            if await self.repository.check_name_exists(data.name, exclude_id=role_id):
                raise DuplicateRoleName(data.name)

        # Update role
        updated_role = await self.repository.update(
            role_id=role_id,
            name=data.name,
            permissions=data.permissions,
            updated_by=updated_by,
        )

        if not updated_role:
            raise RoleNotFound(str(role_id))

        return RoleRead.model_validate(updated_role)

    async def delete_role(self, role_id: UUID, deleted_by: Optional[UUID] = None) -> None:
        """Soft delete a role."""
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise RoleNotFound(str(role_id))

        # Check if role is in use
        if await self.repository.check_role_in_use(role_id):
            raise CannotDeleteRoleInUse(role.code)

        # Soft delete role
        await self.repository.soft_delete(role_id, deleted_by=deleted_by)
