"""Domain-specific dependencies for Project Management module.

Based on F7_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
"""

from uuid import UUID
from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.auth.dependencies import oauth2_scheme
from src.auth.utils import decode_token
from src.auth.exceptions import InvalidCredentials
from src.users.models import User
from src.permissions.models import Role
from src.projects.service import ProjectService
from src.projects.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectListQuery,
)
from src.projects.exceptions import InsufficientPermissions
from jose import JWTError


async def get_current_user_with_company(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Optional[UUID], str]:
    """Get current authenticated user, company_id, and role from JWT token.
    
    Returns tuple of (User, company_id, role) where:
    - company_id is None for SuperAdmin (company_id is null in token)
    - company_id is UUID for company-scoped users (company_id from token)
    - role is the user's role from token (superadmin, ceo, manager, hr, employee)
    
    Based on F7_api_spec.md Section 2.1 - Multi-tenancy from token.
    """
    from src.auth.utils import is_token_blacklisted
    
    # CRITICAL: Check if token is None before decoding
    if not token:
        raise InvalidCredentials()
    
    # Check if token is blacklisted (user has logged out)
    if await is_token_blacklisted(token):
        raise InvalidCredentials()
    
    try:
        # Decode token to get payload
        payload = decode_token(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise InvalidCredentials()
        
        # Fetch user from database
        user = await session.get(User, UUID(user_id))
        if user is None:
            raise InvalidCredentials()
        
        # Validate user is not soft-deleted
        if user.deleted_at is not None:
            raise InvalidCredentials()
        
        # Validate user is active
        if not user.is_active:
            raise InvalidCredentials()
        
        # Extract company_id from token
        # F7_api_spec.md Section 2.1 specifies "company_id" claim
        company_id_str = payload.get("company_id")
        company_id = UUID(company_id_str) if company_id_str else None
        
        # Extract role_id from token and fetch role from database
        role_id_str = payload.get("role_id")
        if not role_id_str:
            raise InvalidCredentials("role_id is required in token")
        
        role_id = UUID(role_id_str)
        role_obj = await session.get(Role, role_id)
        if not role_obj:
            raise InvalidCredentials("Invalid role_id in token")
        
        # Get role code from Role object
        role = role_obj.code.lower()
        
        return user, company_id, role
    except (JWTError, ValueError, TypeError):
        raise InvalidCredentials()


async def get_current_company_user(
    user_company_role: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
) -> tuple[User, UUID, str]:
    """Get current authenticated user, company_id, and role, ensuring company_id is present.
    
    Based on F7_api_spec.md Section 2.1 - Multi-tenancy from token.
    All project operations require company_id (SuperAdmin excluded from project endpoints).
    
    Returns tuple of (User, company_id, role).
    Raises InsufficientPermissions if company_id is None.
    """
    user, company_id, role = user_company_role
    
    if company_id is None:
        raise InsufficientPermissions("Company context is required for project operations.")
    
    return user, company_id, role


class ProjectApiDep:
    """API dependency class for Project Management endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = ProjectService(session)
        self.session = session

    async def list_projects(
        self,
        company_id: UUID,
        query: ProjectListQuery,
        role: str,
        employee_id: Optional[UUID] = None,
        if_none_match: Optional[str] = None,
    ):
        """List projects with pagination, filtering, search, and sorting."""
        return await self.service.list_projects(
            company_id=company_id,
            query=query,
            role=role,
            employee_id=employee_id,
            if_none_match=if_none_match,
        )

    async def get_project_by_id(
        self,
        project_id: UUID,
        company_id: UUID,
        role: str,
        employee_id: Optional[UUID] = None,
        if_none_match: Optional[str] = None,
    ):
        """Get project detail with task summaries and ETag support."""
        return await self.service.get_project_by_id(
            project_id=project_id,
            company_id=company_id,
            role=role,
            employee_id=employee_id,
            if_none_match=if_none_match,
        )

    async def create_project(
        self,
        company_id: UUID,
        data: ProjectCreate,
        user_id: UUID,
        role: str,
    ):
        """Create a new project."""
        return await self.service.create_project(
            company_id=company_id,
            data=data,
            user_id=user_id,
            role=role,
        )

    async def update_project(
        self,
        project_id: UUID,
        company_id: UUID,
        data: ProjectUpdate,
        user_id: UUID,
        role: str,
        if_match: Optional[str] = None,
    ):
        """Update project name and/or status with ETag validation."""
        return await self.service.update_project(
            project_id=project_id,
            company_id=company_id,
            data=data,
            user_id=user_id,
            role=role,
            if_match=if_match,
        )

    async def delete_project(
        self,
        project_id: UUID,
        company_id: UUID,
        user_id: UUID,
        role: str,
        if_match: Optional[str] = None,
    ):
        """Delete a project using soft delete with cascade to tasks."""
        return await self.service.delete_project(
            project_id=project_id,
            company_id=company_id,
            user_id=user_id,
            role=role,
            if_match=if_match,
        )
