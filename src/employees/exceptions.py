"""Domain-specific exceptions for Employee Management module.

Based on F5_api_spec.md - Employee Management (F-005).
All exceptions extend base exception classes from src.exceptions.
"""

from uuid import UUID
from src.exceptions import (
    NotFoundError,
    ConflictError,
    ValidationError,
    ForbiddenError,
    PreconditionRequiredError,
    PreconditionFailedError,
)
from src.employees.constants import (
    ERROR_EMPLOYEE_NOT_FOUND,
    ERROR_USER_NOT_FOUND,
    ERROR_DUPLICATE_EMPLOYEE,
    ERROR_DUPLICATE_WORK_EMAIL,
    ERROR_SEPARATION_FIELDS_REQUIRED,
    ERROR_CANNOT_SOFT_DELETE_OWN_EMPLOYEE,
    ERROR_CANNOT_DEACTIVATE_OWN_EMPLOYEE,
    ERROR_USER_DIFFERENT_COMPANY,
    ERROR_INSUFFICIENT_PERMISSIONS,
    ERROR_SUPERADMIN_NO_ACCESS,
    ERROR_CODE_EMPLOYEE_NOT_FOUND,
    ERROR_CODE_USER_NOT_FOUND,
    ERROR_CODE_DUPLICATE_EMPLOYEE,
    ERROR_CODE_DUPLICATE_WORK_EMAIL,
    ERROR_CODE_BUSINESS_RULE_FAILED,
    ERROR_CODE_INSUFFICIENT_PERMISSIONS,
)


class EmployeeNotFound(NotFoundError):
    """Employee not found exception."""

    def __init__(self, employee_id: str):
        super().__init__(resource="Employee", resource_id=employee_id)


class UserNotFound(NotFoundError):
    """User not found exception."""

    def __init__(self, user_id: str):
        super().__init__(resource="User", resource_id=user_id)


class DuplicateEmployee(ConflictError):
    """User already has an employee record (one-to-one constraint violation)."""

    def __init__(self, user_id: str):
        super().__init__(
            message=f"Employee creation failed: {ERROR_DUPLICATE_EMPLOYEE}",
            error_code=ERROR_CODE_DUPLICATE_EMPLOYEE,
            details=[{"field": "user_id", "issue": ERROR_DUPLICATE_EMPLOYEE}],
        )


class DuplicateWorkEmail(ConflictError):
    """WorkEmail already exists in company (case-insensitive)."""

    def __init__(self, work_email: str):
        super().__init__(
            message=f"WorkEmail '{work_email}' already exists in company (case-insensitive).",
            error_code=ERROR_CODE_DUPLICATE_WORK_EMAIL,
            details=[{"field": "work_email", "issue": ERROR_DUPLICATE_WORK_EMAIL}],
        )


class SeparationFieldsRequired(ValidationError):
    """Separation fields are required when employment_status is RESIGNED or TERMINATED."""

    def __init__(self):
        super().__init__(
            message=f"Business rule violation: {ERROR_SEPARATION_FIELDS_REQUIRED}",
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[
                {
                    "field": "separation_initiated_date",
                    "issue": ERROR_SEPARATION_FIELDS_REQUIRED,
                }
            ],
        )


class CannotSoftDeleteOwnEmployee(ValidationError):
    """Cannot soft delete own employee record."""

    def __init__(self):
        super().__init__(
            message=f"Business rule violation: {ERROR_CANNOT_SOFT_DELETE_OWN_EMPLOYEE}",
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[
                {
                    "field": "employee_id",
                    "issue": ERROR_CANNOT_SOFT_DELETE_OWN_EMPLOYEE,
                }
            ],
        )


class CannotDeactivateOwnEmployee(ValidationError):
    """Cannot deactivate own employee record."""

    def __init__(self):
        super().__init__(
            message=f"Business rule violation: {ERROR_CANNOT_DEACTIVATE_OWN_EMPLOYEE}",
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[
                {
                    "field": "is_active",
                    "issue": ERROR_CANNOT_DEACTIVATE_OWN_EMPLOYEE,
                }
            ],
        )


class UserDifferentCompany(ValidationError):
    """User belongs to a different company."""

    def __init__(self, user_id: str):
        super().__init__(
            message=f"Business rule violation: {ERROR_USER_DIFFERENT_COMPANY}",
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[
                {
                    "field": "user_id",
                    "issue": f"User {user_id} belongs to a different company",
                }
            ],
        )


class InsufficientPermissions(ForbiddenError):
    """Insufficient permissions to access employee endpoints."""

    def __init__(self, message: str = ERROR_INSUFFICIENT_PERMISSIONS):
        super().__init__(
            message=message,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[{"field": "role", "issue": message}],
        )


class SuperAdminNoAccess(ForbiddenError):
    """SuperAdmin is explicitly excluded from employee endpoints."""

    def __init__(self):
        super().__init__(
            message=ERROR_SUPERADMIN_NO_ACCESS,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[{"field": "role", "issue": ERROR_SUPERADMIN_NO_ACCESS}],
        )


class PreconditionRequired(PreconditionRequiredError):
    """If-Match header is required for update/delete operations."""

    def __init__(self):
        super().__init__(
            message="If-Match header is required for update operations",
            error_code="PRECONDITION_REQUIRED",
            details=[
                {
                    "field": "If-Match",
                    "issue": "If-Match header is required for update operations",
                }
            ],
        )


class PreconditionFailed(PreconditionFailedError):
    """ETag mismatch - resource was modified since retrieval."""

    def __init__(self):
        super().__init__(
            message="Resource version mismatch. The resource was modified by another user.",
            error_code="PRECONDITION_FAILED",
            details=[
                {
                    "field": "etag",
                    "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry.",
                }
            ],
        )
