"""Database operations for Permissions System module.

Repository layer - pure database operations only, no business logic.
All methods filter by deleted_at IS NULL for soft-delete support.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_, desc, asc, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.permissions.models import Role, UserRoleAssignment


class RoleRepository:
    """Repository for role database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID.
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        """
        result = await self.session.execute(
            select(Role)
            .where(
                Role.id == role_id,
                Role.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Role]:
        """Get role by code.
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        """
        result = await self.session.execute(
            select(Role)
            .where(
                Role.code == code,
                Role.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_with_pagination(
        self,
        page: int,
        page_size: int,
        code: Optional[str] = None,
        name: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Role], int]:
        """List roles with pagination, filtering, and sorting.
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        - Optional: code filter (exact match)
        - Optional: name filter (partial match, case-insensitive)
        
        Sorting:
        - sort_by: created_at, updated_at, name, code
        - sort_order: asc, desc
        """
        # Build base query with required filters
        query = select(Role).where(
            Role.deleted_at.is_(None),
        )

        # Apply optional filters
        if code is not None:
            query = query.where(Role.code == code)

        if name is not None:
            query = query.where(Role.name.ilike(f"%{name}%"))

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = None
        if sort_by == "created_at":
            sort_column = Role.created_at
        elif sort_by == "updated_at":
            sort_column = Role.updated_at
        elif sort_by == "name":
            sort_column = Role.name
        elif sort_by == "code":
            sort_column = Role.code
        else:
            # Default to created_at if invalid sort_by
            sort_column = Role.created_at

        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def create(
        self,
        name: str,
        code: str,
        permissions: dict,
        created_by: Optional[UUID] = None,
    ) -> Role:
        """Create a new role."""
        role = Role(
            name=name,
            code=code,
            permissions=permissions,
            created_by=created_by,
        )
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def update(
        self,
        role_id: UUID,
        name: Optional[str] = None,
        permissions: Optional[dict] = None,
        updated_by: Optional[UUID] = None,
    ) -> Optional[Role]:
        """Update a role.
        
        Note: code is immutable and cannot be updated.
        """
        role = await self.get_by_id(role_id)
        if not role:
            return None

        if name is not None:
            role.name = name
        if permissions is not None:
            role.permissions = permissions
        if updated_by is not None:
            role.updated_by = updated_by

        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def soft_delete(
        self,
        role_id: UUID,
        deleted_by: Optional[UUID] = None,
    ) -> Optional[Role]:
        """Soft delete a role."""
        role = await self.get_by_id(role_id)
        if not role:
            return None

        role.deleted_at = datetime.now(timezone.utc)
        if deleted_by is not None:
            role.deleted_by = deleted_by

        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def check_role_in_use(self, role_id: UUID) -> bool:
        """Check if role is assigned to any users.
        
        Returns True if role has active assignments, False otherwise.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(UserRoleAssignment)
            .where(
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.is_active == True,
                UserRoleAssignment.deleted_at.is_(None),
            )
        )
        count = result.scalar() or 0
        return count > 0

    async def check_code_exists(self, code: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if role code already exists.
        
        Returns True if code exists, False otherwise.
        Excludes soft-deleted roles and optionally excludes a specific role ID.
        """
        query = select(func.count()).select_from(Role).where(
            Role.code == code,
            Role.deleted_at.is_(None),
        )
        if exclude_id is not None:
            query = query.where(Role.id != exclude_id)

        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def check_name_exists(self, name: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if role name already exists.
        
        Returns True if name exists, False otherwise.
        Excludes soft-deleted roles and optionally excludes a specific role ID.
        """
        query = select(func.count()).select_from(Role).where(
            Role.name == name,
            Role.deleted_at.is_(None),
        )
        if exclude_id is not None:
            query = query.where(Role.id != exclude_id)

        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
