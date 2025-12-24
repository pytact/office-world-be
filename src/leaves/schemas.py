from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum


# Enums from spec
class LeaveType(str, Enum):
    CASUAL = "CASUAL"
    SICK = "SICK"
    PAID = "PAID"
    UNPAID = "UNPAID"


class DayType(str, Enum):
    FULL_DAY = "FULL_DAY"
    FIRST_HALF = "FIRST_HALF"
    SECOND_HALF = "SECOND_HALF"


class ManagerStatus(str, Enum):
    PENDING_MANAGER = "PENDING_MANAGER"
    APPROVED_MANAGER = "APPROVED_MANAGER"
    REJECTED_MANAGER = "REJECTED_MANAGER"
    CANCELLED = "CANCELLED"


class HrStatus(str, Enum):
    PENDING_HR = "PENDING_HR"
    APPROVED_HR = "APPROVED_HR"
    REJECTED_HR = "REJECTED_HR"
    CANCELLED = "CANCELLED"


class ActionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    CANCEL = "cancel"


# Request Schemas
class LeaveCreate(BaseModel):
    """Schema for creating a new leave request."""
    leave_type: LeaveType = Field(..., description="Type of leave")
    start_date: date = Field(..., description="Leave start date (inclusive, ISO 8601 date format: YYYY-MM-DD)")
    end_date: date = Field(..., description="Leave end date (inclusive, ISO 8601 date format: YYYY-MM-DD)")
    day_type: DayType = Field(..., description="Full or half day")
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for leave")
    manager_approver_id: UUID = Field(..., description="Manager approver ID")
    hr_approver_id: UUID = Field(..., description="HR approver ID")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: date, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be greater than or equal to start_date')
        return v

    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v: date):
        from datetime import date as dt_date
        if v < dt_date.today():
            raise ValueError('start_date must be today or in the future')
        return v

    model_config = ConfigDict(from_attributes=True)


class LeaveListQuery(BaseModel):
    """Query schema for listing leave requests with pagination and filtering."""
    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    status: Optional[str] = Field(None, description="Filter by manager_status or hr_status: PENDING_MANAGER, APPROVED_MANAGER, REJECTED_MANAGER, PENDING_HR, APPROVED_HR, REJECTED_HR, CANCELLED")
    start_date: Optional[date] = Field(None, description="Filter by start_date (ISO 8601 date format: YYYY-MM-DD)")
    end_date: Optional[date] = Field(None, description="Filter by end_date (ISO 8601 date format: YYYY-MM-DD)")
    employee_id: Optional[UUID] = Field(None, description="Filter by employee_id (UUID format, HR/CEO only)")
    pending_for_me: Optional[bool] = Field(None, description="Filter to show only leave requests awaiting current user's approval (true/false)")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, start_date, end_date")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v: str):
        allowed_fields = ["created_at", "updated_at", "start_date", "end_date"]
        if v not in allowed_fields:
            raise ValueError(f'sort_by must be one of: {", ".join(allowed_fields)}')
        return v

    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v: str):
        if v not in ["asc", "desc"]:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v

    model_config = ConfigDict(from_attributes=True)


class LeaveActionRequest(BaseModel):
    """Schema for performing actions on leave requests."""
    action: ActionType = Field(..., description="Action to perform")
    rejection_reason: Optional[str] = Field(None, min_length=10, max_length=500, description="Reason for rejection (required if action is 'reject')")

    @field_validator('rejection_reason')
    @classmethod
    def validate_rejection_reason(cls, v: Optional[str], values):
        if 'action' in values and values['action'] == ActionType.REJECT and not v:
            raise ValueError('rejection_reason is mandatory when action is "reject"')
        return v

    model_config = ConfigDict(from_attributes=True)


# Response Schemas
class LeaveSummary(BaseModel):
    """Summary schema for leave request list items."""
    id: UUID
    employee_id: UUID
    employee: dict = Field(..., description="Employee basic info")
    leave_type: LeaveType
    start_date: date
    end_date: date
    day_type: DayType
    number_of_days: Decimal
    manager_status: ManagerStatus
    hr_status: HrStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaveRead(BaseModel):
    """Detailed schema for leave request responses."""
    id: UUID
    employee_id: UUID
    employee: dict = Field(..., description="Employee basic info")
    company_id: UUID
    leave_type: LeaveType
    start_date: date
    end_date: date
    day_type: DayType
    number_of_days: Decimal
    reason: str
    manager_status: ManagerStatus
    manager_approver_id: UUID
    manager_approved_at: Optional[datetime] = None
    manager_rejection_reason: Optional[str] = None
    hr_status: HrStatus
    hr_approver_id: UUID
    hr_approved_at: Optional[datetime] = None
    hr_rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeavePaginatedResponse(BaseModel):
    """Paginated response for leave request lists."""
    items: List[LeaveSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    next_page: Optional[str] = None
    prev_page: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

