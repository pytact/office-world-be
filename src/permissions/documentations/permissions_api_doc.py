"""API documentation for Permissions System endpoints.

Based on F2_db_spec.md - API Documentation Class (Rule 10).
All endpoint documentation MUST use this centralized class structure.
"""

from typing import ClassVar


class PermissionApiDocs:
    """API documentation for Permissions System endpoints.
    
    Based on F2_db_spec.md - API Documentation Class (Rule 10).
    Router endpoints MUST reference summary and description from this class,
    NOT hardcoded strings.
    """
    
    list: ClassVar[dict] = {
        "summary": "List roles with pagination, filtering, and sorting",
        "description": "Retrieves a paginated list of all roles. Supports filtering by role code and name (partial match), and sorting by created_at, updated_at, name, or code. All roles are visible to authenticated users. Soft-deleted roles are excluded from results."
    }
    
    get: ClassVar[dict] = {
        "summary": "Get role by ID",
        "description": "Retrieves detailed role information by its unique identifier. Includes role name, code, permissions structure, and audit fields (created_at, updated_at, deleted_at, created_by, updated_by, deleted_by). Returns 404 if role not found or soft-deleted. Supports ETag-based cache validation with If-None-Match header."
    }
