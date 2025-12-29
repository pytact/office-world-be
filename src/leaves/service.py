from uuid import UUID
from typing import List, Optional, Tuple
from datetime import datetime
from fastapi import Response
from fastapi.responses import Response as FastAPIResponse
from fastapi import status

from sqlalchemy.ext.asyncio import AsyncSession

from src.leaves.models import LeaveRequest
from src.leaves.schemas import (
    LeaveCreate, LeaveRead, LeaveListQuery, LeavePaginatedResponse,
    LeaveActionRequest, ActionType, ManagerStatus, HrStatus
)
from src.leaves.repository import LeaveRepository
from src.leaves.exceptions import (
    LeaveRequestNotFound, OverlappingLeaveRequest, InvalidWorkingDay,
    InvalidApprover, BusinessRuleFailed, InsufficientPermissionsForLeaveAction,
    LeaveActionNotAllowed, LeaveAlreadyProcessed
)
from src.leaves.constants import (
    STATUS_PENDING_MANAGER, STATUS_PENDING_HR, STATUS_APPROVED_MANAGER,
    STATUS_APPROVED_HR, STATUS_REJECTED_MANAGER, STATUS_REJECTED_HR,
    STATUS_CANCELLED, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
)
from src.leaves.utils import (
    calculate_days, validate_working_days, generate_etag, format_last_modified,
    get_workflow_stage_from_status, can_user_approve_at_stage, validate_leave_overlap
)
from src.celery_worker import (
    send_leave_created_notification, send_leave_approved_notification,
    send_leave_rejected_notification, send_leave_cancelled_notification
)


class LeaveService:
    """Service layer for leave request business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = LeaveRepository(session)

    async def create_leave_request(
        self,
        leave_data: LeaveCreate,
        employee_id: UUID,
        company_id: UUID
    ) -> LeaveRead:
        """Create a new leave request with full validation."""
        # Validate working days
        invalid_dates = validate_working_days(leave_data.start_date, leave_data.end_date)
        if invalid_dates:
            raise InvalidWorkingDay(invalid_dates)

        # Check for overlapping leaves
        existing_leaves = await self.repository.get_by_employee_and_date_range(
            employee_id,
            leave_data.start_date.isoformat(),
            leave_data.end_date.isoformat()
        )

        # Extract date ranges for overlap checking
        existing_ranges = [(leave.start_date, leave.end_date) for leave in existing_leaves]
        if validate_leave_overlap(existing_ranges, leave_data.start_date, leave_data.end_date):
            # Find the overlapping leave for error message
            overlapping_leave = existing_leaves[0] if existing_leaves else None
            if overlapping_leave:
                raise OverlappingLeaveRequest(
                    employee_id,
                    overlapping_leave.start_date.isoformat(),
                    overlapping_leave.end_date.isoformat()
                )

        # Validate approvers exist and have correct roles
        await self._validate_approvers(leave_data.manager_approver_id, leave_data.hr_approver_id, company_id)

        # Calculate number of days
        number_of_days = calculate_days(leave_data.start_date, leave_data.end_date, leave_data.day_type)

        # Create leave request
        leave_request = LeaveRequest(
            employee_id=employee_id,
            company_id=company_id,
            leave_type=leave_data.leave_type,
            start_date=leave_data.start_date,
            end_date=leave_data.end_date,
            day_type=leave_data.day_type,
            number_of_days=number_of_days,
            reason=leave_data.reason,
            manager_approver_id=leave_data.manager_approver_id,
            hr_approver_id=leave_data.hr_approver_id,
            manager_status=STATUS_PENDING_MANAGER,
            hr_status=STATUS_PENDING_HR
        )

        created_leave = await self.repository.create(leave_request)

        # Trigger notification to manager approver
        # Use created_leave which has eagerly loaded relationships
        if created_leave.manager_approver and created_leave.manager_approver.user:
            send_leave_created_notification.delay(
                manager_email=created_leave.manager_approver.user.email,
                manager_name=f"{created_leave.manager_approver.user.first_name} {created_leave.manager_approver.user.last_name}".strip(),
                manager_user_id=str(created_leave.manager_approver.user_id),
                applicant_name=f"{created_leave.employee.user.first_name} {created_leave.employee.user.last_name}".strip() if created_leave.employee.user else "Employee",
                leave_type=created_leave.leave_type,
                start_date=created_leave.start_date.isoformat(),
                end_date=created_leave.end_date.isoformat(),
                company_id=str(created_leave.company_id),
                company_name=created_leave.company.name if created_leave.company else "Company",
                leave_id=str(created_leave.id)
            )

        # Trigger notification to HR approver (informational - they'll need to approve after manager)
        if created_leave.hr_approver and created_leave.hr_approver.user:
            send_leave_created_notification.delay(
                manager_email=created_leave.hr_approver.user.email,
                manager_name=f"{created_leave.hr_approver.user.first_name} {created_leave.hr_approver.user.last_name}".strip(),
                manager_user_id=str(created_leave.hr_approver.user_id),
                applicant_name=f"{created_leave.employee.user.first_name} {created_leave.employee.user.last_name}".strip() if created_leave.employee.user else "Employee",
                leave_type=created_leave.leave_type,
                start_date=created_leave.start_date.isoformat(),
                end_date=created_leave.end_date.isoformat(),
                company_id=str(created_leave.company_id),
                company_name=created_leave.company.name if created_leave.company else "Company",
                leave_id=str(created_leave.id)
            )

        # Return response schema
        return await self._leave_to_response_schema(created_leave)

    async def get_leave_by_id(
        self,
        leave_id: UUID,
        company_id: UUID = None,
        user_id: UUID = None,
        employee_id: Optional[UUID] = None,
        user_role: str = None,
        if_none_match: str = None
    ) -> LeaveRead | FastAPIResponse:
        """Get leave request by ID with ETag support and access control."""
        leave_request = await self.repository.get_by_id(leave_id)

        if not leave_request:
            raise LeaveRequestNotFound(str(leave_id))

        # Check access permissions
        await self._check_leave_access(leave_request, company_id, user_id, user_role, employee_id)

        # Generate ETag and check If-None-Match
        etag = generate_etag(leave_request.updated_at)

        if if_none_match and if_none_match == etag:
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)

        # Return leave data with ETag metadata
        result = await self._leave_to_response_schema(leave_request)
        result._etag = etag
        result._last_modified = leave_request.updated_at
        return result

    async def list_leaves(
        self,
        query: LeaveListQuery,
        company_id: UUID = None,
        employee_id: Optional[UUID] = None,
        user_role: str = None
    ) -> LeavePaginatedResponse:
        """List leave requests with pagination, filtering, and role-based access."""
        # Validate pagination parameters
        page_size = min(query.page_size, MAX_PAGE_SIZE)

        # Prepare filters
        filters = {}
        if query.status:
            filters["status"] = query.status
        if query.start_date:
            filters["start_date"] = query.start_date
        if query.end_date:
            filters["end_date"] = query.end_date
        if query.employee_id:
            filters["employee_id"] = query.employee_id
        if query.pending_for_me:
            filters["pending_for_me"] = query.pending_for_me

        # Get data from repository
        items, total = await self.repository.list_with_pagination(
            page=query.page,
            page_size=page_size,
            filters=filters,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            company_id=company_id,
            employee_id=employee_id,
            user_role=user_role
        )

        # Convert to response schemas
        leave_summaries = []
        for item in items:
            summary = {
                "id": item.id,
                "employee_id": item.employee_id,
                "employee": {
                    "id": item.employee.id if item.employee else None,
                    "first_name": item.employee.user.first_name if item.employee and item.employee.user else None,
                    "last_name": item.employee.user.last_name if item.employee and item.employee.user else None,
                } if item.employee else None,
                "leave_type": item.leave_type,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "day_type": item.day_type,
                "number_of_days": item.number_of_days,
                "manager_status": item.manager_status,
                "hr_status": item.hr_status,
                "created_at": item.created_at,
                "updated_at": item.updated_at
            }
            leave_summaries.append(summary)

        # Calculate pagination info
        total_pages = (total + page_size - 1) // page_size  # Ceiling division

        # Generate next/prev page URLs (simplified, would need full URL construction in real implementation)
        next_page = f"?page={query.page + 1}&page_size={page_size}" if query.page < total_pages else None
        prev_page = f"?page={query.page - 1}&page_size={page_size}" if query.page > 1 else None

        return LeavePaginatedResponse(
            items=leave_summaries,
            total=total,
            page=query.page,
            page_size=page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page
        )

    async def perform_leave_action(
        self,
        leave_id: UUID,
        action_data: LeaveActionRequest,
        user_id: UUID,
        employee_id: Optional[UUID],
        user_role: str,
        company_id: UUID = None,
        if_match: str = None
    ) -> LeaveRead:
        """Perform approve/reject/cancel action on leave request."""
        leave_request = await self.repository.get_by_id(leave_id)

        if not leave_request:
            raise LeaveRequestNotFound(str(leave_id))

        # Check company access
        if company_id and leave_request.company_id != company_id:
            raise LeaveRequestNotFound(str(leave_id))

        # Validate ETag for concurrency control
        current_etag = generate_etag(leave_request.updated_at)
        if if_match and if_match != current_etag:
            raise BusinessRuleFailed(
                "Resource version mismatch. The leave request was modified by another user.",
                "etag",
                "Resource has been modified since retrieval. Please fetch the latest version and retry."
            )

        # Get employee for notifications (for approve/reject actions)
        from src.employees.repository import EmployeeRepository
        employee_repo = EmployeeRepository(self.session)
        user = None
        if employee_id:
            user = await employee_repo.get_by_id(employee_id)
        elif user_id:
            # Fallback: try to get employee by user_id
            user = await employee_repo.get_by_user_id(user_id, company_id)

        # Perform action based on type
        if action_data.action == ActionType.APPROVE:
            if not user:
                raise InvalidApprover("user", user_id)
            await self._approve_leave(leave_request, user, user_role)
        elif action_data.action == ActionType.REJECT:
            if not user:
                raise InvalidApprover("user", user_id)
            await self._reject_leave(leave_request, action_data.rejection_reason, user, user_role)
        elif action_data.action == ActionType.CANCEL:
            if not employee_id:
                raise BusinessRuleFailed(
                    "Employee record not found",
                    "employee_id",
                    "You must be an employee to cancel a leave request."
                )
            await self._cancel_leave(leave_request, employee_id)

        # Update and return
        updated_leave = await self.repository.update(leave_request)
        result = await self._leave_to_response_schema(updated_leave)
        result._etag = generate_etag(updated_leave.updated_at)
        return result

    async def _approve_leave(self, leave_request: LeaveRequest, user, user_role: str) -> None:
        """Approve leave request with workflow logic."""
        current_stage = get_workflow_stage_from_status(leave_request.manager_status, leave_request.hr_status)

        # Check permissions
        if not can_user_approve_at_stage(user_role, current_stage, leave_request.employee.role if hasattr(leave_request.employee, 'role') else None):
            raise InsufficientPermissionsForLeaveAction(
                "approve",
                f"You are a {user_role} and cannot approve at the {current_stage} stage."
            )

        # Check if user is the assigned approver
        if current_stage == "manager" and leave_request.manager_approver_id != user.id:
            raise InsufficientPermissionsForLeaveAction(
                "approve",
                "You are not assigned as the manager approver for this leave request."
            )
        elif current_stage == "hr" and leave_request.hr_approver_id != user.id:
            raise InsufficientPermissionsForLeaveAction(
                "approve",
                "You are not assigned as the HR approver for this leave request."
            )

        # Check if already processed
        if leave_request.manager_status in [STATUS_REJECTED_MANAGER, STATUS_CANCELLED] or \
           leave_request.hr_status in [STATUS_REJECTED_HR, STATUS_CANCELLED]:
            raise LeaveAlreadyProcessed(str(leave_request.id), f"{leave_request.manager_status or leave_request.hr_status}")

        # Update status based on current stage
        now = datetime.utcnow()

        if current_stage == "manager":
            leave_request.manager_status = STATUS_APPROVED_MANAGER
            leave_request.manager_approved_at = now
            # HR status remains PENDING_HR

            # Trigger notifications to HR approver and applicant
            if leave_request.hr_approver and leave_request.hr_approver.user:
                send_leave_approved_notification.delay(
                    recipient_email=leave_request.hr_approver.user.email,
                    recipient_name=f"{leave_request.hr_approver.user.first_name} {leave_request.hr_approver.user.last_name}".strip(),
                    recipient_user_id=str(leave_request.hr_approver.user_id),
                    applicant_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip() if leave_request.employee.user else "Employee",
                    leave_type=leave_request.leave_type,
                    start_date=leave_request.start_date.isoformat(),
                    end_date=leave_request.end_date.isoformat(),
                    approved_by=f"{user.user.first_name} {user.user.last_name}".strip() if user.user else "Unknown",
                    company_id=str(leave_request.company_id),
                    company_name=leave_request.company.name if leave_request.company else "Company",
                    approval_stage="Manager",
                    leave_id=str(leave_request.id),
                    notification_type="leave_manager_approval"
                )

            # Also notify applicant
            if leave_request.employee and leave_request.employee.user:
                send_leave_approved_notification.delay(
                    recipient_email=leave_request.employee.user.email,
                    recipient_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip(),
                    recipient_user_id=str(leave_request.employee.user_id),
                    applicant_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip(),
                    leave_type=leave_request.leave_type,
                    start_date=leave_request.start_date.isoformat(),
                    end_date=leave_request.end_date.isoformat(),
                    approved_by=f"{user.user.first_name} {user.user.last_name}".strip() if user.user else "Unknown",
                    company_id=str(leave_request.company_id),
                    company_name=leave_request.company.name if leave_request.company else "Company",
                    approval_stage="Manager",
                    leave_id=str(leave_request.id),
                    notification_type="leave_approval"
                )
        elif current_stage == "hr":
            leave_request.hr_status = STATUS_APPROVED_HR
            leave_request.hr_approved_at = now

            # Trigger notification to applicant
            if leave_request.employee and leave_request.employee.user:
                send_leave_approved_notification.delay(
                    recipient_email=leave_request.employee.user.email,
                    recipient_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip(),
                    recipient_user_id=str(leave_request.employee.user_id),
                    applicant_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip(),
                    leave_type=leave_request.leave_type,
                    start_date=leave_request.start_date.isoformat(),
                    end_date=leave_request.end_date.isoformat(),
                    approved_by=f"{user.user.first_name} {user.user.last_name}".strip() if user.user else "Unknown",
                    company_id=str(leave_request.company_id),
                    company_name=leave_request.company.name if leave_request.company else "Company",
                    approval_stage="HR",
                    leave_id=str(leave_request.id),
                    notification_type="leave_approval"
                )
        elif current_stage == "ceo":
            # CEO approval for HR leaves (no specific CEO approver field)
            leave_request.hr_status = STATUS_APPROVED_HR
            leave_request.hr_approved_at = now

            # Trigger notification to applicant
            if leave_request.employee and leave_request.employee.user:
                send_leave_approved_notification.delay(
                    recipient_email=leave_request.employee.user.email,
                    recipient_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip(),
                    recipient_user_id=str(leave_request.employee.user_id),
                    applicant_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip(),
                    leave_type=leave_request.leave_type,
                    start_date=leave_request.start_date.isoformat(),
                    end_date=leave_request.end_date.isoformat(),
                    approved_by=f"{user.user.first_name} {user.user.last_name}".strip() if user.user else "Unknown",
                    company_id=str(leave_request.company_id),
                    company_name=leave_request.company.name if leave_request.company else "Company",
                    approval_stage="CEO",
                    leave_id=str(leave_request.id),
                    notification_type="leave_approval"
                )

    async def _reject_leave(self, leave_request: LeaveRequest, rejection_reason: str, user, user_role: str) -> None:
        """Reject leave request."""
        current_stage = get_workflow_stage_from_status(leave_request.manager_status, leave_request.hr_status)

        # Check permissions
        if not can_user_approve_at_stage(user_role, current_stage, leave_request.employee.role if hasattr(leave_request.employee, 'role') else None):
            raise InsufficientPermissionsForLeaveAction(
                "reject",
                f"You are a {user_role} and cannot reject at the {current_stage} stage."
            )

        # Check if user is the assigned approver
        if current_stage == "manager" and leave_request.manager_approver_id != user.id:
            raise InsufficientPermissionsForLeaveAction(
                "reject",
                "You are not assigned as the manager approver for this leave request."
            )
        elif current_stage == "hr" and leave_request.hr_approver_id != user.id:
            raise InsufficientPermissionsForLeaveAction(
                "reject",
                "You are not assigned as the HR approver for this leave request."
            )

        # Check if already processed
        if leave_request.manager_status in [STATUS_REJECTED_MANAGER, STATUS_CANCELLED] or \
           leave_request.hr_status in [STATUS_REJECTED_HR, STATUS_CANCELLED]:
            raise LeaveAlreadyProcessed(str(leave_request.id), f"{leave_request.manager_status or leave_request.hr_status}")

        # Update status
        now = datetime.utcnow()

        if current_stage == "manager":
            leave_request.manager_status = STATUS_REJECTED_MANAGER
            leave_request.manager_rejection_reason = rejection_reason

            # Trigger notification to applicant
            if leave_request.employee and leave_request.employee.user:
                send_leave_rejected_notification.delay(
                    applicant_email=leave_request.employee.user.email,
                    applicant_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip(),
                    applicant_user_id=str(leave_request.employee.user_id),
                    leave_type=leave_request.leave_type,
                    start_date=leave_request.start_date.isoformat(),
                    end_date=leave_request.end_date.isoformat(),
                    rejected_by=f"{user.user.first_name} {user.user.last_name}".strip() if user.user else "Unknown",
                    rejection_reason=rejection_reason,
                    company_id=str(leave_request.company_id),
                    company_name=leave_request.company.name if leave_request.company else "Company",
                    rejection_stage="Manager",
                    leave_id=str(leave_request.id)
                )
        elif current_stage == "hr":
            leave_request.hr_status = STATUS_REJECTED_HR
            leave_request.hr_rejection_reason = rejection_reason

            # Trigger notification to applicant
            if leave_request.employee and leave_request.employee.user:
                send_leave_rejected_notification.delay(
                    applicant_email=leave_request.employee.user.email,
                    applicant_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip(),
                    applicant_user_id=str(leave_request.employee.user_id),
                    leave_type=leave_request.leave_type,
                    start_date=leave_request.start_date.isoformat(),
                    end_date=leave_request.end_date.isoformat(),
                    rejected_by=f"{user.user.first_name} {user.user.last_name}".strip() if user.user else "Unknown",
                    rejection_reason=rejection_reason,
                    company_id=str(leave_request.company_id),
                    company_name=leave_request.company.name if leave_request.company else "Company",
                    rejection_stage="HR",
                    leave_id=str(leave_request.id)
                )
        elif current_stage == "ceo":
            leave_request.hr_status = STATUS_REJECTED_HR
            leave_request.hr_rejection_reason = rejection_reason

            # Trigger notification to applicant
            if leave_request.employee and leave_request.employee.user:
                send_leave_rejected_notification.delay(
                    applicant_email=leave_request.employee.user.email,
                    applicant_name=f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip(),
                    applicant_user_id=str(leave_request.employee.user_id),
                    leave_type=leave_request.leave_type,
                    start_date=leave_request.start_date.isoformat(),
                    end_date=leave_request.end_date.isoformat(),
                    rejected_by=f"{user.user.first_name} {user.user.last_name}".strip() if user.user else "Unknown",
                    rejection_reason=rejection_reason,
                    company_id=str(leave_request.company_id),
                    company_name=leave_request.company.name if leave_request.company else "Company",
                    rejection_stage="CEO",
                    leave_id=str(leave_request.id)
                )

    async def _cancel_leave(self, leave_request: LeaveRequest, employee_id: UUID) -> None:
        """Cancel leave request (only by applicant)."""
        # Only applicant can cancel
        if leave_request.employee_id != employee_id:
            raise InsufficientPermissionsForLeaveAction(
                "cancel",
                "Only the leave applicant can cancel their leave request."
            )

        # Can only cancel if still pending
        if leave_request.manager_status not in [STATUS_PENDING_MANAGER] or \
           leave_request.hr_status not in [STATUS_PENDING_HR]:
            raise LeaveActionNotAllowed("cancel", f"{leave_request.manager_status}/{leave_request.hr_status}")

        # Set both statuses to cancelled
        leave_request.manager_status = STATUS_CANCELLED
        leave_request.hr_status = STATUS_CANCELLED

        # Trigger notifications to manager and HR approvers
        applicant_name = f"{leave_request.employee.user.first_name} {leave_request.employee.user.last_name}".strip() if leave_request.employee and leave_request.employee.user else "Employee"
        
        # Notify manager approver
        if leave_request.manager_approver and leave_request.manager_approver.user:
            send_leave_cancelled_notification.delay(
                recipient_email=leave_request.manager_approver.user.email,
                recipient_name=f"{leave_request.manager_approver.user.first_name} {leave_request.manager_approver.user.last_name}".strip(),
                recipient_user_id=str(leave_request.manager_approver.user_id),
                applicant_name=applicant_name,
                leave_type=leave_request.leave_type,
                start_date=leave_request.start_date.isoformat(),
                end_date=leave_request.end_date.isoformat(),
                company_id=str(leave_request.company_id),
                company_name=leave_request.company.name if leave_request.company else "Company",
                leave_id=str(leave_request.id)
            )

        # Notify HR approver
        if leave_request.hr_approver and leave_request.hr_approver.user:
            send_leave_cancelled_notification.delay(
                recipient_email=leave_request.hr_approver.user.email,
                recipient_name=f"{leave_request.hr_approver.user.first_name} {leave_request.hr_approver.user.last_name}".strip(),
                recipient_user_id=str(leave_request.hr_approver.user_id),
                applicant_name=applicant_name,
                leave_type=leave_request.leave_type,
                start_date=leave_request.start_date.isoformat(),
                end_date=leave_request.end_date.isoformat(),
                company_id=str(leave_request.company_id),
                company_name=leave_request.company.name if leave_request.company else "Company",
                leave_id=str(leave_request.id)
            )

    async def _validate_approvers(self, manager_approver_id: UUID, hr_approver_id: UUID, company_id: UUID) -> None:
        """Validate that approvers exist and have correct roles."""
        # Import here to avoid circular imports
        from src.employees.repository import EmployeeRepository
        from src.permissions.models import UserRoleAssignment, Role
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select

        employee_repo = EmployeeRepository(self.session)

        # Check manager approver
        manager = await employee_repo.get_by_id(manager_approver_id)
        if not manager or manager.company_id != company_id:
            raise InvalidApprover("manager", manager_approver_id)
        
        # Check manager role through UserRoleAssignment
        manager_role_result = await self.session.execute(
            select(UserRoleAssignment)
            .join(Role)
            .where(
                UserRoleAssignment.user_id == manager.user_id,
                UserRoleAssignment.company_id == company_id,
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.deleted_at.is_(None),
                Role.code == "manager"
            )
        )
        manager_role = manager_role_result.scalar_one_or_none()
        if not manager_role:
            raise InvalidApprover("manager", manager_approver_id)

        # Check HR approver
        hr = await employee_repo.get_by_id(hr_approver_id)
        if not hr or hr.company_id != company_id:
            raise InvalidApprover("hr", hr_approver_id)
        
        # Check HR role through UserRoleAssignment
        hr_role_result = await self.session.execute(
            select(UserRoleAssignment)
            .join(Role)
            .where(
                UserRoleAssignment.user_id == hr.user_id,
                UserRoleAssignment.company_id == company_id,
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.deleted_at.is_(None),
                Role.code == "hr"
            )
        )
        hr_role = hr_role_result.scalar_one_or_none()
        if not hr_role:
            raise InvalidApprover("hr", hr_approver_id)

    async def _check_leave_access(self, leave_request: LeaveRequest, company_id: UUID, user_id: UUID, user_role: str, employee_id: Optional[UUID] = None) -> None:
        """Check if user has access to view this leave request."""
        # Company scoping
        if company_id and leave_request.company_id != company_id:
            raise LeaveRequestNotFound(str(leave_request.id))

        # Role-based access
        if user_role == "employee":
            # Can only see own leaves - need employee_id to compare
            if not employee_id:
                # Try to get employee_id from user_id
                from src.employees.repository import EmployeeRepository
                employee_repo = EmployeeRepository(self.session)
                employee = await employee_repo.get_by_user_id(user_id, company_id)
                if employee:
                    employee_id = employee.id
                else:
                    raise LeaveRequestNotFound(str(leave_request.id))
            
            if leave_request.employee_id != employee_id:
                raise LeaveRequestNotFound(str(leave_request.id))
        elif user_role == "manager":
            # Can see own leaves or leaves assigned for approval
            if not employee_id:
                # Try to get employee_id from user_id
                from src.employees.repository import EmployeeRepository
                employee_repo = EmployeeRepository(self.session)
                employee = await employee_repo.get_by_user_id(user_id, company_id)
                if employee:
                    employee_id = employee.id
            
            if employee_id:
                if leave_request.employee_id != employee_id and leave_request.manager_approver_id != employee_id:
                    raise LeaveRequestNotFound(str(leave_request.id))
            else:
                # If no employee_id, check manager_approver_id using user_id (fallback)
                # This shouldn't happen in normal flow, but handle it gracefully
                raise LeaveRequestNotFound(str(leave_request.id))
        # HR and CEO can see all company leaves

    async def _leave_to_response_schema(self, leave_request: LeaveRequest) -> LeaveRead:
        """Convert LeaveRequest model to LeaveRead schema."""
        return LeaveRead(
            id=leave_request.id,
            employee_id=leave_request.employee_id,
            employee={
                "id": leave_request.employee.id if leave_request.employee else None,
                "first_name": leave_request.employee.user.first_name if leave_request.employee and leave_request.employee.user else None,
                "last_name": leave_request.employee.user.last_name if leave_request.employee and leave_request.employee.user else None,
            } if leave_request.employee else None,
            company_id=leave_request.company_id,
            leave_type=leave_request.leave_type,
            start_date=leave_request.start_date,
            end_date=leave_request.end_date,
            day_type=leave_request.day_type,
            number_of_days=leave_request.number_of_days,
            reason=leave_request.reason,
            manager_status=leave_request.manager_status,
            manager_approver_id=leave_request.manager_approver_id,
            manager_approved_at=leave_request.manager_approved_at,
            manager_rejection_reason=leave_request.manager_rejection_reason,
            hr_status=leave_request.hr_status,
            hr_approver_id=leave_request.hr_approver_id,
            hr_approved_at=leave_request.hr_approved_at,
            hr_rejection_reason=leave_request.hr_rejection_reason,
            created_at=leave_request.created_at,
            updated_at=leave_request.updated_at
        )

