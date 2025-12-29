from uuid import UUID
from typing import Optional, Union
from fastapi import Depends
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.leaves.service import LeaveService
from src.leaves.schemas import LeaveCreate, LeaveListQuery, LeaveActionRequest, LeaveRead, LeavePaginatedResponse
from src.auth.dependencies import oauth2_scheme
from src.auth.utils import decode_token
from src.auth.exceptions import InvalidCredentials
from src.users.models import User
from src.permissions.models import Role
from jose import JWTError


async def get_current_user_with_company(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Optional[UUID], str, Optional[UUID]]:
    """Get current authenticated user, company_id, role, and employee_id from JWT token.
    
    Returns tuple of (User, company_id, role, employee_id) where:
    - company_id is None for SuperAdmin (company_id is null in token)
    - company_id is UUID for company-scoped users (company_id from token)
    - role is the user's role from token (superadmin, ceo, hr, manager, employee)
    - employee_id is None for SuperAdmin, UUID for company-scoped users (looked up from user_id)
    
    Based on F5_api_spec.md Section 2.1 - Multi-tenancy from token.
    """
    from src.auth.utils import is_token_blacklisted
    from src.employees.repository import EmployeeRepository
    
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
        # Support both org_id and company_id for backward compatibility
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
        
        # Get employee_id from user_id (for company-scoped users)
        employee_id = None
        if company_id is not None:
            employee_repo = EmployeeRepository(session)
            employee = await employee_repo.get_by_user_id(user.id, company_id)
            if employee:
                employee_id = employee.id
        
        return user, company_id, role, employee_id
    except (JWTError, ValueError, TypeError):
        raise InvalidCredentials()


class LeaveApiDep:
    """API dependency class for Leave Management endpoints.

    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = LeaveService(session)
        self.session = session

    async def create_leave_request(
        self,
        leave_data: LeaveCreate,
        employee_id: UUID,
        company_id: UUID
    ) -> LeaveRead:
        """Create a new leave request."""
        return await self.service.create_leave_request(
            leave_data=leave_data,
            employee_id=employee_id,
            company_id=company_id
        )

    async def get_leave_by_id(
        self,
        leave_id: UUID,
        company_id: Optional[UUID],
        user_id: UUID,
        employee_id: Optional[UUID],
        user_role: str,
        if_none_match: Optional[str] = None
    ) -> Union[LeaveRead, FastAPIResponse]:
        """Get leave request by ID with role-based access control and ETag support."""
        return await self.service.get_leave_by_id(
            leave_id=leave_id,
            company_id=company_id,
            user_id=user_id,
            employee_id=employee_id,
            user_role=user_role,
            if_none_match=if_none_match
        )

    async def list_leaves(
        self,
        company_id: Optional[UUID],
        query: LeaveListQuery,
        employee_id: Optional[UUID],
        user_role: str
    ) -> LeavePaginatedResponse:
        """List leave requests with pagination, filtering, and role-based access control."""
        return await self.service.list_leaves(
            query=query,
            company_id=company_id,
            employee_id=employee_id,
            user_role=user_role
        )

    async def perform_leave_action(
        self,
        leave_id: UUID,
        action_data: LeaveActionRequest,
        user_id: UUID,
        employee_id: Optional[UUID],
        user_role: str,
        company_id: Optional[UUID],
        if_match: Optional[str] = None
    ) -> LeaveRead:
        """Perform action (approve/reject/cancel) on leave request with ETag validation."""
        return await self.service.perform_leave_action(
            leave_id=leave_id,
            action_data=action_data,
            user_id=user_id,
            employee_id=employee_id,
            user_role=user_role,
            company_id=company_id,
            if_match=if_match
        )

