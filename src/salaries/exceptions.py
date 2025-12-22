"""Domain-specific exceptions for Salary Management module.

Based on F6_api_spec.md - Salary Management (F-006).
All exceptions extend base exception classes from src.exceptions.
"""

from uuid import UUID
from src.exceptions import (
    NotFoundError,
    ConflictError,
    ValidationError,
    ForbiddenError,
    BadRequestError,
    PreconditionRequiredError,
    PreconditionFailedError,
    InternalServerError,
)
from src.salaries.constants import (
    ERROR_EMPLOYEE_NOT_FOUND,
    ERROR_SALARY_DETAILS_NOT_FOUND,
    ERROR_BANK_INFO_NOT_FOUND,
    ERROR_SALARY_PAYMENT_NOT_FOUND,
    ERROR_SALARY_SLIP_NOT_FOUND,
    ERROR_OVERLAPPING_SALARY_PERIOD,
    ERROR_DUPLICATE_SALARY_PAYMENT,
    ERROR_NO_ACTIVE_SALARY,
    ERROR_INSUFFICIENT_PERMISSIONS,
    ERROR_PRECONDITION_REQUIRED,
    ERROR_PRECONDITION_FAILED,
    ERROR_ASYNC_OPERATION_FAILED,
    ERROR_CODE_EMPLOYEE_NOT_FOUND,
    ERROR_CODE_SALARY_DETAILS_NOT_FOUND,
    ERROR_CODE_BANK_INFO_NOT_FOUND,
    ERROR_CODE_SALARY_PAYMENT_NOT_FOUND,
    ERROR_CODE_SALARY_SLIP_NOT_FOUND,
    ERROR_CODE_OVERLAPPING_SALARY_PERIOD,
    ERROR_CODE_DUPLICATE_SALARY_PAYMENT,
    ERROR_CODE_BUSINESS_RULE_FAILED,
    ERROR_CODE_INSUFFICIENT_PERMISSIONS,
    ERROR_CODE_PRECONDITION_REQUIRED,
    ERROR_CODE_PRECONDITION_FAILED,
    ERROR_CODE_ASYNC_OPERATION_FAILED,
)


class EmployeeNotFound(NotFoundError):
    """Employee not found exception."""

    def __init__(self, employee_id: str):
        super().__init__(resource="Employee", resource_id=employee_id)


class SalaryDetailsNotFound(NotFoundError):
    """Salary details not found exception."""

    def __init__(self, salary_details_id: str):
        super().__init__(resource="SalaryDetails", resource_id=salary_details_id)


class BankInfoNotFound(NotFoundError):
    """Bank information not found exception."""

    def __init__(self, bank_info_id: str):
        super().__init__(resource="BankInfo", resource_id=bank_info_id)


class SalaryPaymentNotFound(NotFoundError):
    """Salary payment not found exception."""

    def __init__(self, payment_id: str):
        super().__init__(resource="SalaryPayment", resource_id=payment_id)


class SalarySlipNotFound(NotFoundError):
    """Salary slip not found exception."""

    def __init__(self, payment_id: str):
        super().__init__(
            message=f"Salary slip not found. The slip may not have been generated yet.",
            error_code=ERROR_CODE_SALARY_SLIP_NOT_FOUND,
            details=[{"field": "slip", "issue": "Salary slip not found. The slip may not have been generated yet."}],
        )


class OverlappingSalaryPeriod(ConflictError):
    """Overlapping salary period exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_OVERLAPPING_SALARY_PERIOD,
            error_code=ERROR_CODE_OVERLAPPING_SALARY_PERIOD,
            details=[{"field": "effective_from", "issue": ERROR_OVERLAPPING_SALARY_PERIOD}],
        )


class DuplicateSalaryPayment(ConflictError):
    """Duplicate salary payment exception."""

    def __init__(self, month: int, year: int):
        super().__init__(
            message=ERROR_DUPLICATE_SALARY_PAYMENT,
            error_code=ERROR_CODE_DUPLICATE_SALARY_PAYMENT,
            details=[{"field": "payment", "issue": f"Salary payment already exists for employee, month {month}, and year {year}."}],
        )


class NoActiveSalary(ValidationError):
    """No active salary configuration exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_NO_ACTIVE_SALARY,
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[{"field": "salary_details", "issue": ERROR_NO_ACTIVE_SALARY}],
        )


class InsufficientPermissions(ForbiddenError):
    """Insufficient permissions exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_INSUFFICIENT_PERMISSIONS,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[{"field": "access", "issue": "Employees and Managers cannot access salary data."}],
        )


class PreconditionRequired(PreconditionRequiredError):
    """Precondition required exception (If-Match header missing)."""

    def __init__(self):
        super().__init__(
            message=ERROR_PRECONDITION_REQUIRED,
            error_code=ERROR_CODE_PRECONDITION_REQUIRED,
            details=[{"field": "etag", "issue": "If-Match header required but missing (when updating existing resource)."}],
        )


class PreconditionFailed(PreconditionFailedError):
    """Precondition failed exception (ETag mismatch)."""

    def __init__(self):
        super().__init__(
            message=ERROR_PRECONDITION_FAILED,
            error_code=ERROR_CODE_PRECONDITION_FAILED,
            details=[{"field": "etag", "issue": ERROR_PRECONDITION_FAILED}],
        )


class AsyncOperationFailed(InternalServerError):
    """Async operation failed exception (salary slip generation/email)."""

    def __init__(self):
        super().__init__(
            message=ERROR_ASYNC_OPERATION_FAILED,
            error_code=ERROR_CODE_ASYNC_OPERATION_FAILED,
            details=[{"field": "salary_slip", "issue": "Salary slip generation or email delivery failed. Payment record was created, but slip generation needs to be retried."}],
        )
