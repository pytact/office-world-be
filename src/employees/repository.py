"""Database operations for Employee Management module.

Repository layer - pure database operations only, no business logic.
All methods use eager loading for relationships to prevent MissingGreenlet errors.
All methods filter by is_deleted=False for soft-delete support.
"""

from uuid import UUID
from typing import Optional
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.employees.models import Employee
from src.users.models import User


class EmployeeRepository:
    """Repository for employee database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, employee_id: UUID, company_id: Optional[UUID] = None) -> Optional[Employee]:
        """Get employee by ID with eager loading of relationships.
        
        Eager loads:
        - user (User)
        
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

    async def get_by_user_id(self, user_id: UUID, company_id: Optional[UUID] = None) -> Optional[Employee]:
        """Get employee by user_id with eager loading.
        
        Eager loads:
        - user (User)
        
        Filters:
        - is_deleted = False (exclude soft-deleted)
        - Optional: company_id filter
        """
        query = (
            select(Employee)
            .options(selectinload(Employee.user))  # CRITICAL: Eager load user
            .where(
                Employee.user_id == user_id,
                Employee.is_deleted.is_(False),
            )
        )
        
        if company_id is not None:
            query = query.where(Employee.company_id == company_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def check_work_email_exists(
        self, work_email: str, company_id: UUID, exclude_employee_id: Optional[UUID] = None
    ) -> bool:
        """Check if work_email already exists in company (case-insensitive).
        
        Returns True if work_email exists, False otherwise.
        Excludes soft-deleted employees and optionally excludes a specific employee ID.
        """
        query = (
            select(func.count())
            .select_from(Employee)
            .where(
                func.lower(Employee.work_email) == work_email.lower(),
                Employee.company_id == company_id,
                Employee.is_deleted.is_(False),
            )
        )
        
        if exclude_employee_id is not None:
            query = query.where(Employee.id != exclude_employee_id)
        
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def list_with_pagination(
        self,
        company_id: UUID,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        department: Optional[str] = None,
        employment_status: Optional[str] = None,
        exclude_ceo_hr: bool = False,  # For Manager role - exclude CEO and HR employees
        role_code: Optional[str] = None,  # Filter by role code (e.g., 'hr', 'manager', 'ceo', 'employee')
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Employee], int]:
        """List employees with pagination, filtering, and sorting.
        
        Eager loads:
        - user (User)
        
        Filters:
        - is_deleted = False (exclude soft-deleted)
        - company_id (required)
        - Optional: search by user name or email (case-insensitive partial match)
        - Optional: department filter (exact match)
        - Optional: employment_status filter (exact match)
        - Optional: exclude_ceo_hr (for Manager role - exclude employees with CEO or HR role)
        
        Sorting:
        - sort_by: created_at, updated_at, joining_date, job_title, department, employment_status
        - sort_order: asc, desc
        """
        # Build base query with required filters and eager loading
        query = (
            select(Employee)
            .options(selectinload(Employee.user))  # CRITICAL: Eager load user
            .where(
                Employee.company_id == company_id,
                Employee.is_deleted.is_(False),
            )
        )

        # Apply optional filters
        if search is not None:
            # Search by user name or email (case-insensitive partial match)
            search_pattern = f"%{search}%"
            query = query.join(User).where(
                or_(
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            )

        if department is not None:
            query = query.where(Employee.department == department)

        if employment_status is not None:
            query = query.where(Employee.employment_status == employment_status)

        # Filter by role_code if provided
        if role_code is not None:
            from src.permissions.models import UserRoleAssignment, Role
            
            # Normalize role_code to lowercase for case-insensitive matching
            role_code_lower = role_code.lower()
            
            # First, get the role_id from role_code
            role_subquery = (
                select(Role.id)
                .where(Role.code == role_code_lower)
            )
            
            # Filter employees whose users have the specified role assignment
            # Only include active, non-deleted role assignments for the same company
            query = query.where(
                Employee.user_id.in_(
                    select(UserRoleAssignment.user_id)
                    .where(
                        UserRoleAssignment.role_id.in_(role_subquery),
                        UserRoleAssignment.company_id == company_id,
                        UserRoleAssignment.is_active.is_(True),
                        UserRoleAssignment.deleted_at.is_(None),
                    )
                )
            )

        # For Manager role - exclude CEO and HR employees
        if exclude_ceo_hr:
            # Join with UserRoleAssignment to filter by role
            from src.permissions.models import UserRoleAssignment
            from src.permissions.models import Role
            
            # Subquery to get CEO and HR role IDs
            ceo_hr_roles_subquery = (
                select(Role.id)
                .where(Role.code.in_(["ceo", "hr"]))
            )
            
            # Exclude employees whose users have CEO or HR role assignments
            query = query.where(
                ~Employee.user_id.in_(
                    select(UserRoleAssignment.user_id)
                    .where(
                        UserRoleAssignment.role_id.in_(ceo_hr_roles_subquery),
                        UserRoleAssignment.is_active.is_(True),
                        UserRoleAssignment.deleted_at.is_(None),
                    )
                )
            )

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = None
        if sort_by == "created_at":
            sort_column = Employee.created_at
        elif sort_by == "updated_at":
            sort_column = Employee.updated_at
        elif sort_by == "joining_date":
            sort_column = Employee.joining_date
        elif sort_by == "job_title":
            sort_column = Employee.job_title
        elif sort_by == "department":
            sort_column = Employee.department
        elif sort_by == "employment_status":
            sort_column = Employee.employment_status
        else:
            # Default to created_at if invalid sort_by
            sort_column = Employee.created_at

        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def create(self, employee: Employee) -> Employee:
        """Create a new employee."""
        self.session.add(employee)
        await self.session.commit()
        await self.session.refresh(employee)
        # Eager load user after creation
        await self.session.refresh(employee, ["user"])
        return employee

    async def update(self, employee: Employee) -> Employee:
        """Update an employee."""
        await self.session.commit()
        await self.session.refresh(employee)
        # Eager load user after update
        await self.session.refresh(employee, ["user"])
        return employee

    async def soft_delete(self, employee: Employee) -> Employee:
        """Soft delete an employee by setting is_deleted=True."""
        employee.is_deleted = True
        await self.session.commit()
        await self.session.refresh(employee)
        return employee
