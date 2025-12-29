"""Pydantic schemas for Task Management module.

Based on F8_api_spec.md - Task Management & Assignment (F-008).
Request schemas define input validation, Response schemas define output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from src.pagination import PagedCollection
from src.tasks.constants import (
    STATUS_TODO,
    STATUS_IN_PROGRESS,
    STATUS_HALT,
    STATUS_REVIEW,
    STATUS_DONE,
    STATUS_CANCELLED,
    PERMISSION_VIEWER,
    PERMISSION_EDITOR,
)


# ============================================================================
# Request Schemas (Input Validation)
# ============================================================================

class TaskAssignmentAdd(BaseModel):
    """Request schema for adding a task assignment.
    
    Based on F8_api_spec.md Section 4.3.6 - PATCH /api/v1/company/tasks/{task_id}/assignments.
    Also used in TaskCreate for initial assignments.
    """
    
    employee_id: UUID = Field(
        ...,
        description="Employee to assign (UUID format, must be employee in same company)",
    )
    permission: str = Field(
        ...,
        description="Assignment permission (VIEWER, EDITOR)",
    )
    
    @field_validator("permission")
    @classmethod
    def validate_permission(cls, v: str) -> str:
        """Validate permission enum value."""
        if v not in [PERMISSION_VIEWER, PERMISSION_EDITOR]:
            raise ValueError("Invalid permission. Valid values: VIEWER, EDITOR")
        return v
    
    model_config = ConfigDict(from_attributes=True)


class TaskListQuery(BaseModel):
    """Query schema for listing tasks with pagination and filtering.
    
    Based on F8_api_spec.md Section 4.3.1 - GET /api/v1/company/tasks.
    Query parameters MUST be defined using query schema class with Depends() pattern.
    """
    
    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    status: Optional[str] = Field(None, description="Filter by task status: TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED")
    project_id: Optional[str] = Field(None, description="Filter by project ID (UUID format)")
    search: Optional[str] = Field(None, description="Search by task name (case-insensitive partial match)")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, name, status")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status enum value."""
        if v is not None and v not in [STATUS_TODO, STATUS_IN_PROGRESS, STATUS_HALT, STATUS_REVIEW, STATUS_DONE, STATUS_CANCELLED]:
            raise ValueError(f"Invalid status. Valid values: TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED")
        return v
    
    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort_by field."""
        valid_fields = ["created_at", "updated_at", "name", "status"]
        if v not in valid_fields:
            raise ValueError(f"Invalid sort_by. Valid values: {', '.join(valid_fields)}")
        return v
    
    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort_order value."""
        if v not in ["asc", "desc"]:
            raise ValueError("Invalid sort_order. Valid values: asc, desc")
        return v
    
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    """Request schema for creating a new task.
    
    Based on F8_api_spec.md Section 4.3.2 - POST /api/v1/company/tasks.
    The creator will always be the owner. Use assignments to assign tasks to employees.
    """
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Task title (required, min 1, max 255 characters)",
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Task details (optional, max 5000 characters)",
    )
    status: Optional[str] = Field(
        STATUS_TODO,
        description="Initial task status (must be TODO)",
    )
    project_id: Optional[UUID] = Field(
        None,
        description="Optional project linkage (UUID format, must reference ACTIVE project)",
    )
    assignments: Optional[list[TaskAssignmentAdd]] = Field(
        None,
        description="Optional list of employees to assign the task to with their permissions (VIEWER or EDITOR). The creator is always the owner.",
    )
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate initial status must be TODO."""
        if v is not None and v != STATUS_TODO:
            raise ValueError("Initial task status must be TODO. Cannot create task with other statuses.")
        return v or STATUS_TODO
    
    model_config = ConfigDict(from_attributes=True)


class TaskAssignmentRemove(BaseModel):
    """Request schema for removing a task assignment.
    
    Based on F8_api_spec.md Section 4.3.6 - PATCH /api/v1/company/tasks/{task_id}/assignments.
    """
    
    employee_id: UUID = Field(
        ...,
        description="Employee to unassign (UUID format, must be existing assignment)",
    )
    
    model_config = ConfigDict(from_attributes=True)


class TaskAssignmentUpdate(BaseModel):
    """Request schema for updating task assignments.
    
    Based on F8_api_spec.md Section 4.3.6 - PATCH /api/v1/company/tasks/{task_id}/assignments.
    Both add and remove are optional. If provided, only that operation will be performed.
    Empty arrays are allowed and will be ignored (no operation performed).
    """
    
    add: Optional[list[TaskAssignmentAdd]] = Field(
        None,
        description="Assignments to add (array of assignment objects). Optional - if not provided, no additions will be made.",
    )
    remove: Optional[list[TaskAssignmentRemove]] = Field(
        None,
        description="Assignments to remove (array of employee_id objects). Optional - if not provided, no removals will be made.",
    )
    
    @model_validator(mode="before")
    @classmethod
    def filter_empty_values(cls, data):
        """Filter out empty strings and None values from arrays before validation.
        
        This allows empty strings in remove/add arrays to be filtered out gracefully
        instead of causing validation errors.
        """
        if isinstance(data, dict):
            # Filter empty strings from remove array
            if "remove" in data and isinstance(data["remove"], list):
                filtered_remove = []
                for item in data["remove"]:
                    if item is None:
                        continue
                    # Handle both dict and string formats
                    if isinstance(item, dict):
                        emp_id = item.get("employee_id")
                        if emp_id is not None and emp_id != "":
                            filtered_remove.append(item)
                    elif isinstance(item, str) and item != "":
                        # If it's a string, convert to dict format
                        try:
                            UUID(item)  # Validate it's a valid UUID
                            filtered_remove.append({"employee_id": item})
                        except (ValueError, TypeError):
                            continue  # Skip invalid UUIDs
                
                # If remove becomes empty, set to None
                data["remove"] = filtered_remove if filtered_remove else None
            
            # Filter empty strings from add array
            if "add" in data and isinstance(data["add"], list):
                filtered_add = []
                for item in data["add"]:
                    if item is None:
                        continue
                    if isinstance(item, dict):
                        emp_id = item.get("employee_id")
                        if emp_id is not None and emp_id != "":
                            filtered_add.append(item)
                
                # If add becomes empty, set to None
                data["add"] = filtered_add if filtered_add else None
        
        return data
    
    model_config = ConfigDict(from_attributes=True)


class TaskUpdate(BaseModel):
    """Request schema for updating task details.
    
    Based on F8_api_spec.md Section 4.3.4 - PATCH /api/v1/company/tasks/{task_id}.
    Can update name, description, status, and assignments in a single request.
    All fields are optional - only provided fields will be updated.
    """
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Task title (min 1 character, max 255 characters if provided)",
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Task details (max 5000 characters if provided)",
    )
    status: Optional[str] = Field(
        None,
        description="New task status (TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED). Owner or Editor can change status.",
    )
    assignments: Optional[TaskAssignmentUpdate] = Field(
        None,
        description="Task assignments to add or remove. Only owner can manage assignments.",
    )
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status enum value."""
        if v is not None:
            valid_statuses = [STATUS_TODO, STATUS_IN_PROGRESS, STATUS_HALT, STATUS_REVIEW, STATUS_DONE, STATUS_CANCELLED]
            if v not in valid_statuses:
                raise ValueError(f"Invalid status. Valid values: {', '.join(valid_statuses)}")
        return v
    
    model_config = ConfigDict(from_attributes=True)


class TaskStatusUpdate(BaseModel):
    """Request schema for changing task status.
    
    Based on F8_api_spec.md Section 4.3.5 - PATCH /api/v1/company/tasks/{task_id}/status.
    """
    
    status: str = Field(
        ...,
        description="New task status (TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED)",
    )
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status enum value."""
        valid_statuses = [STATUS_TODO, STATUS_IN_PROGRESS, STATUS_HALT, STATUS_REVIEW, STATUS_DONE, STATUS_CANCELLED]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Valid values: {', '.join(valid_statuses)}")
        return v
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas (Output Structure)
# ============================================================================

class ProjectInfo(BaseModel):
    """Project information in task response.
    
    Based on F8_api_spec.md Section 4.3.3 - Project object in task detail response.
    """
    
    id: UUID = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    status: Optional[str] = Field(None, description="Project status (ACTIVE, INACTIVE, COMPLETED)")
    
    model_config = ConfigDict(from_attributes=True)


class TaskAssignmentRead(BaseModel):
    """Response schema for task assignment.
    
    Based on F8_api_spec.md Section 4.3.3 - Assignment object in task detail response.
    """
    
    id: UUID = Field(..., description="Assignment ID")
    employee_id: UUID = Field(..., description="Assigned employee ID")
    permission: str = Field(..., description="Assignment permission (VIEWER, EDITOR)")
    
    model_config = ConfigDict(from_attributes=True)


class TaskRead(BaseModel):
    """Response schema for task detail.
    
    Based on F8_api_spec.md Section 4.3.3 - GET /api/v1/company/tasks/{task_id}.
    """
    
    task_id: UUID = Field(..., description="Unique task identifier", alias="id")
    company_id: UUID = Field(..., description="Owning company")
    owner_id: UUID = Field(..., description="Task creator/owner (immutable)")
    name: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task details")
    status: str = Field(..., description="Task lifecycle state")
    project_id: Optional[UUID] = Field(None, description="Optional project linkage")
    is_deleted: bool = Field(..., description="Hard delete marker")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    created_by: Optional[UUID] = Field(None, description="Creator user ID")
    updated_by: Optional[UUID] = Field(None, description="Last modifier user ID")
    project: Optional[ProjectInfo] = Field(None, description="Project information (if linked)")
    assignments: list[TaskAssignmentRead] = Field(default_factory=list, description="Task assignments")
    
    # Derived permission fields (computed in service)
    is_owner: bool = Field(..., description="True if authenticated user is task owner")
    user_permission: str = Field(..., description="User permission: OWNER, EDITOR, or VIEWER")
    can_edit_task: bool = Field(..., description="True if owner or editor")
    can_change_status: bool = Field(..., description="True if owner or editor")
    can_manage_assignments: bool = Field(..., description="True if owner only")
    is_task_read_only: bool = Field(..., description="True if task is in terminal state or user is VIEWER")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TaskSummary(BaseModel):
    """Response schema for task summary in list.
    
    Based on F8_api_spec.md Section 4.3.1 - GET /api/v1/company/tasks (list response).
    """
    
    task_id: UUID = Field(..., description="Unique task identifier", alias="id")
    name: str = Field(..., description="Task title")
    status: str = Field(..., description="Task lifecycle state")
    project_id: Optional[UUID] = Field(None, description="Optional project linkage")
    owner_id: UUID = Field(..., description="Task creator/owner")
    project: Optional[ProjectInfo] = Field(None, description="Project information (if linked)")
    assignments: list[TaskAssignmentRead] = Field(default_factory=list, description="Task assignments")
    is_owner: bool = Field(..., description="True if authenticated user is task owner")
    user_permission: str = Field(..., description="User permission: OWNER, EDITOR, or VIEWER")
    can_edit_task: bool = Field(..., description="True if owner or editor")
    can_change_status: bool = Field(..., description="True if owner or editor")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ============================================================================
# Paginated Response
# ============================================================================

class TaskPaginatedResponse(PagedCollection[TaskSummary]):
    """Paginated response wrapper for task list.
    
    Based on F8_api_spec.md Section 4.3.1 - GET /api/v1/company/tasks.
    Extends PagedCollection with task-specific structure.
    """
    
    pass
