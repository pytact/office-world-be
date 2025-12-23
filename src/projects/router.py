"""FastAPI endpoints for Project Management module.

Based on F7_api_spec.md - Project Management (F-007).
All endpoints with proper authentication, authorization, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from fastapi.responses import JSONResponse, Response as FastAPIResponse
from src.schemas import StandardResponse
from src.projects.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectListQuery,
    ProjectSummary,
    ProjectDetail,
    ProjectPaginatedResponse,
)
from src.projects.dependencies import (
    ProjectApiDep,
    get_current_user_with_company,
    get_current_company_user,
)
from src.projects.documentations.project_api_doc import ProjectApiDocs
from src.projects.constants import (
    SUCCESS_PROJECT_CREATED,
    SUCCESS_PROJECT_RETRIEVED,
    SUCCESS_PROJECTS_RETRIEVED,
    SUCCESS_PROJECT_UPDATED,
    SUCCESS_PROJECT_DELETED,
)
from src.projects.utils import format_last_modified
from src.users.models import User
from src.users.utils import generate_request_id

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/company/projects",
    tags=["Projects"],
)


# ============================================================================
# Project Endpoints
# ============================================================================

@router.get(
    "",
    response_model=StandardResponse[ProjectPaginatedResponse],
    summary=ProjectApiDocs.list["summary"],
    description=ProjectApiDocs.list["description"],
)
async def list_projects(
    request: Request,
    query: ProjectListQuery = Depends(ProjectListQuery),
    api: ProjectApiDep = Depends(ProjectApiDep),
    user_company_role: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[ProjectPaginatedResponse] | FastAPIResponse:
    """List projects with pagination, filtering, search, and sorting.
    
    Based on F7_api_spec.md Section 4.3.1 - GET /api/v1/company/projects.
    Visibility is role-based: CEO/Manager/HR see all company projects; Employees see only projects with assigned tasks.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role = user_company_role
    
    # Company ID is required for project endpoints
    if company_id is None:
        from src.projects.exceptions import InsufficientPermissions
        raise InsufficientPermissions("Company context is required for project operations.")
    
    # Get employee_id for employee role visibility
    employee_id = None
    if role.lower() == "employee":
        # TODO: Get employee_id from user.employee relationship when available
        # For now, use user.id as fallback (will be updated when employee model is linked)
        employee_id = user.id
    
    # Handle empty strings for If-None-Match
    if_none_match_value = if_none_match if if_none_match and if_none_match.strip() else None
    
    result = await api.list_projects(
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
        message=SUCCESS_PROJECTS_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.post(
    "",
    response_model=StandardResponse[ProjectDetail],
    status_code=status.HTTP_201_CREATED,
    summary=ProjectApiDocs.create["summary"],
    description=ProjectApiDocs.create["description"],
)
async def create_project(
    request: Request,
    data: ProjectCreate,
    api: ProjectApiDep = Depends(ProjectApiDep),
    user_company_role: tuple[User, UUID, str] = Depends(get_current_company_user),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[ProjectDetail]:
    """Create a new project.
    
    Based on F7_api_spec.md Section 4.3.2 - POST /api/v1/company/projects.
    Authorization: CEO, Manager only.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role = user_company_role
    
    result = await api.create_project(
        company_id=company_id,
        data=data,
        user_id=user.id,
        role=role,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_PROJECT_CREATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.get(
    "/{project_id}",
    response_model=StandardResponse[ProjectDetail],
    summary=ProjectApiDocs.get["summary"],
    description=ProjectApiDocs.get["description"],
)
async def get_project(
    request: Request,
    project_id: UUID,
    api: ProjectApiDep = Depends(ProjectApiDep),
    user_company_role: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[ProjectDetail] | FastAPIResponse:
    """Get project detail with task summaries.
    
    Based on F7_api_spec.md Section 4.3.3 - GET /api/v1/company/projects/{project_id}.
    Employees can only access projects where they have assigned tasks.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role = user_company_role
    
    # Company ID is required for project endpoints
    if company_id is None:
        from src.projects.exceptions import InsufficientPermissions
        raise InsufficientPermissions("Company context is required for project operations.")
    
    # Handle empty strings for If-None-Match
    if_none_match_value = if_none_match if if_none_match and if_none_match.strip() else None
    
    # Get employee_id for employee role visibility
    employee_id = None
    if role.lower() == "employee":
        # TODO: Get employee_id from user.employee relationship when available
        employee_id = user.id
    
    result = await api.get_project_by_id(
        project_id=project_id,
        company_id=company_id,
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
        message=SUCCESS_PROJECT_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.patch(
    "/{project_id}",
    response_model=StandardResponse[ProjectDetail],
    summary=ProjectApiDocs.update["summary"],
    description=ProjectApiDocs.update["description"],
)
async def update_project(
    request: Request,
    project_id: UUID,
    data: ProjectUpdate,
    api: ProjectApiDep = Depends(ProjectApiDep),
    user_company_role: tuple[User, UUID, str] = Depends(get_current_company_user),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[ProjectDetail]:
    """Update project name and/or status.
    
    Based on F7_api_spec.md Section 4.3.4 - PATCH /api/v1/company/projects/{project_id}.
    Authorization: CEO, Manager only.
    Requires If-Match header (ETag) for concurrency control.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role = user_company_role
    
    # Handle empty strings for If-Match
    if_match_value = if_match if if_match and if_match.strip() else None
    
    result = await api.update_project(
        project_id=project_id,
        company_id=company_id,
        data=data,
        user_id=user.id,
        role=role,
        if_match=if_match_value,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_PROJECT_UPDATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag header if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    
    return json_response


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary=ProjectApiDocs.delete["summary"],
    description=ProjectApiDocs.delete["description"],
)
async def delete_project(
    request: Request,
    project_id: UUID,
    api: ProjectApiDep = Depends(ProjectApiDep),
    user_company_role: tuple[User, UUID, str] = Depends(get_current_company_user),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> FastAPIResponse:
    """Delete a project using soft delete with cascade to tasks.
    
    Based on F7_api_spec.md Section 4.3.5 - DELETE /api/v1/company/projects/{project_id}.
    Authorization: CEO, Manager only.
    Requires If-Match header (ETag) for concurrency control.
    Returns 204 No Content.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role = user_company_role
    
    # Handle empty strings for If-Match
    if_match_value = if_match if if_match and if_match.strip() else None
    
    await api.delete_project(
        project_id=project_id,
        company_id=company_id,
        user_id=user.id,
        role=role,
        if_match=if_match_value,
    )
    
    # Return 204 No Content
    no_content_response = FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)
    no_content_response.headers["X-Request-ID"] = request_id
    
    return no_content_response
