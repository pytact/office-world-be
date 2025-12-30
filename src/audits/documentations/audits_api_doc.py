"""API documentation for Audit Logging & Activity History endpoints.

Based on F11_api_spec.md Section 4.3 - API Documentation Class (Rule 10).
All endpoint documentation uses centralized AuditLogApiDocs class structure.
"""

from typing import ClassVar


class AuditLogApiDocs:
    """API documentation for AuditLog endpoints"""
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list audit logs with pagination, filtering, and sorting",
        "description": "Retrieves a paginated list of audit logs for the authenticated user's company. Supports filtering by date range, action_code, and table_name. Supports sorting by created_at (default descending). CEO and HR see all company audit logs. Manager sees only logs where table_name is tasks, projects, or task_assignments. Employee role has no access. SuperAdmin is blocked. Company is determined from JWT org_id claim. Requires JWT authentication."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get detailed audit log information",
        "description": "Retrieves detailed information for a specific audit log including old_values, new_values, IP address, and user agent. CEO and HR can access any company audit log. Manager can only access logs where table_name is tasks, projects, or task_assignments (returns 403 if outside scope). Employee role has no access. SuperAdmin is blocked. Company is determined from JWT org_id claim. Requires JWT authentication."
    }
