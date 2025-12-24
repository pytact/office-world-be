"""Domain-specific exceptions for Task Management module.

Based on F8_api_spec.md - Task Management & Assignment (F-008).
All exceptions extend base exception classes from src.exceptions.
"""

from uuid import UUID
from src.exceptions import (
    NotFoundError,
    ConflictError,
    ValidationError,
    ForbiddenError,
    BadRequestError,
)
from src.tasks.constants import (
    ERROR_TASK_NOT_FOUND,
    ERROR_TASK_ALREADY_DELETED,
    ERROR_TASK_TERMINAL_STATE,
    ERROR_TASK_PROJECT_INACTIVE,
    ERROR_ASSIGNMENT_NOT_FOUND,
    ERROR_DUPLICATE_ASSIGNMENT,
    ERROR_EMPLOYEE_NOT_FOUND,
    ERROR_PROJECT_NOT_FOUND,
    ERROR_PROJECT_NOT_ACTIVE,
    ERROR_INVALID_STATUS,
    ERROR_INVALID_INITIAL_STATUS,
    ERROR_INVALID_PERMISSION,
    ERROR_CANNOT_REMOVE_OWNER,
    ERROR_EDITOR_CANNOT_REMOVE_SELF,
    ERROR_INSUFFICIENT_PERMISSIONS_VIEW,
    ERROR_INSUFFICIENT_PERMISSIONS_EDIT,
    ERROR_INSUFFICIENT_PERMISSIONS_STATUS,
    ERROR_INSUFFICIENT_PERMISSIONS_ASSIGNMENTS,
    ERROR_INSUFFICIENT_PERMISSIONS_DELETE,
    ERROR_HR_READ_ONLY,
    ERROR_CODE_TASK_NOT_FOUND,
    ERROR_CODE_TASK_ALREADY_DELETED,
    ERROR_CODE_TASK_TERMINAL_STATE,
    ERROR_CODE_TASK_PROJECT_INACTIVE,
    ERROR_CODE_ASSIGNMENT_NOT_FOUND,
    ERROR_CODE_DUPLICATE_ASSIGNMENT,
    ERROR_CODE_EMPLOYEE_NOT_FOUND,
    ERROR_CODE_PROJECT_NOT_FOUND,
    ERROR_CODE_PROJECT_NOT_ACTIVE,
    ERROR_CODE_INVALID_STATUS,
    ERROR_CODE_INVALID_INITIAL_STATUS,
    ERROR_CODE_INVALID_PERMISSION,
    ERROR_CODE_CANNOT_REMOVE_OWNER,
    ERROR_CODE_EDITOR_CANNOT_REMOVE_SELF,
    ERROR_CODE_INSUFFICIENT_PERMISSIONS,
    ERROR_CODE_HR_READ_ONLY,
)


class TaskNotFound(NotFoundError):
    """Task not found exception."""

    def __init__(self, task_id: str):
        super().__init__(resource="Task", resource_id=task_id)


class TaskAlreadyDeleted(ValidationError):
    """Task is already deleted."""

    def __init__(self, task_id: str):
        super().__init__(
            message=ERROR_TASK_ALREADY_DELETED,
            error_code=ERROR_CODE_TASK_ALREADY_DELETED,
            details=[{"field": "task_id", "issue": ERROR_TASK_ALREADY_DELETED}],
        )


class TaskTerminalState(ValidationError):
    """Task is in terminal state and cannot be modified."""

    def __init__(self, status: str):
        super().__init__(
            message=f"{ERROR_TASK_TERMINAL_STATE}. Current status: {status}",
            error_code=ERROR_CODE_TASK_TERMINAL_STATE,
            details=[
                {
                    "field": "status",
                    "issue": f"{ERROR_TASK_TERMINAL_STATE}. Current status: {status}",
                }
            ],
        )


class TaskProjectInactive(ValidationError):
    """Task is linked to an INACTIVE or COMPLETED project."""

    def __init__(self, project_status: str):
        super().__init__(
            message=f"{ERROR_TASK_PROJECT_INACTIVE}. Project status: {project_status}",
            error_code=ERROR_CODE_TASK_PROJECT_INACTIVE,
            details=[
                {
                    "field": "project_id",
                    "issue": f"{ERROR_TASK_PROJECT_INACTIVE}. Project status: {project_status}",
                }
            ],
        )


class AssignmentNotFound(NotFoundError):
    """Assignment not found exception."""

    def __init__(self, task_id: str, employee_id: str):
        super().__init__(
            resource="Assignment",
            resource_id=f"task_id={task_id}, employee_id={employee_id}",
        )


class DuplicateAssignment(ConflictError):
    """Employee is already assigned to this task."""

    def __init__(self, employee_id: str):
        super().__init__(
            message=f"{ERROR_DUPLICATE_ASSIGNMENT}. Employee ID: {employee_id}",
            error_code=ERROR_CODE_DUPLICATE_ASSIGNMENT,
            details=[
                {
                    "field": "employee_id",
                    "issue": f"{ERROR_DUPLICATE_ASSIGNMENT}. Employee ID: {employee_id}",
                }
            ],
        )


class EmployeeNotFound(NotFoundError):
    """Employee not found or not in same company."""

    def __init__(self, employee_id: str):
        super().__init__(resource="Employee", resource_id=employee_id)


class ProjectNotFound(NotFoundError):
    """Project not found exception."""

    def __init__(self, project_id: str):
        super().__init__(resource="Project", resource_id=project_id)


class ProjectNotActive(ValidationError):
    """Project is not ACTIVE."""

    def __init__(self, project_id: str, project_status: str):
        super().__init__(
            message=f"{ERROR_PROJECT_NOT_ACTIVE}. Project ID: {project_id}, Status: {project_status}",
            error_code=ERROR_CODE_PROJECT_NOT_ACTIVE,
            details=[
                {
                    "field": "project_id",
                    "issue": f"{ERROR_PROJECT_NOT_ACTIVE}. Project status: {project_status}",
                }
            ],
        )


class InvalidStatus(ValidationError):
    """Invalid task status."""

    def __init__(self, status: str):
        super().__init__(
            message=f"{ERROR_INVALID_STATUS}. Provided status: {status}",
            error_code=ERROR_CODE_INVALID_STATUS,
            details=[
                {
                    "field": "status",
                    "issue": f"{ERROR_INVALID_STATUS}. Valid statuses: TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED",
                }
            ],
        )


class InvalidInitialStatus(ValidationError):
    """Initial task status must be TODO."""

    def __init__(self, status: str):
        super().__init__(
            message=f"{ERROR_INVALID_INITIAL_STATUS}. Provided status: {status}",
            error_code=ERROR_CODE_INVALID_INITIAL_STATUS,
            details=[
                {
                    "field": "status",
                    "issue": f"{ERROR_INVALID_INITIAL_STATUS}. Provided status: {status}",
                }
            ],
        )


class InvalidPermission(ValidationError):
    """Invalid assignment permission."""

    def __init__(self, permission: str):
        super().__init__(
            message=f"{ERROR_INVALID_PERMISSION}. Provided permission: {permission}",
            error_code=ERROR_CODE_INVALID_PERMISSION,
            details=[
                {
                    "field": "permission",
                    "issue": f"{ERROR_INVALID_PERMISSION}. Valid permissions: VIEWER, EDITOR",
                }
            ],
        )


class CannotRemoveOwner(ValidationError):
    """Cannot remove task owner from assignments."""

    def __init__(self):
        super().__init__(
            message=ERROR_CANNOT_REMOVE_OWNER,
            error_code=ERROR_CODE_CANNOT_REMOVE_OWNER,
            details=[{"field": "remove", "issue": ERROR_CANNOT_REMOVE_OWNER}],
        )


class EditorCannotRemoveSelf(ValidationError):
    """Editors cannot remove themselves from task assignments."""

    def __init__(self, employee_id: str):
        super().__init__(
            message=f"{ERROR_EDITOR_CANNOT_REMOVE_SELF}. Employee ID: {employee_id}",
            error_code=ERROR_CODE_EDITOR_CANNOT_REMOVE_SELF,
            details=[
                {
                    "field": "remove",
                    "issue": f"{ERROR_EDITOR_CANNOT_REMOVE_SELF}. Employee ID: {employee_id}",
                }
            ],
        )


class InsufficientPermissionsView(ForbiddenError):
    """Insufficient permissions to view task."""

    def __init__(self):
        super().__init__(
            message=ERROR_INSUFFICIENT_PERMISSIONS_VIEW,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[{"field": "task", "issue": ERROR_INSUFFICIENT_PERMISSIONS_VIEW}],
        )


class InsufficientPermissionsEdit(ForbiddenError):
    """Insufficient permissions to edit task."""

    def __init__(self):
        super().__init__(
            message=ERROR_INSUFFICIENT_PERMISSIONS_EDIT,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[{"field": "task", "issue": ERROR_INSUFFICIENT_PERMISSIONS_EDIT}],
        )


class InsufficientPermissionsStatus(ForbiddenError):
    """Insufficient permissions to change task status."""

    def __init__(self):
        super().__init__(
            message=ERROR_INSUFFICIENT_PERMISSIONS_STATUS,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[
                {"field": "status", "issue": ERROR_INSUFFICIENT_PERMISSIONS_STATUS}
            ],
        )


class InsufficientPermissionsAssignments(ForbiddenError):
    """Insufficient permissions to manage task assignments."""

    def __init__(self):
        super().__init__(
            message=ERROR_INSUFFICIENT_PERMISSIONS_ASSIGNMENTS,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[
                {
                    "field": "assignments",
                    "issue": ERROR_INSUFFICIENT_PERMISSIONS_ASSIGNMENTS,
                }
            ],
        )


class InsufficientPermissionsDelete(ForbiddenError):
    """Insufficient permissions to delete task."""

    def __init__(self):
        super().__init__(
            message=ERROR_INSUFFICIENT_PERMISSIONS_DELETE,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[{"field": "task", "issue": ERROR_INSUFFICIENT_PERMISSIONS_DELETE}],
        )


class HRReadOnly(ForbiddenError):
    """HR role has read-only access."""

    def __init__(self, operation: str):
        super().__init__(
            message=f"{ERROR_HR_READ_ONLY}. Operation: {operation}",
            error_code=ERROR_CODE_HR_READ_ONLY,
            details=[
                {"field": "role", "issue": f"{ERROR_HR_READ_ONLY}. Operation: {operation}"}
            ],
        )
