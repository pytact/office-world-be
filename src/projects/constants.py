"""Domain-specific constants for Project Management module.

Based on F7_api_spec.md - Project Management (F-007).
Static values only - no functions, no computed values, no logic.
"""

# ============================================================================
# Error Messages
# ============================================================================

ERROR_PROJECT_NOT_FOUND = "Project not found or you do not have access to it."
ERROR_DUPLICATE_PROJECT_NAME = "A project with this name already exists in your company."
ERROR_INVALID_STATUS = "Status must be one of: ACTIVE, INACTIVE, COMPLETED"
ERROR_PROJECT_ALREADY_DELETED = "Project not found or already deleted."
ERROR_INSUFFICIENT_PERMISSIONS = "You do not have permission to perform this operation."
ERROR_EMPLOYEE_PROJECT_ACCESS = "You can only access projects where you have assigned tasks."

# ============================================================================
# Success Messages
# ============================================================================

SUCCESS_PROJECT_CREATED = "Project created successfully"
SUCCESS_PROJECT_RETRIEVED = "Project retrieved successfully"
SUCCESS_PROJECTS_RETRIEVED = "Projects retrieved successfully"
SUCCESS_PROJECT_UPDATED = "Project updated successfully"
SUCCESS_PROJECT_DELETED = "Project deleted successfully"

# ============================================================================
# Status Values
# ============================================================================

STATUS_ACTIVE = "ACTIVE"
STATUS_INACTIVE = "INACTIVE"
STATUS_COMPLETED = "COMPLETED"

# ============================================================================
# Error Codes
# ============================================================================

ERROR_CODE_PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
ERROR_CODE_DUPLICATE_PROJECT_NAME = "DUPLICATE_PROJECT_NAME"
ERROR_CODE_INVALID_STATUS = "VALIDATION_ERROR"
ERROR_CODE_INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
ERROR_CODE_PRECONDITION_FAILED = "PRECONDITION_FAILED"
ERROR_CODE_PRECONDITION_REQUIRED = "PRECONDITION_REQUIRED"
