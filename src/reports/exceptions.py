"""Custom exceptions for Reports & Analytics module.

Based on F12A_api_spec.md and response_error_handling.md patterns.
"""

from src.exceptions import NotFoundError, ForbiddenError, ValidationError, BadRequestError, GoneError
from src.reports.constants import (
    ERROR_CODE_REPORT_TYPE_NOT_FOUND,
    ERROR_CODE_INSUFFICIENT_PERMISSIONS,
    ERROR_CODE_VALIDATION_ERROR,
    ERROR_CODE_BUSINESS_RULE_FAILED,
    ERROR_CODE_INVALID_REQUEST,
    ERROR_CODE_EXPORT_NOT_FOUND,
    ERROR_CODE_EXPORT_EXPIRED,
    ERROR_CODE_EXPORT_NOT_READY,
    ERROR_CODE_ASYNC_OPERATION_FAILED,
    ERROR_REPORT_TYPE_NOT_FOUND,
    ERROR_INSUFFICIENT_PERMISSIONS,
    ERROR_FILTER_VALIDATION_FAILED,
    ERROR_EMPLOYEE_FILTER_RESTRICTED,
    ERROR_CROSS_COMPANY_FILTER,
    ERROR_DATE_RANGE_INVALID,
    ERROR_INVALID_STATUS,
    ERROR_EXPORT_NOT_FOUND,
    ERROR_EXPORT_EXPIRED,
    ERROR_EXPORT_NOT_READY,
    ERROR_EXPORT_NOT_COMPLETED,
    ERROR_EXPORT_ACCESS_DENIED,
    ERROR_ASYNC_OPERATION_FAILED,
)


class ReportTypeNotFound(NotFoundError):
    """404 Not Found - Report type not found."""

    def __init__(self, report_type: str):
        super().__init__(
            resource="Report type",
            resource_id=report_type,
        )


class InsufficientPermissions(ForbiddenError):
    """403 Forbidden - User role cannot access this report type."""

    def __init__(self, report_type: str, role: str):
        message = f"Your role ({role}) does not have access to {report_type} reports"
        details = [
            {
                "field": "report_type",
                "issue": message,
            }
        ]
        super().__init__(
            message=ERROR_INSUFFICIENT_PERMISSIONS,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=details,
        )


class FilterValidationError(ValidationError):
    """422 Unprocessable Entity - Filter validation failed."""

    def __init__(self, field: str, issue: str):
        details = [
            {
                "field": field,
                "issue": issue,
            }
        ]
        super().__init__(
            message=ERROR_FILTER_VALIDATION_FAILED,
            error_code=ERROR_CODE_VALIDATION_ERROR,
            details=details,
        )


class BusinessRuleFailed(ValidationError):
    """422 Unprocessable Entity - Business rule violation."""

    def __init__(self, field: str, issue: str):
        details = [
            {
                "field": field,
                "issue": issue,
            }
        ]
        super().__init__(
            message=issue,
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=details,
        )


class InvalidReportType(BadRequestError):
    """400 Bad Request - Invalid report type format."""

    def __init__(self, report_type: str):
        details = [
            {
                "field": "report_type",
                "issue": f"Invalid report type: {report_type}",
            }
        ]
        super().__init__(
            message=ERROR_REPORT_TYPE_NOT_FOUND,
            error_code=ERROR_CODE_INVALID_REQUEST,
            details=details,
        )


class DateRangeValidationError(FilterValidationError):
    """422 Unprocessable Entity - Date range validation failed."""

    def __init__(self):
        super().__init__(
            field="end_date",
            issue=ERROR_DATE_RANGE_INVALID,
        )


class EmployeeFilterRestricted(BusinessRuleFailed):
    """422 Unprocessable Entity - Employee trying to filter other employees' data."""

    def __init__(self):
        super().__init__(
            field="employee_id",
            issue=ERROR_EMPLOYEE_FILTER_RESTRICTED,
        )


class CrossCompanyFilterError(BusinessRuleFailed):
    """422 Unprocessable Entity - Cross-company filtering attempted."""

    def __init__(self):
        super().__init__(
            field="employee_id",
            issue=ERROR_CROSS_COMPANY_FILTER,
        )


class InvalidStatusValue(FilterValidationError):
    """422 Unprocessable Entity - Invalid status value for report type."""

    def __init__(self, status: str, report_type: str):
        super().__init__(
            field="status",
            issue=f"Invalid status '{status}' for report type '{report_type}'",
        )


# ============================================================================
# Export Exceptions (F12B_api_spec.md)
# ============================================================================

class ExportNotFound(NotFoundError):
    """404 Not Found - Export not found."""

    def __init__(self, export_id: str):
        super().__init__(
            resource="Export",
            resource_id=export_id,
        )


class ExportExpired(GoneError):
    """410 Gone - Export has expired (24 hours TTL exceeded)."""

    def __init__(self, export_id: str):
        details = [
            {
                "field": "export_id",
                "issue": ERROR_EXPORT_EXPIRED,
            }
        ]
        super().__init__(
            message=ERROR_EXPORT_EXPIRED,
            error_code=ERROR_CODE_EXPORT_EXPIRED,
            details=details,
        )


class ExportNotReady(BusinessRuleFailed):
    """422 Unprocessable Entity - Export is not in COMPLETED status."""

    def __init__(self, status: str):
        super().__init__(
            field="status",
            issue=f"Export is not ready for download. Status: {status}",
        )


class ExportAccessDenied(ForbiddenError):
    """403 Forbidden - User does not have access to this export."""

    def __init__(self, export_id: str):
        details = [
            {
                "field": "export_id",
                "issue": ERROR_EXPORT_ACCESS_DENIED,
            }
        ]
        super().__init__(
            message=ERROR_EXPORT_ACCESS_DENIED,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=details,
        )


class AsyncOperationFailed(BadRequestError):
    """500 Internal Server Error - Async export generation failed."""

    def __init__(self, error_message: str):
        details = [
            {
                "field": "export",
                "issue": error_message,
            }
        ]
        super().__init__(
            message=ERROR_ASYNC_OPERATION_FAILED,
            error_code=ERROR_CODE_ASYNC_OPERATION_FAILED,
            details=details,
        )

