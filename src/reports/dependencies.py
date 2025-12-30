"""Domain-specific dependencies for Reports & Analytics module.

Based on F12A_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
"""

from uuid import UUID
from typing import Optional, Any
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.auth.dependencies import oauth2_scheme
from src.auth.utils import decode_token, is_token_blacklisted
from src.auth.exceptions import InvalidCredentials
from src.users.models import User
from src.employees.repository import EmployeeRepository
from src.permissions.models import Role
from src.reports.service import ReportService
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
    
    Based on F12A_api_spec.md Section 2.1 - Multi-tenancy from token.
    Token payload contains "company_id" field (see auth/service.py line 103).
    """
    # CRITICAL: Check if token is provided
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
        
        # Get user from database
        user = await session.get(User, UUID(user_id))
        if not user:
            raise InvalidCredentials()
        
        # Validate user is not soft-deleted
        if user.deleted_at is not None:
            raise InvalidCredentials()
        
        # Validate user is active
        if not user.is_active:
            raise InvalidCredentials()
        
        # Extract company_id from token
        # Token uses "company_id" field (see auth/service.py line 103)
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


async def get_current_user_with_employee(
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Optional[UUID], str, Optional[UUID]]:
    """Get current authenticated user with employee_id if user is an employee.
    
    Returns tuple of (User, company_id, role, employee_id) where:
    - employee_id is None for non-employee roles (CEO, HR, Manager, SuperAdmin)
    - employee_id is UUID for employee role
    
    Based on F12A_api_spec.md Section 3.3 - Filter Scope Restrictions.
    """
    user, company_id, role = user_company
    
    employee_id = None
    
    # Get employee_id if user is an employee
    if role == "employee" and company_id:
        employee_repo = EmployeeRepository(session)
        employee = await employee_repo.get_by_user_id(user.id, company_id)
        if employee and employee.is_active and not employee.is_deleted:
            employee_id = employee.id
    
    return user, company_id, role, employee_id


class ReportApiDep:
    """API dependency class for Reports & Analytics endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """
    
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = ReportService(session)
        self.session = session
    
    async def list_report_types(
        self,
        role: str,
    ):
        """List accessible report types based on user role."""
        return await self.service.list_report_types(role=role)
    
    async def get_report_data(
        self,
        report_type: str,
        company_id: Optional[UUID],
        role: str,
        employee_id: Optional[UUID],
        query: Any,  # ReportViewQuery
    ):
        """Get report data with optional filters."""
        return await self.service.get_report_data(
            report_type=report_type,
            company_id=company_id,
            role=role,
            employee_id=employee_id,
            query=query,
        )
    
    # Export Methods (F12B_api_spec.md)
    async def create_export(
        self,
        report_type: str,
        user_id: UUID,
        company_id: Optional[UUID],
        role: str,
        filters: Any,  # Optional[ExportFilter]
    ):
        """Create an asynchronous PDF export request."""
        return await self.service.create_export(
            report_type=report_type,
            user_id=user_id,
            company_id=company_id,
            role=role,
            filters=filters,
        )
    
    async def get_export_status(
        self,
        export_id: UUID,
        report_type: str,
        user_id: UUID,
        role: str,
        company_id: Optional[UUID],
    ):
        """Get export status (polling endpoint)."""
        return await self.service.get_export_status(
            export_id=export_id,
            report_type=report_type,
            user_id=user_id,
            role=role,
            company_id=company_id,
        )
    
    async def get_export_file_path(
        self,
        export_id: UUID,
        report_type: str,
        user_id: UUID,
        role: str,
        company_id: Optional[UUID],
    ):
        """Get export file path, size, and creation date for download."""
        return await self.service.get_export_file_path(
            export_id=export_id,
            report_type=report_type,
            user_id=user_id,
            role=role,
            company_id=company_id,
        )

