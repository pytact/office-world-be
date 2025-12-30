"""Domain-specific dependencies for Employee Management module.

Based on F5_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
"""

from uuid import UUID
from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.auth.dependencies import oauth2_scheme
from src.auth.utils import decode_token, is_token_blacklisted
from src.auth.exceptions import InvalidCredentials
from src.users.models import User
from src.permissions.models import Role
from src.employees.service import EmployeeService
from src.employees.exceptions import SuperAdminNoAccess
from jose import JWTError


async def get_current_user_with_company(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Optional[UUID], str]:
    """Get current authenticated user, company_id, and role from JWT token.
    
    Returns tuple of (User, company_id, role) where:
    - company_id is None for SuperAdmin (company_id is null in token)
    - company_id is UUID for company-scoped users (company_id from token)
    - role is the user's role from token (superadmin, ceo, hr, manager, employee)
    
    Based on F5_api_spec.md Section 2.1 - Multi-tenancy from token.
    """
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
        # F5_api_spec.md Section 2.1 specifies "org_id" claim
        # Support both for backward compatibility: try org_id first (per spec), then company_id
        company_id_str = payload.get("org_id") or payload.get("company_id")
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


class EmployeeApiDep:
    """API dependency class for Employee Management endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = EmployeeService(session)
        self.session = session

    async def list_employees(
        self,
        company_id: Optional[UUID],
        query,
        role: str,
    ):
        """List employees with pagination, filtering, and sorting."""
        return await self.service.list_employees(company_id, query, role)

    async def get_employee_by_id(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        role: str,
        if_none_match: Optional[str] = None,
    ):
        """Get employee by ID with role-based field visibility and ETag support."""
        return await self.service.get_employee_by_id(employee_id, company_id, role, if_none_match)

    async def update_employee(
        self,
        employee_id: UUID,
        data,
        company_id: Optional[UUID],
        updated_by: UUID,
        role: str,
        if_match: Optional[str] = None,
    ):
        """Update an employee with ETag validation."""
        return await self.service.update_employee(
            employee_id, data, company_id, updated_by, role, if_match
        )

    async def soft_delete_employee(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        user_id: UUID,
        if_match: Optional[str] = None,
    ):
        """Soft delete an employee with ETag validation."""
        return await self.service.soft_delete_employee(employee_id, company_id, user_id, if_match)
