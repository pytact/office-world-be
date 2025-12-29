"""FastAPI endpoints for Attendance Management module.

Based on F10_api_spec.md - Attendance Management (F-010).
All endpoints with proper authentication, authorization, and StandardResponse format.
"""

import logging
from uuid import UUID
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, status, Request, Header, Response
from fastapi.responses import Response as FastAPIResponse
from src.schemas import StandardResponse
from src.attendance.schemas import (
    CheckInRequest,
    CheckOutRequest,
    AttendanceHistoryQuery,
    CompanyAttendanceListQuery,
    AttendanceRead,
    AttendanceTodayResponse,
    AttendanceDetailResponse,
    AttendancePaginatedResponse,
    CompanyAttendancePaginatedResponse,
)
from src.attendance.dependencies import (
    AttendanceApiDep,
    get_current_employee,
    get_current_manager_hr_ceo,
    get_current_user_with_company,
)
from src.attendance.documentations.attendance_api_doc import AttendanceApiDocs
from src.attendance.constants import (
    SUCCESS_ATTENDANCE_TODAY_RETRIEVED,
    SUCCESS_ATTENDANCE_HISTORY_RETRIEVED,
    SUCCESS_CHECK_IN_RECORDED,
    SUCCESS_CHECK_OUT_RECORDED,
    SUCCESS_COMPANY_ATTENDANCE_RETRIEVED,
    SUCCESS_ATTENDANCE_DETAIL_RETRIEVED,
)
from src.attendance.utils import format_last_modified

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Employee endpoints router
router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"],
)

# Company endpoints router
company_router = APIRouter(
    prefix="/company/attendance",
    tags=["Attendance"],
)


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request headers.
    
    Based on F10_api_spec.md - IP address is automatically captured server-side.
    """
    # Try X-Forwarded-For header first (for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()
    
    # Try X-Real-IP header (for nginx proxy)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct client IP
    if request.client:
        return request.client.host
    
    return None


# ============================================================================
# Employee Endpoints (Employee, Manager, HR, CEO)
# ============================================================================

@router.get(
    "/today",
    response_model=StandardResponse[AttendanceTodayResponse],
    summary=AttendanceApiDocs.get_today["summary"],
    description=AttendanceApiDocs.get_today["description"],
)
async def get_today_attendance(
    user_employee: tuple = Depends(get_current_employee),
    api: AttendanceApiDep = Depends(AttendanceApiDep),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = Response(),
) -> StandardResponse[AttendanceTodayResponse] | FastAPIResponse:
    """Get today's attendance data for the authenticated employee."""
    user, employee, employee_id, company_id = user_employee
    
    result = await api.get_today_attendance(
        employee_id=employee_id,
        company_id=company_id,
        user_id=user.id,
        if_none_match=if_none_match,
    )
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        return result
    
    # Set ETag and Last-Modified headers from service result
    if hasattr(result, 'etag'):
        response.headers["ETag"] = result.etag
        response.headers["Last-Modified"] = format_last_modified(result.last_modified)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_ATTENDANCE_TODAY_RETRIEVED,
    )


@router.get(
    "",
    response_model=StandardResponse[AttendancePaginatedResponse],
    summary=AttendanceApiDocs.get_history["summary"],
    description=AttendanceApiDocs.get_history["description"],
)
async def get_attendance_history(
    query: AttendanceHistoryQuery = Depends(AttendanceHistoryQuery),
    user_employee: tuple = Depends(get_current_employee),
    api: AttendanceApiDep = Depends(AttendanceApiDep),
) -> StandardResponse[AttendancePaginatedResponse]:
    """Get paginated attendance history for authenticated employee."""
    user, employee, employee_id, company_id = user_employee
    
    result = await api.get_attendance_history(
        employee_id=employee_id,
        company_id=company_id,
        query=query,
    )
    
    return StandardResponse(
        data=result,
        message=SUCCESS_ATTENDANCE_HISTORY_RETRIEVED,
    )


@router.post(
    "/check-in",
    response_model=StandardResponse[AttendanceRead],
    status_code=status.HTTP_200_OK,
    summary=AttendanceApiDocs.check_in["summary"],
    description=AttendanceApiDocs.check_in["description"],
)
async def check_in(
    request_data: CheckInRequest,
    request: Request,
    user_employee: tuple = Depends(get_current_employee),
    api: AttendanceApiDep = Depends(AttendanceApiDep),
) -> StandardResponse[AttendanceRead]:
    """Record employee check-in for current day."""
    user, employee, employee_id, company_id = user_employee
    
    # Extract IP address from request
    ip_address = get_client_ip(request)
    
    result = await api.check_in(
        employee_id=employee_id,
        company_id=company_id,
        request=request_data,
        user_id=user.id,
        ip_address=ip_address,
    )
    
    return StandardResponse(
        data=result,
        message=SUCCESS_CHECK_IN_RECORDED,
    )


@router.post(
    "/check-out",
    response_model=StandardResponse[AttendanceRead],
    status_code=status.HTTP_200_OK,
    summary=AttendanceApiDocs.check_out["summary"],
    description=AttendanceApiDocs.check_out["description"],
)
async def check_out(
    request_data: CheckOutRequest,
    request: Request,
    user_employee: tuple = Depends(get_current_employee),
    api: AttendanceApiDep = Depends(AttendanceApiDep),
) -> StandardResponse[AttendanceRead]:
    """Record employee check-out for current day."""
    user, employee, employee_id, company_id = user_employee
    
    # Extract IP address from request
    ip_address = get_client_ip(request)
    
    result = await api.check_out(
        employee_id=employee_id,
        company_id=company_id,
        request=request_data,
        user_id=user.id,
        ip_address=ip_address,
    )
    
    return StandardResponse(
        data=result,
        message=SUCCESS_CHECK_OUT_RECORDED,
    )


# ============================================================================
# Company Endpoints (Manager, HR, CEO only)
# ============================================================================

@company_router.get(
    "",
    response_model=StandardResponse[CompanyAttendancePaginatedResponse],
    summary=AttendanceApiDocs.list_company["summary"],
    description=AttendanceApiDocs.list_company["description"],
)
async def list_company_attendance(
    query: CompanyAttendanceListQuery = Depends(CompanyAttendanceListQuery),
    user_company: tuple = Depends(get_current_manager_hr_ceo),
    user_with_role: tuple = Depends(get_current_user_with_company),
    api: AttendanceApiDep = Depends(AttendanceApiDep),
) -> StandardResponse[CompanyAttendancePaginatedResponse]:
    """List company attendance records with pagination, filtering, search, and sorting."""
    user, company_id = user_company
    _, _, role = user_with_role
    
    result = await api.list_company_attendance(
        company_id=company_id,
        query=query,
        role=role,
        manager_employee_id=None,  # TODO: Get manager's employee_id if needed for scope validation
    )
    
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANY_ATTENDANCE_RETRIEVED,
    )


@company_router.get(
    "/{employee_id}/{date}",
    response_model=StandardResponse[AttendanceDetailResponse],
    summary=AttendanceApiDocs.get_detail["summary"],
    description=AttendanceApiDocs.get_detail["description"],
)
async def get_attendance_detail(
    employee_id: UUID,
    date: date,
    user_company: tuple = Depends(get_current_manager_hr_ceo),
    user_with_role: tuple = Depends(get_current_user_with_company),
    api: AttendanceApiDep = Depends(AttendanceApiDep),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = Response(),
) -> StandardResponse[AttendanceDetailResponse] | FastAPIResponse:
    """Get detailed attendance for specific employee and date."""
    user, company_id = user_company
    _, _, role = user_with_role
    
    result = await api.get_attendance_detail(
        employee_id=employee_id,
        attendance_date=date,
        company_id=company_id,
        role=role,
        manager_employee_id=None,  # TODO: Get manager's employee_id if needed for scope validation
        if_none_match=if_none_match,
    )
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        return result
    
    # Set ETag and Last-Modified headers from service result
    if hasattr(result, 'etag'):
        response.headers["ETag"] = result.etag
        response.headers["Last-Modified"] = format_last_modified(result.last_modified)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_ATTENDANCE_DETAIL_RETRIEVED,
    )
