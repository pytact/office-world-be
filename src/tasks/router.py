"""FastAPI endpoints for Task Management module.

Based on F8_api_spec.md - Task Management & Assignment (F-008).
All endpoints with proper authentication, authorization, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from fastapi.responses import JSONResponse, Response as FastAPIResponse
from src.schemas import StandardResponse
from src.tasks.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskListQuery,
    TaskRead,
    TaskPaginatedResponse,
)
from src.tasks.dependencies import (
    TaskApiDep,
    get_current_user_with_company,
    get_current_company_user,
)
from src.tasks.documentations.task_api_doc import TaskApiDocs
from src.tasks.constants import (
    SUCCESS_TASK_CREATED,
    SUCCESS_TASK_RETRIEVED,
    SUCCESS_TASKS_RETRIEVED,
    SUCCESS_TASK_UPDATED,
    SUCCESS_TASK_STATUS_UPDATED,
    SUCCESS_TASK_ASSIGNMENTS_UPDATED,
    SUCCESS_TASK_DELETED,
)
from src.tasks.exceptions import InsufficientPermissionsView
from src.exceptions import BadRequestError
from src.tasks.utils import format_last_modified
from src.users.models import User
from src.users.utils import generate_request_id

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/company/tasks",
    tags=["Tasks"],
)


# ============================================================================
# Task Endpoints
# ============================================================================

@router.get(
    "",
    response_model=StandardResponse[TaskPaginatedResponse],
    summary=TaskApiDocs.list["summary"],
    description=TaskApiDocs.list["description"],
)
async def list_tasks(
    request: Request,
    query: TaskListQuery = Depends(TaskListQuery),
    api: TaskApiDep = Depends(TaskApiDep),
    user_company_role_employee: tuple[User, Optional[UUID], str, Optional[UUID]] = Depends(
        get_current_user_with_company
    ),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[TaskPaginatedResponse] | FastAPIResponse:
    """List tasks with pagination, filtering, search, and sorting.
    
    Based on F8_api_spec.md Section 4.3.1 - GET /api/v1/company/tasks.
    Visibility is role-based: CEO/Manager see all tasks; HR sees all (read-only); Employees see own/assigned tasks only.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role, employee_id = user_company_role_employee
    
    # Company ID is required for task endpoints
    if company_id is None:
        raise InsufficientPermissionsView()
    
    # Handle empty strings for If-None-Match
    if_none_match_value = if_none_match if if_none_match and if_none_match.strip() else None
    
    result = await api.list_tasks(
        company_id=company_id,
        query=query,
        role=role,
        employee_id=employee_id,
        if_none_match=if_none_match_value,
    )
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        if response:
            response.headers["X-Request-ID"] = request_id
        return result
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_TASKS_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode="json"))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, "_etag") and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, "_last_modified") and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.post(
    "",
    response_model=StandardResponse[TaskRead],
    status_code=status.HTTP_201_CREATED,
    summary=TaskApiDocs.create["summary"],
    description=TaskApiDocs.create["description"],
)
async def create_task(
    request: Request,
    data: TaskCreate,
    api: TaskApiDep = Depends(TaskApiDep),
    user_company_role_employee: tuple[User, UUID, str, Optional[UUID]] = Depends(
        get_current_company_user
    ),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[TaskRead]:
    """Create a new task.
    
    Based on F8_api_spec.md Section 4.3.2 - POST /api/v1/company/tasks.
    Authorization: CEO, Manager, Employee (HR blocked - read-only).
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role, employee_id = user_company_role_employee
    role_lower = role.lower() if role else ""
    
    # Employee ID is required for task creation (creator becomes owner)
    # Note: This is the creator's employee_id from their user account, not the employee_id in assignments
    if employee_id is None:
        raise BadRequestError(
            message="You must have an employee record to create tasks. The creator automatically becomes the task owner. The employee_id in assignments is for assigning tasks to other employees.",
            error_code="VALIDATION_FAILED",
            details=[{"field": "employee_id", "issue": "Your user account must be linked to an employee record in this company to create tasks"}],
        )
    
    # Extract request metadata for audit logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    result = await api.create_task(
        company_id=company_id,
        data=data,
        user_id=user.id,
        employee_id=employee_id,
        role=role,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_TASK_CREATED,
    )
    json_response = JSONResponse(
        content=response_data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED
    )
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, "_etag") and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, "_last_modified") and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.get(
    "/{task_id}",
    response_model=StandardResponse[TaskRead],
    summary=TaskApiDocs.get["summary"],
    description=TaskApiDocs.get["description"],
)
async def get_task(
    request: Request,
    task_id: UUID,
    api: TaskApiDep = Depends(TaskApiDep),
    user_company_role_employee: tuple[User, UUID, str, Optional[UUID]] = Depends(
        get_current_company_user
    ),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[TaskRead] | FastAPIResponse:
    """Get task details with assignments, project info, and derived permission fields.
    
    Based on F8_api_spec.md Section 4.3.3 - GET /api/v1/company/tasks/{task_id}.
    Access is based on visibility rules: owner, assignee, or CEO/Manager/HR roles.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role, employee_id = user_company_role_employee
    
    # Handle empty strings for If-None-Match
    if_none_match_value = if_none_match if if_none_match and if_none_match.strip() else None
    
    result = await api.get_task_by_id(
        task_id=task_id,
        company_id=company_id,
        user_id=user.id,
        employee_id=employee_id,
        role=role,
        if_none_match=if_none_match_value,
    )
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        if response:
            response.headers["X-Request-ID"] = request_id
        return result
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_TASK_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode="json"))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, "_etag") and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, "_last_modified") and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.patch(
    "/{task_id}",
    response_model=StandardResponse[TaskRead],
    summary=TaskApiDocs.update["summary"],
    description=TaskApiDocs.update["description"],
)
async def update_task(
    request: Request,
    task_id: UUID,
    data: TaskUpdate,
    api: TaskApiDep = Depends(TaskApiDep),
    user_company_role_employee: tuple[User, UUID, str, Optional[UUID]] = Depends(
        get_current_company_user
    ),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[TaskRead]:
    """Update task details (name, description, status, assignments).
    
    Based on F8_api_spec.md Section 4.3.4 - PATCH /api/v1/company/tasks/{task_id}.
    Can update name, description, status, and assignments in a single request.
    All fields are optional - only provided fields will be updated.
    
    Authorization:
    - Name/Description: Owner or Editor
    - Status: Owner or Editor
    - Assignments: Owner, CEO, or Manager
    
    Requires If-Match header for concurrency control.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role, employee_id = user_company_role_employee
    
    # Handle empty strings for If-Match
    if_match_value = if_match if if_match and if_match.strip() else None
    
    # Extract request metadata for audit logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    result = await api.update_task(
        task_id=task_id,
        company_id=company_id,
        data=data,
        user_id=user.id,
        employee_id=employee_id,
        role=role,
        if_match=if_match_value,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Determine success message based on what was updated
    updated_fields = []
    if data.name is not None or data.description is not None:
        updated_fields.append("details")
    if data.status is not None:
        updated_fields.append("status")
    if data.assignments is not None:
        updated_fields.append("assignments")
    
    # Use appropriate success message
    if len(updated_fields) == 1:
        if "status" in updated_fields:
            message = SUCCESS_TASK_STATUS_UPDATED
        elif "assignments" in updated_fields:
            message = SUCCESS_TASK_ASSIGNMENTS_UPDATED
        else:
            message = SUCCESS_TASK_UPDATED
    else:
        message = SUCCESS_TASK_UPDATED
    
    response_data = StandardResponse(
        data=result,
        message=message,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode="json"))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, "_etag") and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, "_last_modified") and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.delete(
    "/{task_id}",
    response_model=StandardResponse[dict],
    summary=TaskApiDocs.delete["summary"],
    description=TaskApiDocs.delete["description"],
)
async def delete_task(
    request: Request,
    task_id: UUID,
    api: TaskApiDep = Depends(TaskApiDep),
    user_company_role_employee: tuple[User, UUID, str, Optional[UUID]] = Depends(
        get_current_company_user
    ),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[dict]:
    """Hard delete a task (permanent removal).
    
    Based on F8_api_spec.md Section 4.3.7 - DELETE /api/v1/company/tasks/{task_id}.
    Authorization: Owner, CEO, or Manager. Requires If-Match header for concurrency control.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role, employee_id = user_company_role_employee
    
    # Handle empty strings for If-Match
    if_match_value = if_match if if_match and if_match.strip() else None
    
    # Extract request metadata for audit logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    await api.delete_task(
        task_id=task_id,
        company_id=company_id,
        user_id=user.id,
        employee_id=employee_id,
        role=role,
        if_match=if_match_value,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Return 200 OK with StandardResponse (per universal.md RULE 12.1.6 - FastAPI doesn't allow response body with 204)
    response_data = StandardResponse(
        data={},
        message=SUCCESS_TASK_DELETED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode="json"))
    json_response.headers["X-Request-ID"] = request_id
    
    return json_response
