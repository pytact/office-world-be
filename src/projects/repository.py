"""Database operations for Project Management module.

Repository layer - pure database operations only, no business logic.
All methods use eager loading for relationships to prevent MissingGreenlet errors.
All methods filter by deleted_at IS NULL for soft-delete support.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.projects.models import Project


class ProjectRepository:
    """Repository for project database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, project_id: UUID, company_id: Optional[UUID] = None
    ) -> Optional[Project]:
        """Get project by ID with eager loading of relationships.
        
        Eager loads:
        - company (Company)
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        - Optional: company_id filter (for multi-tenant isolation)
        """
        query = (
            select(Project)
            .options(selectinload(Project.company))  # CRITICAL: Eager load company
            .where(
                Project.id == project_id,
                Project.deleted_at.is_(None),
            )
        )
        
        if company_id is not None:
            query = query.where(Project.company_id == company_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def check_name_exists(
        self, name: str, company_id: UUID, exclude_project_id: Optional[UUID] = None
    ) -> bool:
        """Check if project name exists in company (case-insensitive).
        
        Based on F7_db_spec.md Section 6.4 - Unique Project Name per Company (Case-Insensitive).
        
        Returns True if name exists, False otherwise.
        Excludes soft-deleted records and optionally excludes a specific project_id.
        """
        query = (
            select(func.count())
            .select_from(Project)
            .where(
                Project.company_id == company_id,
                func.lower(Project.name) == func.lower(name),
                Project.deleted_at.is_(None),
            )
        )
        
        if exclude_project_id is not None:
            query = query.where(Project.id != exclude_project_id)
        
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def list_with_pagination(
        self,
        company_id: UUID,
        page: int,
        page_size: int,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Project], int]:
        """List projects with pagination, filtering, and sorting.
        
        Eager loads:
        - company (Company)
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        - company_id (required for multi-tenant isolation)
        - Optional: status filter (exact match, case-sensitive)
        - Optional: search by name (case-insensitive partial match using ILIKE)
        
        Sorting:
        - sort_by: created_at, updated_at, name, status, task_count
        - sort_order: asc, desc
        
        Note: task_count sorting will be implemented when tasks are available (F-008).
        """
        # Build base query with required filters and eager loading
        query = (
            select(Project)
            .options(selectinload(Project.company))  # CRITICAL: Eager load company
            .where(
                Project.company_id == company_id,
                Project.deleted_at.is_(None),
            )
        )

        # Apply optional filters
        if status is not None:
            query = query.where(Project.status == status)

        if search is not None:
            # Search by project name (case-insensitive partial match)
            search_pattern = f"%{search}%"
            query = query.where(Project.name.ilike(search_pattern))

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = None
        if sort_by == "created_at":
            sort_column = Project.created_at
        elif sort_by == "updated_at":
            sort_column = Project.updated_at
        elif sort_by == "name":
            sort_column = Project.name
        elif sort_by == "status":
            sort_column = Project.status
        elif sort_by == "task_count":
            # Note: task_count sorting will be implemented when tasks are available (F-008)
            # For now, default to created_at
            sort_column = Project.created_at
        else:
            # Default to created_at if invalid sort_by
            sort_column = Project.created_at

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

    async def create(
        self,
        company_id: UUID,
        name: str,
        status: str,
        created_by: Optional[UUID] = None,
    ) -> Project:
        """Create a new project.
        
        Pure database operation - no business logic.
        """
        project = Project(
            company_id=company_id,
            name=name,
            status=status,
            created_by=created_by,
            updated_by=created_by,
        )
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        
        # Eager load company relationship
        await self.session.execute(
            select(Project)
            .options(selectinload(Project.company))
            .where(Project.id == project.id)
        )
        await self.session.refresh(project)
        
        return project

    async def update(
        self,
        project_id: UUID,
        name: Optional[str] = None,
        status: Optional[str] = None,
        updated_by: Optional[UUID] = None,
    ) -> Optional[Project]:
        """Update project fields.
        
        Pure database operation - no business logic.
        Updates only provided fields.
        """
        project = await self.get_by_id(project_id)
        if not project:
            return None
        
        if name is not None:
            project.name = name
        if status is not None:
            project.status = status
        if updated_by is not None:
            project.updated_by = updated_by
        
        await self.session.commit()
        await self.session.refresh(project)
        
        # Eager load company relationship
        await self.session.execute(
            select(Project)
            .options(selectinload(Project.company))
            .where(Project.id == project.id)
        )
        await self.session.refresh(project)
        
        return project

    async def soft_delete(
        self,
        project_id: UUID,
        deleted_by: Optional[UUID] = None,
    ) -> Optional[Project]:
        """Soft delete a project by setting deleted_at timestamp.
        
        Pure database operation - no business logic.
        Cascade deletion to tasks is handled in service layer (application-level).
        """
        
        project = await self.get_by_id(project_id)
        if not project:
            return None
        
        project.deleted_at = datetime.now(timezone.utc)
        if deleted_by is not None:
            project.deleted_by = deleted_by
        
        await self.session.commit()
        await self.session.refresh(project)
        
        return project

    async def get_task_count(self, project_id: UUID) -> int:
        """Get count of associated tasks for a project.
        
        Note: This will be implemented when tasks model is available (F-008).
        For now, returns 0.
        
        Based on F7_api_spec.md - task_count is a derived field.
        """
        # TODO: Implement when tasks model is available (F-008)
        # Query: SELECT COUNT(*) FROM tasks WHERE project_id = project_id AND deleted_at IS NULL
        return 0

    async def list_projects_with_employee_tasks(
        self,
        company_id: UUID,
        employee_id: UUID,
        page: int,
        page_size: int,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Project], int]:
        """List projects where employee has assigned tasks.
        
        Based on F7_api_spec.md Section 3.3 - Employee visibility rules.
        Employees see only projects where they have at least one assigned task.
        
        Note: This will be fully implemented when tasks model is available (F-008).
        For now, returns empty list.
        
        Eager loads:
        - company (Company)
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        - company_id (required for multi-tenant isolation)
        - project has at least one task assigned to employee
        - Optional: status filter
        - Optional: search by name
        """
        # TODO: Implement when tasks model is available (F-008)
        # Query should join with tasks table and filter by employee assignments
        # For now, return empty list
        return [], 0
