"""Domain-specific dependencies for Attendance Management module.

Based on F10_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
All endpoints explicitly exclude SuperAdmin and deactivated employees.
"""

from uuid import UUID
from typing import Optional
from fastapi import Depends, Request, Response
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.auth.dependencies import oauth2_scheme
from src.auth.utils import decode_token
from src.auth.exceptions import InvalidCredentials
from src.users.models import User
from src.employees.repository import EmployeeRepository
from src.employees.models import Employee
from src.permissions.models import Role
from src.attendance.service import AttendanceService
from src.attendance.exceptions import (
    SuperAdminNoAccess,
    DeactivatedEmployeeNoAccess,
    EmployeeNoAccess,
)
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
    
    Based on F10_api_spec.md Section 2.1 - Multi-tenancy from token.
    """
    from src.auth.utils import is_token_blacklisted
    
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


async def get_current_employee(
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Employee, UUID, UUID]:
    """Get current authenticated employee for employee endpoints.
    
    Based on F10_api_spec.md Section 3 - Roles & Permissions.
    Only Employee, Manager, HR, CEO can access employee endpoints.
    SuperAdmin and deactivated employees are explicitly excluded.
    
    Returns tuple of (User, Employee, employee_id, company_id).
    Raises SuperAdminNoAccess if user is SuperAdmin.
    Raises DeactivatedEmployeeNoAccess if employee is deactivated.
    """
    user, company_id, role = user_company
    
    # CRITICAL: SuperAdmin explicitly excluded from all attendance endpoints
    if role == "superadmin" or company_id is None:
        raise SuperAdminNoAccess()
    
    # Get employee for user
    employee_repo = EmployeeRepository(session)
    employee = await employee_repo.get_by_user_id(user.id, company_id)
    
    if not employee:
        raise DeactivatedEmployeeNoAccess()
    
    # CRITICAL: Deactivated employees cannot access attendance features
    if not employee.is_active or employee.is_deleted:
        raise DeactivatedEmployeeNoAccess()
    
    return user, employee, employee.id, company_id


async def get_current_manager_hr_ceo(
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, UUID]:
    """Get current authenticated user and company_id for company endpoints.
    
    Based on F10_api_spec.md Section 3 - Roles & Permissions.
    Only Manager, HR, CEO can access company endpoints.
    SuperAdmin, Employee, and deactivated employees are explicitly excluded.
    
    Returns tuple of (User, company_id).
    Raises SuperAdminNoAccess if user is SuperAdmin.
    Raises EmployeeNoAccess if user is Employee.
    Raises DeactivatedEmployeeNoAccess if employee is deactivated.
    """
    user, company_id, role = user_company
    
    # CRITICAL: SuperAdmin explicitly excluded from all attendance endpoints
    if role == "superadmin" or company_id is None:
        raise SuperAdminNoAccess()
    
    # CRITICAL: Employee cannot access company endpoints
    if role == "employee":
        raise EmployeeNoAccess()
    
    # Check if user is deactivated employee
    employee_repo = EmployeeRepository(session)
    employee = await employee_repo.get_by_user_id(user.id, company_id)
    
    if employee and (not employee.is_active or employee.is_deleted):
        raise DeactivatedEmployeeNoAccess()
    
    return user, company_id


class AttendanceApiDep:
    """API dependency class for Attendance Management endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """
    
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session
        self.service = AttendanceService(session)
    
    async def get_today_attendance(
        self,
        employee_id: UUID,
        company_id: UUID,
        user_id: UUID,
        if_none_match: Optional[str] = None,
    ):
        """Get today's attendance for authenticated employee."""
        return await self.service.get_today_attendance(
            employee_id=employee_id,
            company_id=company_id,
            user_id=user_id,
            if_none_match=if_none_match,
        )
    
    async def get_attendance_history(
        self,
        employee_id: UUID,
        company_id: UUID,
        query,
    ):
        """Get paginated attendance history for authenticated employee."""
        return await self.service.get_attendance_history(
            employee_id=employee_id,
            company_id=company_id,
            query=query,
        )
    
    async def check_in(
        self,
        employee_id: UUID,
        company_id: UUID,
        request,
        user_id: UUID,
        ip_address: Optional[str] = None,
    ):
        """Record employee check-in for current day."""
        return await self.service.check_in(
            employee_id=employee_id,
            company_id=company_id,
            request=request,
            user_id=user_id,
            ip_address=ip_address,
        )
    
    async def check_out(
        self,
        employee_id: UUID,
        company_id: UUID,
        request,
        user_id: UUID,
        ip_address: Optional[str] = None,
    ):
        """Record employee check-out for current day."""
        return await self.service.check_out(
            employee_id=employee_id,
            company_id=company_id,
            request=request,
            user_id=user_id,
            ip_address=ip_address,
        )
    
    async def list_company_attendance(
        self,
        company_id: UUID,
        query,
        role: str,
        manager_employee_id: Optional[UUID] = None,
    ):
        """Get paginated attendance records list with filters (Manager/HR/CEO only)."""
        return await self.service.list_company_attendance(
            company_id=company_id,
            query=query,
            role=role,
            manager_employee_id=manager_employee_id,
        )
    
    async def get_attendance_detail(
        self,
        employee_id: UUID,
        attendance_date,
        company_id: UUID,
        role: str,
        manager_employee_id: Optional[UUID] = None,
        if_none_match: Optional[str] = None,
    ):
        """Get detailed attendance for specific employee and date (Manager/HR/CEO only)."""
        return await self.service.get_attendance_detail(
            employee_id=employee_id,
            attendance_date=attendance_date,
            company_id=company_id,
            role=role,
            manager_employee_id=manager_employee_id,
            if_none_match=if_none_match,
        )
