"""FastAPI endpoints for Employee Management module.

Based on F5_api_spec.md - Employee Management (F-005).
All endpoints with proper authentication, authorization, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from src.schemas import StandardResponse
from src.employees.schemas import (
    EmployeeListQuery,
    EmployeeUpdate,
    EmployeeSummary,
    EmployeeDetail,
    EmployeePaginatedResponse,
)
from src.employees.dependencies import (
    EmployeeApiDep,
    get_current_user_with_company,
)
from src.employees.documentations.employees_api_doc import EmployeeApiDocs
from src.employees.constants import (
    SUCCESS_EMPLOYEES_RETRIEVED,
    SUCCESS_EMPLOYEE_RETRIEVED,
    SUCCESS_EMPLOYEE_UPDATED,
    SUCCESS_EMPLOYEE_SOFT_DELETED,
)
from src.users.models import User
from fastapi.responses import JSONResponse, Response as FastAPIResponse
from src.employees.utils import format_last_modified
from src.users.utils import generate_request_id

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/company/employees",
    tags=["Employees"],
)


# ============================================================================
# Employee Endpoints
# ============================================================================

@router.get(
    "",
    response_model=StandardResponse[EmployeePaginatedResponse],
    summary=EmployeeApiDocs.list["summary"],
    description=EmployeeApiDocs.list["description"],
)
async def list_employees(
    request: Request,
    query: EmployeeListQuery = Depends(EmployeeListQuery),
    api: EmployeeApiDep = Depends(EmployeeApiDep),
    user_company_role: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    response: Response = None,
) -> StandardResponse[EmployeePaginatedResponse]:
    """List employees with pagination, filtering, search, and sorting.
    
    Based on F5_api_spec.md Section 5.1 - GET /api/v1/company/employees.
    Authorization: CEO, HR, Manager (Employee role returns 403, SuperAdmin returns 403).
    """
    request_id = generate_request_id()
    user, company_id, role = user_company_role
    
    # SuperAdmin and Employee roles are handled in service layer (raises exception)
    if company_id is None:
        # SuperAdmin - will raise SuperAdminNoAccess in service
        pass
    
    result = await api.list_employees(company_id, query, role)
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_EMPLOYEES_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    return json_response


@router.get(
    "/{employee_id}",
    response_model=StandardResponse[EmployeeDetail],
    summary=EmployeeApiDocs.get["summary"],
    description=EmployeeApiDocs.get["description"],
)
async def get_employee(
    request: Request,
    employee_id: UUID,
    api: EmployeeApiDep = Depends(EmployeeApiDep),
    user_company_role: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = None,
) -> StandardResponse[EmployeeDetail] | FastAPIResponse:
    """Get employee details with role-based field visibility and ETag support.
    
    Based on F5_api_spec.md Section 5.3 - GET /api/v1/company/employees/{employee_id}.
    Authorization: CEO, HR, Manager (Employee role returns 403, SuperAdmin returns 403).
    """
    request_id = generate_request_id()
    user, company_id, role = user_company_role
    
    # SuperAdmin and Employee roles are handled in service layer (raises exception)
    if company_id is None:
        # SuperAdmin - will raise SuperAdminNoAccess in service
        pass
    
    result = await api.get_employee_by_id(employee_id, company_id, role, if_none_match)
    
    # Check if service returned 304 Not Modified
    if isinstance(result, FastAPIResponse):
        result.headers["X-Request-ID"] = request_id
        return result
    
    # Set ETag and Last-Modified headers
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_EMPLOYEE_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    return json_response


@router.patch(
    "/{employee_id}",
    response_model=StandardResponse[EmployeeDetail],
    summary=EmployeeApiDocs.update["summary"],
    description=EmployeeApiDocs.update["description"],
)
async def update_employee(
    request: Request,
    employee_id: UUID,
    data: EmployeeUpdate,
    api: EmployeeApiDep = Depends(EmployeeApiDep),
    user_company_role: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[EmployeeDetail]:
    """Update employee fields including activation/deactivation.
    
    Based on F5_api_spec.md Section 5.4 - PATCH /api/v1/company/employees/{employee_id}.
    Authorization: CEO, HR only (Manager, Employee, SuperAdmin return 403).
    """
    request_id = generate_request_id()
    user, company_id, role = user_company_role
    
    # SuperAdmin and non-CEO/HR roles are handled in service layer (raises exception)
    if company_id is None:
        # SuperAdmin - will raise SuperAdminNoAccess in service
        pass
    
    result = await api.update_employee(employee_id, data, company_id, user.id, role, if_match)
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_EMPLOYEE_UPDATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    return json_response


# Note: DELETE endpoint uses /api/v1/employees/{employee_id} path (no /company prefix) per F5_api_spec.md
# This requires a separate router with different prefix
delete_router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
)


@delete_router.delete(
    "/{employee_id}",
    response_model=StandardResponse[dict],
    summary=EmployeeApiDocs.delete["summary"],
    description=EmployeeApiDocs.delete["description"],
)
async def delete_employee(
    request: Request,
    employee_id: UUID,
    api: EmployeeApiDep = Depends(EmployeeApiDep),
    user_company_role: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[dict]:
    """Soft delete an employee.
    
    Based on F5_api_spec.md Section 5.5 - DELETE /api/v1/employees/{employee_id}.
    Note: DELETE endpoint uses /api/v1/employees/{employee_id} path (no /company prefix) per design decision.
    Authorization: CEO, HR only (Manager, Employee, SuperAdmin return 403).
    """
    request_id = generate_request_id()
    user, company_id, role = user_company_role
    
    # SuperAdmin and non-CEO/HR roles are handled in service layer (raises exception)
    if company_id is None:
        # SuperAdmin - will raise SuperAdminNoAccess in service
        pass
    
    await api.soft_delete_employee(employee_id, company_id, user.id, if_match)
    response_data = StandardResponse(
        data={},
        message=SUCCESS_EMPLOYEE_SOFT_DELETED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    return json_response
