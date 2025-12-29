"""Domain-specific exceptions for Attendance Management module.

Based on F10_api_spec.md Section 7 - Error Handling.
All exceptions extend base exception classes from src.exceptions.
"""

from uuid import UUID
from src.exceptions import (
    NotFoundError,
    ConflictError,
    ForbiddenError,
    ValidationError,
)


class AttendanceNotFound(NotFoundError):
    """404 Not Found - Attendance record not found."""
    
    def __init__(self, attendance_id: str | None = None, message: str | None = None):
        if message:
            super().__init__(resource="Attendance", resource_id=attendance_id)
            self.message = message
        else:
            super().__init__(resource="Attendance", resource_id=attendance_id)


class EmployeeNotFound(NotFoundError):
    """404 Not Found - Employee not found or not in user's scope."""
    
    def __init__(self, employee_id: str | None = None):
        super().__init__(resource="Employee", resource_id=employee_id)


class AlreadyCheckedOut(ConflictError):
    """409 Conflict - Employee already checked out for today."""
    
    def __init__(self):
        super().__init__(
            message="Cannot check in. You have already checked out for today.",
            error_code="ALREADY_CHECKED_OUT",
            details=[{
                "field": "attendance",
                "issue": "You have already checked out for today. Check-in is only allowed once per day."
            }]
        )


class SuperAdminNoAccess(ForbiddenError):
    """403 Forbidden - SuperAdmin explicitly excluded from attendance endpoints."""
    
    def __init__(self):
        super().__init__(
            message="SuperAdmin cannot access attendance data. Attendance endpoints are restricted to company-scoped users.",
            error_code="INSUFFICIENT_PERMISSIONS",
            details=[{
                "field": "role",
                "issue": "SuperAdmin is explicitly excluded from all attendance endpoints"
            }]
        )


class DeactivatedEmployeeNoAccess(ForbiddenError):
    """403 Forbidden - Deactivated employee cannot access attendance features."""
    
    def __init__(self):
        super().__init__(
            message="Deactivated employees cannot access attendance features. Please contact your administrator.",
            error_code="INSUFFICIENT_PERMISSIONS",
            details=[{
                "field": "employee",
                "issue": "Deactivated employees cannot view attendance history or perform check-in/check-out actions"
            }]
        )


class EmployeeNoAccess(ForbiddenError):
    """403 Forbidden - Employee cannot access company attendance endpoints."""
    
    def __init__(self):
        super().__init__(
            message="Employees cannot access company attendance endpoints. This endpoint is restricted to Managers, HR, and CEO.",
            error_code="INSUFFICIENT_PERMISSIONS",
            details=[{
                "field": "role",
                "issue": "Employees cannot access company attendance endpoints"
            }]
        )


class ManagerScopeViolation(ForbiddenError):
    """403 Forbidden - Manager attempting to access employee outside their scope."""
    
    def __init__(self, employee_id: UUID | None = None):
        employee_id_str = str(employee_id) if employee_id else "unknown"
        super().__init__(
            message=f"Manager cannot access attendance for employee {employee_id_str}. Access is restricted to employees in your scope.",
            error_code="INSUFFICIENT_PERMISSIONS",
            details=[{
                "field": "employee_id",
                "issue": f"Manager cannot access employee {employee_id_str} outside their scope"
            }]
        )


class CheckOutWithoutCheckIn(ValidationError):
    """422 Unprocessable Entity - Attempting check-out without prior check-in."""
    
    def __init__(self):
        super().__init__(
            message="Cannot check out. You must check in first.",
            error_code="BUSINESS_RULE_FAILED",
            details=[{
                "field": "attendance",
                "issue": "No attendance record found for today. Please check in first."
            }]
        )


class FutureDateCheckIn(ValidationError):
    """422 Unprocessable Entity - Attempting check-in on future date."""
    
    def __init__(self):
        super().__init__(
            message="Cannot check in on a future date. Check-in is only allowed for today's date.",
            error_code="BUSINESS_RULE_FAILED",
            details=[{
                "field": "attendance_date",
                "issue": "Check-in is not allowed on future dates"
            }]
        )


class FutureDateCheckOut(ValidationError):
    """422 Unprocessable Entity - Attempting check-out on future date."""
    
    def __init__(self):
        super().__init__(
            message="Cannot check out on a future date. Check-out is only allowed for today's date.",
            error_code="BUSINESS_RULE_FAILED",
            details=[{
                "field": "attendance_date",
                "issue": "Check-out is not allowed on future dates"
            }]
        )
