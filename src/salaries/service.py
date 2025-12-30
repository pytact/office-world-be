"""Business logic for Salary Management module.

Service layer - all business logic, validation, and orchestration.
Based on F6_api_spec.md - Salary Management (F-006).
"""

from uuid import UUID
from typing import Optional
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import status
from fastapi.responses import Response as FastAPIResponse

from src.salaries.repository import SalaryRepository
from src.salaries.schemas import (
    SalaryCreate,
    BankInfoUpsert,
    SalaryPaymentCreate,
    SalaryPaymentRun,
    SalaryPaymentUpdate,
    SalaryOverviewQuery,
    SalaryPaymentListQuery,
    SalaryOverviewResponse,
    SalaryDetailsOnlyResponse,
    SalaryDetailsResponse,
    BankInfoResponse,
    SalaryHistoryResponse,
    SalaryPaymentResponse,
    SalaryPaymentListItem,
    EmployeeBasicInfo,
    SalaryPaymentPaginatedResponse,
)
from src.salaries.models import BankInfo, SalaryDetails, SalaryPayment, SalaryHistory
from src.salaries.exceptions import (
    EmployeeNotFound,
    SalaryDetailsNotFound,
    BankInfoNotFound,
    SalaryPaymentNotFound,
    OverlappingSalaryPeriod,
    DuplicateSalaryPayment,
    NoActiveSalary,
    PreconditionRequired,
    PreconditionFailed,
    SalarySlipNotFound,
)
import logging
from src.exceptions import ConflictError, ValidationError
from src.audits.repository import AuditLogRepository
from src.salaries.utils import (
    generate_etag,
    format_last_modified,
    mask_account_number,
    mask_ifsc_code,
    generate_payment_period_label,
    get_latest_updated_at,
)
from src.salaries.constants import (
    SUCCESS_SALARY_OVERVIEW_RETRIEVED,
    SUCCESS_SALARY_DETAILS_CREATED,
    SUCCESS_SALARY_DETAILS_UPDATED,
    SUCCESS_SALARY_DETAILS_DELETED,
    SUCCESS_BANK_INFO_RETRIEVED,
    SUCCESS_BANK_INFO_CREATED,
    SUCCESS_BANK_INFO_UPDATED,
    SUCCESS_BANK_INFO_DELETED,
    SUCCESS_SALARY_PAYMENT_CREATED,
    SUCCESS_SALARY_PAYMENT_UPDATED,
    SUCCESS_SALARY_PAYMENT_DELETED,
    SUCCESS_SALARY_PAYMENTS_RETRIEVED,
)
from src.employees.models import Employee
from src.users.models import User
from src.pagination import PagedCollection


class ListWithMetadata(list):
    """A list subclass that supports arbitrary attribute assignment.
    
    Used to attach ETag and Last-Modified metadata to list responses
    while maintaining list behavior for serialization.
    """
    pass


class SalaryService:
    """Service for salary management business logic.
    
    Based on F6_api_spec.md - All business rules in service layer.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = SalaryRepository(session)
        self.audit_repository = AuditLogRepository(session)

    async def _get_user_name(self, user_id: Optional[UUID]) -> Optional[str]:
        """Get user full name from user_id.
        
        Returns None if user_id is None or user not found.
        """
        if user_id is None:
            return None
        
        result = await self.session.execute(
            select(User)
            .where(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Return full name if available, otherwise email
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        elif user.first_name:
            return user.first_name
        elif user.last_name:
            return user.last_name
        else:
            return user.email

    async def get_active_salary(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        if_none_match: Optional[str] = None,
    ) -> SalaryDetailsResponse | FastAPIResponse:
        """Get active salary for an employee.
        
        Used for:
        - Payroll
        - Employee view
        - Offer confirmation
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Gets active salary details (effective_to IS NULL)
        - Generates ETag from updated_at
        - Handles If-None-Match for cache validation
        - Returns 404 if no active salary exists
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get active salary details
        active_salary = await self.repository.get_active_salary_details(employee_id)
        if not active_salary:
            raise SalaryDetailsNotFound(str(employee_id))
        
        # Generate ETag from updated_at
        etag = generate_etag(active_salary.updated_at)
        
        # Check If-None-Match for cache validation
        if if_none_match and if_none_match == etag:
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Build response
        created_by_name = await self._get_user_name(active_salary.created_by)
        updated_by_name = await self._get_user_name(active_salary.updated_by)
        
        response = SalaryDetailsResponse(
            id=active_salary.id,
            employee_id=active_salary.employee_id,
            amount=active_salary.amount,
            currency=active_salary.currency,
            payment_frequency=active_salary.payment_frequency,
            effective_from=active_salary.effective_from,
            effective_to=active_salary.effective_to,
            created_at=active_salary.created_at,
            updated_at=active_salary.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = etag  # Attach for router
        response._last_modified = active_salary.updated_at
        return response

    async def get_salary_history(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        if_none_match: Optional[str] = None,
    ) -> list[SalaryHistoryResponse] | FastAPIResponse:
        """Get salary history for an employee with ETag support.
        
        HR / CEO only.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Gets all salary history records for the employee
        - Returns list of salary history entries
        
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get active salary to get its history
        active_salary = await self.repository.get_active_salary_details(employee_id)
        history_list = ListWithMetadata()
        
        if not active_salary:
            # If no active salary, get all salary details and their history
            all_salaries = await self.repository.get_all_salary_details(employee_id)
            for salary in all_salaries:
                history_records = await self.repository.get_salary_history_by_salary_details_id(salary.id)
                for history in history_records:
                    changed_by_name = await self._get_user_name(history.changed_by)
                    history_list.append(
                        SalaryHistoryResponse(
                            id=history.id,
                            previous_amount=history.previous_amount,
                            new_amount=history.new_amount,
                            effective_from=history.effective_from,
                            changed_by=changed_by_name,
                            created_at=history.created_at,
                        )
                    )
        else:
            # Get salary history for active salary
            history_records = await self.repository.get_salary_history_by_salary_details_id(active_salary.id)
            for history in history_records:
                changed_by_name = await self._get_user_name(history.changed_by)
                history_list.append(
                    SalaryHistoryResponse(
                        id=history.id,
                        previous_amount=history.previous_amount,
                        new_amount=history.new_amount,
                        effective_from=history.effective_from,
                        changed_by=changed_by_name,
                        created_at=history.created_at,
                    )
                )
        
        # Sort by created_at descending (newest first)
        history_list.sort(key=lambda x: x.created_at, reverse=True)
        
        # Generate ETag based on most recent history entry's created_at
        if history_list:
            most_recent_created_at = history_list[0].created_at
            etag = generate_etag(most_recent_created_at)
        else:
            # Empty result set - use current timestamp
            etag = generate_etag(datetime.now(timezone.utc))
        
        # Check If-None-Match header for conditional request
        if if_none_match and if_none_match == etag:
            # Resource hasn't changed - return 304 Not Modified
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Attach ETag metadata to the list itself (Python allows this)
        # Router will extract from the list object
        history_list._etag = etag
        if history_list:
            history_list._last_modified = history_list[0].created_at
        
        return history_list

    async def create_salary(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: SalaryCreate,
        user_id: UUID,
    ) -> SalaryDetailsResponse:
        """Create initial salary details.
        
        Key Rules:
        1. Salary is time-based - uses effective_from and effective_to dates
        2. Only one active salary per employee - enforced by validation
        3. Past salaries are preserved using effective_to - never hard deleted
        4. No overlapping periods allowed - validated before creation
        
        Validations:
        - No active salary exists (returns 409 if active salary exists - use revise endpoint instead)
        - effective_from >= today
        
        Creating First Salary:
        - effective_from = today (or provided date, must be >= today)
        - effective_to = NULL (active)
        - This becomes the employee's current salary
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Validation: No active salary exists (must use revise endpoint if active salary exists)
        current_salary = await self.repository.get_active_salary_details(employee_id)
        if current_salary:
            raise ConflictError(
                message="Active salary already exists for this employee. Use revise endpoint to update salary.",
                error_code="ACTIVE_SALARY_EXISTS",
                details=[{"field": "salary", "issue": "Active salary already exists. Use POST /salary/revise to update salary."}],
            )
        
        # Validate no overlapping periods (should not happen for initial salary, but check anyway)
        has_overlap = await self.repository.check_overlapping_salary_period(
            employee_id=employee_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            exclude_salary_details_ids=None,
        )
        if has_overlap:
            raise OverlappingSalaryPeriod()
        
        # Create new salary details (first salary - no history entry needed)
        new_salary = SalaryDetails(
            employee_id=employee_id,
            amount=data.amount,
            currency=data.currency,
            payment_frequency=data.payment_frequency,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            created_by=user_id,
            updated_by=user_id,
        )
        new_salary = await self.repository.create_salary_details(new_salary)
        
        # Build response
        created_by_name = await self._get_user_name(new_salary.created_by)
        updated_by_name = await self._get_user_name(new_salary.updated_by)
        
        response = SalaryDetailsResponse(
            id=new_salary.id,
            employee_id=new_salary.employee_id,
            amount=new_salary.amount,
            currency=new_salary.currency,
            payment_frequency=new_salary.payment_frequency,
            effective_from=new_salary.effective_from,
            effective_to=new_salary.effective_to,
            created_at=new_salary.created_at,
            updated_at=new_salary.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(new_salary.updated_at)  # Attach for router
        return response

    async def revise_salary(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: SalaryCreate,
        user_id: UUID,
        if_match: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> SalaryDetailsResponse:
        """Revise existing salary (increment/change).
        
        Key Rules:
        1. Salary is time-based - uses effective_from and effective_to dates
        2. Only one active salary per employee - enforced by closing previous active salary
        3. Past salaries are preserved using effective_to - never hard deleted
        4. No overlapping periods allowed - validated before creation
        5. NEVER update amount in-place - always close old record and create new one
        
        Backend Logic:
        - Fetch active salary
        - Set effective_to = effective_from - 1 day (yesterday relative to new effective_from)
        - Insert new salary record with new amount, effective_from = today, effective_to = NULL
        
        Why separate endpoint?
        Because revise ≠ update. This endpoint always creates a new record and closes the old one.
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get current active salary (required for revision)
        active_salary = await self.repository.get_active_salary_details(employee_id)
        if not active_salary:
            raise ValidationError(
                message="No active salary exists. Use create endpoint to create initial salary.",
                error_code="NO_ACTIVE_SALARY",
                details=[{"field": "salary", "issue": "No active salary exists. Use POST /salary to create initial salary."}],
            )
        
        # Validate ETag if provided
        if if_match:
            current_etag = generate_etag(active_salary.updated_at)
            if if_match != current_etag:
                raise PreconditionFailed()
        
        # Store previous amount for history
        previous_amount = active_salary.amount
        
        # Validate no overlapping periods (exclude active salary)
        has_overlap = await self.repository.check_overlapping_salary_period(
            employee_id=employee_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            exclude_salary_details_ids=[active_salary.id],
        )
        if has_overlap:
            raise OverlappingSalaryPeriod()
        
        # Rule: NEVER update in-place. Always close old record and create new one.
        # Step 1: Close the active salary record (set effective_to = effective_from - 1 day)
        # Ensure effective_to >= effective_from (constraint requirement)
        new_effective_to = data.effective_from - timedelta(days=1)
        # If the new effective_to would be before the old effective_from, set it to the old effective_from
        # This handles the case where the new effective_from is the same as or before the old effective_from
        if new_effective_to < active_salary.effective_from:
            new_effective_to = active_salary.effective_from
        
        active_salary.effective_to = new_effective_to
        active_salary.updated_by = user_id
        await self.repository.update_salary_details(active_salary)
        
        # Step 2: Create new salary record (never update in-place)
        new_salary = SalaryDetails(
            employee_id=employee_id,
            amount=data.amount,
            currency=data.currency,
            payment_frequency=data.payment_frequency,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            created_by=user_id,
            updated_by=user_id,
        )
        new_salary = await self.repository.create_salary_details(new_salary)
        
        # Step 3: Create salary history entry
        history = SalaryHistory(
            salary_details_id=new_salary.id,
            previous_amount=previous_amount,
            new_amount=data.amount,
            effective_from=data.effective_from,
            changed_by=user_id,
        )
        await self.repository.create_salary_history(history)
        
        # Create audit log for salary update (revise is also an update)
        if company_id:
            try:
                old_values = {
                    "amount": str(previous_amount),
                    "effective_from": active_salary.effective_from.isoformat() if active_salary.effective_from else None,
                    "effective_to": active_salary.effective_to.isoformat() if active_salary.effective_to else None,
                }
                new_values = {
                    "amount": str(data.amount),
                    "effective_from": data.effective_from.isoformat(),
                    "effective_to": data.effective_to.isoformat() if data.effective_to else None,
                }
                
                await self.audit_repository.create(
                    company_id=company_id,
                    action_code="SALARY_UPDATED",
                    table_name="salary_details",
                    record_id=new_salary.id,
                    actor_id=user_id,
                    old_values=old_values,
                    new_values=new_values,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    description=f"Salary revised for employee (amount: {previous_amount} -> {data.amount})",
                )
            except Exception as e:
                # Audit logging is asynchronous and non-blocking
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create audit log for salary revision: {e}")
        
        # Build response (return the new salary record, not the old one)
        created_by_name = await self._get_user_name(new_salary.created_by)
        updated_by_name = await self._get_user_name(new_salary.updated_by)
        
        response = SalaryDetailsResponse(
            id=new_salary.id,
            employee_id=new_salary.employee_id,
            amount=new_salary.amount,
            currency=new_salary.currency,
            payment_frequency=new_salary.payment_frequency,
            effective_from=new_salary.effective_from,
            effective_to=new_salary.effective_to,
            created_at=new_salary.created_at,
            updated_at=new_salary.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(new_salary.updated_at)  # Attach for router
        return response

    async def update_salary(
        self,
        employee_id: UUID,
        salary_id: UUID,
        company_id: Optional[UUID],
        data: SalaryCreate,
        user_id: UUID,
        if_match: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> SalaryDetailsResponse:
        """Update existing salary details by ID.
        
        Key Rules:
        1. Salary is time-based - uses effective_from and effective_to dates
        2. Only one active salary per employee - enforced by closing previous active salary
        3. Past salaries are preserved using effective_to - never hard deleted
        4. No overlapping periods allowed - validated before creation
        5. NEVER update amount in-place - always close old record and create new one
        
        How Salary Changes Should Work:
        - Find active salary record
        - Set effective_to = effective_from - 1 day (yesterday relative to new effective_from)
        - Insert new salary record:
          - New amount
          - effective_from = today (or provided date)
          - effective_to = NULL (active)
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates salary details exists and belongs to employee
        - Validates ETag if provided (from active salary)
        - Validates no overlapping salary periods
        - Closes old salary record (sets effective_to)
        - Creates new salary record (never updates in-place)
        - Creates salary history entry
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get salary details to update (the one being replaced)
        old_salary = await self.repository.get_salary_details_by_id(salary_id)
        if not old_salary or old_salary.employee_id != employee_id:
            raise SalaryDetailsNotFound(str(salary_id))
        
        # Get current active salary (should be the same as old_salary if updating active salary)
        current_active_salary = await self.repository.get_active_salary_details(employee_id)
        
        # If updating the active salary, validate ETag
        if current_active_salary and current_active_salary.id == salary_id:
            if if_match:
                current_etag = generate_etag(current_active_salary.updated_at)
                if if_match != current_etag:
                    raise PreconditionFailed()
            # Store previous amount for history
            previous_amount = old_salary.amount
        else:
            # If updating a historical salary, we still need previous_amount
            previous_amount = old_salary.amount
        
        # Collect salaries to exclude from overlap check
        exclude_ids = [salary_id]
        if current_active_salary and current_active_salary.id != salary_id:
            exclude_ids.append(current_active_salary.id)
        
        # Validate no overlapping periods
        has_overlap = await self.repository.check_overlapping_salary_period(
            employee_id=employee_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            exclude_salary_details_ids=exclude_ids,
        )
        if has_overlap:
            raise OverlappingSalaryPeriod()
        
        # Rule: NEVER update in-place. Always close old record and create new one.
        # Step 1: Close the old salary record (set effective_to = effective_from - 1 day)
        if old_salary.effective_to is None:
            # If it's an active salary, close it
            old_salary.effective_to = data.effective_from - timedelta(days=1)
            old_salary.updated_by = user_id
            await self.repository.update_salary_details(old_salary)
        elif old_salary.effective_from == data.effective_from:
            # If updating a salary that starts on the same date, allow same date for effective_to
            old_salary.effective_to = data.effective_from
            old_salary.updated_by = user_id
            await self.repository.update_salary_details(old_salary)
        
        # Step 2: Close any other active salary that might overlap
        if current_active_salary and current_active_salary.id != salary_id:
            if current_active_salary.effective_to is None or current_active_salary.effective_to >= data.effective_from:
                current_active_salary.effective_to = data.effective_from - timedelta(days=1)
                current_active_salary.updated_by = user_id
                await self.repository.update_salary_details(current_active_salary)
        
        # Step 3: Create new salary record (never update in-place)
        new_salary = SalaryDetails(
            employee_id=employee_id,
            amount=data.amount,
            currency=data.currency,
            payment_frequency=data.payment_frequency,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            created_by=user_id,
            updated_by=user_id,
        )
        new_salary = await self.repository.create_salary_details(new_salary)
        
        # Step 4: Create salary history entry
        history = SalaryHistory(
            salary_details_id=new_salary.id,
            previous_amount=previous_amount,
            new_amount=data.amount,
            effective_from=data.effective_from,
            changed_by=user_id,
        )
        await self.repository.create_salary_history(history)
        
        # Create audit log for salary update
        if company_id:
            try:
                old_values = {
                    "amount": str(previous_amount),
                    "effective_from": old_salary.effective_from.isoformat() if old_salary.effective_from else None,
                    "effective_to": old_salary.effective_to.isoformat() if old_salary.effective_to else None,
                }
                new_values = {
                    "amount": str(data.amount),
                    "effective_from": data.effective_from.isoformat(),
                    "effective_to": data.effective_to.isoformat() if data.effective_to else None,
                }
                
                await self.audit_repository.create(
                    company_id=company_id,
                    action_code="SALARY_UPDATED",
                    table_name="salary_details",
                    record_id=new_salary.id,
                    actor_id=user_id,
                    old_values=old_values,
                    new_values=new_values,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    description=f"Salary updated for employee (amount: {previous_amount} -> {data.amount})",
                )
            except Exception as e:
                # Audit logging is asynchronous and non-blocking
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create audit log for salary update: {e}")
        
        # Build response (return the new salary record, not the old one)
        created_by_name = await self._get_user_name(new_salary.created_by)
        updated_by_name = await self._get_user_name(new_salary.updated_by)
        
        response = SalaryDetailsResponse(
            id=new_salary.id,
            employee_id=new_salary.employee_id,
            amount=new_salary.amount,
            currency=new_salary.currency,
            payment_frequency=new_salary.payment_frequency,
            effective_from=new_salary.effective_from,
            effective_to=new_salary.effective_to,
            created_at=new_salary.created_at,
            updated_at=new_salary.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(new_salary.updated_at)  # Attach for router
        return response

    async def delete_salary(
        self,
        employee_id: UUID,
        salary_id: UUID,
        company_id: Optional[UUID],
        user_id: UUID,
    ) -> None:
        """Soft delete salary details by ID.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates salary details exists and belongs to employee
        - Soft deletes salary details (sets deleted_at and deleted_by)
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get salary details to delete
        salary_to_delete = await self.repository.get_salary_details_by_id(salary_id)
        if not salary_to_delete or salary_to_delete.employee_id != employee_id:
            raise SalaryDetailsNotFound(str(salary_id))
        
        # Soft delete
        await self.repository.soft_delete_salary_details(salary_to_delete, user_id)

    async def create_or_update_salary(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: SalaryCreate,
        user_id: UUID,
        if_match: Optional[str] = None,
    ) -> SalaryDetailsResponse:
        """Create or update salary details with ETag validation.
        
        Based on F6_api_spec.md Section 4.3.2 - POST /v1/company/employees/{employee_id}/salary.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates no overlapping salary periods
        - Gets current active salary (if exists)
        - Validates ETag if updating existing salary
        - Closes previous active salary (sets effective_to)
        - Creates new salary details
        - Creates salary history entry (if previous salary existed)
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get current active salary
        current_salary = await self.repository.get_active_salary_details(employee_id)
        
        # Check if there's a salary that starts on the same date (for replacement)
        existing_salary_same_date = await self.repository.get_salary_by_effective_from(
            employee_id, data.effective_from
        )
        
        # Priority: If there's a salary with same effective_from, replace that one (regardless of active status)
        # Otherwise, replace active salary if it exists
        salary_to_replace = existing_salary_same_date if existing_salary_same_date else current_salary
        
        # If updating existing salary (active or same start date), validate ETag
        if salary_to_replace:
            if not if_match:
                raise PreconditionRequired()
            
            current_etag = generate_etag(salary_to_replace.updated_at)
            if if_match != current_etag:
                raise PreconditionFailed()
        
        # Collect all salaries to exclude from overlap check
        exclude_ids = []
        if salary_to_replace:
            exclude_ids.append(salary_to_replace.id)
        # Also exclude current_salary if it's different from salary_to_replace
        if current_salary and current_salary.id != (salary_to_replace.id if salary_to_replace else None):
            exclude_ids.append(current_salary.id)
        
        # Validate no overlapping periods (exclude salaries being replaced)
        has_overlap = await self.repository.check_overlapping_salary_period(
            employee_id=employee_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            exclude_salary_details_ids=exclude_ids if exclude_ids else None,
        )
        if has_overlap:
            raise OverlappingSalaryPeriod()
        
        # Close previous salaries (if exists)
        previous_amount = None
        if salary_to_replace:
            previous_amount = salary_to_replace.amount
            # If it's an active salary, close it by setting effective_to to effective_from - 1 day
            if salary_to_replace.effective_to is None:
                salary_to_replace.effective_to = data.effective_from - timedelta(days=1)
                salary_to_replace.updated_by = user_id
                await self.repository.update_salary_details(salary_to_replace)
            # If it starts on same date, set effective_to to the same date (allowed by constraint: effective_to >= effective_from)
            elif salary_to_replace.effective_from == data.effective_from:
                salary_to_replace.effective_to = data.effective_from
                salary_to_replace.updated_by = user_id
                await self.repository.update_salary_details(salary_to_replace)
        
        # Also close current_salary if it's different from salary_to_replace and would overlap
        if current_salary and current_salary.id != (salary_to_replace.id if salary_to_replace else None):
            # Only close if it would overlap with the new salary period
            if current_salary.effective_to is None or current_salary.effective_to >= data.effective_from:
                current_salary.effective_to = data.effective_from - timedelta(days=1)
                current_salary.updated_by = user_id
                await self.repository.update_salary_details(current_salary)
        
        # Create new salary details
        new_salary = SalaryDetails(
            employee_id=employee_id,
            amount=data.amount,
            currency=data.currency,
            payment_frequency=data.payment_frequency,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            created_by=user_id,
            updated_by=user_id,
        )
        new_salary = await self.repository.create_salary_details(new_salary)
        
        # Create salary history entry (if previous salary existed)
        if salary_to_replace:
            history = SalaryHistory(
                salary_details_id=new_salary.id,
                previous_amount=previous_amount,
                new_amount=data.amount,
                effective_from=data.effective_from,
                changed_by=user_id,
            )
            await self.repository.create_salary_history(history)
        
        # Build response
        created_by_name = await self._get_user_name(new_salary.created_by)
        updated_by_name = await self._get_user_name(new_salary.updated_by)
        
        response = SalaryDetailsResponse(
            id=new_salary.id,
            employee_id=new_salary.employee_id,
            amount=new_salary.amount,
            currency=new_salary.currency,
            payment_frequency=new_salary.payment_frequency,
            effective_from=new_salary.effective_from,
            effective_to=new_salary.effective_to,
            created_at=new_salary.created_at,
            updated_at=new_salary.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(new_salary.updated_at)  # Attach for router
        return response

    async def get_bank_info(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        if_none_match: Optional[str] = None,
    ) -> BankInfoResponse | FastAPIResponse:
        """Get bank information for an employee with ETag support.
        
        Based on F6_api_spec.md - GET /v1/company/employees/{employee_id}/salary/bank-info.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Gets bank info for employee
        - Returns 404 if bank info not found
        - Supports ETag-based caching with If-None-Match header
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get bank info
        bank_info = await self.repository.get_bank_info(employee_id)
        if not bank_info:
            raise BankInfoNotFound(str(employee_id))
        
        # Check If-None-Match header for 304 Not Modified
        if if_none_match:
            current_etag = generate_etag(bank_info.updated_at)
            if if_none_match == current_etag:
                # Return 304 Not Modified
                response = FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
                response.headers["ETag"] = current_etag
                response.headers["Last-Modified"] = format_last_modified(bank_info.updated_at)
                return response
        
        # Build response (with masking)
        created_by_name = await self._get_user_name(bank_info.created_by)
        updated_by_name = await self._get_user_name(bank_info.updated_by)
        
        response = BankInfoResponse(
            id=bank_info.id,
            employee_id=bank_info.employee_id,
            bank_name=bank_info.bank_name,
            branch=bank_info.branch,
            account_number=mask_account_number(bank_info.account_number),  # Masked
            ifsc_code=mask_ifsc_code(bank_info.ifsc_code),  # Masked
            created_at=bank_info.created_at,
            updated_at=bank_info.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(bank_info.updated_at)  # Attach for router
        response._last_modified = bank_info.updated_at
        return response

    async def create_bank_info(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: BankInfoUpsert,
        user_id: UUID,
    ) -> BankInfoResponse:
        """Create new bank information.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates no existing active bank info for employee (Rule: One bank account per employee, active at a time)
        - Creates new bank info
        - Bank info is used only for future payments (past payments remain unchanged)
        
        Key Rules:
        1. One bank account per employee (active at a time) - enforced by checking existing active bank info
        2. Never hard deleted (only soft delete) - enforced by repository soft_delete_bank_info method
        3. Used only for future payments - bank info updates don't affect past payments
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Rule 1: One bank account per employee (active at a time)
        # Check if active bank info already exists (filters by deleted_at IS NULL)
        existing_bank_info = await self.repository.get_bank_info(employee_id)
        if existing_bank_info:
            raise ConflictError(
                message="Bank information already exists for this employee.",
                error_code="BANK_INFO_ALREADY_EXISTS",
                details=[{"field": "bank_info", "issue": "Bank information already exists for this employee. Use update endpoint instead."}],
            )
        
        # Create new bank info
        new_bank_info = BankInfo(
            employee_id=employee_id,
            bank_name=data.bank_name,
            branch=data.branch,
            account_number=data.account_number,
            ifsc_code=data.ifsc_code,
            created_by=user_id,
            updated_by=user_id,
        )
        bank_info = await self.repository.create_bank_info(new_bank_info)
        
        # Build response (with masking)
        created_by_name = await self._get_user_name(bank_info.created_by)
        updated_by_name = await self._get_user_name(bank_info.updated_by)
        
        response = BankInfoResponse(
            id=bank_info.id,
            employee_id=bank_info.employee_id,
            bank_name=bank_info.bank_name,
            branch=bank_info.branch,
            account_number=mask_account_number(bank_info.account_number),  # Masked
            ifsc_code=mask_ifsc_code(bank_info.ifsc_code),  # Masked
            created_at=bank_info.created_at,
            updated_at=bank_info.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(bank_info.updated_at)  # Attach for router
        return response

    async def update_bank_info(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: BankInfoUpsert,
        user_id: UUID,
        if_match: Optional[str] = None,
    ) -> BankInfoResponse:
        """Update existing bank information.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates bank info exists and belongs to employee
        - Validates ETag if provided
        - Updates bank info
        
        Key Rules:
        1. One bank account per employee (active at a time) - enforced by repository get_bank_info (filters deleted_at IS NULL)
        2. Never hard deleted (only soft delete) - enforced by repository update_bank_info (no hard delete)
        3. Used only for future payments - updates don't affect past payments (past payments use bank info at payment time)
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get bank info to update (by employee_id since only one per employee)
        bank_info_to_update = await self.repository.get_bank_info(employee_id)
        if not bank_info_to_update:
            raise BankInfoNotFound(str(employee_id))
        
        # Validate ETag if provided
        if if_match:
            current_etag = generate_etag(bank_info_to_update.updated_at)
            if if_match != current_etag:
                raise PreconditionFailed()
        
        # Update bank info
        bank_info_to_update.bank_name = data.bank_name
        bank_info_to_update.branch = data.branch
        bank_info_to_update.account_number = data.account_number
        bank_info_to_update.ifsc_code = data.ifsc_code
        bank_info_to_update.updated_by = user_id
        
        updated_bank_info = await self.repository.update_bank_info(bank_info_to_update)
        
        # Build response (with masking)
        created_by_name = await self._get_user_name(updated_bank_info.created_by)
        updated_by_name = await self._get_user_name(updated_bank_info.updated_by)
        
        response = BankInfoResponse(
            id=updated_bank_info.id,
            employee_id=updated_bank_info.employee_id,
            bank_name=updated_bank_info.bank_name,
            branch=updated_bank_info.branch,
            account_number=mask_account_number(updated_bank_info.account_number),  # Masked
            ifsc_code=mask_ifsc_code(updated_bank_info.ifsc_code),  # Masked
            created_at=updated_bank_info.created_at,
            updated_at=updated_bank_info.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(updated_bank_info.updated_at)  # Attach for router
        return response

    async def delete_bank_info(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        user_id: UUID,
    ) -> None:
        """Soft delete bank information.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates bank info exists and belongs to employee
        - Soft deletes bank info (sets deleted_at and deleted_by)
        
        Key Rules:
        1. One bank account per employee (active at a time) - enforced by repository get_bank_info (filters deleted_at IS NULL)
        2. Never hard deleted (only soft delete) - enforced by repository soft_delete_bank_info (sets deleted_at, never removes record)
        3. Used only for future payments - soft deletion doesn't affect past payments (past payments remain unchanged)
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Rule 1: One bank account per employee (active at a time)
        # Get active bank info to delete (by employee_id, filters by deleted_at IS NULL)
        bank_info_to_delete = await self.repository.get_bank_info(employee_id)
        if not bank_info_to_delete:
            raise BankInfoNotFound(str(employee_id))
        
        # Rule 2: Never hard deleted (only soft delete)
        # Soft delete sets deleted_at and deleted_by, preserves record for audit
        await self.repository.soft_delete_bank_info(bank_info_to_delete, user_id)

    async def upsert_bank_info(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: BankInfoUpsert,
        user_id: UUID,
        if_match: Optional[str] = None,
    ) -> BankInfoResponse:
        """Upsert bank information with ETag validation.
        
        Based on F6_api_spec.md Section 4.3.3 - PATCH /v1/company/employees/{employee_id}/salary/bank-info.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Gets existing bank info (if exists)
        - Validates ETag if updating existing bank info
        - Creates new or updates existing bank info
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get existing bank info
        existing_bank_info = await self.repository.get_bank_info(employee_id)
        
        # If updating existing bank info, validate ETag
        if existing_bank_info:
            if not if_match:
                raise PreconditionRequired()
            
            current_etag = generate_etag(existing_bank_info.updated_at)
            if if_match != current_etag:
                raise PreconditionFailed()
            
            # Update existing bank info
            existing_bank_info.bank_name = data.bank_name
            existing_bank_info.branch = data.branch
            existing_bank_info.account_number = data.account_number
            existing_bank_info.ifsc_code = data.ifsc_code
            existing_bank_info.updated_by = user_id
            
            updated_bank_info = await self.repository.update_bank_info(existing_bank_info)
            bank_info = updated_bank_info
        else:
            # Create new bank info
            new_bank_info = BankInfo(
                employee_id=employee_id,
                bank_name=data.bank_name,
                branch=data.branch,
                account_number=data.account_number,
                ifsc_code=data.ifsc_code,
                created_by=user_id,
                updated_by=user_id,
            )
            bank_info = await self.repository.create_bank_info(new_bank_info)
        
        # Build response (with masking)
        created_by_name = await self._get_user_name(bank_info.created_by)
        updated_by_name = await self._get_user_name(bank_info.updated_by)
        
        response = BankInfoResponse(
            id=bank_info.id,
            employee_id=bank_info.employee_id,
            bank_name=bank_info.bank_name,
            branch=bank_info.branch,
            account_number=mask_account_number(bank_info.account_number),  # Masked
            ifsc_code=mask_ifsc_code(bank_info.ifsc_code),  # Masked
            created_at=bank_info.created_at,
            updated_at=bank_info.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(bank_info.updated_at)  # Attach for router
        return response

    async def run_salary_payment(
        self,
        data: SalaryPaymentRun,
        company_id: Optional[UUID],
        user_id: UUID,
    ) -> SalaryPaymentResponse:
        """Execute salary payment.
        
        Used by HR and automated payroll jobs.
        
        Backend Logic:
        1. Check payment not already done
        2. Fetch active salary_details
        3. Fetch active bank_info
        4. Insert salary_payment
        5. Trigger async slip generation
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates no duplicate payment for same month/year
        - Gets active salary for payment month
        - Gets active bank info for payment
        - Creates salary payment record with paid_on = now
        - Returns payment with derived fields
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(data.employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(data.employee_id))
        
        # Check for duplicate payment
        is_duplicate = await self.repository.check_duplicate_payment(
            employee_id=data.employee_id,
            month=data.month,
            year=data.year,
        )
        if is_duplicate:
            raise DuplicateSalaryPayment(data.month, data.year)
        
        # Fetch active salary_details
        active_salary = await self.repository.get_active_salary_for_payment_month(
            employee_id=data.employee_id,
            month=data.month,
            year=data.year,
        )
        if not active_salary:
            raise NoActiveSalary()
        
        # Fetch active bank_info (required for payment execution)
        active_bank_info = await self.repository.get_bank_info(data.employee_id)
        if not active_bank_info:
            raise BankInfoNotFound(str(data.employee_id))
        
        # Insert salary_payment with paid_on = now
        payment = SalaryPayment(
            employee_id=data.employee_id,
            amount=active_salary.amount,
            currency=active_salary.currency,
            month=data.month,
            year=data.year,
            paid_on=datetime.utcnow(),  # Set paid_on to current time
            payment_method=data.payment_method,
            slip_url=None,  # Will be set by async slip generation
            created_by=user_id,
        )
        payment = await self.repository.create_salary_payment(payment)
        
        # TODO: Trigger async slip generation (background task)
        # This should be implemented as a background task that:
        # 1. Generates the salary slip PDF
        # 2. Uploads it to storage
        # 3. Updates payment.slip_url
        # 4. Emails the slip to the employee
        
        # Build response with derived fields
        created_by_name = await self._get_user_name(payment.created_by)
        slip_url = f"/v1/company/employees/{data.employee_id}/salary/payments/{payment.id}/slip" if payment.slip_url else None
        
        response = SalaryPaymentResponse(
            id=payment.id,
            employee_id=payment.employee_id,
            amount=payment.amount,
            currency=payment.currency,
            month=payment.month,
            year=payment.year,
            paid_on=payment.paid_on,
            payment_method=payment.payment_method,
            slip_url=slip_url,
            payable_amount=payment.amount,  # Derived field
            payment_period_label=generate_payment_period_label(payment.month, payment.year),  # Derived field
            created_at=payment.created_at,
            created_by=created_by_name,
        )
        return response

    async def create_salary_payment(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: SalaryPaymentCreate,
        user_id: UUID,
    ) -> SalaryPaymentResponse:
        """Create salary payment record.
        
        Based on F6_api_spec.md Section 4.3.4 - POST /v1/company/employees/{employee_id}/salary/payments.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates no duplicate payment for same month/year
        - Gets active salary for payment month
        - Creates salary payment record
        - Returns payment with derived fields
        
        Bank Info Rule:
        - Bank info is used only for future payments - payment uses active bank info at payment time
        - Updates to bank info after payment creation don't affect this payment
        - Past payments remain unchanged even if bank info is updated or deleted
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Check for duplicate payment
        is_duplicate = await self.repository.check_duplicate_payment(
            employee_id=employee_id,
            month=data.month,
            year=data.year,
        )
        if is_duplicate:
            raise DuplicateSalaryPayment(data.month, data.year)
        
        # Get active salary for payment month
        active_salary = await self.repository.get_active_salary_for_payment_month(
            employee_id=employee_id,
            month=data.month,
            year=data.year,
        )
        if not active_salary:
            raise NoActiveSalary()
        
        # Create salary payment
        payment = SalaryPayment(
            employee_id=employee_id,
            amount=active_salary.amount,
            currency=active_salary.currency,
            month=data.month,
            year=data.year,
            paid_on=data.paid_on,
            payment_method=data.payment_method,
            slip_url=None,  # Will be set by async slip generation
            created_by=user_id,
        )
        payment = await self.repository.create_salary_payment(payment)
        
        # Build response with derived fields
        created_by_name = await self._get_user_name(payment.created_by)
        slip_url = f"/v1/company/employees/{employee_id}/salary/payments/{payment.id}/slip" if payment.slip_url else None
        
        response = SalaryPaymentResponse(
            id=payment.id,
            employee_id=payment.employee_id,
            amount=payment.amount,
            currency=payment.currency,
            month=payment.month,
            year=payment.year,
            paid_on=payment.paid_on,
            payment_method=payment.payment_method,
            slip_url=slip_url,
            payable_amount=payment.amount,  # Derived field
            payment_period_label=generate_payment_period_label(payment.month, payment.year),  # Derived field
            created_at=payment.created_at,
            created_by=created_by_name,
        )
        return response

    async def list_salary_payments_by_month_year(
        self,
        company_id: Optional[UUID],
        month: int,
        year: int,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "paid_on",
        sort_order: str = "desc",
        if_none_match: Optional[str] = None,
    ) -> SalaryPaymentPaginatedResponse | FastAPIResponse:
        """List salary payments by month/year across company with ETag support.
        
        Used for:
        - Payroll reports
        - Compliance
        - Finance reconciliation
        
        Business Logic:
        - Gets all salary payments for the specified month/year
        - Filters by company_id if provided
        - Returns paginated results
        
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        items, total = await self.repository.list_salary_payments_by_month_year(
            company_id=company_id,
            month=month,
            year=year,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        # Generate ETag based on most recent payment's created_at (if any)
        # Note: SalaryPayment is immutable, so we use created_at instead of updated_at
        if items:
            # Get the most recent created_at from the result set
            most_recent_created_at = items[0].created_at
            etag = generate_etag(most_recent_created_at)
        else:
            # Empty result set - use current timestamp
            etag = generate_etag(datetime.now(timezone.utc))
        
        # Check If-None-Match header for conditional request
        if if_none_match and if_none_match == etag:
            # Resource hasn't changed - return 304 Not Modified
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Convert to response schemas
        payment_items = []
        for payment in items:
            created_by_name = await self._get_user_name(payment.created_by)
            slip_url = f"/v1/company/employees/{payment.employee_id}/salary/payments/{payment.id}/slip" if payment.slip_url else None
            
            payment_items.append(
                SalaryPaymentListItem(
                    id=payment.id,
                    employee_id=payment.employee_id,
                    amount=payment.amount,
                    currency=payment.currency,
                    month=payment.month,
                    year=payment.year,
                    paid_on=payment.paid_on,
                    payment_method=payment.payment_method,
                    slip_url=slip_url,
                    payable_amount=payment.amount,  # Derived field
                    payment_period_label=generate_payment_period_label(payment.month, payment.year),  # Derived field
                    created_at=payment.created_at,
                    created_by=created_by_name,
                )
            )
        
        # Build pagination metadata
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        result = SalaryPaymentPaginatedResponse(
            items=payment_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
        
        # Attach ETag metadata for router
        result._etag = etag
        if items:
            # Note: SalaryPayment is immutable, so we use created_at instead of updated_at
            result._last_modified = items[0].created_at
        
        return result

    async def list_salary_payments(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        query: SalaryPaymentListQuery,
        if_none_match: Optional[str] = None,
    ) -> SalaryPaymentPaginatedResponse | FastAPIResponse:
        """List salary payments with pagination, filtering, and sorting with ETag support.
        
        Based on F6_api_spec.md Section 4.3.5 - GET /v1/company/employees/{employee_id}/salary/payments.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Gets paginated payments from repository
        - Converts to response schemas
        - Builds pagination metadata
        
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get payments from repository
        items, total = await self.repository.list_salary_payments(
            employee_id=employee_id,
            page=query.page,
            page_size=query.page_size,
            year=query.year,
            month=query.month,
            payment_method=query.payment_method,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        # Generate ETag based on most recent payment's created_at (if any)
        # Note: SalaryPayment is immutable, so we use created_at instead of updated_at
        if items:
            # Get the most recent created_at from the result set
            most_recent_created_at = items[0].created_at
            etag = generate_etag(most_recent_created_at)
        else:
            # Empty result set - use current timestamp
            etag = generate_etag(datetime.now(timezone.utc))
        
        # Check If-None-Match header for conditional request
        if if_none_match and if_none_match == etag:
            # Resource hasn't changed - return 304 Not Modified
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Convert to response schemas
        payment_items = []
        for payment in items:
            created_by_name = await self._get_user_name(payment.created_by)
            slip_url = f"/v1/company/employees/{employee_id}/salary/payments/{payment.id}/slip" if payment.slip_url else None
            
            payment_items.append(
                SalaryPaymentListItem(
                    id=payment.id,
                    employee_id=payment.employee_id,
                    amount=payment.amount,
                    currency=payment.currency,
                    month=payment.month,
                    year=payment.year,
                    paid_on=payment.paid_on,
                    payment_method=payment.payment_method,
                    slip_url=slip_url,
                    created_at=payment.created_at,
                    created_by=created_by_name,
                )
            )
        
        # Calculate pagination metadata
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build query params string with all filters (preserve pagination state)
        query_params = []
        query_params.append(f"page_size={query.page_size}")
        if query.year is not None:
            query_params.append(f"year={query.year}")
        if query.month is not None:
            query_params.append(f"month={query.month}")
        if query.payment_method is not None:
            query_params.append(f"payment_method={query.payment_method}")
        query_params.append(f"sort_by={query.sort_by}")
        query_params.append(f"sort_order={query.sort_order}")
        query_params_str = "&".join(query_params)
        
        # Build next_page and prev_page URLs with all query parameters
        next_page = None
        if query.page < total_pages:
            next_page = f"/v1/company/employees/{employee_id}/salary/payments?page={query.page + 1}&{query_params_str}"
        
        prev_page = None
        if query.page > 1:
            prev_page = f"/v1/company/employees/{employee_id}/salary/payments?page={query.page - 1}&{query_params_str}"
        
        result = SalaryPaymentPaginatedResponse(
            items=payment_items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )
        
        # Attach ETag metadata for router
        result._etag = etag
        if items:
            # Note: SalaryPayment is immutable, so we use created_at instead of updated_at
            result._last_modified = items[0].created_at
        
        return result

    async def update_salary_payment(
        self,
        employee_id: UUID,
        payment_id: UUID,
        company_id: Optional[UUID],
        data: SalaryPaymentUpdate,
        user_id: UUID,
    ) -> SalaryPaymentResponse:
        """Update existing salary payment by ID.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates payment exists and belongs to employee
        - Updates only payment_method and paid_on (amount, currency, month, year are immutable)
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get payment to update
        payment_to_update = await self.repository.get_salary_payment_by_id(payment_id)
        if not payment_to_update or payment_to_update.employee_id != employee_id:
            raise SalaryPaymentNotFound(str(payment_id))
        
        # Update only mutable fields
        payment_to_update.payment_method = data.payment_method
        payment_to_update.paid_on = data.paid_on
        
        updated_payment = await self.repository.update_salary_payment(payment_to_update)
        
        # Build response with derived fields
        created_by_name = await self._get_user_name(updated_payment.created_by)
        slip_url = f"/v1/company/employees/{employee_id}/salary/payments/{updated_payment.id}/slip" if updated_payment.slip_url else None
        
        response = SalaryPaymentResponse(
            id=updated_payment.id,
            employee_id=updated_payment.employee_id,
            amount=updated_payment.amount,
            currency=updated_payment.currency,
            month=updated_payment.month,
            year=updated_payment.year,
            paid_on=updated_payment.paid_on,
            payment_method=updated_payment.payment_method,
            slip_url=slip_url,
            payable_amount=updated_payment.amount,  # Derived field
            payment_period_label=generate_payment_period_label(updated_payment.month, updated_payment.year),  # Derived field
            created_at=updated_payment.created_at,
            created_by=created_by_name,
        )
        return response

    async def delete_salary_payment(
        self,
        employee_id: UUID,
        payment_id: UUID,
        company_id: Optional[UUID],
        user_id: UUID,
    ) -> None:
        """Soft delete salary payment by ID.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates payment exists and belongs to employee
        - Soft deletes payment (sets deleted_at and deleted_by)
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get payment to delete
        payment_to_delete = await self.repository.get_salary_payment_by_id(payment_id)
        if not payment_to_delete or payment_to_delete.employee_id != employee_id:
            raise SalaryPaymentNotFound(str(payment_id))
        
        # Soft delete
        await self.repository.soft_delete_salary_payment(payment_to_delete, user_id)

    async def get_salary_slip(
        self,
        employee_id: UUID,
        payment_id: UUID,
        company_id: Optional[UUID],
    ) -> tuple[bytes, int, int]:
        """Get salary slip PDF file.
        
        Based on F6_api_spec.md Section 4.3.6 - GET /v1/company/employees/{employee_id}/salary/payments/{payment_id}/slip.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates payment exists and belongs to employee
        - Validates slip exists (slip_url is not None)
        - Returns tuple of (PDF bytes, year, month) for filename generation
        
        Note: Actual PDF generation/retrieval would be implemented here.
        For now, raises exception if slip not found.
        
        Returns:
            Tuple of (pdf_bytes: bytes, year: int, month: int) for filename generation.
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get payment
        payment = await self.repository.get_salary_payment_by_id(payment_id)
        if not payment or payment.employee_id != employee_id:
            raise SalaryPaymentNotFound(str(payment_id))
        
        # Check if slip exists
        if not payment.slip_url:
            raise SalarySlipNotFound(str(payment_id))
        
        # TODO: Implement actual PDF file retrieval from storage
        # For now, raise exception indicating slip not generated yet
        # When implemented, return: (pdf_bytes, payment.year, payment.month)
        raise SalarySlipNotFound(str(payment_id))
