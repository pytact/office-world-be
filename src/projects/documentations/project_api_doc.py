"""API documentation for Project Management endpoints.

Based on F7_api_spec.md Section 8 - Swagger Documentation.
"""

from typing import ClassVar


class ProjectApiDocs:
    """API documentation for Project endpoints."""
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list projects with pagination and filtering",
        "description": "Retrieves a paginated list of projects. Supports filtering by status, search by name, and sorting. Visibility is role-based: CEO/Manager/HR see all company projects; Employees see only projects with assigned tasks."
    }
    
    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new project",
        "description": "Creates a new project within the user's company. Only CEO and Manager can create projects. Project name must be unique within the company (case-insensitive)."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get project detail with task summaries",
        "description": "Retrieves project detail including task summaries. Employees can only access projects where they have assigned tasks."
    }
    
    update: ClassVar[dict] = {
        "summary": "Purpose of this API is to update project name and/or status",
        "description": "Updates project name and/or status. Only CEO and Manager can update projects. Requires If-Match header (ETag) for concurrency control."
    }
    
    delete: ClassVar[dict] = {
        "summary": "Purpose of this API is to delete a project with cascade to tasks",
        "description": "Deletes a project using soft delete (IsDeleted marker). Cascades soft delete to all associated tasks. Only CEO and Manager can delete projects. Requires If-Match header (ETag) for concurrency control."
    }

