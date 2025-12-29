from uuid import UUID
from typing import Optional
from fastapi import APIRouter, status, Header, Response, Depends, Request
from fastapi.responses import Response as FastAPIResponse, JSONResponse

from src.schemas import StandardResponse
from src.leaves.schemas import (
    LeaveCreate, LeaveRead, LeaveListQuery, LeavePaginatedResponse, LeaveActionRequest
)
from src.leaves.dependencies import (
    LeaveApiDep, get_current_user_with_company
)
from src.leaves.documentations.leaves_api_doc import LeaveApiDocs
from src.leaves.constants import SUCCESS_LEAVE_REQUEST_CREATED, SUCCESS_LEAVE_REQUESTS_RETRIEVED, SUCCESS_LEAVE_REQUEST_RETRIEVED
from src.users.models import User
from src.users.utils import generate_request_id

router = APIRouter(
    prefix="/company/leaves",
    tags=["Leave Management"],
)


@router.get(
    "",
    response_model=StandardResponse[LeavePaginatedResponse],
    summary=LeaveApiDocs.list["summary"],
    description=LeaveApiDocs.list["description"],
)
async def list_leaves(
    request: Request,
    query: LeaveListQuery = Depends(LeaveListQuery),
    api: LeaveApiDep = Depends(LeaveApiDep),
    user_company_role: tuple[User, Optional[UUID], str, Optional[UUID]] = Depends(get_current_user_with_company),
) -> StandardResponse[LeavePaginatedResponse]:
    """List leave requests with pagination and filtering."""
    request_id = generate_request_id()
    user, company_id, role, employee_id = user_company_role

    result = await api.list_leaves(company_id, query, employee_id, role)

    response_data = StandardResponse(
        data=result,
        message=SUCCESS_LEAVE_REQUESTS_RETRIEVED
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    return json_response


@router.post(
    "",
    response_model=StandardResponse[LeaveRead],
    status_code=status.HTTP_201_CREATED,
    summary=LeaveApiDocs.create["summary"],
    description=LeaveApiDocs.create["description"],
)
async def create_leave(
    request: Request,
    data: LeaveCreate,
    api: LeaveApiDep = Depends(LeaveApiDep),
    user_company_role: tuple[User, Optional[UUID], str, Optional[UUID]] = Depends(get_current_user_with_company),
) -> StandardResponse[LeaveRead]:
    """Create a new leave request."""
    request_id = generate_request_id()
    user, company_id, role, employee_id = user_company_role

    if not employee_id:
        from src.leaves.exceptions import BusinessRuleFailed
        raise BusinessRuleFailed(
            "Employee record not found for this user",
            "employee_id",
            "You must be an employee to create a leave request."
        )

    result = await api.create_leave_request(data, employee_id, company_id)

    return StandardResponse(
        data=result,
        message=SUCCESS_LEAVE_REQUEST_CREATED
    )


@router.get(
    "/{leave_id}",
    response_model=StandardResponse[LeaveRead],
    summary=LeaveApiDocs.get["summary"],
    description=LeaveApiDocs.get["description"],
)
async def get_leave(
    request: Request,
    leave_id: UUID,
    api: LeaveApiDep = Depends(LeaveApiDep),
    user_company_role: tuple[User, Optional[UUID], str, Optional[UUID]] = Depends(get_current_user_with_company),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = None,  # FastAPI injects Response for setting headers
) -> StandardResponse[LeaveRead] | FastAPIResponse:
    """Get leave request details with ETag support."""
    request_id = generate_request_id()
    user, company_id, role, employee_id = user_company_role

    result = await api.get_leave_by_id(leave_id, company_id, user.id, employee_id, role, if_none_match)

    # If service returned 304 Not Modified, return it directly
    if isinstance(result, FastAPIResponse):
        result.headers["X-Request-ID"] = request_id
        return result

    # Set ETag and Last-Modified headers from service result
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_LEAVE_REQUEST_RETRIEVED
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        from src.leaves.utils import format_last_modified
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    return json_response


@router.post(
    "/{leave_id}/action",
    response_model=StandardResponse[LeaveRead],
    summary=LeaveApiDocs.action["summary"],
    description=LeaveApiDocs.action["description"],
)
async def perform_leave_action(
    request: Request,
    leave_id: UUID,
    data: LeaveActionRequest,
    api: LeaveApiDep = Depends(LeaveApiDep),
    user_company_role: tuple[User, Optional[UUID], str, Optional[UUID]] = Depends(get_current_user_with_company),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,  # FastAPI injects Response for setting headers
) -> StandardResponse[LeaveRead]:
    """Perform approve, reject, or cancel action on leave request."""
    request_id = generate_request_id()
    user, company_id, role, employee_id = user_company_role

    # For cancel action, we need employee_id. For approve/reject, we can use user_id to get employee
    updated_leave = await api.perform_leave_action(leave_id, data, user.id, employee_id, role, company_id, if_match)

    # Determine success message based on action
    action_messages = {
        "approve": "Leave request approved successfully",
        "reject": "Leave request rejected successfully",
        "cancel": "Leave request cancelled successfully"
    }

    message = action_messages.get(data.action, "Leave request updated successfully")

    # Set new ETag header
    response_data = StandardResponse(
        data=updated_leave,
        message=message
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(updated_leave, '_etag') and updated_leave._etag:
        json_response.headers["ETag"] = updated_leave._etag

    return json_response

