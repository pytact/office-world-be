"""Domain-specific dependencies for Salary Management module.

Based on F6_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
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
from src.salaries.service import SalaryService
from src.salaries.schemas import SalaryCreate, BankInfoUpsert, SalaryPaymentCreate, SalaryOverviewQuery, SalaryPaymentListQuery
from src.salaries.exceptions import InsufficientPermissions
from jose import JWTError


async def get_current_user_with_company(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Optional[UUID], str]:
    """Get current authenticated user, company_id, and role from JWT token.
    
    Returns tuple of (User, company_id, role) where:
    - company_id is None for SuperAdmin (org_id is null in token)
    - company_id is UUID for company-scoped users (org_id from token)
    - role is the user's role from token (superadmin, ceo, hr, manager, employee)
    
    Based on F6_api_spec.md Section 2.1 - Multi-tenancy from token.
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
        # F6_api_spec.md Section 2.1 specifies "org_id" claim
        company_id_str = payload.get("org_id") or payload.get("company_id")
        company_id = UUID(company_id_str) if company_id_str else None
        
        # Extract role from token
        role = payload.get("role", "").lower()
        
        return user, company_id, role
    except (JWTError, ValueError, TypeError):
        raise InvalidCredentials()


async def get_current_ceo_or_hr(
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
) -> tuple[User, Optional[UUID]]:
    """Get current authenticated user and company_id, ensuring role is CEO, HR, or SuperAdmin.
    
    Based on F6_api_spec.md Section 3 - Roles & Permissions.
    Only CEO, HR, and SuperAdmin can access salary endpoints.
    Employees and Managers are explicitly denied.
    
    Returns tuple of (User, company_id).
    Raises InsufficientPermissions if user is Employee or Manager.
    """
    user, company_id, role = user_company
    
    # Normalize role to lowercase for comparison
    role_lower = role.lower() if role else ""
    
    # Check if role is allowed (CEO, HR, or SuperAdmin)
    if role_lower not in ["ceo", "hr", "superadmin"]:
        raise InsufficientPermissions()
    
    return user, company_id


class SalaryApiDep:
    """API dependency class for Salary Management endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = SalaryService(session)
        self.session = session

    async def get_salary_overview(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        query: SalaryOverviewQuery,
        if_none_match: Optional[str] = None,
    ):
        """Get salary overview for employee."""
        return await self.service.get_salary_overview(
            employee_id=employee_id,
            company_id=company_id,
            query=query,
            if_none_match=if_none_match,
        )

    async def create_or_update_salary(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: SalaryCreate,
        user_id: UUID,
        if_match: Optional[str] = None,
    ):
        """Create or update salary details."""
        return await self.service.create_or_update_salary(
            employee_id=employee_id,
            company_id=company_id,
            data=data,
            user_id=user_id,
            if_match=if_match,
        )

    async def upsert_bank_info(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: BankInfoUpsert,
        user_id: UUID,
        if_match: Optional[str] = None,
    ):
        """Upsert bank information."""
        return await self.service.upsert_bank_info(
            employee_id=employee_id,
            company_id=company_id,
            data=data,
            user_id=user_id,
            if_match=if_match,
        )

    async def create_salary_payment(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: SalaryPaymentCreate,
        user_id: UUID,
    ):
        """Create salary payment."""
        return await self.service.create_salary_payment(
            employee_id=employee_id,
            company_id=company_id,
            data=data,
            user_id=user_id,
        )

    async def list_salary_payments(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        query: SalaryPaymentListQuery,
    ):
        """List salary payments."""
        return await self.service.list_salary_payments(
            employee_id=employee_id,
            company_id=company_id,
            query=query,
        )

    async def get_salary_slip(
        self,
        employee_id: UUID,
        payment_id: UUID,
        company_id: Optional[UUID],
    ):
        """Get salary slip PDF with payment metadata."""
        return await self.service.get_salary_slip(
            employee_id=employee_id,
            payment_id=payment_id,
            company_id=company_id,
        )
