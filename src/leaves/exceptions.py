from uuid import UUID
from src.exceptions import NotFoundError, ConflictError, ValidationError, BadRequestError


class LeaveRequestNotFound(NotFoundError):
    """Raised when a leave request is not found."""
    def __init__(self, leave_id: str):
        super().__init__(
            resource="LeaveRequest",
            resource_id=leave_id
        )


class OverlappingLeaveRequest(ConflictError):
    """Raised when leave request overlaps with existing leave."""
    def __init__(self, employee_id: UUID, start_date: str, end_date: str):
        super().__init__(
            message=f"Leave request overlaps with existing leave for employee {employee_id}",
            error_code="OVERLAPPING_LEAVE_REQUEST",
            details=[{
                "field": "date_range",
                "issue": f"Leave request overlaps with existing leave request from {start_date} to {end_date}. Overlapping leave requests for the same employee are not allowed."
            }]
        )


class InvalidWorkingDay(BadRequestError):
    """Raised when leave request includes weekend or holiday."""
    def __init__(self, invalid_dates: list[str]):
        super().__init__(
            message="Leave request includes non-working days",
            error_code="INVALID_WORKING_DAY",
            details=[{
                "field": "dates",
                "issue": f"The following dates are not working days: {', '.join(invalid_dates)}. Leave requests cannot include weekends or holidays."
            }]
        )


class InvalidApprover(ValidationError):
    """Raised when approver ID is invalid."""
    def __init__(self, approver_type: str, approver_id: UUID):
        super().__init__(
            message=f"Invalid {approver_type} approver",
            error_code="INVALID_APPROVER",
            details=[{
                "field": f"{approver_type}_approver_id",
                "issue": f"{approver_type.capitalize()} approver does not exist, is not in the same company, or does not have {approver_type.capitalize()} role."
            }]
        )


class BusinessRuleFailed(ValidationError):
    """Raised when business rules are violated."""
    def __init__(self, message: str, field: str, issue: str):
        super().__init__(
            message=message,
            error_code="BUSINESS_RULE_FAILED",
            details=[{
                "field": field,
                "issue": issue
            }]
        )


class InsufficientPermissionsForLeaveAction(BadRequestError):
    """Raised when user doesn't have permission to perform leave action."""
    def __init__(self, action: str, reason: str):
        super().__init__(
            message=f"Insufficient permissions to {action} leave request",
            error_code="INSUFFICIENT_PERMISSIONS",
            details=[{
                "field": "action",
                "issue": reason
            }]
        )


class LeaveActionNotAllowed(BadRequestError):
    """Raised when leave action is not allowed in current state."""
    def __init__(self, action: str, current_status: str):
        super().__init__(
            message=f"Cannot {action} leave request in current state",
            error_code="BUSINESS_RULE_FAILED",
            details=[{
                "field": "action",
                "issue": f"Cannot {action} leave request. Current status is {current_status}. Please check the workflow rules."
            }]
        )


class LeaveAlreadyProcessed(BadRequestError):
    """Raised when trying to modify already processed leave."""
    def __init__(self, leave_id: UUID, status: str):
        super().__init__(
            message="Leave request has already been processed",
            error_code="BUSINESS_RULE_FAILED",
            details=[{
                "field": "leave_id",
                "issue": f"Leave request {leave_id} has already been {status.lower()}. Further actions are not allowed."
            }]
        )

