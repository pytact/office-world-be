"""Domain-specific constants for Audit Logging & Activity History module.

Based on F11_api_spec.md - Audit Logging & Activity History (F-011).
Static values only - no functions, no computed values, no logic.
"""

# ============================================================================
# Error Messages
# ============================================================================

ERROR_AUDIT_LOG_NOT_FOUND = "Audit log not found or does not belong to your company."
ERROR_INSUFFICIENT_PERMISSIONS = "You do not have permission to access audit logs."
ERROR_EMPLOYEE_NO_ACCESS = "Employee role does not have access to audit logs."
ERROR_SUPERADMIN_BLOCKED = "SuperAdmin role is blocked from accessing audit logs."
ERROR_MANAGER_TABLE_RESTRICTION = "Manager role can only access audit logs for tasks, projects, or task_assignments."
ERROR_INVALID_DATE_FORMAT = "Invalid date format. Must be ISO 8601 datetime with UTC (e.g., 2024-01-20T10:30:00Z)."
ERROR_INVALID_SORT_FIELD = "Invalid sort field. Only 'created_at' is allowed."
ERROR_INVALID_DATE_RANGE = "Start date must be less than or equal to end date."

# ============================================================================
# Success Messages
# ============================================================================

SUCCESS_AUDIT_LOGS_RETRIEVED = "Audit logs retrieved successfully"
SUCCESS_AUDIT_LOG_RETRIEVED = "Audit log retrieved successfully"

# ============================================================================
# Role-Based Access Constants
# ============================================================================

# Manager role allowed table names
MANAGER_ALLOWED_TABLES = ["tasks", "projects", "task_assignments"]

# ============================================================================
# Error Codes
# ============================================================================

ERROR_CODE_AUDIT_LOG_NOT_FOUND = "AUDIT_LOG_NOT_FOUND"
ERROR_CODE_INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
ERROR_CODE_VALIDATION_FAILED = "VALIDATION_FAILED"

# ============================================================================
# Actor Display Name Constants
# ============================================================================

ACTOR_DISPLAY_NAME_SYSTEM = "SYSTEM"
