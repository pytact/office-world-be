"""Database operations for User & Role Management module.

Repository layer - pure database operations only, no business logic.
All methods use eager loading for relationships to prevent MissingGreenlet errors.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.users.models import User
from src.permissions.models import UserRoleAssignment, Role
from src.companies.models import Company


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID with eager loading of relationships.
        
        Eager loads:
        - role_assignments (UserRoleAssignment)
        - role_assignments.role (Role)
        - role_assignments.company (Company)
        """
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.role),
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.company),
            )
            .where(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email with eager loading of relationships.
        
        Eager loads:
        - role_assignments (UserRoleAssignment)
        - role_assignments.role (Role)
        - role_assignments.company (Company)
        """
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.role),
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.company),
            )
            .where(
                User.email.ilike(email),  # Case-insensitive email match
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_role_assignment(self, user_id: UUID) -> Optional[UserRoleAssignment]:
        """Get active role assignment for user with eager loading.
        
        Eager loads:
        - role (Role)
        - company (Company)
        """
        result = await self.session.execute(
            select(UserRoleAssignment)
            .options(
                selectinload(UserRoleAssignment.role),
                selectinload(UserRoleAssignment.company),
            )
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_platform_users(
        self,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        company_slug: Optional[str] = None,
        role_code: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[User], int]:
        """List all users across platform with pagination, filtering, and sorting.
        
        Eager loads:
        - role_assignments (UserRoleAssignment)
        - role_assignments.role (Role)
        - role_assignments.company (Company)
        """
        # Base query with eager loading
        query = (
            select(User)
            .options(
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.role),
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.company),
            )
            .where(User.deleted_at.is_(None))
        )

        # Join with UserRoleAssignment for filtering
        query = query.join(
            UserRoleAssignment,
            and_(
                UserRoleAssignment.user_id == User.id,
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.deleted_at.is_(None),
            ),
        )

        # Apply filters
        if search:
            search_filter = or_(
                User.email.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)

        if company_slug:
            query = query.join(Company, UserRoleAssignment.company_id == Company.id).where(
                Company.slug == company_slug,
                Company.deleted_at.is_(None),
            )

        if role_code:
            query = query.join(Role, UserRoleAssignment.role_id == Role.id).where(
                Role.code == role_code,
                Role.deleted_at.is_(None),
            )

        if status:
            if status == "active":
                query = query.where(User.is_active.is_(True))
            elif status == "inactive":
                query = query.where(User.is_active.is_(False))
            elif status == "pending":
                query = query.where(
                    User.invite_at.isnot(None),
                    User.activate_at.is_(None),
                    User.expiry > func.now(),
                )
            elif status == "expired":
                query = query.where(
                    User.invite_at.isnot(None),
                    User.activate_at.is_(None),
                    User.expiry <= func.now(),
                )
            elif status == "activated":
                query = query.where(User.activate_at.isnot(None))

        # Apply sorting
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        users = result.unique().scalars().all()

        return list(users), total

    async def list_company_users(
        self,
        company_id: UUID,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        role_code: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[User], int]:
        """List users in a specific company with pagination, filtering, and sorting.
        
        Eager loads:
        - role_assignments (UserRoleAssignment)
        - role_assignments.role (Role)
        - role_assignments.company (Company)
        """
        # Base query with eager loading
        query = (
            select(User)
            .options(
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.role),
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.company),
            )
            .join(
                UserRoleAssignment,
                and_(
                    UserRoleAssignment.user_id == User.id,
                    UserRoleAssignment.company_id == company_id,
                    UserRoleAssignment.is_active.is_(True),
                    UserRoleAssignment.deleted_at.is_(None),
                ),
            )
            .where(User.deleted_at.is_(None))
        )

        # Apply filters
        if search:
            search_filter = or_(
                User.email.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)

        if role_code:
            query = query.join(Role, UserRoleAssignment.role_id == Role.id).where(
                Role.code == role_code,
                Role.deleted_at.is_(None),
            )

        if status:
            if status == "active":
                query = query.where(User.is_active.is_(True))
            elif status == "inactive":
                query = query.where(User.is_active.is_(False))
            elif status == "pending":
                query = query.where(
                    User.invite_at.isnot(None),
                    User.activate_at.is_(None),
                    User.expiry > func.now(),
                )
            elif status == "expired":
                query = query.where(
                    User.invite_at.isnot(None),
                    User.activate_at.is_(None),
                    User.expiry <= func.now(),
                )
            elif status == "activated":
                query = query.where(User.activate_at.isnot(None))

        # Apply sorting
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        users = result.unique().scalars().all()

        return list(users), total

    async def create_user(self, user: User) -> User:
        """Create a new user record."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user: User) -> User:
        """Update an existing user record."""
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def list_roles(self) -> list[Role]:
        """List all active roles (for reference data).
        
        Based on F1A_api_spec.md Section 5.6 - GET /api/v1/roles.
        """
        result = await self.session.execute(
            select(Role)
            .where(
                Role.deleted_at.is_(None),
            )
            .order_by(Role.code.asc())
        )
        return list(result.scalars().all())

    async def list_companies(self) -> list[Company]:
        """List all active companies (for SuperAdmin reference data).
        
        Based on F1A_api_spec.md Section 5.7 - GET /api/v1/companies.
        """
        result = await self.session.execute(
            select(Company)
            .where(
                Company.is_active.is_(True),
                Company.deleted_at.is_(None),
            )
            .order_by(Company.name.asc())
        )
        return list(result.scalars().all())

    async def get_company_by_slug(self, slug: str) -> Optional[Company]:
        """Get company by slug."""
        result = await self.session.execute(
            select(Company)
            .where(
                Company.slug == slug,
                Company.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_role_by_code(self, code: str) -> Optional[Role]:
        """Get role by code."""
        result = await self.session.execute(
            select(Role)
            .where(
                Role.code == code,
                Role.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def check_company_has_ceo(self, company_id: UUID) -> bool:
        """Check if company already has an active CEO.
        
        Returns True if company has an active CEO, False otherwise.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(UserRoleAssignment)
            .join(Role, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.company_id == company_id,
                Role.code == "ceo",
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.deleted_at.is_(None),
                Role.deleted_at.is_(None),
            )
        )
        count = result.scalar() or 0
        return count > 0

    async def get_active_ceo_for_company(self, company_id: UUID) -> Optional[User]:
        """Get active CEO user for company.
        
        Returns the User who is the active CEO for the company, or None if no CEO exists.
        Eager loads relationships.
        """
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.role),
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.company),
            )
            .join(
                UserRoleAssignment,
                and_(
                    UserRoleAssignment.user_id == User.id,
                    UserRoleAssignment.company_id == company_id,
                    UserRoleAssignment.is_active.is_(True),
                    UserRoleAssignment.deleted_at.is_(None),
                ),
            )
            .join(Role, UserRoleAssignment.role_id == Role.id)
            .where(
                Role.code == "ceo",
                Role.deleted_at.is_(None),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_company_by_id(self, company_id: UUID) -> Optional[Company]:
        """Get company by ID."""
        result = await self.session.execute(
            select(Company)
            .where(
                Company.id == company_id,
                Company.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
