from uuid import UUID
from typing import Optional, Union
from fastapi import Depends
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.leaves.service import LeaveService
from src.leaves.schemas import LeaveCreate, LeaveListQuery, LeaveActionRequest, LeaveRead, LeavePaginatedResponse
from src.auth.dependencies import get_current_user
from src.users.models import User

# Uses global OAuth2 authentication from auth module


# Note: Leaves endpoints use global get_current_user for authentication
# The leaves-specific OAuth2 scheme ensures Swagger UI points to the leaves token endpoint


def get_leave_service(session: AsyncSession = Depends(get_session)) -> LeaveService:
    """Dependency to get LeaveService instance."""
    return LeaveService(session)


async def create_leave_request(
    leave_data: LeaveCreate,
    service: LeaveService = Depends(get_leave_service),
    current_user: User = Depends(get_current_user)
) -> LeaveRead:
    """Create a new leave request."""
    return await service.create_leave_request(
        leave_data=leave_data,
        employee_id=current_user.id,
        company_id=current_user.org_id
    )


async def get_leave_by_id(
    leave_id: UUID,
    service: LeaveService = Depends(get_leave_service),
    current_user: User = Depends(get_current_user),
    if_none_match: Optional[str] = None
) -> Union[LeaveRead, FastAPIResponse]:
    """Get leave request by ID with ETag support."""
    return await service.get_leave_by_id(
        leave_id=leave_id,
        company_id=current_user.org_id,
        user_id=current_user.sub,
        user_role=current_user.role,
        if_none_match=if_none_match
    )


async def list_leaves(
    query: LeaveListQuery = Depends(LeaveListQuery),
    service: LeaveService = Depends(get_leave_service),
    current_user: User = Depends(get_current_user)
) -> LeavePaginatedResponse:
    """List leave requests with pagination and filtering."""
    return await service.list_leaves(
        query=query,
        company_id=current_user.org_id,
        user_id=current_user.sub,
        user_role=current_user.role
    )


async def get_leave_action_result(
    leave_id: UUID,
    action_data: LeaveActionRequest,
    service: LeaveService = Depends(get_leave_service),
    current_user: User = Depends(get_current_user),
    if_match: Optional[str] = None
) -> LeaveRead:
    """Perform action (approve/reject/cancel) on leave request."""
    return await service.perform_leave_action(
        leave_id=leave_id,
        action_data=action_data,
        user_id=current_user.sub,
        user_role=current_user.role,
        company_id=current_user.org_id,
        if_match=if_match
    )

