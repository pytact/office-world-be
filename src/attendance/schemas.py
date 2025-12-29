"""Pydantic schemas for Attendance Management module.

Based on F10_api_spec.md Section 4 - Resources & Endpoints.
Request schemas define input validation, Response schemas define output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from src.pagination import PagedCollection


# ============================================================================
# Request Schemas (Input Validation)
# ============================================================================

class CheckInRequest(BaseModel):
    """Request schema for check-in action.
    
    Based on F10_api_spec.md Section 4.3.3 - POST /v1/attendance/check-in.
    """
    
    location: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional location information (free text, max 500 characters)"
    )
    device_info: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional device information (free text, max 255 characters)"
    )
    
    model_config = ConfigDict(from_attributes=True)


class CheckOutRequest(BaseModel):
    """Request schema for check-out action.
    
    Based on F10_api_spec.md Section 4.3.4 - POST /v1/attendance/check-out.
    """
    
    location: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional location information (free text, max 500 characters)"
    )
    device_info: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional device information (free text, max 255 characters)"
    )
    
    model_config = ConfigDict(from_attributes=True)


class AttendanceHistoryQuery(BaseModel):
    """Query schema for listing employee's own attendance history with pagination and filtering.
    
    Based on F10_api_spec.md Section 4.3.2 - GET /v1/attendance.
    Query parameters MUST be defined using query schema class with Depends() pattern.
    """
    
    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    start_date: Optional[str] = Field(None, description="Filter by start date (ISO 8601 date format: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Filter by end date (ISO 8601 date format: YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="Filter by status: NOT_STARTED, CHECKED_IN, CHECKED_OUT")
    sort_by: str = Field("attendance_date", description="Sort field: attendance_date, check_in_time, check_out_time, worked_time")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    
    model_config = ConfigDict(from_attributes=True)


class CompanyAttendanceListQuery(BaseModel):
    """Query schema for listing company attendance records with pagination and filtering.
    
    Based on F10_api_spec.md Section 4.3.5 - GET /v1/company/attendance.
    Query parameters MUST be defined using query schema class with Depends() pattern.
    """
    
    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    employee_id: Optional[str] = Field(None, description="Filter by employee ID (UUID format, HR/CEO only)")
    start_date: Optional[str] = Field(None, description="Filter by start date (ISO 8601 date format: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Filter by end date (ISO 8601 date format: YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="Filter by status: NOT_STARTED, CHECKED_IN, CHECKED_OUT")
    sort_by: str = Field("attendance_date", description="Sort field: attendance_date, check_in_time, check_out_time, worked_time, employee_name")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas (Output Structure)
# ============================================================================

class AttendanceRead(BaseModel):
    """Full attendance record response schema.
    
    Based on F10_api_spec.md Section 4.3.1, 4.3.3, 4.3.4 - Attendance response structure.
    """
    
    id: UUID = Field(..., description="Attendance record ID")
    employee_id: UUID = Field(..., description="Employee ID")
    company_id: UUID = Field(..., description="Company ID")
    attendance_date: date = Field(..., description="Local calendar date (ISO 8601: YYYY-MM-DD)")
    check_in_time: Optional[datetime] = Field(None, description="Server timestamp of check-in (UTC, nullable)")
    check_out_time: Optional[datetime] = Field(None, description="Server timestamp of check-out (UTC, nullable)")
    status: str = Field(..., description="Attendance lifecycle state: NOT_STARTED, CHECKED_IN, CHECKED_OUT")
    worked_time: Optional[str] = Field(None, description="Derived duration (e.g., '9h 29m'), nullable if not checked out")
    is_auto_check_out: bool = Field(..., description="Flag indicating if check-out was automatic")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    
    model_config = ConfigDict(from_attributes=True)


class AttendanceSummary(BaseModel):
    """Attendance summary for list responses.
    
    Based on F10_api_spec.md Section 4.3.2 - GET /v1/attendance response.
    """
    
    id: UUID = Field(..., description="Attendance record ID")
    attendance_date: date = Field(..., description="Local calendar date (ISO 8601: YYYY-MM-DD)")
    check_in_time: Optional[datetime] = Field(None, description="Server timestamp of check-in (UTC, nullable)")
    check_out_time: Optional[datetime] = Field(None, description="Server timestamp of check-out (UTC, nullable)")
    status: str = Field(..., description="Attendance lifecycle state: NOT_STARTED, CHECKED_IN, CHECKED_OUT")
    worked_time: Optional[str] = Field(None, description="Derived duration (e.g., '9h 29m'), nullable if not checked out")
    is_auto_check_out: bool = Field(..., description="Flag indicating if check-out was automatic")
    
    model_config = ConfigDict(from_attributes=True)


class AttendanceContext(BaseModel):
    """Contextual information for attendance.
    
    Based on F10_api_spec.md Section 4.3.1 - GET /v1/attendance/today context field.
    """
    
    server_time: datetime = Field(..., description="Current server time (UTC)")
    employee_timezone: str = Field(..., description="Employee's configured timezone (IANA timezone identifier)")
    
    model_config = ConfigDict(from_attributes=True)


class AttendanceTodayResponse(BaseModel):
    """Response schema for today's attendance endpoint.
    
    Based on F10_api_spec.md Section 4.3.1 - GET /v1/attendance/today.
    """
    
    attendance: AttendanceRead = Field(..., description="Attendance record for today")
    context: AttendanceContext = Field(..., description="Contextual information")
    
    # ETag metadata (set by service, used by router for headers)
    etag: Optional[str] = Field(None, exclude=True, description="ETag for cache validation")
    last_modified: Optional[datetime] = Field(None, exclude=True, description="Last modified timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class AttendanceLogRead(BaseModel):
    """Attendance log entry response schema.
    
    Based on F10_api_spec.md Section 4.3.6 - GET /v1/company/attendance/{employee_id}/{date} logs field.
    """
    
    id: UUID = Field(..., description="Attendance log entry ID")
    action_type: str = Field(..., description="Attendance action type: CHECK_IN, CHECK_OUT, AUTO_CHECK_OUT")
    action_time: datetime = Field(..., description="Server timestamp of action (UTC)")
    location: Optional[str] = Field(None, description="Location information (nullable)")
    ip_address: Optional[str] = Field(None, description="Client IP address (nullable)")
    device_info: Optional[str] = Field(None, description="Device information (nullable)")
    notes: Optional[str] = Field(None, description="System notes (nullable)")
    is_auto_action: bool = Field(..., description="Flag indicating if action was automatic")
    
    model_config = ConfigDict(from_attributes=True)


class EmployeeSummary(BaseModel):
    """Employee summary for company attendance list.
    
    Based on F10_api_spec.md Section 4.3.5 - GET /v1/company/attendance employee field.
    """
    
    id: UUID = Field(..., description="Employee ID")
    first_name: str = Field(..., description="Employee first name")
    last_name: str = Field(..., description="Employee last name")
    
    model_config = ConfigDict(from_attributes=True)


class CompanyAttendanceSummary(BaseModel):
    """Company attendance summary for list responses.
    
    Based on F10_api_spec.md Section 4.3.5 - GET /v1/company/attendance response.
    """
    
    id: UUID = Field(..., description="Attendance record ID")
    employee: EmployeeSummary = Field(..., description="Employee information")
    attendance_date: date = Field(..., description="Local calendar date (ISO 8601: YYYY-MM-DD)")
    status: str = Field(..., description="Attendance lifecycle state: NOT_STARTED, CHECKED_IN, CHECKED_OUT")
    worked_time: Optional[str] = Field(None, description="Derived duration (e.g., '9h 29m'), nullable if not checked out")
    is_auto_check_out: bool = Field(..., description="Flag indicating if check-out was automatic")
    
    model_config = ConfigDict(from_attributes=True)


class AttendanceDetailResponse(BaseModel):
    """Response schema for attendance detail endpoint.
    
    Based on F10_api_spec.md Section 4.3.6 - GET /v1/company/attendance/{employee_id}/{date}.
    """
    
    attendance: AttendanceRead = Field(..., description="Attendance record")
    employee: EmployeeSummary = Field(..., description="Employee information")
    logs: list[AttendanceLogRead] = Field(..., description="Array of attendance log entries in chronological order")
    
    # ETag metadata (set by service, used by router for headers)
    etag: Optional[str] = Field(None, exclude=True, description="ETag for cache validation")
    last_modified: Optional[datetime] = Field(None, exclude=True, description="Last modified timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Paginated Response Types
# ============================================================================

# Type aliases for paginated responses using PagedCollection
AttendancePaginatedResponse = PagedCollection[AttendanceSummary]
CompanyAttendancePaginatedResponse = PagedCollection[CompanyAttendanceSummary]
