from uuid import UUID
from typing import Optional
from fastapi import APIRouter, status, Header, Response, Depends
from fastapi.responses import Response as FastAPIResponse

from src.schemas import StandardResponse
from src.leaves.schemas import (
    LeaveCreate, LeaveRead, LeaveListQuery, LeavePaginatedResponse, LeaveActionRequest
)
from src.leaves.dependencies import (
    create_leave_request, get_leave_by_id, list_leaves, get_leave_action_result
)
from src.leaves.documentations.leaves_api_doc import LeaveApiDocs
from src.leaves.constants import SUCCESS_LEAVE_REQUEST_CREATED, SUCCESS_LEAVE_REQUESTS_RETRIEVED, SUCCESS_LEAVE_REQUEST_RETRIEVED

router = APIRouter(
    prefix="/api/v1/company/leaves",
    tags=["Leave Management"],
)


@router.get(
    "",
    response_model=StandardResponse[LeavePaginatedResponse],
    summary=LeaveApiDocs.list["summary"],
    description=LeaveApiDocs.list["description"],
)
async def list_leaves(
    leaves_data: LeavePaginatedResponse = Depends(list_leaves),
) -> StandardResponse[LeavePaginatedResponse]:
    """List leave requests with pagination and filtering."""
    return StandardResponse(
        data=leaves_data,
        message=SUCCESS_LEAVE_REQUESTS_RETRIEVED
    )


@router.post(
    "",
    response_model=StandardResponse[LeaveRead],
    status_code=status.HTTP_201_CREATED,
    summary=LeaveApiDocs.create["summary"],
    description=LeaveApiDocs.create["description"],
)
async def create_leave(
    data: LeaveCreate,
    leave_data: LeaveRead = Depends(create_leave_request),
) -> StandardResponse[LeaveRead]:
    """Create a new leave request."""
    return StandardResponse(
        data=leave_data,
        message=SUCCESS_LEAVE_REQUEST_CREATED
    )


@router.get(
    "/{leave_id}",
    response_model=StandardResponse[LeaveRead],
    summary=LeaveApiDocs.get["summary"],
    description=LeaveApiDocs.get["description"],
)
async def get_leave(
    leave_id: UUID,
    leave_data: LeaveRead | FastAPIResponse = Depends(get_leave_by_id),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = None,  # FastAPI injects Response for setting headers
) -> StandardResponse[LeaveRead] | FastAPIResponse:
    """Get leave request details with ETag support."""
    # If service returned 304 Not Modified, return it directly
    if isinstance(leave_data, FastAPIResponse):
        return leave_data

    # Set ETag and Last-Modified headers from service result
    if hasattr(leave_data, '_etag'):
        response.headers["ETag"] = leave_data._etag
        response.headers["Last-Modified"] = leave_data._last_modified

    return StandardResponse(
        data=leave_data,
        message=SUCCESS_LEAVE_REQUEST_RETRIEVED
    )


@router.post(
    "/{leave_id}/action",
    response_model=StandardResponse[LeaveRead],
    summary=LeaveApiDocs.action["summary"],
    description=LeaveApiDocs.action["description"],
)
async def perform_leave_action(
    leave_id: UUID,
    data: LeaveActionRequest,
    updated_leave: LeaveRead = Depends(get_leave_action_result),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,  # FastAPI injects Response for setting headers
) -> StandardResponse[LeaveRead]:
    """Perform approve, reject, or cancel action on leave request."""
    # Set new ETag header
    if hasattr(updated_leave, '_etag'):
        response.headers["ETag"] = updated_leave._etag

    # Determine success message based on action
    action_messages = {
        "approve": "Leave request approved successfully",
        "reject": "Leave request rejected successfully",
        "cancel": "Leave request cancelled successfully"
    }

    message = action_messages.get(data.action, "Leave request updated successfully")

    return StandardResponse(
        data=updated_leave,
        message=message
    )

