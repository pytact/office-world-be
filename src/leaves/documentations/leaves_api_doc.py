# API documentation for Leave endpoints
from typing import ClassVar

class LeaveApiDocs:
    """API documentation for Leave endpoints"""

    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list leave requests with pagination, filtering, and sorting",
        "description": "Retrieves a paginated list of leave requests based on user role. Employees see only their own leave requests. Managers see leave requests assigned to them for approval. HR and CEO see all company leave requests. Supports filtering by status, date range, employee, and pending_for_me flag. Includes pagination with navigation URLs. Requires JWT authentication."
    }

    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new leave request",
        "description": "Creates a new leave request for the authenticated user. Requires manager_approver_id and hr_approver_id (both must be in the same company). Validates overlapping leave requests, non-working days (weekends/holidays), and employee active status. Calculates number_of_days from date range and day_type. Sets initial manager_status to PENDING_MANAGER and hr_status to PENDING_HR. Triggers notification to manager approver and HR approver. Only active employees can create leave requests."
    }

    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get leave request details",
        "description": "Retrieves detailed leave request information. Employees can view only their own leave requests. Managers can view leave requests assigned to them. HR and CEO can view all company leave requests. Includes both manager_status and hr_status. Supports ETag-based cache validation with If-None-Match header. Requires JWT authentication."
    }

    action: ClassVar[dict] = {
        "summary": "Purpose of this API is to approve, reject, or cancel a leave request",
        "description": "Performs approve, reject, or cancel action on a leave request. Approve: User must be the assigned approver at the current workflow stage. Reject: User must be the assigned approver at the current workflow stage, rejection_reason is mandatory. Cancel: Only the applicant can cancel, and only if status is pending. Requires If-Match header for concurrency control. Triggers notifications on approve/reject/cancel. Updates workflow status and timestamps accordingly."
    }

