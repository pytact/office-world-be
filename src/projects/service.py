"""Business logic for Project Management module.

Service layer - all business logic, validation, and orchestration.
Based on F7_api_spec.md - Project Management (F-007).
ETag logic in service layer per error_prevention.md RULE 19.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from fastapi.responses import Response as FastAPIResponse

from src.projects.repository import ProjectRepository
from src.projects.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectListQuery,
    ProjectSummary,
    ProjectDetail,
    ProjectPaginatedResponse,
    TaskSummary,
)
from src.projects.models import Project
from src.projects.exceptions import (
    ProjectNotFound,
    DuplicateProjectName,
    InsufficientPermissions,
    EmployeeProjectAccessDenied,
    PreconditionRequired,
    PreconditionFailed,
)
from src.projects.utils import (
    generate_etag,
    format_last_modified,
)
from src.projects.constants import (
    STATUS_ACTIVE,
    STATUS_INACTIVE,
    STATUS_COMPLETED,
    ERROR_INVALID_STATUS,
    ERROR_CODE_INVALID_STATUS,
)
from src.exceptions import ValidationError
from src.audits.repository import AuditLogRepository
import logging


class ProjectService:
    """Service for project management business logic.
    
    Based on F7_api_spec.md - All business rules in service layer.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ProjectRepository(session)
        self.audit_repository = AuditLogRepository(session)

    def _validate_status(self, status_value: str) -> None:
        """Validate project status enum value.
        
        Based on F7_api_spec.md Section 6.6 - Field Validation Rules.
        """
        valid_statuses = [STATUS_ACTIVE, STATUS_INACTIVE, STATUS_COMPLETED]
        if status_value not in valid_statuses:
            raise ValidationError(
                message=ERROR_INVALID_STATUS,
                error_code=ERROR_CODE_INVALID_STATUS,
                details=[{"field": "status", "issue": f"Status must be one of: {', '.join(valid_statuses)}"}]
            )

    def _check_ceo_or_manager(self, role: str) -> None:
        """Check if user role is CEO or Manager.
        
        Based on F7_api_spec.md Section 3.2 - Permission Matrix.
        Raises InsufficientPermissions if role is not CEO or Manager.
        """
        role_lower = role.lower() if role else ""
        if role_lower not in ["ceo", "manager"]:
            raise InsufficientPermissions("Only CEO and Manager can perform this operation.")

    async def _get_task_count(self, project_id: UUID) -> int:
        """Get count of associated tasks for a project.
        
        Note: This will be implemented when tasks model is available (F-008).
        For now, returns 0.
        """
        return await self.repository.get_task_count(project_id)

    async def _get_task_summaries(self, project_id: UUID) -> list[TaskSummary]:
        """Get task summaries for a project.
        
        Based on F7_api_spec.md Section 5.3 - Task Summary.
        Read-only data from F-008 (Task Management & Assignment).
        
        Note: This will be implemented when tasks model is available (F-008).
        For now, returns empty list.
        """
        # TODO: Implement when tasks model is available (F-008)
        # Query tasks table: SELECT id, title, status, assignee_id FROM tasks 
        # WHERE project_id = project_id AND deleted_at IS NULL
        return []

    async def list_projects(
        self,
        company_id: UUID,
        query: ProjectListQuery,
        role: str,
        employee_id: Optional[UUID] = None,
        if_none_match: Optional[str] = None,
    ) -> ProjectPaginatedResponse | FastAPIResponse:
        """List projects with pagination, filtering, search, and sorting.
        
        Based on F7_api_spec.md Section 4.3.1 - GET /api/v1/company/projects.
        
        Business Logic:
        - Role-based visibility: CEO/Manager/HR see all; Employee sees only assigned tasks
        - Filters by company_id (multi-tenant isolation)
        - Filters by status (optional)
        - Searches by name (case-insensitive partial match)
        - Sorts by created_at, updated_at, name, status, task_count
        - Paginates results
        - Builds pagination URLs with all query parameters
        """
        role_lower = role.lower() if role else ""
        
        # Role-based visibility filtering
        if role_lower == "employee":
            # Employee: Only projects with assigned tasks
            if employee_id is None:
                raise InsufficientPermissions("Employee ID is required for employee role.")
            
            # TODO: Implement when tasks model is available (F-008)
            # For now, return empty list for employees
            projects, total = await self.repository.list_projects_with_employee_tasks(
                company_id=company_id,
                employee_id=employee_id,
                page=query.page,
                page_size=query.page_size,
                status=query.status,
                search=query.search,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
            )
        else:
            # CEO/Manager/HR: All company projects
            projects, total = await self.repository.list_with_pagination(
                company_id=company_id,
                page=query.page,
                page_size=query.page_size,
                status=query.status,
                search=query.search,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
            )
        
        # Build project summaries with task_count
        items = []
        latest_updated_at = None
        for project in projects:
            task_count = await self._get_task_count(project.id)
            items.append(
                ProjectSummary(
                    id=project.id,
                    name=project.name,
                    status=project.status,
                    task_count=task_count,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
            )
            # Track latest updated_at for ETag generation
            if latest_updated_at is None or project.updated_at > latest_updated_at:
                latest_updated_at = project.updated_at
        
        # Generate ETag from latest updated_at (if projects exist)
        if latest_updated_at:
            etag = generate_etag(latest_updated_at)
            
            # Check If-None-Match for cache validation
            if if_none_match and if_none_match == etag:
                # Return 304 in service (business logic decision)
                return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Calculate pagination
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build navigation URLs with all query parameters
        base_path = "/api/v1/company/projects"
        next_page = None
        prev_page = None
        
        if query.page < total_pages:
            # Build next_page URL with all query parameters
            next_params = []
            if query.page_size != 20:
                next_params.append(f"page_size={query.page_size}")
            if query.status is not None:
                next_params.append(f"status={query.status}")
            if query.search is not None:
                next_params.append(f"search={query.search}")
            if query.sort_by != "created_at":
                next_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                next_params.append(f"sort_order={query.sort_order}")
            next_params.append(f"page={query.page + 1}")
            next_page = f"{base_path}?{'&'.join(next_params)}"
        
        if query.page > 1:
            # Build prev_page URL with all query parameters
            prev_params = []
            if query.page_size != 20:
                prev_params.append(f"page_size={query.page_size}")
            if query.status is not None:
                prev_params.append(f"status={query.status}")
            if query.search is not None:
                prev_params.append(f"search={query.search}")
            if query.sort_by != "created_at":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"
        
        result = ProjectPaginatedResponse(
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )
        
        # Attach ETag and Last-Modified for router to set headers
        if latest_updated_at:
            result._etag = generate_etag(latest_updated_at)
            result._last_modified = latest_updated_at
        
        return result

    async def get_project_by_id(
        self,
        project_id: UUID,
        company_id: UUID,
        role: str,
        employee_id: Optional[UUID] = None,
        if_none_match: Optional[str] = None,
    ) -> ProjectDetail | FastAPIResponse:
        """Get project detail with task summaries and ETag support.
        
        Based on F7_api_spec.md Section 4.3.3 - GET /api/v1/company/projects/{project_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Business Logic:
        - Validates project exists and belongs to company
        - Role-based access: Employee can only access if has assigned tasks
        - Generates ETag from updated_at
        - Handles If-None-Match for cache validation
        - Includes task summaries (read-only from F-008)
        - Calculates is_frozen from status
        """
        # Get project from repository
        project = await self.repository.get_by_id(project_id, company_id)
        if not project:
            raise ProjectNotFound(str(project_id))
        
        # Role-based access control for Employees
        role_lower = role.lower() if role else ""
        if role_lower == "employee":
            if employee_id is None:
                raise InsufficientPermissions("Employee ID is required for employee role.")
            
            # TODO: Check if employee has assigned tasks in this project
            # For now, allow access (will be fully implemented when tasks are available)
            # When tasks are available:
            # task_count = await self._get_task_count(project_id)
            # if task_count == 0:
            #     raise EmployeeProjectAccessDenied()
        
        # Generate ETag in service (business logic)
        etag = generate_etag(project.updated_at)
        
        # Check If-None-Match in service (version validation)
        if if_none_match and if_none_match == etag:
            # Return 304 in service (business logic decision)
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Get task count and summaries
        task_count = await self._get_task_count(project.id)
        task_summaries = await self._get_task_summaries(project.id)
        
        # Calculate is_frozen (derived from status)
        is_frozen = project.status in [STATUS_INACTIVE, STATUS_COMPLETED]
        
        # Build response
        result = ProjectDetail(
            id=project.id,
            name=project.name,
            status=project.status,
            task_count=task_count,
            is_frozen=is_frozen,
            tasks=task_summaries,
            created_at=project.created_at,
            updated_at=project.updated_at,
            created_by=project.created_by,
            updated_by=project.updated_by,
        )
        
        # Attach ETag to result for router to set header
        result._etag = etag
        result._last_modified = project.updated_at
        
        return result

    async def create_project(
        self,
        company_id: UUID,
        data: ProjectCreate,
        user_id: UUID,
        role: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectDetail:
        """Create a new project.
        
        Based on F7_api_spec.md Section 4.3.2 - POST /api/v1/company/projects.
        
        Business Logic:
        - Validates user role (CEO or Manager only)
        - Validates status enum value
        - Validates project name uniqueness (case-insensitive within company)
        - Creates project with audit fields
        - Returns project detail with task_count and task summaries
        """
        # Check permissions
        self._check_ceo_or_manager(role)
        
        # Validate status
        self._validate_status(data.status)
        
        # Validate name uniqueness (case-insensitive)
        name_exists = await self.repository.check_name_exists(
            name=data.name,
            company_id=company_id,
        )
        if name_exists:
            raise DuplicateProjectName(data.name)
        
        # Create project
        project = await self.repository.create(
            company_id=company_id,
            name=data.name,
            status=data.status,
            created_by=user_id,
        )
        
        # Create audit log for project creation
        try:
            new_values = {
                "name": project.name,
                "status": project.status,
            }
            
            await self.audit_repository.create(
                company_id=company_id,
                action_code="PROJECT_CREATED",
                table_name="projects",
                record_id=project.id,
                actor_id=user_id,
                old_values=None,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent,
                description=f"Project '{project.name}' created",
            )
        except Exception as e:
            # Audit logging is asynchronous and non-blocking
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create audit log for project creation: {e}")
        
        # Get task count and summaries
        task_count = await self._get_task_count(project.id)
        task_summaries = await self._get_task_summaries(project.id)
        
        # Calculate is_frozen
        is_frozen = project.status in [STATUS_INACTIVE, STATUS_COMPLETED]
        
        # Build response
        result = ProjectDetail(
            id=project.id,
            name=project.name,
            status=project.status,
            task_count=task_count,
            is_frozen=is_frozen,
            tasks=task_summaries,
            created_at=project.created_at,
            updated_at=project.updated_at,
            created_by=project.created_by,
            updated_by=project.updated_by,
        )
        
        # Attach ETag to result for router
        result._etag = generate_etag(project.updated_at)
        result._last_modified = project.updated_at
        
        return result

    async def update_project(
        self,
        project_id: UUID,
        company_id: UUID,
        data: ProjectUpdate,
        user_id: UUID,
        role: str,
        if_match: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectDetail:
        """Update project name and/or status with ETag validation.
        
        Based on F7_api_spec.md Section 4.3.4 - PATCH /api/v1/company/projects/{project_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Business Logic:
        - Validates user role (CEO or Manager only)
        - Validates project exists and belongs to company
        - Validates ETag (If-Match header required)
        - Validates at least one field is provided
        - Validates status enum value (if provided)
        - Validates name uniqueness (case-insensitive, if provided)
        - Updates project fields
        - Returns updated project detail
        """
        # Check permissions
        self._check_ceo_or_manager(role)
        
        # Validate at least one field is provided
        if data.name is None and data.status is None:
            raise ValidationError(
                message="At least one field (name or status) must be provided.",
                error_code="VALIDATION_ERROR",
                details=[{"field": "body", "issue": "At least one field (name or status) must be provided."}]
            )
        
        # Get current project
        current_project = await self.repository.get_by_id(project_id, company_id)
        if not current_project:
            raise ProjectNotFound(str(project_id))
        
        # Validate ETag (If-Match header required)
        if not if_match:
            raise PreconditionRequired()
        
        current_etag = generate_etag(current_project.updated_at)
        if if_match != current_etag:
            raise PreconditionFailed()
        
        # Build old_values and new_values for audit log (only changed fields)
        old_values = {}
        new_values = {}
        
        if data.name is not None and data.name != current_project.name:
            old_values["name"] = current_project.name
            new_values["name"] = data.name
        if data.status is not None and data.status != current_project.status:
            old_values["status"] = current_project.status
            new_values["status"] = data.status
        
        # Validate status if provided
        if data.status is not None:
            self._validate_status(data.status)
        
        # Validate name uniqueness if provided
        if data.name is not None:
            name_exists = await self.repository.check_name_exists(
                name=data.name,
                company_id=company_id,
                exclude_project_id=project_id,
            )
            if name_exists:
                raise DuplicateProjectName(data.name)
        
        # Update project
        updated_project = await self.repository.update(
            project_id=project_id,
            name=data.name,
            status=data.status,
            updated_by=user_id,
        )
        
        if not updated_project:
            raise ProjectNotFound(str(project_id))
        
        # Create audit log for project update (only if there were changes)
        if old_values or new_values:
            try:
                await self.audit_repository.create(
                    company_id=company_id,
                    action_code="PROJECT_UPDATED",
                    table_name="projects",
                    record_id=project_id,
                    actor_id=user_id,
                    old_values=old_values if old_values else None,
                    new_values=new_values if new_values else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    description=f"Project '{updated_project.name}' updated",
                )
            except Exception as e:
                # Audit logging is asynchronous and non-blocking
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create audit log for project update: {e}")
        
        # Get task count and summaries
        task_count = await self._get_task_count(updated_project.id)
        task_summaries = await self._get_task_summaries(updated_project.id)
        
        # Calculate is_frozen
        is_frozen = updated_project.status in [STATUS_INACTIVE, STATUS_COMPLETED]
        
        # Build response
        result = ProjectDetail(
            id=updated_project.id,
            name=updated_project.name,
            status=updated_project.status,
            task_count=task_count,
            is_frozen=is_frozen,
            tasks=task_summaries,
            created_at=updated_project.created_at,
            updated_at=updated_project.updated_at,
            created_by=updated_project.created_by,
            updated_by=updated_project.updated_by,
        )
        
        # Attach ETag to result for router
        result._etag = generate_etag(updated_project.updated_at)
        result._last_modified = updated_project.updated_at
        
        return result

    async def delete_project(
        self,
        project_id: UUID,
        company_id: UUID,
        user_id: UUID,
        role: str,
        if_match: Optional[str] = None,
    ) -> None:
        """Delete a project using soft delete with cascade to tasks.
        
        Based on F7_api_spec.md Section 4.3.5 - DELETE /api/v1/company/projects/{project_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Business Logic:
        - Validates user role (CEO or Manager only)
        - Validates project exists and belongs to company
        - Validates ETag (If-Match header required)
        - Soft deletes project (sets deleted_at timestamp)
        - Cascades soft delete to all associated tasks (application-level)
        - Returns None (204 No Content response)
        """
        # Check permissions
        self._check_ceo_or_manager(role)
        
        # Get current project
        current_project = await self.repository.get_by_id(project_id, company_id)
        if not current_project:
            raise ProjectNotFound(str(project_id))
        
        # Validate ETag (If-Match header required)
        if not if_match:
            raise PreconditionRequired()
        
        current_etag = generate_etag(current_project.updated_at)
        if if_match != current_etag:
            raise PreconditionFailed()
        
        # Soft delete project
        await self.repository.soft_delete(
            project_id=project_id,
            deleted_by=user_id,
        )
        
        # Cascade soft delete to associated tasks (application-level)
        # TODO: Implement when tasks model is available (F-008)
        # For each task with project_id = project_id:
        #   Set task.deleted_at = current_timestamp
        #   Set task.deleted_by = user_id
        
        # Return None (router will return 204 No Content)
