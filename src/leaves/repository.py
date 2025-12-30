from uuid import UUID
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.leaves.models import LeaveRequest
from src.leaves.constants import SORT_FIELDS, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.employees.models import Employee


class LeaveRepository:
    """Repository for LeaveRequest database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, leave_id: UUID) -> Optional[LeaveRequest]:
        """Get leave request by ID with eager loading."""
        result = await self.session.execute(
            select(LeaveRequest)
            .options(
                selectinload(LeaveRequest.employee).selectinload(Employee.user),
                selectinload(LeaveRequest.manager_approver).selectinload(Employee.user),
                selectinload(LeaveRequest.hr_approver).selectinload(Employee.user),
                selectinload(LeaveRequest.company)
            )
            .where(
                LeaveRequest.id == leave_id,
                LeaveRequest.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_employee(self, leave_id: UUID) -> Optional[LeaveRequest]:
        """Get leave request by ID with employee relationship only."""
        result = await self.session.execute(
            select(LeaveRequest)
            .options(selectinload(LeaveRequest.employee))
            .where(
                LeaveRequest.id == leave_id,
                LeaveRequest.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_employee_and_date_range(
        self,
        employee_id: UUID,
        start_date: str,
        end_date: str
    ) -> List[LeaveRequest]:
        """Get leave requests for employee in date range (for overlap checking)."""
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        result = await self.session.execute(
            select(LeaveRequest)
            .where(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.deleted_at.is_(None),
                LeaveRequest.manager_status != "CANCELLED",
                LeaveRequest.hr_status != "CANCELLED",
                # Check for date overlap
                or_(
                    and_(LeaveRequest.start_date <= start_dt.date(), LeaveRequest.end_date >= start_dt.date()),
                    and_(LeaveRequest.start_date <= end_dt.date(), LeaveRequest.end_date >= end_dt.date()),
                    and_(LeaveRequest.start_date >= start_dt.date(), LeaveRequest.end_date <= end_dt.date())
                )
            )
        )
        return result.scalars().all()

    async def create(self, leave_request: LeaveRequest) -> LeaveRequest:
        """Create new leave request with eager loading of relationships."""
        self.session.add(leave_request)
        await self.session.commit()
        await self.session.refresh(leave_request)
        
        # Eagerly load relationships to avoid lazy loading issues in async context
        # Also load user relationships for employee, manager_approver, and hr_approver
        result = await self.session.execute(
            select(LeaveRequest)
            .options(
                selectinload(LeaveRequest.employee).selectinload(Employee.user),
                selectinload(LeaveRequest.manager_approver).selectinload(Employee.user),
                selectinload(LeaveRequest.hr_approver).selectinload(Employee.user),
                selectinload(LeaveRequest.company)
            )
            .where(LeaveRequest.id == leave_request.id)
        )
        leave_request_with_relations = result.scalar_one()
        return leave_request_with_relations

    async def update(self, leave_request: LeaveRequest) -> LeaveRequest:
        """Update existing leave request."""
        await self.session.commit()
        await self.session.refresh(leave_request)
        return leave_request

    async def list_with_pagination(
        self,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        filters: dict = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        company_id: UUID = None,
        employee_id: UUID = None,
        user_role: str = None
    ) -> Tuple[List[LeaveRequest], int]:
        """List leave requests with pagination, filtering, and sorting."""
        query = select(LeaveRequest).options(
            selectinload(LeaveRequest.employee).selectinload(Employee.user),
            selectinload(LeaveRequest.manager_approver).selectinload(Employee.user),
            selectinload(LeaveRequest.hr_approver).selectinload(Employee.user)
        ).where(LeaveRequest.deleted_at.is_(None))

        # Apply company scoping
        if company_id:
            query = query.where(LeaveRequest.company_id == company_id)

        # Apply role-based visibility
        if user_role == "employee":
            # Employees see only their own leaves
            if employee_id:
                query = query.where(LeaveRequest.employee_id == employee_id)
        elif user_role == "manager":
            # Managers see leaves assigned to them for approval
            if employee_id:
                query = query.where(
                    or_(
                        LeaveRequest.employee_id == employee_id,  # Own leaves
                        LeaveRequest.manager_approver_id == employee_id  # Assigned for approval
                    )
                )
        elif user_role in ["hr", "ceo"]:
            # HR and CEO see all company leaves
            pass  # No additional filtering needed

        # Apply filters
        if filters:
            if filters.get("status"):
                status = filters["status"]
                if status in ["PENDING_MANAGER", "APPROVED_MANAGER", "REJECTED_MANAGER", "CANCELLED"]:
                    query = query.where(LeaveRequest.manager_status == status)
                elif status in ["PENDING_HR", "APPROVED_HR", "REJECTED_HR", "CANCELLED"]:
                    query = query.where(LeaveRequest.hr_status == status)

            if filters.get("start_date"):
                query = query.where(LeaveRequest.start_date >= filters["start_date"])

            if filters.get("end_date"):
                query = query.where(LeaveRequest.end_date <= filters["end_date"])

            if filters.get("employee_id"):
                query = query.where(LeaveRequest.employee_id == filters["employee_id"])

            if filters.get("pending_for_me") and employee_id:
                # Show only requests awaiting current user's approval
                if user_role == "manager":
                    query = query.where(
                        LeaveRequest.manager_approver_id == employee_id,
                        LeaveRequest.manager_status == "PENDING_MANAGER"
                    )
                elif user_role == "hr":
                    query = query.where(
                        LeaveRequest.hr_approver_id == employee_id,
                        LeaveRequest.manager_status == "APPROVED_MANAGER",
                        LeaveRequest.hr_status == "PENDING_HR"
                    )
                elif user_role == "ceo":
                    # CEO approves HR leaves
                    query = query.where(
                        LeaveRequest.manager_status == "APPROVED_MANAGER",
                        LeaveRequest.hr_status == "PENDING_HR"
                    )

        # Apply sorting
        if sort_by in SORT_FIELDS:
            sort_column = getattr(LeaveRequest, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # Default sorting
            query = query.order_by(desc(LeaveRequest.created_at))

        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_pending_for_approver(
        self,
        approver_id: UUID,
        approver_role: str,
        company_id: UUID = None
    ) -> List[LeaveRequest]:
        """Get leave requests pending approval for specific user."""
        query = select(LeaveRequest).options(
            selectinload(LeaveRequest.employee)
        ).where(LeaveRequest.deleted_at.is_(None))

        if company_id:
            query = query.where(LeaveRequest.company_id == company_id)

        if approver_role == "manager":
            query = query.where(
                LeaveRequest.manager_approver_id == approver_id,
                LeaveRequest.manager_status == "PENDING_MANAGER"
            )
        elif approver_role == "hr":
            query = query.where(
                LeaveRequest.hr_approver_id == approver_id,
                LeaveRequest.manager_status == "APPROVED_MANAGER",
                LeaveRequest.hr_status == "PENDING_HR"
            )
        elif approver_role == "ceo":
            # CEO approves HR leaves (no specific approver field, role-based)
            query = query.where(
                LeaveRequest.manager_status == "APPROVED_MANAGER",
                LeaveRequest.hr_status == "PENDING_HR"
            )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def soft_delete(self, leave_id: UUID, deleted_by: UUID) -> bool:
        """Soft delete leave request."""
        result = await self.session.execute(
            select(LeaveRequest)
            .where(
                LeaveRequest.id == leave_id,
                LeaveRequest.deleted_at.is_(None)
            )
        )
        leave_request = result.scalar_one_or_none()

        if not leave_request:
            return False

        leave_request.deleted_at = datetime.utcnow()
        leave_request.deleted_by = deleted_by
        await self.session.commit()
        return True

