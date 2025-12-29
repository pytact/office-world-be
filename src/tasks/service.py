"""Business logic for Task Management module.

Service layer - all business logic, validation, and orchestration.
Based on F8_api_spec.md - Task Management & Assignment (F-008).
ETag logic in service layer per error_prevention.md RULE 19.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from fastapi.responses import Response as FastAPIResponse

from src.celery_worker import (
    send_task_created_notification,
    send_task_updated_notification,
    send_task_status_changed_notification,
    send_task_assigned_notification,
    send_task_unassigned_notification,
    send_task_permission_changed_notification,
    send_task_deleted_notification,
)

from src.tasks.repository import TaskRepository
from src.tasks.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskAssignmentUpdate,
    TaskListQuery,
    TaskRead,
    TaskSummary,
    TaskPaginatedResponse,
    TaskAssignmentRead,
    ProjectInfo,
)
from src.tasks.models import Task, TaskAssignment
from src.tasks.exceptions import (
    TaskNotFound,
    TaskAlreadyDeleted,
    TaskTerminalState,
    TaskProjectInactive,
    AssignmentNotFound,
    DuplicateAssignment,
    EmployeeNotFound,
    ProjectNotFound,
    ProjectNotActive,
    InvalidStatus,
    InvalidInitialStatus,
    InvalidPermission,
    CannotRemoveOwner,
    EditorCannotRemoveSelf,
    InsufficientPermissionsView,
    InsufficientPermissionsEdit,
    InsufficientPermissionsStatus,
    InsufficientPermissionsAssignments,
    InsufficientPermissionsDelete,
    HRReadOnly,
)
from src.tasks.utils import (
    generate_etag,
    format_last_modified,
)
from src.tasks.constants import (
    STATUS_TODO,
    STATUS_IN_PROGRESS,
    STATUS_HALT,
    STATUS_REVIEW,
    STATUS_DONE,
    STATUS_CANCELLED,
    PERMISSION_VIEWER,
    PERMISSION_EDITOR,
    PERMISSION_OWNER,
    TERMINAL_STATES,
)
from src.exceptions import PreconditionRequiredError, PreconditionFailedError


class TaskService:
    """Service for task management business logic.
    
    Based on F8_api_spec.md - All business rules in service layer.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = TaskRepository(session)

    def _check_user_permission(
        self,
        task: Task,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
    ) -> tuple[bool, str, bool, bool, bool, bool]:
        """Calculate user permissions for a task.
        
        Returns:
            (is_owner, user_permission, can_edit_task, can_change_status, can_manage_assignments, is_task_read_only)
        """
        role_lower = role.lower() if role else ""
        
        # Check if user is owner
        is_owner = employee_id is not None and task.owner_id == employee_id
        
        # Check if user is assigned
        user_permission = PERMISSION_OWNER if is_owner else None
        if not is_owner and employee_id is not None:
            for assignment in task.assignments:
                if assignment.employee_id == employee_id:
                    user_permission = assignment.permission
                    break
        
        # If no permission found, user is VIEWER (for CEO/Manager/HR)
        if user_permission is None:
            if role_lower in ["ceo", "manager", "hr"]:
                user_permission = PERMISSION_VIEWER  # Read-only for HR, full access for CEO/Manager
            else:
                user_permission = None  # No access
        
        # Calculate permissions
        # CEO/Manager can edit and manage assignments for any company task
        # Owner and Editor can change status
        can_edit_task = (
            is_owner 
            or user_permission == PERMISSION_EDITOR 
            or role_lower in ["ceo", "manager"]
        )
        can_change_status = (
            is_owner 
            or user_permission == PERMISSION_EDITOR
        )  # Owner and Editor can change status
        can_manage_assignments = (
            is_owner 
            or role_lower in ["ceo", "manager"]
        )  # Owner, CEO, and Manager can manage assignments
        is_task_read_only = (
            task.status in TERMINAL_STATES 
            or (user_permission == PERMISSION_VIEWER and role_lower not in ["ceo", "manager"])
        )
        
        return (
            is_owner,
            user_permission or PERMISSION_VIEWER,
            can_edit_task,
            can_change_status,
            can_manage_assignments,
            is_task_read_only,
        )

    def _check_visibility_access(
        self,
        task: Task,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
    ) -> None:
        """Check if user has visibility access to task.
        
        Based on F8_api_spec.md Section 3.3 - Visibility Rules.
        Raises InsufficientPermissionsView if user cannot access task.
        """
        role_lower = role.lower() if role else ""
        
        # CEO/Manager/HR can access any company task
        if role_lower in ["ceo", "manager", "hr"]:
            return
        
        # Employee can only access tasks they own or are assigned to
        if role_lower == "employee":
            if employee_id is None:
                raise InsufficientPermissionsView()
            
            # Check if owner
            if task.owner_id == employee_id:
                return
            
            # Check if assigned
            for assignment in task.assignments:
                if assignment.employee_id == employee_id:
                    return
            
            # No access
            raise InsufficientPermissionsView()

    async def list_tasks(
        self,
        company_id: UUID,
        query: TaskListQuery,
        role: str,
        employee_id: Optional[UUID] = None,
        if_none_match: Optional[str] = None,
    ) -> TaskPaginatedResponse | FastAPIResponse:
        """List tasks with pagination, filtering, search, and sorting.
        
        Based on F8_api_spec.md Section 4.3.1 - GET /api/v1/company/tasks.
        
        Business Logic:
        - Role-based visibility: CEO/Manager see all; HR sees all (read-only); Employee sees own/assigned only
        - Filters by company_id (multi-tenant isolation)
        - Filters by status, project_id (optional)
        - Searches by name (case-insensitive partial match)
        - Sorts by created_at, updated_at, name, status
        - Paginates results
        - Builds pagination URLs with all query parameters
        - Generates ETag from latest updated_at
        """
        role_lower = role.lower() if role else ""
        
        # Role-based visibility filtering
        owner_id = None
        assigned_employee_id = None
        if role_lower == "employee":
            # Employee: Only own tasks or assigned tasks
            if employee_id is None:
                raise InsufficientPermissionsView()
            owner_id = employee_id
            assigned_employee_id = employee_id
        # CEO/Manager/HR: All company tasks (pass None for both)
        
        # Convert project_id string to UUID if provided
        project_id_uuid = None
        if query.project_id:
            try:
                project_id_uuid = UUID(query.project_id)
            except ValueError:
                from src.exceptions import BadRequestError
                raise BadRequestError(
                    message=f"Invalid project_id format: {query.project_id}",
                    error_code="VALIDATION_FAILED",
                    details=[{"field": "project_id", "issue": f"Invalid UUID format: {query.project_id}"}],
                )
        
        # Get tasks from repository
        tasks, total = await self.repository.list_with_pagination(
            company_id=company_id,
            page=query.page,
            page_size=query.page_size,
            status=query.status,
            project_id=project_id_uuid,
            search=query.search,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            owner_id=owner_id,
            assigned_employee_id=assigned_employee_id,
        )
        
        # Build task summaries with derived permissions
        items = []
        latest_updated_at = None
        for task in tasks:
            (
                is_owner,
                user_permission,
                can_edit_task,
                can_change_status,
                _,
                _,
            ) = self._check_user_permission(task, None, employee_id, role)
            
            # Build project info if linked
            project_info = None
            if task.project:
                project_info = ProjectInfo(
                    id=task.project.id,
                    name=task.project.name,
                    status=getattr(task.project, "status", None),
                )
            
            # Build assignments
            assignments = [
                TaskAssignmentRead(
                    id=assignment.id,
                    employee_id=assignment.employee_id,
                    permission=assignment.permission,
                )
                for assignment in task.assignments
            ]
            
            items.append(
                TaskSummary(
                    task_id=task.id,
                    name=task.name,
                    status=task.status,
                    project_id=task.project_id,
                    owner_id=task.owner_id,
                    project=project_info,
                    assignments=assignments,
                    is_owner=is_owner,
                    user_permission=user_permission,
                    can_edit_task=can_edit_task,
                    can_change_status=can_change_status,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                )
            )
            
            # Track latest updated_at for ETag generation
            if latest_updated_at is None or task.updated_at > latest_updated_at:
                latest_updated_at = task.updated_at
        
        # Generate ETag from latest updated_at (if tasks exist)
        if latest_updated_at:
            etag = generate_etag(latest_updated_at)
            
            # Check If-None-Match for cache validation
            if if_none_match and if_none_match == etag:
                # Return 304 in service (business logic decision)
                return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Calculate pagination
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build navigation URLs with all query parameters
        base_path = "/api/v1/company/tasks"
        next_page = None
        prev_page = None
        
        if query.page < total_pages:
            # Build next_page URL with all query parameters
            next_params = []
            if query.page_size != 20:
                next_params.append(f"page_size={query.page_size}")
            if query.status is not None:
                next_params.append(f"status={query.status}")
            if query.project_id is not None:
                next_params.append(f"project_id={query.project_id}")
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
            if query.project_id is not None:
                prev_params.append(f"project_id={query.project_id}")
            if query.search is not None:
                prev_params.append(f"search={query.search}")
            if query.sort_by != "created_at":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"
        
        result = TaskPaginatedResponse(
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

    async def get_task_by_id(
        self,
        task_id: UUID,
        company_id: UUID,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_none_match: Optional[str] = None,
    ) -> TaskRead | FastAPIResponse:
        """Get task detail with assignments, project info, and derived permission fields.
        
        Based on F8_api_spec.md Section 4.3.3 - GET /api/v1/company/tasks/{task_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Business Logic:
        - Validates task exists and belongs to company
        - Checks visibility access (role-based)
        - Generates ETag from updated_at
        - Handles If-None-Match for cache validation
        - Calculates derived permission fields
        - Includes assignments and project info
        """
        # Get task from repository
        task = await self.repository.get_by_id(task_id, company_id)
        if not task:
            raise TaskNotFound(str(task_id))
        
        # Check visibility access
        self._check_visibility_access(task, user_id, employee_id, role)
        
        # Generate ETag in service (business logic)
        etag = generate_etag(task.updated_at)
        
        # Check If-None-Match in service (version validation)
        if if_none_match and if_none_match == etag:
            # Return 304 in service (business logic decision)
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Calculate derived permissions
        (
            is_owner,
            user_permission,
            can_edit_task,
            can_change_status,
            can_manage_assignments,
            is_task_read_only,
        ) = self._check_user_permission(task, user_id, employee_id, role)
        
        # Build assignments
        # CRITICAL: Use assignment.employee_id directly from the column (not from assignment.employee.id)
        # The employee_id column is the source of truth for the assigned employee
        assignments = [
            TaskAssignmentRead(
                id=assignment.id,
                employee_id=assignment.employee_id,  # Direct column access - this is the assigned employee
                permission=assignment.permission,
            )
            for assignment in task.assignments
        ]
        
        # Build project info if linked
        project_info = None
        if task.project:
            project_info = ProjectInfo(
                id=task.project.id,
                name=task.project.name,
                status=getattr(task.project, "status", None),
            )
        
        # Build response
        result = TaskRead(
            task_id=task.id,
            company_id=task.company_id,
            owner_id=task.owner_id,
            name=task.name,
            description=task.description,
            status=task.status,
            project_id=task.project_id,
            is_deleted=task.is_deleted,
            created_at=task.created_at,
            updated_at=task.updated_at,
            created_by=task.created_by,
            updated_by=task.updated_by,
            project=project_info,
            assignments=assignments,
            is_owner=is_owner,
            user_permission=user_permission,
            can_edit_task=can_edit_task,
            can_change_status=can_change_status,
            can_manage_assignments=can_manage_assignments,
            is_task_read_only=is_task_read_only,
        )
        
        # Attach ETag to result for router to set header
        result._etag = etag
        result._last_modified = task.updated_at
        
        return result

    async def create_task(
        self,
        company_id: UUID,
        data: TaskCreate,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
    ) -> TaskRead:
        """Create a new task.
        
        Based on F8_api_spec.md Section 4.3.2 - POST /api/v1/company/tasks.
        
        Business Logic:
        - Validates user role (CEO, Manager, or Employee; HR blocked)
        - Validates initial status must be TODO
        - Validates project exists and is ACTIVE (if provided)
        - Determines task owner: uses data.owner_id if provided, otherwise uses employee_id
        - Validates owner employee exists and belongs to company
        - Sets task owner (immutable)
        - Sets company_id from JWT token
        - Creates task with audit fields
        - Returns task detail with assignments
        """
        role_lower = role.lower() if role else ""
        
        # Check permissions (HR cannot create tasks)
        if role_lower == "hr":
            raise HRReadOnly("create")
        
        # Owner is always the creator (immutable)
        owner_id = employee_id
        if owner_id is None:
            raise EmployeeNotFound("employee_id")
        
        # Validate owner employee exists and belongs to company
        owner_employee = await self.repository.get_employee_by_id(owner_id, company_id)
        if not owner_employee:
            raise EmployeeNotFound(str(owner_id))
        
        # Validate initial status must be TODO
        if data.status != STATUS_TODO:
            raise InvalidInitialStatus(data.status or "None")
        
        # Validate project if provided
        if data.project_id:
            # Check project exists and belongs to company (repository filters by company_id and deleted_at)
            project = await self.repository.get_project_by_id(data.project_id, company_id)
            if not project:
                raise ProjectNotFound(str(data.project_id))
            
            # Check project status (must be ACTIVE)
            project_status = getattr(project, "status", None)
            if project_status != "ACTIVE":
                raise ProjectNotActive(str(data.project_id), project_status or "UNKNOWN")
        
        # Validate assignments if provided
        if data.assignments:
            for assignment_item in data.assignments:
                # Cannot assign task to owner (owner already has full access)
                if assignment_item.employee_id == owner_id:
                    from src.exceptions import BadRequestError
                    raise BadRequestError(
                        message="Cannot assign task to the owner. The creator is always the owner.",
                        error_code="VALIDATION_FAILED",
                        details=[{"field": "assignments", "issue": f"Cannot assign task to owner (employee_id: {owner_id})"}],
                    )
                
                # Validate assigned employee exists and belongs to company
                assigned_employee = await self.repository.get_employee_by_id(
                    assignment_item.employee_id, company_id
                )
                if not assigned_employee:
                    raise EmployeeNotFound(str(assignment_item.employee_id))
        
        # Create task
        task = Task(
            company_id=company_id,
            owner_id=owner_id,  # Always the creator (immutable)
            name=data.name,
            description=data.description,
            status=data.status or STATUS_TODO,
            project_id=data.project_id,
            created_by=user_id,
            updated_by=user_id,
        )
        
        task = await self.repository.create(task)
        
        # Create assignments if provided
        if data.assignments:
            for assignment_item in data.assignments:
                assignment = TaskAssignment(
                    task_id=task.id,
                    employee_id=assignment_item.employee_id,
                    permission=assignment_item.permission,
                    created_by=user_id,
                    updated_by=user_id,
                )
                await self.repository.create_assignment(assignment)
        
        # Reload task with assignments
        task = await self.repository.get_by_id(task.id, company_id)
        
        # Calculate derived permissions
        (
            is_owner,
            user_permission,
            can_edit_task,
            can_change_status,
            can_manage_assignments,
            is_task_read_only,
        ) = self._check_user_permission(task, user_id, employee_id, role)
        
        # Build assignments list for response
        assignments = [
            TaskAssignmentRead(
                id=assignment.id,
                employee_id=assignment.employee_id,
                permission=assignment.permission,
            )
            for assignment in task.assignments
        ]
        
        # Build project info if linked
        project_info = None
        if task.project:
            project_info = ProjectInfo(
                id=task.project.id,
                name=task.project.name,
                status=getattr(task.project, "status", None),
            )
        
        # Build response
        result = TaskRead(
            task_id=task.id,
            company_id=task.company_id,
            owner_id=task.owner_id,
            name=task.name,
            description=task.description,
            status=task.status,
            project_id=task.project_id,
            is_deleted=task.is_deleted,
            created_at=task.created_at,
            updated_at=task.updated_at,
            created_by=task.created_by,
            updated_by=task.updated_by,
            project=project_info,
            assignments=assignments,
            is_owner=is_owner,
            user_permission=user_permission,
            can_edit_task=can_edit_task,
            can_change_status=can_change_status,
            can_manage_assignments=can_manage_assignments,
            is_task_read_only=is_task_read_only,
        )
        
        # Attach ETag to result for router
        result._etag = generate_etag(task.updated_at)
        result._last_modified = task.updated_at
        
        # Send notifications
        # Get owner name for notifications
        owner_name = "Unknown"
        if owner_employee and owner_employee.user:
            owner_name = f"{owner_employee.user.first_name} {owner_employee.user.last_name}".strip()
        
        # Get project name for notifications
        project_name = task.project.name if task.project else None
        
        # Get company name for notifications
        company_name = task.company.name if task.company else "Company"
        
        # Notify owner (confirmation)
        if owner_employee and owner_employee.user:
            try:
                send_task_created_notification.delay(
                    recipient_email=owner_employee.user.email,
                    recipient_name=owner_name,
                    recipient_user_id=str(owner_employee.user_id),
                    task_id=str(task.id),
                    task_name=task.name,
                    task_description=task.description or "",
                    owner_name=owner_name,
                    project_name=project_name or "",
                    company_id=str(company_id),
                    company_name=company_name,
                    is_owner=True,
                )
            except Exception as e:
                print(f"[TASK SERVICE] Warning: Failed to send owner notification: {str(e)}")
        
        # Notify assignees
        if data.assignments:
            for assignment_item in data.assignments:
                # Get assignee details
                assignee = await self.repository.get_employee_by_id(assignment_item.employee_id, company_id)
                if assignee and assignee.user:
                    try:
                        send_task_assigned_notification.delay(
                            recipient_email=assignee.user.email,
                            recipient_name=f"{assignee.user.first_name} {assignee.user.last_name}".strip(),
                            recipient_user_id=str(assignee.user_id),
                            task_id=str(task.id),
                            task_name=task.name,
                            task_description=task.description or "",
                            permission=assignment_item.permission,
                            assigned_by_name=owner_name,
                            project_name=project_name or "",
                            company_id=str(company_id),
                            company_name=company_name,
                        )
                    except Exception as e:
                        print(f"[TASK SERVICE] Warning: Failed to send assignee notification: {str(e)}")
        
        return result

    async def update_task(
        self,
        task_id: UUID,
        company_id: UUID,
        data: TaskUpdate,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_match: Optional[str] = None,
    ) -> TaskRead:
        """Update task details (name, description, status, assignments).
        
        Based on F8_api_spec.md Section 4.3.4 - PATCH /api/v1/company/tasks/{task_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Business Logic:
        - Validates task exists and belongs to company
        - Checks visibility access
        - Validates ETag (If-Match header required)
        - Validates user permissions for each update type:
          * Name/Description: owner or editor
          * Status: owner or editor
          * Assignments: owner, CEO, or Manager
        - Validates task is not in terminal state (for name/description updates)
        - Validates task project is not INACTIVE/COMPLETED (if linked)
        - Updates task fields
        - Handles assignments if provided
        - Returns updated task detail
        """
        # Get current task
        current_task = await self.repository.get_by_id(task_id, company_id)
        if not current_task:
            raise TaskNotFound(str(task_id))
        
        # Check visibility access
        self._check_visibility_access(current_task, user_id, employee_id, role)
        
        # Validate ETag (If-Match header required)
        if not if_match:
            raise PreconditionRequiredError(
                message="If-Match header required",
                error_code="PRECONDITION_REQUIRED",
                details=[{"field": "etag", "issue": "If-Match header required"}],
            )
        
        current_etag = generate_etag(current_task.updated_at)
        if if_match != current_etag:
            raise PreconditionFailedError(
                message="Resource has been modified since retrieval. Please fetch the latest version and retry.",
                error_code="PRECONDITION_FAILED",
                details=[
                    {
                        "field": "etag",
                        "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry.",
                    }
                ],
            )
        
        # Check permissions
        (
            is_owner,
            user_permission,
            can_edit_task,
            can_change_status,
            can_manage_assignments,
            is_task_read_only,
        ) = self._check_user_permission(current_task, user_id, employee_id, role)
        
        # Validate status update permission (owner or editor)
        if data.status is not None:
            if not can_change_status:
                raise InsufficientPermissionsStatus()
            
            # Validate status transition
            if current_task.status in TERMINAL_STATES:
                raise TaskTerminalState(current_task.status)
            
            # Validate new status
            if data.status not in [STATUS_TODO, STATUS_IN_PROGRESS, STATUS_HALT, STATUS_REVIEW, STATUS_DONE, STATUS_CANCELLED]:
                raise InvalidStatus(data.status)
        
        # Validate name/description update permission (owner or editor)
        if data.name is not None or data.description is not None:
            if not can_edit_task:
                raise InsufficientPermissionsEdit()
            
            # Validate task is not in terminal state
            if current_task.status in TERMINAL_STATES:
                raise TaskTerminalState(current_task.status)
            
            # Validate task project is not INACTIVE/COMPLETED (if linked)
            if current_task.project:
                project_status = getattr(current_task.project, "status", None)
                if project_status in ["INACTIVE", "COMPLETED"]:
                    raise TaskProjectInactive(project_status or "UNKNOWN")
        
        # Validate assignments update permission (owner, CEO, or Manager)
        if data.assignments is not None:
            if not can_manage_assignments:
                raise InsufficientPermissionsAssignments()
        
        # Update task fields
        if data.name is not None:
            current_task.name = data.name
        if data.description is not None:
            current_task.description = data.description
        if data.status is not None:
            current_task.status = data.status
        
        current_task.updated_by = user_id
        
        updated_task = await self.repository.update(current_task)
        
        # Reload task with eager loading after update (refresh may clear relationships)
        updated_task = await self.repository.get_by_id(task_id, company_id)
        if not updated_task:
            raise TaskNotFound(str(task_id))
        
        # Handle assignments if provided
        # Both add and remove are optional - if not provided or empty, that operation is skipped
        if data.assignments is not None:
            # Process add assignments (only if add is provided and non-empty)
            if data.assignments.add and len(data.assignments.add) > 0:
                for add_item in data.assignments.add:
                    # Cannot assign task to owner (owner already has full access)
                    if add_item.employee_id == updated_task.owner_id:
                        from src.exceptions import BadRequestError
                        raise BadRequestError(
                            message="Cannot assign task to the owner. The creator is always the owner.",
                            error_code="VALIDATION_FAILED",
                            details=[{"field": "assignments.add", "issue": f"Cannot assign task to owner (employee_id: {updated_task.owner_id})"}],
                        )
                    
                    # Validate employee exists and is in same company
                    employee = await self.repository.get_employee_by_id(
                        add_item.employee_id, company_id
                    )
                    if not employee:
                        raise EmployeeNotFound(str(add_item.employee_id))
                    
                    # Check if assignment already exists
                    existing = await self.repository.get_assignment_by_task_and_employee(
                        task_id, add_item.employee_id
                    )
                    if existing:
                        # Store old permission for notification
                        old_permission = existing.permission
                        # Update existing assignment permission
                        existing.permission = add_item.permission
                        existing.updated_by = user_id
                        await self.repository.update_assignment(existing)
                        
                        # Send permission change notification if permission actually changed
                        if old_permission != add_item.permission:
                            assignee = await self.repository.get_employee_by_id(add_item.employee_id, company_id)
                            if assignee and assignee.user:
                                # Get updater name for notification
                                updater_employee = await self.repository.get_employee_by_id(employee_id, company_id) if employee_id else None
                                updater_name = "Unknown"
                                if updater_employee and updater_employee.user:
                                    updater_name = f"{updater_employee.user.first_name} {updater_employee.user.last_name}".strip()
                                
                                company_name = updated_task.company.name if updated_task.company else "Company"
                                
                                try:
                                    send_task_permission_changed_notification.delay(
                                        recipient_email=assignee.user.email,
                                        recipient_name=f"{assignee.user.first_name} {assignee.user.last_name}".strip(),
                                        recipient_user_id=str(assignee.user_id),
                                        task_id=str(updated_task.id),
                                        task_name=updated_task.name,
                                        old_permission=old_permission,
                                        new_permission=add_item.permission,
                                        changed_by_name=updater_name,
                                        company_id=str(company_id),
                                        company_name=company_name,
                                    )
                                except Exception as e:
                                    print(f"[TASK SERVICE] Warning: Failed to send permission change notification: {str(e)}")
                    else:
                        # Create new assignment
                        assignment = TaskAssignment(
                            task_id=task_id,
                            employee_id=add_item.employee_id,
                            permission=add_item.permission,
                            created_by=user_id,
                            updated_by=user_id,
                        )
                        await self.repository.create_assignment(assignment)
            
            # Process remove assignments (only if remove is provided and non-empty)
            if data.assignments.remove and len(data.assignments.remove) > 0:
                for remove_item in data.assignments.remove:
                    # Cannot remove owner
                    if remove_item.employee_id == updated_task.owner_id:
                        raise CannotRemoveOwner()
                    
                    # Get assignment
                    assignment = await self.repository.get_assignment_by_task_and_employee(
                        task_id, remove_item.employee_id
                    )
                    if not assignment:
                        raise AssignmentNotFound(str(task_id), str(remove_item.employee_id))
                    
                    # Editors cannot remove themselves
                    if assignment.permission == PERMISSION_EDITOR and remove_item.employee_id == employee_id:
                        raise EditorCannotRemoveSelf(str(employee_id))
                    
                    # Remove assignment
                    await self.repository.delete_assignment(assignment)
            
            # Reload task with updated assignments
            updated_task = await self.repository.get_by_id(task_id, company_id)
        
        # Recalculate derived permissions
        (
            is_owner,
            user_permission,
            can_edit_task,
            can_change_status,
            can_manage_assignments,
            is_task_read_only,
        ) = self._check_user_permission(updated_task, user_id, employee_id, role)
        
        # Build assignments
        assignments = [
            TaskAssignmentRead(
                id=assignment.id,
                employee_id=assignment.employee_id,
                permission=assignment.permission,
            )
            for assignment in updated_task.assignments
        ]
        
        # Build project info if linked
        project_info = None
        if updated_task.project:
            project_info = ProjectInfo(
                id=updated_task.project.id,
                name=updated_task.project.name,
                status=getattr(updated_task.project, "status", None),
            )
        
        # Build response
        result = TaskRead(
            task_id=updated_task.id,
            company_id=updated_task.company_id,
            owner_id=updated_task.owner_id,
            name=updated_task.name,
            description=updated_task.description,
            status=updated_task.status,
            project_id=updated_task.project_id,
            is_deleted=updated_task.is_deleted,
            created_at=updated_task.created_at,
            updated_at=updated_task.updated_at,
            created_by=updated_task.created_by,
            updated_by=updated_task.updated_by,
            project=project_info,
            assignments=assignments,
            is_owner=is_owner,
            user_permission=user_permission,
            can_edit_task=can_edit_task,
            can_change_status=can_change_status,
            can_manage_assignments=can_manage_assignments,
            is_task_read_only=is_task_read_only,
        )
        
        # Attach ETag to result for router
        result._etag = generate_etag(updated_task.updated_at)
        result._last_modified = updated_task.updated_at
        
        # Send notifications
        # Get updater name
        updater_employee = await self.repository.get_employee_by_id(employee_id, company_id) if employee_id else None
        updater_name = "Unknown"
        if updater_employee and updater_employee.user:
            updater_name = f"{updater_employee.user.first_name} {updater_employee.user.last_name}".strip()
        
        # Get company name
        company_name = updated_task.company.name if updated_task.company else "Company"
        
        # Determine what was updated
        updated_fields = []
        if data.name is not None:
            updated_fields.append("name")
        if data.description is not None:
            updated_fields.append("description")
        
        # Send update notification for name/description changes
        if updated_fields:
            updated_fields_str = ", ".join(updated_fields)
            
            # Notify owner (if not the updater)
            if updated_task.owner and updated_task.owner.user and updated_task.owner_id != employee_id:
                try:
                    send_task_updated_notification.delay(
                        recipient_email=updated_task.owner.user.email,
                        recipient_name=f"{updated_task.owner.user.first_name} {updated_task.owner.user.last_name}".strip(),
                        recipient_user_id=str(updated_task.owner.user_id),
                        task_id=str(updated_task.id),
                        task_name=updated_task.name,
                        updated_by_name=updater_name,
                        updated_fields=updated_fields_str,
                        company_id=str(company_id),
                        company_name=company_name,
                    )
                except Exception as e:
                    print(f"[TASK SERVICE] Warning: Failed to send update notification to owner: {str(e)}")
            
            # Notify all assignees (except the updater)
            for assignment in updated_task.assignments:
                if assignment.employee and assignment.employee.user and assignment.employee_id != employee_id:
                    try:
                        send_task_updated_notification.delay(
                            recipient_email=assignment.employee.user.email,
                            recipient_name=f"{assignment.employee.user.first_name} {assignment.employee.user.last_name}".strip(),
                            recipient_user_id=str(assignment.employee.user_id),
                            task_id=str(updated_task.id),
                            task_name=updated_task.name,
                            updated_by_name=updater_name,
                            updated_fields=updated_fields_str,
                            company_id=str(company_id),
                            company_name=company_name,
                        )
                    except Exception as e:
                        print(f"[TASK SERVICE] Warning: Failed to send update notification to assignee: {str(e)}")
        
        # Handle status change notification (will be sent by change_status method if status was updated)
        # Note: If status is updated here, we'll send notification
        if data.status is not None:
            # Notify owner (if not the updater)
            if updated_task.owner and updated_task.owner.user and updated_task.owner_id != employee_id:
                try:
                    send_task_status_changed_notification.delay(
                        recipient_email=updated_task.owner.user.email,
                        recipient_name=f"{updated_task.owner.user.first_name} {updated_task.owner.user.last_name}".strip(),
                        recipient_user_id=str(updated_task.owner.user_id),
                        task_id=str(updated_task.id),
                        task_name=updated_task.name,
                        old_status=current_task.status,
                        new_status=updated_task.status,
                        changed_by_name=updater_name,
                        company_id=str(company_id),
                        company_name=company_name,
                    )
                except Exception as e:
                    print(f"[TASK SERVICE] Warning: Failed to send status notification to owner: {str(e)}")
            
            # Notify all assignees (except the updater)
            for assignment in updated_task.assignments:
                if assignment.employee and assignment.employee.user and assignment.employee_id != employee_id:
                    try:
                        send_task_status_changed_notification.delay(
                            recipient_email=assignment.employee.user.email,
                            recipient_name=f"{assignment.employee.user.first_name} {assignment.employee.user.last_name}".strip(),
                            recipient_user_id=str(assignment.employee.user_id),
                            task_id=str(updated_task.id),
                            task_name=updated_task.name,
                            old_status=current_task.status,
                            new_status=updated_task.status,
                            changed_by_name=updater_name,
                            company_id=str(company_id),
                            company_name=company_name,
                        )
                    except Exception as e:
                        print(f"[TASK SERVICE] Warning: Failed to send status notification to assignee: {str(e)}")
        
        # Handle assignment notifications (add/remove)
        # Note: These are handled in update_assignments method, but we also handle them here
        # when assignments are updated as part of the general update
        if data.assignments is not None:
            project_name = updated_task.project.name if updated_task.project else None
            
            # Notify newly assigned employees
            if data.assignments.add and len(data.assignments.add) > 0:
                for add_item in data.assignments.add:
                    assignee = await self.repository.get_employee_by_id(add_item.employee_id, company_id)
                    if assignee and assignee.user:
                        try:
                            send_task_assigned_notification.delay(
                                recipient_email=assignee.user.email,
                                recipient_name=f"{assignee.user.first_name} {assignee.user.last_name}".strip(),
                                recipient_user_id=str(assignee.user_id),
                                task_id=str(updated_task.id),
                                task_name=updated_task.name,
                                task_description=updated_task.description or "",
                                permission=add_item.permission,
                                assigned_by_name=updater_name,
                                project_name=project_name or "",
                                company_id=str(company_id),
                                company_name=company_name,
                            )
                        except Exception as e:
                            print(f"[TASK SERVICE] Warning: Failed to send assignment notification: {str(e)}")
            
            # Notify removed employees
            if data.assignments.remove and len(data.assignments.remove) > 0:
                for remove_item in data.assignments.remove:
                    removed_employee = await self.repository.get_employee_by_id(remove_item.employee_id, company_id)
                    if removed_employee and removed_employee.user:
                        try:
                            send_task_unassigned_notification.delay(
                                recipient_email=removed_employee.user.email,
                                recipient_name=f"{removed_employee.user.first_name} {removed_employee.user.last_name}".strip(),
                                recipient_user_id=str(removed_employee.user_id),
                                task_id=str(updated_task.id),
                                task_name=updated_task.name,
                                removed_by_name=updater_name,
                                company_id=str(company_id),
                                company_name=company_name,
                            )
                        except Exception as e:
                            print(f"[TASK SERVICE] Warning: Failed to send unassignment notification: {str(e)}")
        
        return result

    async def change_status(
        self,
        task_id: UUID,
        company_id: UUID,
        data: TaskStatusUpdate,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_match: Optional[str] = None,
    ) -> TaskRead:
        """Change task status (owner or editor).
        
        Based on F8_api_spec.md Section 4.3.5 - PATCH /api/v1/company/tasks/{task_id}/status.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Business Logic:
        - Validates task exists and belongs to company
        - Checks visibility access
        - Validates ETag (If-Match header required)
        - Validates user is task owner or editor (owner or editor can change status)
        - Updates task status
        - Returns updated task detail
        """
        # Get current task
        current_task = await self.repository.get_by_id(task_id, company_id)
        if not current_task:
            raise TaskNotFound(str(task_id))
        
        # Check visibility access
        self._check_visibility_access(current_task, user_id, employee_id, role)
        
        # Validate ETag (If-Match header required)
        if not if_match:
            raise PreconditionRequiredError(
                message="If-Match header required",
                error_code="PRECONDITION_REQUIRED",
                details=[{"field": "etag", "issue": "If-Match header required"}],
            )
        
        current_etag = generate_etag(current_task.updated_at)
        if if_match != current_etag:
            raise PreconditionFailedError(
                message="Resource has been modified since retrieval. Please fetch the latest version and retry.",
                error_code="PRECONDITION_FAILED",
                details=[
                    {
                        "field": "etag",
                        "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry.",
                    }
                ],
            )
        
        # Check permissions (owner or editor can change status)
        (
            is_owner,
            _,
            _,
            can_change_status,
            _,
            _,
        ) = self._check_user_permission(current_task, user_id, employee_id, role)
        
        if not can_change_status:
            raise InsufficientPermissionsStatus()
        
        # Update task status
        current_task.status = data.status
        current_task.updated_by = user_id
        
        updated_task = await self.repository.update(current_task)
        
        # Reload task with eager loading after update (refresh may clear relationships)
        updated_task = await self.repository.get_by_id(task_id, company_id)
        if not updated_task:
            raise TaskNotFound(str(task_id))
        
        # Recalculate derived permissions
        (
            is_owner,
            user_permission,
            can_edit_task,
            can_change_status,
            can_manage_assignments,
            is_task_read_only,
        ) = self._check_user_permission(updated_task, user_id, employee_id, role)
        
        # Build assignments
        assignments = [
            TaskAssignmentRead(
                id=assignment.id,
                employee_id=assignment.employee_id,
                permission=assignment.permission,
            )
            for assignment in updated_task.assignments
        ]
        
        # Build project info if linked
        project_info = None
        if updated_task.project:
            project_info = ProjectInfo(
                id=updated_task.project.id,
                name=updated_task.project.name,
                status=getattr(updated_task.project, "status", None),
            )
        
        # Build response
        result = TaskRead(
            task_id=updated_task.id,
            company_id=updated_task.company_id,
            owner_id=updated_task.owner_id,
            name=updated_task.name,
            description=updated_task.description,
            status=updated_task.status,
            project_id=updated_task.project_id,
            is_deleted=updated_task.is_deleted,
            created_at=updated_task.created_at,
            updated_at=updated_task.updated_at,
            created_by=updated_task.created_by,
            updated_by=updated_task.updated_by,
            project=project_info,
            assignments=assignments,
            is_owner=is_owner,
            user_permission=user_permission,
            can_edit_task=can_edit_task,
            can_change_status=can_change_status,
            can_manage_assignments=can_manage_assignments,
            is_task_read_only=is_task_read_only,
        )
        
        # Attach ETag to result for router
        result._etag = generate_etag(updated_task.updated_at)
        result._last_modified = updated_task.updated_at
        
        # Send notifications
        # Get changer name
        changer_employee = await self.repository.get_employee_by_id(employee_id, company_id) if employee_id else None
        changer_name = "Unknown"
        if changer_employee and changer_employee.user:
            changer_name = f"{changer_employee.user.first_name} {changer_employee.user.last_name}".strip()
        
        # Get company name
        company_name = updated_task.company.name if updated_task.company else "Company"
        
        # Store old status for notification
        old_status = current_task.status
        
        # Notify owner (if not the changer)
        if updated_task.owner and updated_task.owner.user and updated_task.owner_id != employee_id:
            try:
                send_task_status_changed_notification.delay(
                    recipient_email=updated_task.owner.user.email,
                    recipient_name=f"{updated_task.owner.user.first_name} {updated_task.owner.user.last_name}".strip(),
                    recipient_user_id=str(updated_task.owner.user_id),
                    task_id=str(updated_task.id),
                    task_name=updated_task.name,
                    old_status=old_status,
                    new_status=updated_task.status,
                    changed_by_name=changer_name,
                    company_id=str(company_id),
                    company_name=company_name,
                )
            except Exception as e:
                print(f"[TASK SERVICE] Warning: Failed to send status notification to owner: {str(e)}")
        
        # Notify all assignees (except the changer)
        for assignment in updated_task.assignments:
            if assignment.employee and assignment.employee.user and assignment.employee_id != employee_id:
                try:
                    send_task_status_changed_notification.delay(
                        recipient_email=assignment.employee.user.email,
                        recipient_name=f"{assignment.employee.user.first_name} {assignment.employee.user.last_name}".strip(),
                        recipient_user_id=str(assignment.employee.user_id),
                        task_id=str(updated_task.id),
                        task_name=updated_task.name,
                        old_status=old_status,
                        new_status=updated_task.status,
                        changed_by_name=changer_name,
                        company_id=str(company_id),
                        company_name=company_name,
                    )
                except Exception as e:
                    print(f"[TASK SERVICE] Warning: Failed to send status notification to assignee: {str(e)}")
        
        return result

    async def update_assignments(
        self,
        task_id: UUID,
        company_id: UUID,
        data: TaskAssignmentUpdate,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_match: Optional[str] = None,
    ) -> TaskRead:
        """Update task assignments (add or remove).
        
        Based on F8_api_spec.md Section 4.3.6 - PATCH /api/v1/company/tasks/{task_id}/assignments.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Business Logic:
        - Validates task exists and belongs to company
        - Checks visibility access
        - Validates ETag (If-Match header required)
        - Validates user is task owner (only owner can manage assignments)
        - Validates employees exist and are in same company
        - Validates no duplicate assignments
        - Validates assignments exist before removing
        - Validates owner cannot be removed
        - Validates editors cannot remove themselves
        - Adds/removes assignments
        - Returns updated task detail
        """
        # Get current task
        current_task = await self.repository.get_by_id(task_id, company_id)
        if not current_task:
            raise TaskNotFound(str(task_id))
        
        # Check visibility access
        self._check_visibility_access(current_task, user_id, employee_id, role)
        
        # Validate ETag (If-Match header required)
        if not if_match:
            raise PreconditionRequiredError(
                message="If-Match header required",
                error_code="PRECONDITION_REQUIRED",
                details=[{"field": "etag", "issue": "If-Match header required"}],
            )
        
        current_etag = generate_etag(current_task.updated_at)
        if if_match != current_etag:
            raise PreconditionFailedError(
                message="Resource has been modified since retrieval. Please fetch the latest version and retry.",
                error_code="PRECONDITION_FAILED",
                details=[
                    {
                        "field": "etag",
                        "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry.",
                    }
                ],
            )
        
        # Check permissions (owner, CEO, or Manager can manage assignments)
        (
            is_owner,
            _,
            _,
            _,
            can_manage_assignments,
            _,
        ) = self._check_user_permission(current_task, user_id, employee_id, role)
        
        if not can_manage_assignments:
            raise InsufficientPermissionsAssignments()
        
        # Process add assignments (only if add is provided and non-empty)
        if data.add and len(data.add) > 0:
            for add_item in data.add:
                # Cannot assign task to owner (owner already has full access)
                if add_item.employee_id == current_task.owner_id:
                    from src.exceptions import BadRequestError
                    raise BadRequestError(
                        message="Cannot assign task to the owner. The creator is always the owner.",
                        error_code="VALIDATION_FAILED",
                        details=[{"field": "assignments.add", "issue": f"Cannot assign task to owner (employee_id: {current_task.owner_id})"}],
                    )
                
                # Validate employee exists and is in same company
                employee = await self.repository.get_employee_by_id(
                    add_item.employee_id, company_id
                )
                if not employee:
                    raise EmployeeNotFound(str(add_item.employee_id))
                
                # Check if assignment already exists
                existing = await self.repository.get_assignment_by_task_and_employee(
                    task_id, add_item.employee_id
                )
                if existing:
                    # Store old permission for notification
                    old_permission = existing.permission
                    # Update existing assignment permission
                    existing.permission = add_item.permission
                    existing.updated_by = user_id
                    await self.repository.update_assignment(existing)
                    
                    # Send permission change notification if permission actually changed
                    if old_permission != add_item.permission:
                        assignee = await self.repository.get_employee_by_id(add_item.employee_id, company_id)
                        if assignee and assignee.user:
                            # Get updater name for notification
                            updater_employee = await self.repository.get_employee_by_id(employee_id, company_id) if employee_id else None
                            updater_name = "Unknown"
                            if updater_employee and updater_employee.user:
                                updater_name = f"{updater_employee.user.first_name} {updater_employee.user.last_name}".strip()
                            
                            company_name = current_task.company.name if current_task.company else "Company"
                            
                            try:
                                send_task_permission_changed_notification.delay(
                                    recipient_email=assignee.user.email,
                                    recipient_name=f"{assignee.user.first_name} {assignee.user.last_name}".strip(),
                                    recipient_user_id=str(assignee.user_id),
                                    task_id=str(current_task.id),
                                    task_name=current_task.name,
                                    old_permission=old_permission,
                                    new_permission=add_item.permission,
                                    changed_by_name=updater_name,
                                    company_id=str(company_id),
                                    company_name=company_name,
                                )
                            except Exception as e:
                                print(f"[TASK SERVICE] Warning: Failed to send permission change notification: {str(e)}")
                else:
                    # Create new assignment
                    assignment = TaskAssignment(
                        task_id=task_id,
                        employee_id=add_item.employee_id,
                        permission=add_item.permission,
                        created_by=user_id,
                        updated_by=user_id,
                    )
                    await self.repository.create_assignment(assignment)
        
        # Process remove assignments (only if remove is provided and non-empty)
        if data.remove and len(data.remove) > 0:
            for remove_item in data.remove:
                # Validate assignment exists
                assignment = await self.repository.get_assignment_by_task_and_employee(
                    task_id, remove_item.employee_id
                )
                if not assignment:
                    raise AssignmentNotFound(str(task_id), str(remove_item.employee_id))
                
                # Validate owner cannot be removed
                if current_task.owner_id == remove_item.employee_id:
                    raise CannotRemoveOwner()
                
                # Validate editors cannot remove themselves
                if (
                    assignment.permission == PERMISSION_EDITOR
                    and remove_item.employee_id == employee_id
                ):
                    raise EditorCannotRemoveSelf(str(remove_item.employee_id))
                
                # Delete assignment
                await self.repository.delete_assignment(assignment)
        
        # Refresh task to get updated assignments
        updated_task = await self.repository.get_by_id(task_id, company_id)
        
        # Recalculate derived permissions
        (
            is_owner,
            user_permission,
            can_edit_task,
            can_change_status,
            can_manage_assignments,
            is_task_read_only,
        ) = self._check_user_permission(updated_task, user_id, employee_id, role)
        
        # Build assignments
        assignments = [
            TaskAssignmentRead(
                id=assignment.id,
                employee_id=assignment.employee_id,
                permission=assignment.permission,
            )
            for assignment in updated_task.assignments
        ]
        
        # Build project info if linked
        project_info = None
        if updated_task.project:
            project_info = ProjectInfo(
                id=updated_task.project.id,
                name=updated_task.project.name,
                status=getattr(updated_task.project, "status", None),
            )
        
        # Build response
        result = TaskRead(
            task_id=updated_task.id,
            company_id=updated_task.company_id,
            owner_id=updated_task.owner_id,
            name=updated_task.name,
            description=updated_task.description,
            status=updated_task.status,
            project_id=updated_task.project_id,
            is_deleted=updated_task.is_deleted,
            created_at=updated_task.created_at,
            updated_at=updated_task.updated_at,
            created_by=updated_task.created_by,
            updated_by=updated_task.updated_by,
            project=project_info,
            assignments=assignments,
            is_owner=is_owner,
            user_permission=user_permission,
            can_edit_task=can_edit_task,
            can_change_status=can_change_status,
            can_manage_assignments=can_manage_assignments,
            is_task_read_only=is_task_read_only,
        )
        
        # Attach ETag to result for router
        result._etag = generate_etag(updated_task.updated_at)
        result._last_modified = updated_task.updated_at
        
        # Send notifications
        # Get updater name
        updater_employee = await self.repository.get_employee_by_id(employee_id, company_id) if employee_id else None
        updater_name = "Unknown"
        if updater_employee and updater_employee.user:
            updater_name = f"{updater_employee.user.first_name} {updater_employee.user.last_name}".strip()
        
        # Get company name
        company_name = updated_task.company.name if updated_task.company else "Company"
        
        # Get project name
        project_name = updated_task.project.name if updated_task.project else None
        
        # Notify newly assigned employees
        if data.add and len(data.add) > 0:
            for add_item in data.add:
                assignee = await self.repository.get_employee_by_id(add_item.employee_id, company_id)
                if assignee and assignee.user:
                    try:
                        send_task_assigned_notification.delay(
                            recipient_email=assignee.user.email,
                            recipient_name=f"{assignee.user.first_name} {assignee.user.last_name}".strip(),
                            recipient_user_id=str(assignee.user_id),
                            task_id=str(updated_task.id),
                            task_name=updated_task.name,
                            task_description=updated_task.description or "",
                            permission=add_item.permission,
                            assigned_by_name=updater_name,
                            project_name=project_name or "",
                            company_id=str(company_id),
                            company_name=company_name,
                        )
                    except Exception as e:
                        print(f"[TASK SERVICE] Warning: Failed to send assignment notification: {str(e)}")
        
        # Notify removed employees
        if data.remove and len(data.remove) > 0:
            for remove_item in data.remove:
                removed_employee = await self.repository.get_employee_by_id(remove_item.employee_id, company_id)
                if removed_employee and removed_employee.user:
                    try:
                        send_task_unassigned_notification.delay(
                            recipient_email=removed_employee.user.email,
                            recipient_name=f"{removed_employee.user.first_name} {removed_employee.user.last_name}".strip(),
                            recipient_user_id=str(removed_employee.user_id),
                            task_id=str(updated_task.id),
                            task_name=updated_task.name,
                            removed_by_name=updater_name,
                            company_id=str(company_id),
                            company_name=company_name,
                        )
                    except Exception as e:
                        print(f"[TASK SERVICE] Warning: Failed to send unassignment notification: {str(e)}")
        
        return result

    async def delete_task(
        self,
        task_id: UUID,
        company_id: UUID,
        user_id: UUID,
        employee_id: Optional[UUID],
        role: str,
        if_match: Optional[str] = None,
    ) -> None:
        """Hard delete a task (permanent removal).
        
        Based on F8_api_spec.md Section 4.3.7 - DELETE /api/v1/company/tasks/{task_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Business Logic:
        - Validates task exists and belongs to company
        - Checks visibility access
        - Validates ETag (If-Match header required)
        - Validates user permission (owner, CEO, or Manager)
        - Hard deletes task (sets is_deleted = True)
        - Returns None (204 No Content response)
        """
        # Get current task
        current_task = await self.repository.get_by_id(task_id, company_id)
        if not current_task:
            raise TaskNotFound(str(task_id))
        
        # Check visibility access
        self._check_visibility_access(current_task, user_id, employee_id, role)
        
        # Validate ETag (If-Match header required)
        if not if_match:
            raise PreconditionRequiredError(
                message="If-Match header required",
                error_code="PRECONDITION_REQUIRED",
                details=[{"field": "etag", "issue": "If-Match header required"}],
            )
        
        current_etag = generate_etag(current_task.updated_at)
        if if_match != current_etag:
            raise PreconditionFailedError(
                message="Resource has been modified since retrieval. Please fetch the latest version and retry.",
                error_code="PRECONDITION_FAILED",
                details=[
                    {
                        "field": "etag",
                        "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry.",
                    }
                ],
            )
        
        # Check permissions (owner, CEO, or Manager can delete)
        role_lower = role.lower() if role else ""
        (
            is_owner,
            _,
            _,
            _,
            _,
            _,
        ) = self._check_user_permission(current_task, user_id, employee_id, role)
        
        if not is_owner and role_lower not in ["ceo", "manager"]:
            raise InsufficientPermissionsDelete()
        
        # Send notifications before deleting
        # Get deleter name
        deleter_employee = await self.repository.get_employee_by_id(employee_id, company_id) if employee_id else None
        deleter_name = "Unknown"
        if deleter_employee and deleter_employee.user:
            deleter_name = f"{deleter_employee.user.first_name} {deleter_employee.user.last_name}".strip()
        
        # Get company name
        company_name = current_task.company.name if current_task.company else "Company"
        
        # Notify owner (if not the deleter)
        if current_task.owner and current_task.owner.user and current_task.owner_id != employee_id:
            try:
                send_task_deleted_notification.delay(
                    recipient_email=current_task.owner.user.email,
                    recipient_name=f"{current_task.owner.user.first_name} {current_task.owner.user.last_name}".strip(),
                    recipient_user_id=str(current_task.owner.user_id),
                    task_id=str(current_task.id),
                    task_name=current_task.name,
                    deleted_by_name=deleter_name,
                    company_id=str(company_id),
                    company_name=company_name,
                )
            except Exception as e:
                print(f"[TASK SERVICE] Warning: Failed to send deletion notification to owner: {str(e)}")
        
        # Notify all assignees (except the deleter)
        for assignment in current_task.assignments:
            if assignment.employee and assignment.employee.user and assignment.employee_id != employee_id:
                try:
                    send_task_deleted_notification.delay(
                        recipient_email=assignment.employee.user.email,
                        recipient_name=f"{assignment.employee.user.first_name} {assignment.employee.user.last_name}".strip(),
                        recipient_user_id=str(assignment.employee.user_id),
                        task_id=str(current_task.id),
                        task_name=current_task.name,
                        deleted_by_name=deleter_name,
                        company_id=str(company_id),
                        company_name=company_name,
                    )
                except Exception as e:
                    print(f"[TASK SERVICE] Warning: Failed to send deletion notification to assignee: {str(e)}")
        
        # Hard delete task
        await self.repository.delete(current_task)
        
        # Return None (router will return 204 No Content)
        return None
