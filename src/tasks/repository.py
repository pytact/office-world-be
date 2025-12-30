"""Database operations for Task Management module.

Repository layer - pure database operations only, no business logic.
All methods use eager loading for relationships to prevent MissingGreenlet errors.
All methods filter by is_deleted = False for hard-delete support.
"""

from uuid import UUID
from typing import Optional
from sqlalchemy import select, func, and_, or_, desc, asc, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.tasks.models import Task, TaskAssignment
from src.employees.models import Employee
from src.projects.models import Project


class TaskRepository:
    """Repository for task database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, task_id: UUID, company_id: Optional[UUID] = None
    ) -> Optional[Task]:
        """Get task by ID with eager loading of relationships.
        
        Eager loads:
        - company (Company)
        - owner (Employee)
        - project (Project)
        - assignments (list[TaskAssignment]) with employee
        
        Filters:
        - is_deleted = False (exclude hard-deleted)
        - Optional: company_id filter (for multi-tenant isolation)
        """
        query = (
            select(Task)
            .options(
                selectinload(Task.company),  # CRITICAL: Eager load company
                selectinload(Task.owner).selectinload(Employee.user),  # CRITICAL: Eager load owner with user
                selectinload(Task.project),  # CRITICAL: Eager load project
                selectinload(Task.assignments).selectinload(TaskAssignment.employee).selectinload(Employee.user),  # CRITICAL: Eager load assignments with employee and user
            )
            .where(
                Task.id == task_id,
                Task.is_deleted.is_(False),
            )
        )
        
        if company_id is not None:
            query = query.where(Task.company_id == company_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, task: Task) -> Task:
        """Create a new task.
        
        Pure database operation - no business logic.
        """
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def update(self, task: Task) -> Task:
        """Update an existing task.
        
        Pure database operation - no business logic.
        """
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        """Hard delete a task (set is_deleted = True).
        
        Pure database operation - no business logic.
        """
        task.is_deleted = True
        await self.session.commit()

    async def list_with_pagination(
        self,
        company_id: UUID,
        page: int,
        page_size: int,
        status: Optional[str] = None,
        project_id: Optional[UUID] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        # Visibility filters (for Employee role)
        owner_id: Optional[UUID] = None,
        assigned_employee_id: Optional[UUID] = None,
    ) -> tuple[list[Task], int]:
        """List tasks with pagination, filtering, and sorting.
        
        Eager loads:
        - company (Company)
        - owner (Employee)
        - project (Project)
        - assignments (list[TaskAssignment]) with employee
        
        Filters:
        - is_deleted = False (exclude hard-deleted)
        - company_id (required for multi-tenant isolation)
        - Optional: status filter (exact match, case-sensitive)
        - Optional: project_id filter (exact match)
        - Optional: search by name (case-insensitive partial match using ILIKE)
        - Optional: owner_id filter (for Employee role - own tasks)
        - Optional: assigned_employee_id filter (for Employee role - assigned tasks)
        
        Sorting:
        - sort_by: created_at, updated_at, name, status
        - sort_order: asc, desc
        
        Note: For Employee role, use owner_id and assigned_employee_id to filter.
        For CEO/Manager/HR, pass None for both to see all company tasks.
        """
        # Build base query with required filters and eager loading
        query = (
            select(Task)
            .options(
                selectinload(Task.company),  # CRITICAL: Eager load company
                selectinload(Task.owner).selectinload(Employee.user),  # CRITICAL: Eager load owner with user
                selectinload(Task.project),  # CRITICAL: Eager load project
                selectinload(Task.assignments).selectinload(TaskAssignment.employee).selectinload(Employee.user),  # CRITICAL: Eager load assignments with employee and user
            )
            .where(
                Task.company_id == company_id,
                Task.is_deleted.is_(False),
            )
        )

        # Apply optional filters
        if status is not None:
            query = query.where(Task.status == status)

        if project_id is not None:
            query = query.where(Task.project_id == project_id)

        if search is not None:
            # Search by task name (case-insensitive partial match)
            search_pattern = f"%{search}%"
            query = query.where(Task.name.ilike(search_pattern))

        # Visibility filters for Employee role
        if owner_id is not None or assigned_employee_id is not None:
            if owner_id is not None and assigned_employee_id is not None and owner_id == assigned_employee_id:
                # Employee sees own tasks OR assigned tasks (same employee)
                # Use OR condition with subquery for assignments
                assignment_exists = exists().where(
                    and_(
                        TaskAssignment.task_id == Task.id,
                        TaskAssignment.employee_id == assigned_employee_id,
                    )
                )
                query = query.where(
                    or_(
                        Task.owner_id == owner_id,
                        assignment_exists,
                    )
                )
            elif assigned_employee_id is not None:
                # Employee sees only assigned tasks
                assignment_exists = exists().where(
                    and_(
                        TaskAssignment.task_id == Task.id,
                        TaskAssignment.employee_id == assigned_employee_id,
                    )
                )
                query = query.where(assignment_exists)
            elif owner_id is not None:
                # Employee sees only own tasks
                query = query.where(Task.owner_id == owner_id)

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = None
        if sort_by == "created_at":
            sort_column = Task.created_at
        elif sort_by == "updated_at":
            sort_column = Task.updated_at
        elif sort_by == "name":
            sort_column = Task.name
        elif sort_by == "status":
            sort_column = Task.status
        else:
            sort_column = Task.created_at  # Default

        if sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def get_assignments_by_task_id(self, task_id: UUID) -> list[TaskAssignment]:
        """Get all assignments for a task.
        
        Eager loads:
        - employee (Employee)
        
        Filters:
        - task_id
        """
        result = await self.session.execute(
            select(TaskAssignment)
            .options(
                selectinload(TaskAssignment.employee).selectinload(Employee.user),  # CRITICAL: Eager load employee with user
            )
            .where(TaskAssignment.task_id == task_id)
        )
        return list(result.scalars().all())

    async def get_assignment_by_task_and_employee(
        self, task_id: UUID, employee_id: UUID
    ) -> Optional[TaskAssignment]:
        """Get assignment by task and employee.
        
        Eager loads:
        - employee (Employee)
        
        Filters:
        - task_id
        - employee_id
        """
        result = await self.session.execute(
            select(TaskAssignment)
            .options(
                selectinload(TaskAssignment.employee).selectinload(Employee.user),  # CRITICAL: Eager load employee with user
            )
            .where(
                TaskAssignment.task_id == task_id,
                TaskAssignment.employee_id == employee_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_assignment(self, assignment: TaskAssignment) -> TaskAssignment:
        """Create a new task assignment.
        
        Pure database operation - no business logic.
        """
        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def update_assignment(self, assignment: TaskAssignment) -> TaskAssignment:
        """Update an existing task assignment.
        
        Pure database operation - no business logic.
        """
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def delete_assignment(self, assignment: TaskAssignment) -> None:
        """Delete a task assignment.
        
        Pure database operation - no business logic.
        """
        await self.session.delete(assignment)
        await self.session.commit()

    async def get_employee_by_id(
        self, employee_id: UUID, company_id: Optional[UUID] = None
    ) -> Optional[Employee]:
        """Get employee by ID.
        
        Eager loads:
        - user (User)
        - company (Company)
        
        Filters:
        - is_deleted = False (exclude soft-deleted)
        - Optional: company_id filter (for multi-tenant isolation)
        """
        query = (
            select(Employee)
            .options(
                selectinload(Employee.user),  # CRITICAL: Eager load user
                selectinload(Employee.company),  # CRITICAL: Eager load company
            )
            .where(
                Employee.id == employee_id,
                Employee.is_deleted.is_(False),
            )
        )
        
        if company_id is not None:
            query = query.where(Employee.company_id == company_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_project_by_id(
        self, project_id: UUID, company_id: Optional[UUID] = None
    ) -> Optional[Project]:
        """Get project by ID.
        
        Eager loads:
        - company (Company)
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        - Optional: company_id filter (for multi-tenant isolation)
        """
        query = (
            select(Project)
            .options(
                selectinload(Project.company),  # CRITICAL: Eager load company
            )
            .where(
                Project.id == project_id,
                Project.deleted_at.is_(None),
            )
        )
        
        if company_id is not None:
            query = query.where(Project.company_id == company_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
