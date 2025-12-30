"""Domain-specific exceptions for Audit Logging & Activity History module.

Based on F11_api_spec.md - Audit Logging & Activity History (F-011).
All exceptions extend base exception classes from src.exceptions.
"""

from src.exceptions import (
    NotFoundError,
    ForbiddenError,
    BadRequestError,
)
from src.audits.constants import (
    ERROR_AUDIT_LOG_NOT_FOUND,
    ERROR_INSUFFICIENT_PERMISSIONS,
    ERROR_EMPLOYEE_NO_ACCESS,
    ERROR_SUPERADMIN_BLOCKED,
    ERROR_MANAGER_TABLE_RESTRICTION,
    ERROR_INVALID_DATE_FORMAT,
    ERROR_INVALID_SORT_FIELD,
    ERROR_INVALID_DATE_RANGE,
    ERROR_CODE_AUDIT_LOG_NOT_FOUND,
    ERROR_CODE_INSUFFICIENT_PERMISSIONS,
    ERROR_CODE_VALIDATION_FAILED,
)


class AuditLogNotFound(NotFoundError):
    """Audit log not found exception."""

    def __init__(self, audit_log_id: str):
        super().__init__(resource="Audit log", resource_id=audit_log_id)


class InsufficientPermissions(ForbiddenError):
    """Insufficient permissions to access audit logs."""

    def __init__(self, message: str = ERROR_INSUFFICIENT_PERMISSIONS):
        super().__init__(
            message=message,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[{"field": "role", "issue": message}],
        )


class EmployeeNoAccess(InsufficientPermissions):
    """Employee role does not have access to audit logs."""

    def __init__(self):
        super().__init__(message=ERROR_EMPLOYEE_NO_ACCESS)


class SuperAdminBlocked(InsufficientPermissions):
    """SuperAdmin role is blocked from accessing audit logs."""

    def __init__(self):
        super().__init__(message=ERROR_SUPERADMIN_BLOCKED)


class ManagerTableRestriction(InsufficientPermissions):
    """Manager role can only access audit logs for specific tables."""

    def __init__(self, table_name: str):
        message = f"{ERROR_MANAGER_TABLE_RESTRICTION}. This audit log is for table '{table_name}'."
        super().__init__(message=message)
        self.details = [{"field": "table_name", "issue": message}]


class InvalidDateFormat(BadRequestError):
    """Invalid date format."""

    def __init__(self, field: str):
        super().__init__(
            message=f"{ERROR_INVALID_DATE_FORMAT}",
            error_code=ERROR_CODE_VALIDATION_FAILED,
            details=[{"field": field, "issue": ERROR_INVALID_DATE_FORMAT}],
        )


class InvalidSortField(BadRequestError):
    """Invalid sort field."""

    def __init__(self, sort_field: str):
        super().__init__(
            message=f"{ERROR_INVALID_SORT_FIELD}",
            error_code=ERROR_CODE_VALIDATION_FAILED,
            details=[{"field": "sort_by", "issue": ERROR_INVALID_SORT_FIELD}],
        )


class InvalidDateRange(BadRequestError):
    """Invalid date range - start date must be less than or equal to end date."""

    def __init__(self):
        super().__init__(
            message=ERROR_INVALID_DATE_RANGE,
            error_code=ERROR_CODE_VALIDATION_FAILED,
            details=[{"field": "date_range", "issue": ERROR_INVALID_DATE_RANGE}],
        )
