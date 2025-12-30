"""Domain-specific dependencies for Task Management module.

Based on F8_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
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
from src.employees.repository import EmployeeRepository
from src.permissions.models import Role
from src.tasks.service import TaskService
from src.tasks.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskAssignmentUpdate,
    TaskListQuery,
)
from src.tasks.exceptions import InsufficientPermissionsView
from jose import JWTError


async def get_current_user_with_company(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Optional[UUID], str, Optional[UUID]]:
    """Get current authenticated user, company_id, role, and employee_id from JWT token.
    
    Returns tuple of (User, company_id, role, employee_id) where:
    - company_id is None for SuperAdmin, UUID for company-scoped users
    - role is the user's role from token (superadmin, ceo, hr, manager, employee)
    - employee_id is None for SuperAdmin, UUID for company-scoped users (looked up from user_id)
    
    Based on F8_api_spec.md Section 2.1 - Multi-tenancy from token.
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
        # F8_api_spec.md Section 2.1 specifies "company_id" claim
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


async def get_current_company_user(
    user_company_role_employee: tuple[User, Optional[UUID], str, Optional[UUID]] = Depends(
        get_current_user_with_company
    ),
) -> tuple[User, UUID, str, Optional[UUID]]:
    """Get current authenticated user, company_id, role, and employee_id.
    
    Ensures company_id is not None (raises error for SuperAdmin accessing company-scoped endpoints).
    
    Returns tuple of (User, company_id, role, employee_id).
    Raises InvalidCredentials if company_id is None.
    """
    user, company_id, role, employee_id = user_company_role_employee
    
    if company_id is None:
        raise InvalidCredentials("Company context required for this endpoint")
    
    return user, company_id, role, employee_id


class TaskApiDep:
    """API dependency class for Task Management endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = TaskService(session)
        self.session = session

    async def list_tasks(
        self,
        company_id: UUID,
        query: TaskListQuery,
        role: str,
        employee_id: Optional[UUID] = None,
        if_none_match: Optional[str] = None,
    ):
        """List tasks with pagination, filtering, search, and sorting."""
        return await self.service.list_tasks(
            company_id=company_id,
            query=query,
            role=role,
            employee_id=employee_id,
            if_none_match=if_none_match,
        )

    async def get_task_by_id(
        self,
        task_id: UUID,
        company_id: UUID,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_none_match: Optional[str] = None,
    ):
        """Get task detail with assignments, project info, and derived permission fields."""
        return await self.service.get_task_by_id(
            task_id=task_id,
            company_id=company_id,
            user_id=user_id,
            employee_id=employee_id,
            role=role,
            if_none_match=if_none_match,
        )

    async def create_task(
        self,
        company_id: UUID,
        data: TaskCreate,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Create a new task."""
        return await self.service.create_task(
            company_id=company_id,
            data=data,
            user_id=user_id,
            employee_id=employee_id,
            role=role,
        )

    async def update_task(
        self,
        task_id: UUID,
        company_id: UUID,
        data: TaskUpdate,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_match: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Update task name and description."""
        return await self.service.update_task(
            task_id=task_id,
            company_id=company_id,
            data=data,
            user_id=user_id,
            employee_id=employee_id,
            role=role,
            if_match=if_match,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def change_status(
        self,
        task_id: UUID,
        company_id: UUID,
        data: TaskStatusUpdate,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_match: Optional[str] = None,
    ):
        """Change task status (owner or editor)."""
        return await self.service.change_status(
            task_id=task_id,
            company_id=company_id,
            data=data,
            user_id=user_id,
            employee_id=employee_id,
            role=role,
            if_match=if_match,
        )

    async def update_assignments(
        self,
        task_id: UUID,
        company_id: UUID,
        data: TaskAssignmentUpdate,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_match: Optional[str] = None,
    ):
        """Update task assignments (add or remove)."""
        return await self.service.update_assignments(
            task_id=task_id,
            company_id=company_id,
            data=data,
            user_id=user_id,
            employee_id=employee_id,
            role=role,
            if_match=if_match,
        )

    async def delete_task(
        self,
        task_id: UUID,
        company_id: UUID,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_match: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Hard delete a task (permanent removal)."""
        return await self.service.delete_task(
            task_id=task_id,
            company_id=company_id,
            user_id=user_id,
            employee_id=employee_id,
            role=role,
            if_match=if_match,
            ip_address=ip_address,
            user_agent=user_agent,
        )
