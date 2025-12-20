"""Database operations for authentication."""

from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.users.models import User
from src.permissions.models import UserRoleAssignment, Role
from src.companies.models import Company


class AuthRepository:
    """Repository for authentication database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with eager loading of role assignments, roles, and companies."""
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.role),
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.company),
            )
            .where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_user_by_token(self, token: UUID) -> Optional[User]:
        """Get user by invitation/reset token with eager loading."""
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.role),
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.company),
            )
            .where(User.token == token, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_active_role_assignment(self, user_id: UUID) -> Optional[UserRoleAssignment]:
        """Get active role assignment for user with eager loading of role and company."""
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
            .order_by(UserRoleAssignment.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_user(self, user: User) -> User:
        """Update user in database."""
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def create_user(self, user: User) -> User:
        """Create user in database."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_with_permissions_context(self, user_id: UUID) -> Optional[User]:
        """Get user by ID with eager loading of role assignment, role, and company.
        
        Used for permission evaluation in GET /api/v1/auth/me endpoint.
        Loads all relationships needed to compute PermissionSet and AuthContext.
        """
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.role),
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.company),
            )
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
