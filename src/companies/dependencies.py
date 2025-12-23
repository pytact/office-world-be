"""Domain-specific dependencies for Companies System module.

Based on F4_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
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
from src.companies.service import CompanyService
from src.users.exceptions import InsufficientPermissions
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
    
    Based on F4_api_spec.md Section 2.1 - Multi-tenancy from token.
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
        # F4_api_spec.md Section 2.1 specifies "org_id" claim, but actual JWT uses "company_id"
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


async def get_current_ceo_or_hr(
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
) -> tuple[User, Optional[UUID]]:
    """Get current authenticated user and company_id, ensuring role is CEO or HR.
    
    Based on F4_api_spec.md Section 3 - Roles & Permissions.
    Only CEO and HR can access company profile endpoints.
    SuperAdmin, Employees, and Managers are explicitly denied.
    
    Returns tuple of (User, company_id).
    Raises InsufficientPermissions if user is not CEO or HR, or if company_id is null.
    """
    user, company_id, role = user_company
    
    # Normalize role to lowercase for comparison
    role_lower = role.lower() if role else ""
    
    # Check if role is allowed (CEO or HR only, not SuperAdmin)
    if role_lower not in ["ceo", "hr"]:
        raise InsufficientPermissions()
    
    # For profile endpoints, company_id must be present
    if company_id is None:
        raise InsufficientPermissions()
    
    return user, company_id


class CompanyApiDep:
    """API dependency class for Companies System endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = CompanyService(session)
        self.session = session

    async def list_companies_paginated(self, query):
        """List companies with pagination, filtering, and sorting."""
        return await self.service.list_companies_paginated(query)

    async def get_company_by_id(self, company_id: UUID, if_none_match: Optional[str] = None):
        """Get company by ID with ETag support."""
        return await self.service.get_company_by_id(company_id, if_none_match=if_none_match)

    async def create_company(self, data, created_by: Optional[UUID] = None):
        """Create a new company."""
        return await self.service.create_company(data, created_by=created_by)

    async def update_company(
        self, 
        company_id: UUID, 
        data, 
        if_match: Optional[str] = None,
        updated_by: Optional[UUID] = None
    ):
        """Update a company with ETag validation."""
        return await self.service.update_company(
            company_id, data, if_match=if_match, updated_by=updated_by
        )

    async def delete_company(self, company_id: UUID, if_match: Optional[str] = None):
        """Delete a company."""
        return await self.service.delete_company(company_id, if_match=if_match)

    async def get_company_profile(self, company_id: UUID, if_none_match: Optional[str] = None):
        """Get company profile with ETag support."""
        return await self.service.get_company_profile(company_id, if_none_match=if_none_match)

    async def update_company_profile(
        self,
        company_id: UUID,
        data,
        if_match: Optional[str] = None,
        updated_by: Optional[UUID] = None
    ):
        """Update company profile with ETag validation."""
        return await self.service.update_company_profile(
            company_id, data, if_match=if_match, updated_by=updated_by
        )

