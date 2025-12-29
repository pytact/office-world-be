"""API documentation for Tasks endpoints.

Based on F8_api_spec.md Section 9 - Documentation Class Structure.
Centralizes Swagger/OpenAPI documentation for all task endpoints.
"""

from typing import ClassVar


class TaskApiDocs:
    """API documentation for Task endpoints"""

    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list tasks with pagination and filtering",
        "description": "Retrieves a paginated list of tasks. Supports filtering by status and project, search by name, and sorting. Visibility is role-based: CEO/Manager see all tasks, HR sees all (read-only), Employees see own/assigned tasks only.",
    }

    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new task",
        "description": "Creates a new task with required name and optional description. Task owner is automatically set to authenticated user (immutable). Initial status must be TODO. Project linkage is optional but must reference an ACTIVE project.",
    }

    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get task details",
        "description": "Retrieves full task details including assignments, project info, and derived permission fields. Access is based on visibility rules: owner, assignee, or CEO/Manager/HR roles.",
    }

    update: ClassVar[dict] = {
        "summary": "Purpose of this API is to update task name and description",
        "description": "Updates task name and/or description. Owner, Editors, CEO, and Manager can edit. CEO and Manager can edit any company task. Viewers cannot edit. Tasks in terminal states (DONE, CANCELLED) are read-only. Requires If-Match header for concurrency control.",
    }

    change_status: ClassVar[dict] = {
        "summary": "Purpose of this API is to change task status",
        "description": "Changes task status. Task owner or editor can change status. Owner and editor can move task to any status at any time. DONE and CANCELLED are terminal states. Requires If-Match header for concurrency control.",
    }

    update_assignments: ClassVar[dict] = {
        "summary": "Purpose of this API is to update task assignments",
        "description": "Adds or removes task assignments. Task owner, CEO, and Manager can manage assignments. CEO and Manager can manage assignments for any company task. Supports adding multiple assignments and removing multiple assignments in a single request. Prevents duplicate assignments. Editors cannot remove themselves. Requires If-Match header for concurrency control.",
    }

    delete: ClassVar[dict] = {
        "summary": "Purpose of this API is to hard delete a task",
        "description": "Permanently deletes a task (hard deletion with is_deleted marker). Task owner, CEO, and Manager can delete tasks. CEO and Manager can delete any company task (not limited to tasks they own). Deleted tasks are not returned in queries. Cannot be undone. Requires If-Match header for concurrency control.",
    }
