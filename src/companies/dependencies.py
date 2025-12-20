"""Domain-specific dependencies for Companies System module.

Based on F1A_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
"""

from uuid import UUID
from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.auth.dependencies import get_current_user, oauth2_scheme
from src.auth.utils import decode_token
from src.auth.exceptions import InvalidCredentials
from src.users.models import User
from src.companies.service import CompanyService
from jose import JWTError


async def get_current_user_with_company(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Optional[UUID]]:
    """Get current authenticated user and company_id from JWT token.
    
    Returns tuple of (User, company_id) where company_id is:
    - None for SuperAdmin (company_id is null in token)
    - UUID for company-scoped users (company_id from token)
    
    Based on F3_api_spec.md Section 2.1 - Multi-tenancy from token.
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
        # Note: JWT token uses "company_id" (not "org_id") - see auth/service.py line 98
        # F3_api_spec.md mentions "org_id" but actual implementation uses "company_id"
        company_id_str = payload.get("company_id")  # JWT token uses company_id
        company_id = UUID(company_id_str) if company_id_str else None
        
        return user, company_id
    except (JWTError, ValueError, TypeError):
        raise InvalidCredentials()


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

    async def get_company_by_id(self, company_id: UUID):
        """Get company by ID."""
        return await self.service.get_company_by_id(company_id)

    async def create_company(self, data, created_by: Optional[UUID] = None):
        """Create a new company."""
        return await self.service.create_company(data, created_by=created_by)

    async def update_company(self, company_id: UUID, data, updated_by: Optional[UUID] = None):
        """Update a company."""
        return await self.service.update_company(company_id, data, updated_by=updated_by)

    async def delete_company(self, company_id: UUID, deleted_by: Optional[UUID] = None):
        """Delete a company."""
        return await self.service.delete_company(company_id, deleted_by=deleted_by)
