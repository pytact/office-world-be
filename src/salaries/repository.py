"""Database operations for Salary Management module.

Repository layer - pure database operations only, no business logic.
All methods use eager loading for relationships to prevent MissingGreenlet errors.
All methods filter by deleted_at IS NULL for soft-delete support.
"""

from uuid import UUID
from typing import Optional
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.salaries.models import BankInfo, SalaryDetails, SalaryPayment, SalaryHistory
from src.employees.models import Employee


class SalaryRepository:
    """Repository for salary database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_employee_by_id(
        self, employee_id: UUID, company_id: Optional[UUID] = None
    ) -> Optional[Employee]:
        """Get employee by ID with eager loading of relationships.
        
        Eager loads:
        - user (User)
        - company (Company)
        
        Filters:
        - is_deleted = False (exclude soft-deleted)
        - Optional: company_id filter
        """
        query = (
            select(Employee)
            .options(selectinload(Employee.user))  # CRITICAL: Eager load user
            .where(
                Employee.id == employee_id,
                Employee.is_deleted.is_(False),
            )
        )
        
        if company_id is not None:
            query = query.where(Employee.company_id == company_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_salary_details(
        self, employee_id: UUID
    ) -> Optional[SalaryDetails]:
        """Get active salary details for employee (effective_to IS NULL).
        
        Eager loads:
        - employee (Employee)
        - salary_history (list[SalaryHistory])
        
        Filters:
        - employee_id
        - effective_to IS NULL (active)
        - deleted_at IS NULL (not soft-deleted)
        """
        result = await self.session.execute(
            select(SalaryDetails)
            .options(
                selectinload(SalaryDetails.employee),  # CRITICAL: Eager load employee
                selectinload(SalaryDetails.salary_history),  # CRITICAL: Eager load history
            )
            .where(
                SalaryDetails.employee_id == employee_id,
                SalaryDetails.effective_to.is_(None),
                SalaryDetails.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_salary_details_by_id(
        self, salary_details_id: UUID
    ) -> Optional[SalaryDetails]:
        """Get salary details by ID.
        
        Eager loads:
        - employee (Employee)
        - salary_history (list[SalaryHistory])
        
        Filters:
        - id
        - deleted_at IS NULL (not soft-deleted)
        """
        result = await self.session.execute(
            select(SalaryDetails)
            .options(
                selectinload(SalaryDetails.employee),  # CRITICAL: Eager load employee
                selectinload(SalaryDetails.salary_history),  # CRITICAL: Eager load history
            )
            .where(
                SalaryDetails.id == salary_details_id,
                SalaryDetails.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_salary_details(
        self, employee_id: UUID
    ) -> list[SalaryDetails]:
        """Get all salary details for employee (including historical).
        
        Eager loads:
        - employee (Employee)
        - salary_history (list[SalaryHistory])
        
        Filters:
        - employee_id
        - deleted_at IS NULL (not soft-deleted)
        
        Sorted by effective_from DESC (newest first).
        """
        result = await self.session.execute(
            select(SalaryDetails)
            .options(
                selectinload(SalaryDetails.employee),  # CRITICAL: Eager load employee
                selectinload(SalaryDetails.salary_history),  # CRITICAL: Eager load history
            )
            .where(
                SalaryDetails.employee_id == employee_id,
                SalaryDetails.deleted_at.is_(None),
            )
            .order_by(desc(SalaryDetails.effective_from))
        )
        return list(result.scalars().all())

    async def get_salary_by_effective_from(
        self, employee_id: UUID, effective_from: date
    ) -> Optional[SalaryDetails]:
        """Get salary details that starts on a specific date.
        
        Used to find existing salary that starts on the same date as new salary (for replacement).
        """
        result = await self.session.execute(
            select(SalaryDetails)
            .options(
                selectinload(SalaryDetails.employee),
                selectinload(SalaryDetails.salary_history),
            )
            .where(
                SalaryDetails.employee_id == employee_id,
                SalaryDetails.effective_from == effective_from,
                SalaryDetails.deleted_at.is_(None),
            )
            .order_by(desc(SalaryDetails.created_at))  # Get most recent if multiple
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def check_overlapping_salary_period(
        self,
        employee_id: UUID,
        effective_from: date,
        effective_to: Optional[date],
        exclude_salary_details_id: Optional[UUID] = None,
        exclude_salary_details_ids: Optional[list[UUID]] = None,
    ) -> bool:
        """Check if salary period overlaps with existing SalaryDetails.
        
        Returns True if overlap exists, False otherwise.
        Excludes soft-deleted records and optionally excludes specific salary_details_id(s).
        
        Handles None effective_to (active salary) by checking if new period overlaps with any existing period.
        """
        # Build overlap conditions
        # For new period to overlap with existing period:
        # - New period starts before existing period ends (or existing is active)
        # - New period ends after existing period starts (or new is active)
        
        overlap_conditions = [
            SalaryDetails.employee_id == employee_id,
            SalaryDetails.deleted_at.is_(None),
        ]
        
        # If new period has an end date (effective_to is not None)
        if effective_to is not None:
            # New period overlaps if:
            # - Existing period starts before new period ends AND
            #   (Existing period ends after new period starts OR existing period is active)
            overlap_conditions.append(
                SalaryDetails.effective_from <= effective_to
            )
            overlap_conditions.append(
                or_(
                    SalaryDetails.effective_to >= effective_from,
                    SalaryDetails.effective_to.is_(None),  # Active record (effective_to IS NULL)
                )
            )
        else:
            # New period is active (no end date) - overlaps if existing period hasn't ended yet
            # or if existing period ends after new period starts
            overlap_conditions.append(
                or_(
                    SalaryDetails.effective_to >= effective_from,
                    SalaryDetails.effective_to.is_(None),  # Both are active
                )
            )
        
        query = (
            select(func.count())
            .select_from(SalaryDetails)
            .where(and_(*overlap_conditions))
        )
        
        # Exclude IDs from overlap check
        exclude_ids = []
        if exclude_salary_details_id is not None:
            exclude_ids.append(exclude_salary_details_id)
        if exclude_salary_details_ids:
            exclude_ids.extend(exclude_salary_details_ids)
        
        if exclude_ids:
            # Remove duplicates while preserving order
            exclude_ids = list(dict.fromkeys(exclude_ids))
            query = query.where(SalaryDetails.id.notin_(exclude_ids))
        
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def get_active_salary_for_payment_month(
        self, employee_id: UUID, month: int, year: int
    ) -> Optional[SalaryDetails]:
        """Get active salary details for a specific payment month/year.
        
        Active salary must be effective on the first day of the payment month.
        """
        payment_date = date(year, month, 1)
        
        result = await self.session.execute(
            select(SalaryDetails)
            .options(selectinload(SalaryDetails.employee))  # CRITICAL: Eager load employee
            .where(
                SalaryDetails.employee_id == employee_id,
                SalaryDetails.effective_from <= payment_date,
                or_(
                    SalaryDetails.effective_to >= payment_date,
                    SalaryDetails.effective_to.is_(None),  # Active record
                ),
                SalaryDetails.deleted_at.is_(None),
            )
            .order_by(desc(SalaryDetails.effective_from))  # Get most recent active salary
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_bank_info(
        self, employee_id: UUID
    ) -> Optional[BankInfo]:
        """Get active bank info for employee.
        
        Key Rules Enforced:
        - Only returns active bank info (deleted_at IS NULL)
        - One bank account per employee (active at a time) - enforced by query filter
        
        Eager loads:
        - employee (Employee)
        
        Filters:
        - employee_id
        - deleted_at IS NULL (not soft-deleted) - ensures only active bank info is returned
        """
        result = await self.session.execute(
            select(BankInfo)
            .options(selectinload(BankInfo.employee))  # CRITICAL: Eager load employee
            .where(
                BankInfo.employee_id == employee_id,
                BankInfo.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_bank_info_by_id(
        self, bank_info_id: UUID
    ) -> Optional[BankInfo]:
        """Get bank info by ID.
        
        Eager loads:
        - employee (Employee)
        
        Filters:
        - id
        - deleted_at IS NULL (not soft-deleted)
        """
        result = await self.session.execute(
            select(BankInfo)
            .options(selectinload(BankInfo.employee))  # CRITICAL: Eager load employee
            .where(
                BankInfo.id == bank_info_id,
                BankInfo.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def check_duplicate_payment(
        self, employee_id: UUID, month: int, year: int
    ) -> bool:
        """Check if salary payment already exists for employee, month, and year.
        
        Returns True if duplicate exists, False otherwise.
        Excludes soft-deleted records.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(SalaryPayment)
            .where(
                SalaryPayment.employee_id == employee_id,
                SalaryPayment.month == month,
                SalaryPayment.year == year,
                SalaryPayment.deleted_at.is_(None),
            )
        )
        count = result.scalar() or 0
        return count > 0

    async def get_salary_payment_by_id(
        self, payment_id: UUID
    ) -> Optional[SalaryPayment]:
        """Get salary payment by ID.
        
        Eager loads:
        - employee (Employee)
        
        Filters:
        - id
        - deleted_at IS NULL (not soft-deleted)
        """
        result = await self.session.execute(
            select(SalaryPayment)
            .options(selectinload(SalaryPayment.employee))  # CRITICAL: Eager load employee
            .where(
                SalaryPayment.id == payment_id,
                SalaryPayment.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_salary_payments(
        self,
        employee_id: UUID,
        page: int,
        page_size: int,
        year: Optional[int] = None,
        month: Optional[int] = None,
        payment_method: Optional[str] = None,
        sort_by: str = "paid_on",
        sort_order: str = "desc",
    ) -> tuple[list[SalaryPayment], int]:
        """List salary payments with pagination, filtering, and sorting.
        
        Eager loads:
        - employee (Employee)
        
        Filters:
        - employee_id
        - deleted_at IS NULL (not soft-deleted)
        - Optional: year filter
        - Optional: month filter
        - Optional: payment_method filter
        
        Sorting:
        - sort_by: paid_on, month, year, amount, created_at
        - sort_order: asc, desc
        """
        # Build base query with required filters and eager loading
        query = (
            select(SalaryPayment)
            .options(selectinload(SalaryPayment.employee))  # CRITICAL: Eager load employee
            .where(
                SalaryPayment.employee_id == employee_id,
                SalaryPayment.deleted_at.is_(None),
            )
        )

        # Apply optional filters
        if year is not None:
            query = query.where(SalaryPayment.year == year)
        
        if month is not None:
            query = query.where(SalaryPayment.month == month)
        
        if payment_method is not None:
            query = query.where(SalaryPayment.payment_method == payment_method)

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = {
            "paid_on": SalaryPayment.paid_on,
            "month": SalaryPayment.month,
            "year": SalaryPayment.year,
            "amount": SalaryPayment.amount,
            "created_at": SalaryPayment.created_at,
        }.get(sort_by, SalaryPayment.paid_on)
        
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def list_salary_payments_by_month_year(
        self,
        company_id: Optional[UUID],
        month: int,
        year: int,
        page: int,
        page_size: int,
        sort_by: str = "paid_on",
        sort_order: str = "desc",
    ) -> tuple[list[SalaryPayment], int]:
        """List salary payments by month/year across company.
        
        Used for:
        - Payroll reports
        - Compliance
        - Finance reconciliation
        
        Eager loads:
        - employee (Employee)
        
        Filters:
        - month
        - year
        - deleted_at IS NULL (not soft-deleted)
        - Optional: company_id filter (if provided, filters by employee.company_id)
        
        Sorting:
        - sort_by: paid_on, month, year, amount, created_at
        - sort_order: asc, desc
        """
        # Build base query with required filters and eager loading
        query = (
            select(SalaryPayment)
            .options(selectinload(SalaryPayment.employee))  # CRITICAL: Eager load employee
            .join(Employee, SalaryPayment.employee_id == Employee.id)
            .where(
                SalaryPayment.month == month,
                SalaryPayment.year == year,
                SalaryPayment.deleted_at.is_(None),
                Employee.is_deleted.is_(False),  # Exclude soft-deleted employees
            )
        )
        
        # Apply company filter if provided
        if company_id is not None:
            query = query.where(Employee.company_id == company_id)
        
        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0
        
        # Apply sorting
        sort_column = {
            "paid_on": SalaryPayment.paid_on,
            "month": SalaryPayment.month,
            "year": SalaryPayment.year,
            "amount": SalaryPayment.amount,
            "created_at": SalaryPayment.created_at,
        }.get(sort_by, SalaryPayment.paid_on)
        
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        items = list(result.scalars().all())
        
        return items, total

    async def get_salary_history_by_salary_details_id(
        self, salary_details_id: UUID
    ) -> list[SalaryHistory]:
        """Get salary history for salary details.
        
        Eager loads:
        - salary_details (SalaryDetails)
        
        Filters:
        - salary_details_id
        
        Sorted by created_at DESC (newest first).
        """
        result = await self.session.execute(
            select(SalaryHistory)
            .options(selectinload(SalaryHistory.salary_details))  # CRITICAL: Eager load salary_details
            .where(SalaryHistory.salary_details_id == salary_details_id)
            .order_by(desc(SalaryHistory.created_at))
        )
        return list(result.scalars().all())

    async def create_salary_details(
        self, salary_details: SalaryDetails
    ) -> SalaryDetails:
        """Create new salary details record."""
        self.session.add(salary_details)
        await self.session.commit()
        await self.session.refresh(salary_details)
        return salary_details

    async def update_salary_details(
        self, salary_details: SalaryDetails
    ) -> SalaryDetails:
        """Update existing salary details record."""
        await self.session.commit()
        await self.session.refresh(salary_details)
        return salary_details

    async def soft_delete_salary_details(
        self, salary_details: SalaryDetails, deleted_by: UUID
    ) -> SalaryDetails:
        """Soft delete salary details record."""
        salary_details.deleted_at = datetime.now(timezone.utc)
        salary_details.deleted_by = deleted_by
        await self.session.commit()
        await self.session.refresh(salary_details)
        return salary_details

    async def create_bank_info(
        self, bank_info: BankInfo
    ) -> BankInfo:
        """Create new bank info record."""
        self.session.add(bank_info)
        await self.session.commit()
        await self.session.refresh(bank_info)
        return bank_info

    async def update_bank_info(
        self, bank_info: BankInfo
    ) -> BankInfo:
        """Update existing bank info record."""
        await self.session.commit()
        await self.session.refresh(bank_info)
        return bank_info

    async def soft_delete_bank_info(
        self, bank_info: BankInfo, deleted_by: UUID
    ) -> BankInfo:
        """Soft delete bank info record.
        
        Key Rules Enforced:
        - Never hard deleted (only soft delete) - sets deleted_at, preserves record
        - Used only for future payments - soft deletion doesn't affect past payments
        
        Note: This method only sets deleted_at and deleted_by. The record is never
        physically removed from the database, preserving audit trail and ensuring
        past payments remain unchanged.
        """
        bank_info.deleted_at = datetime.now(timezone.utc)
        bank_info.deleted_by = deleted_by
        await self.session.commit()
        await self.session.refresh(bank_info)
        return bank_info

    async def create_salary_payment(
        self, salary_payment: SalaryPayment
    ) -> SalaryPayment:
        """Create new salary payment record."""
        self.session.add(salary_payment)
        await self.session.commit()
        await self.session.refresh(salary_payment)
        return salary_payment

    async def update_salary_payment(
        self, salary_payment: SalaryPayment
    ) -> SalaryPayment:
        """Update existing salary payment record."""
        await self.session.commit()
        await self.session.refresh(salary_payment)
        return salary_payment

    async def soft_delete_salary_payment(
        self, salary_payment: SalaryPayment, deleted_by: UUID
    ) -> SalaryPayment:
        """Soft delete salary payment record."""
        salary_payment.deleted_at = datetime.now(timezone.utc)
        salary_payment.deleted_by = deleted_by
        await self.session.commit()
        await self.session.refresh(salary_payment)
        return salary_payment

    async def create_salary_history(
        self, salary_history: SalaryHistory
    ) -> SalaryHistory:
        """Create new salary history record."""
        self.session.add(salary_history)
        await self.session.commit()
        await self.session.refresh(salary_history)
        return salary_history
