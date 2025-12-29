"""Pydantic schemas for Employee Management API.

Based on F5_api_spec.md - Request schemas for input validation,
Response schemas for output structure.
"""

from uuid import UUID
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# ============================================================================
# REQUEST SCHEMAS (Input Validation)
# ============================================================================

class EmployeeListQuery(BaseModel):
    """Query schema for listing employees with pagination and filtering.
    
    Based on F5_api_spec.md Section 5.1 - GET /api/v1/company/employees query parameters.
    """

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    search: Optional[str] = Field(None, description="Search by user name or email (case-insensitive partial match)")
    department: Optional[str] = Field(None, description="Filter by department (exact match): FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT")
    employment_status: Optional[str] = Field(None, description="Filter by employment status (exact match): TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED")
    role_code: Optional[str] = Field(None, description="Filter by role code: 'superadmin', 'ceo', 'hr', 'manager', 'employee'. If not provided, returns all employees.")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, joining_date, job_title, department, employment_status")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(BaseModel):
    """Request schema for creating an employee.
    
    Based on F5_api_spec.md Section 5.2 - POST /api/v1/company/employees request body.
    """

    user_id: UUID = Field(..., description="User ID to link employee to (RFC 4122 UUID v4 format, must exist, must not already have employee record)")
    joining_date: date = Field(..., description="Employment start date (ISO 8601 date format YYYY-MM-DD, cannot be future date, immutable after creation)")
    employment_status: str = Field(..., description="Current HR state (ENUM: TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED, case-sensitive)")
    job_title: Optional[str] = Field(None, max_length=255, description="Professional title (max 255 characters, alphanumeric and spaces only)")
    department: Optional[str] = Field(None, description="Functional department (ENUM: FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT, case-sensitive)")
    employment_type: Optional[str] = Field(None, description="Nature of employment (ENUM: FULL_TIME, PART_TIME, CONTRACT, FREELANCE, TEMPORARY, case-sensitive)")
    employment_level: Optional[str] = Field(None, description="Seniority level (ENUM: INTERN, JUNIOR, MID, SENIOR, LEAD, MANAGER, case-sensitive)")
    work_email: Optional[EmailStr] = Field(None, max_length=254, description="Official email (RFC 5322 format, max 254 characters, case-insensitive unique within company)")
    gender: Optional[str] = Field(None, description="Gender identity (ENUM: MALE, FEMALE, OTHER, case-sensitive)")
    marital_status: Optional[str] = Field(None, description="Marital status (ENUM: SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED, case-sensitive)")
    blood_group: Optional[str] = Field(None, description="Blood group (ENUM: A+, A-, B+, B-, AB+, AB-, O+, O-, case-sensitive)")
    nationality: Optional[str] = Field(None, max_length=100, description="Nationality (max 100 characters, free text)")
    address: Optional[str] = Field(None, max_length=500, description="Residential address (max 500 characters)")
    city: Optional[str] = Field(None, max_length=100, description="City (max 100 characters, API-based dropdown)")
    state: Optional[str] = Field(None, max_length=100, description="State (max 100 characters, dependent dropdown)")
    country: Optional[str] = Field(None, max_length=100, description="Country (max 100 characters, API-based dropdown)")
    document_type: Optional[str] = Field(None, description="Identity document type (ENUM: AADHAAR, PAN, DL, VOTER_ID, PASSPORT, case-sensitive)")
    document_number: Optional[str] = Field(None, max_length=50, description="Identity document reference (max 50 characters, restricted visibility)")
    separation_initiated_date: Optional[date] = Field(None, description="Resignation/termination date (ISO 8601 date format YYYY-MM-DD, required if employment_status is RESIGNED or TERMINATED)")
    separation_reason: Optional[str] = Field(None, max_length=500, description="Reason for resignation/termination (max 500 characters, required if employment_status is RESIGNED or TERMINATED)")
    last_working_day: Optional[date] = Field(None, description="Final working day (ISO 8601 date format YYYY-MM-DD, valid for resignation & termination)")
    notice_period_days: Optional[int] = Field(None, ge=0, le=365, description="Notice period duration (integer, min 0, max 365, 0 allowed for immediate termination)")
    is_active: Optional[bool] = Field(True, description="System access state (defaults to true)")

    model_config = ConfigDict(from_attributes=True)


class EmployeeUpdate(BaseModel):
    """Request schema for updating an employee.
    
    Based on F5_api_spec.md Section 5.4 - PATCH /api/v1/company/employees/{employee_id} request body.
    """

    employment_status: Optional[str] = Field(None, description="Current HR state (ENUM: TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED, case-sensitive)")
    job_title: Optional[str] = Field(None, max_length=255, description="Professional title (max 255 characters, alphanumeric and spaces only)")
    department: Optional[str] = Field(None, description="Functional department (ENUM: FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT, case-sensitive)")
    employment_type: Optional[str] = Field(None, description="Nature of employment (ENUM: FULL_TIME, PART_TIME, CONTRACT, FREELANCE, TEMPORARY, case-sensitive)")
    employment_level: Optional[str] = Field(None, description="Seniority level (ENUM: INTERN, JUNIOR, MID, SENIOR, LEAD, MANAGER, case-sensitive)")
    work_email: Optional[EmailStr] = Field(None, max_length=254, description="Official email (RFC 5322 format, max 254 characters, case-insensitive unique within company)")
    gender: Optional[str] = Field(None, description="Gender identity (ENUM: MALE, FEMALE, OTHER, case-sensitive)")
    marital_status: Optional[str] = Field(None, description="Marital status (ENUM: SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED, case-sensitive)")
    blood_group: Optional[str] = Field(None, description="Blood group (ENUM: A+, A-, B+, B-, AB+, AB-, O+, O-, case-sensitive)")
    nationality: Optional[str] = Field(None, max_length=100, description="Nationality (max 100 characters, free text)")
    address: Optional[str] = Field(None, max_length=500, description="Residential address (max 500 characters)")
    city: Optional[str] = Field(None, max_length=100, description="City (max 100 characters, API-based dropdown)")
    state: Optional[str] = Field(None, max_length=100, description="State (max 100 characters, dependent dropdown)")
    country: Optional[str] = Field(None, max_length=100, description="Country (max 100 characters, API-based dropdown)")
    document_type: Optional[str] = Field(None, description="Identity document type (ENUM: AADHAAR, PAN, DL, VOTER_ID, PASSPORT, case-sensitive)")
    document_number: Optional[str] = Field(None, max_length=50, description="Identity document reference (max 50 characters, restricted visibility)")
    separation_initiated_date: Optional[date] = Field(None, description="Resignation/termination date (ISO 8601 date format YYYY-MM-DD, required if employment_status is RESIGNED or TERMINATED)")
    separation_reason: Optional[str] = Field(None, max_length=500, description="Reason for resignation/termination (max 500 characters, required if employment_status is RESIGNED or TERMINATED)")
    last_working_day: Optional[date] = Field(None, description="Final working day (ISO 8601 date format YYYY-MM-DD, valid for resignation & termination)")
    notice_period_days: Optional[int] = Field(None, ge=0, le=365, description="Notice period duration (integer, min 0, max 365, 0 allowed for immediate termination)")
    is_active: Optional[bool] = Field(None, description="System access state (setting to false deactivates employee, setting to true reactivates employee)")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RESPONSE SCHEMAS (Output Structure)
# ============================================================================

class UserSummary(BaseModel):
    """User summary schema for nested user information in employee responses.
    
    Based on F5_api_spec.md Section 11.3 - UserSummary nested in EmployeeSummary.
    """

    user_id: UUID = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")

    model_config = ConfigDict(from_attributes=True)


class EmployeeSummary(BaseModel):
    """Summary schema for employee list responses.
    
    Based on F5_api_spec.md Section 11.3 - EmployeeSummary for list responses.
    """

    employee_id: UUID = Field(..., description="Unique employee identifier")
    user: UserSummary = Field(..., description="Nested user object with user_id, email, first_name, last_name")
    job_title: Optional[str] = Field(None, description="Professional title")
    department: Optional[str] = Field(None, description="Functional department")
    employment_status: str = Field(..., description="Current HR state")
    is_active: bool = Field(..., description="System access state")
    joining_date: date = Field(..., description="Employment start date")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class EmployeeDetail(BaseModel):
    """Detail schema for employee detail responses.
    
    Based on F5_api_spec.md Section 11.4 - EmployeeDetail for detail responses.
    """

    employee_id: UUID = Field(..., description="Unique employee identifier")
    user_id: UUID = Field(..., description="Linked User ID")
    company_id: UUID = Field(..., description="Owning company ID")
    joining_date: date = Field(..., description="Employment start date")
    employment_status: str = Field(..., description="Current HR state")
    job_title: Optional[str] = Field(None, description="Professional title")
    department: Optional[str] = Field(None, description="Functional department")
    employment_type: Optional[str] = Field(None, description="Nature of employment")
    employment_level: Optional[str] = Field(None, description="Seniority level")
    work_email: Optional[str] = Field(None, description="Official email")
    gender: Optional[str] = Field(None, description="Gender identity")
    marital_status: Optional[str] = Field(None, description="Marital status")
    blood_group: Optional[str] = Field(None, description="Blood group")
    nationality: Optional[str] = Field(None, description="Nationality")
    address: Optional[str] = Field(None, description="Residential address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    country: Optional[str] = Field(None, description="Country")
    document_type: Optional[str] = Field(None, description="Identity document type")
    document_number: Optional[str] = Field(None, description="Identity document reference")
    separation_initiated_date: Optional[date] = Field(None, description="Resignation/termination date")
    separation_reason: Optional[str] = Field(None, description="Reason for resignation/termination")
    last_working_day: Optional[date] = Field(None, description="Final working day")
    notice_period_days: Optional[int] = Field(None, description="Notice period duration")
    is_active: bool = Field(..., description="System access state")
    is_deleted: bool = Field(..., description="Soft delete flag")
    user: UserSummary = Field(..., description="Nested user object")
    can_edit_employee: bool = Field(..., description="True if authenticated user can edit employee (CEO/HR only)")
    can_deactivate: bool = Field(..., description="True if authenticated user can deactivate employee (CEO/HR only, cannot deactivate own employee)")
    can_soft_delete: bool = Field(..., description="True if authenticated user can soft delete employee (CEO/HR only, cannot soft delete own employee)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[UUID] = Field(None, description="User ID who created the employee")
    updated_by: Optional[UUID] = Field(None, description="User ID who last updated the employee")
    
    # ETag metadata (set by service, used by router for headers)
    etag: Optional[str] = Field(None, exclude=True, description="ETag for cache validation")
    last_modified: Optional[datetime] = Field(None, exclude=True, description="Last modified timestamp")

    model_config = ConfigDict(from_attributes=True)


class EmployeePaginatedResponse(BaseModel):
    """Pagination wrapper for employee list responses.
    
    Based on F5_api_spec.md Section 11.5 - EmployeePaginatedResponse.
    """
    
    items: List[EmployeeSummary] = Field(..., description="List of employee summary items")
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    next_page: Optional[str] = Field(None, description="Full relative URL for next page or null")
    prev_page: Optional[str] = Field(None, description="Full relative URL for previous page or null")

    model_config = ConfigDict(from_attributes=True)
