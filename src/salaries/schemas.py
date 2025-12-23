"""Pydantic schemas for Salary Management module.

Based on F6_api_spec.md - Salary Management (F-006).
Request schemas define input validation, Response schemas define output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from src.salaries.constants import (
    CURRENCY_INR,
    CURRENCY_USD,
    CURRENCY_EUR,
    CURRENCY_GBP,
    CURRENCY_AUD,
    CURRENCY_CAD,
    FREQUENCY_MONTHLY,
    FREQUENCY_BI_WEEKLY,
    FREQUENCY_WEEKLY,
    BANK_HDFC,
    BANK_ICICI,
    BANK_SBI,
    BANK_AXIS,
    BANK_KOTAK,
    BANK_PNB,
    BANK_BOB,
    PAYMENT_METHOD_BANK_TRANSFER,
    PAYMENT_METHOD_UPI,
    PAYMENT_METHOD_CHEQUE,
    PAYMENT_METHOD_CASH,
)


# ============================================================================
# Request Schemas (Input Validation)
# ============================================================================

class SalaryCreate(BaseModel):
    """Request schema for creating/updating salary details."""
    
    amount: Decimal = Field(
        ...,
        description="Monthly gross salary amount",
        gt=0,
        le=Decimal("999999999.99"),
        decimal_places=2,
    )
    currency: str = Field(
        ...,
        description="Salary currency",
        pattern="^(INR|USD|EUR|GBP|AUD|CAD)$",
    )
    payment_frequency: str = Field(
        ...,
        description="Payment cadence",
        pattern="^(MONTHLY|BI_WEEKLY|WEEKLY)$",
    )
    effective_from: date = Field(
        ...,
        description="Start date of salary configuration (inclusive), must be today or future date",
    )
    effective_to: Optional[date] = Field(
        None,
        description="End date of salary configuration (inclusive), must be >= effective_from. NULL for active/ongoing salary.",
    )
    
    @field_validator("effective_from")
    @classmethod
    def validate_effective_from(cls, v: date) -> date:
        """Validate effective_from >= today.
        
        Based on F6_api_spec.md Section 4.3.2 - effective_from must be today or future date.
        """
        if v < date.today():
            raise ValueError("Effective from date must be today or future date.")
        return v
    
    @field_validator("effective_to", mode="before")
    @classmethod
    def validate_effective_to_before(cls, v) -> Optional[date]:
        """Handle empty string by converting to None for active salary."""
        # Handle empty string - convert to None for active salary
        if v == "" or v is None:
            return None
        return v
    
    @field_validator("effective_to")
    @classmethod
    def validate_effective_to(cls, v: Optional[date], info) -> Optional[date]:
        """Validate effective_to >= effective_from (if provided)."""
        if v is not None and "effective_from" in info.data and v < info.data["effective_from"]:
            raise ValueError("Effective to date must be greater than or equal to effective from date (inclusive dates allowed).")
        return v
    
    model_config = ConfigDict(from_attributes=True)


class BankInfoUpsert(BaseModel):
    """Request schema for upserting bank information."""
    
    bank_name: str = Field(
        ...,
        description="Bank identifier",
        pattern="^(HDFC|ICICI|SBI|AXIS|KOTAK|PNB|BOB)$",
    )
    branch: str = Field(
        ...,
        description="Bank branch name",
        min_length=1,
        max_length=255,
    )
    account_number: str = Field(
        ...,
        description="Bank account number",
        min_length=8,
        max_length=20,
        pattern="^[A-Za-z0-9]+$",
    )
    ifsc_code: str = Field(
        ...,
        description="Bank IFSC code",
        min_length=11,
        max_length=11,
        pattern="^[A-Z]{4}0[A-Z0-9]{6}$",
    )
    
    model_config = ConfigDict(from_attributes=True)


class SalaryPaymentRun(BaseModel):
    """Request schema for executing salary payment.
    
    Used by HR and automated payroll jobs.
    """
    
    employee_id: UUID = Field(
        ...,
        description="Employee UUID",
    )
    month: int = Field(
        ...,
        description="Salary month",
        ge=1,
        le=12,
    )
    year: int = Field(
        ...,
        description="Salary year",
        ge=2000,
        le=9999,
    )
    payment_method: str = Field(
        ...,
        description="Mode of payment",
        pattern="^(BANK_TRANSFER|UPI|CHEQUE|CASH)$",
    )
    
    model_config = ConfigDict(from_attributes=True)


class SalaryPaymentCreate(BaseModel):
    """Request schema for creating salary payment (legacy - kept for backward compatibility)."""
    
    month: int = Field(
        ...,
        description="Salary month",
        ge=1,
        le=12,
    )
    year: int = Field(
        ...,
        description="Salary year",
        ge=2000,
        le=9999,
    )
    payment_method: str = Field(
        ...,
        description="Mode of payment",
        pattern="^(BANK_TRANSFER|UPI|CHEQUE|CASH)$",
    )
    paid_on: datetime = Field(
        ...,
        description="Payment execution date (UTC)",
    )
    
    model_config = ConfigDict(from_attributes=True)


class SalaryPaymentUpdate(BaseModel):
    """Request schema for updating salary payment.
    
    Only payment_method and paid_on can be updated.
    Amount, currency, month, and year are immutable.
    """
    
    payment_method: str = Field(
        ...,
        description="Mode of payment",
        pattern="^(BANK_TRANSFER|UPI|CHEQUE|CASH)$",
    )
    paid_on: datetime = Field(
        ...,
        description="Payment execution date (UTC)",
    )
    
    model_config = ConfigDict(from_attributes=True)


class SalaryOverviewQuery(BaseModel):
    """Query schema for salary overview endpoint."""
    
    include_history: bool = Field(True, description="Include salary history records")
    include_payments: bool = Field(True, description="Include recent payment summary")
    payment_limit: int = Field(10, ge=1, le=100, description="Number of recent payments to include (1-100)")
    
    model_config = ConfigDict(from_attributes=True)


class SalaryPaymentListQuery(BaseModel):
    """Query schema for listing salary payments with pagination and filtering."""
    
    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    year: Optional[int] = Field(None, ge=2000, le=9999, description="Filter by year (YYYY format)")
    month: Optional[int] = Field(None, ge=1, le=12, description="Filter by month (1-12)")
    payment_method: Optional[str] = Field(None, description="Filter by payment method: BANK_TRANSFER, UPI, CHEQUE, CASH")
    sort_by: str = Field("paid_on", description="Sort field: paid_on, month, year, amount, created_at")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas (Output Structure)
# ============================================================================

class EmployeeBasicInfo(BaseModel):
    """Basic employee information for salary overview."""
    
    id: UUID
    first_name: str
    last_name: str
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class SalaryDetailsResponse(BaseModel):
    """Response schema for salary details."""
    
    id: UUID
    employee_id: UUID
    amount: Decimal
    currency: str
    payment_frequency: str
    effective_from: date
    effective_to: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None  # User name
    updated_by: Optional[str] = None  # User name
    
    model_config = ConfigDict(from_attributes=True)


class BankInfoResponse(BaseModel):
    """Response schema for bank information (with masked sensitive fields)."""
    
    id: UUID
    employee_id: UUID
    bank_name: str
    branch: str
    account_number: str  # Masked in service layer
    ifsc_code: str  # Masked in service layer
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None  # User name
    updated_by: Optional[str] = None  # User name
    
    model_config = ConfigDict(from_attributes=True)


class SalaryHistoryResponse(BaseModel):
    """Response schema for salary history."""
    
    id: UUID
    previous_amount: Optional[Decimal] = None
    new_amount: Decimal
    effective_from: date
    changed_by: Optional[str] = None  # User name
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SalaryPaymentResponse(BaseModel):
    """Response schema for salary payment."""
    
    id: UUID
    employee_id: UUID
    amount: Decimal
    currency: str
    month: int
    year: int
    paid_on: datetime
    payment_method: str
    slip_url: Optional[str] = None
    payable_amount: Decimal  # Derived field (same as amount)
    payment_period_label: str  # Derived field (e.g., "March 2024")
    created_at: datetime
    created_by: Optional[str] = None  # User name
    
    model_config = ConfigDict(from_attributes=True)


class SalaryPaymentListItem(BaseModel):
    """Response schema for salary payment list item (without derived fields)."""
    
    id: UUID
    employee_id: UUID
    amount: Decimal
    currency: str
    month: int
    year: int
    paid_on: datetime
    payment_method: str
    slip_url: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None  # User name
    
    model_config = ConfigDict(from_attributes=True)


class SalaryDetailsOnlyResponse(BaseModel):
    """Response schema for salary details only (no extra info)."""
    
    current_salary: Optional[SalaryDetailsResponse] = None
    salary_history: list[SalaryHistoryResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class SalaryOverviewResponse(BaseModel):
    """Response schema for salary overview."""
    
    employee: EmployeeBasicInfo
    current_salary: Optional[SalaryDetailsResponse] = None
    bank_info: Optional[BankInfoResponse] = None
    salary_history: list[SalaryHistoryResponse] = []
    recent_payments: list[SalaryPaymentListItem] = []
    current_salary_amount: Optional[Decimal] = None  # Derived from current_salary
    current_salary_currency: Optional[str] = None  # Derived from current_salary
    has_active_salary: bool
    masked_account_number: Optional[str] = None  # Derived from bank_info
    
    model_config = ConfigDict(from_attributes=True)


# Paginated response for salary payments
from src.pagination import PagedCollection

SalaryPaymentPaginatedResponse = PagedCollection[SalaryPaymentListItem]
