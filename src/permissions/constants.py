"""Domain-specific constants for Permissions System module.

Based on F2_db_spec.md - Role codes, permission structures, and error messages.
"""

# Error Messages
ERROR_ROLE_NOT_FOUND = "Role not found or you do not have access to this role"
ERROR_INVALID_REQUEST = "Invalid request format"
ERROR_VALIDATION_FAILED = "Request validation failed"
ERROR_INVALID_ROLE_CODE = "Invalid role code"
ERROR_DUPLICATE_ROLE_CODE = "Role code already exists"
ERROR_DUPLICATE_ROLE_NAME = "Role name already exists"
ERROR_INVALID_PERMISSIONS = "Invalid permissions format"
ERROR_INVALID_SORT_FIELD = "Invalid sort field"
ERROR_INVALID_SORT_ORDER = "Invalid sort order"
ERROR_PRECONDITION_REQUIRED = "If-Match header is required for update operations"
ERROR_PRECONDITION_FAILED = "Resource version mismatch. The resource was modified by another user"
ERROR_CANNOT_DELETE_ROLE_IN_USE = "Cannot delete role that is assigned to users"

# Success Messages
SUCCESS_ROLES_RETRIEVED = "Roles retrieved successfully"
SUCCESS_ROLE_RETRIEVED = "Role retrieved successfully"
SUCCESS_ROLE_CREATED = "Role created successfully"
SUCCESS_ROLE_UPDATED = "Role updated successfully"
SUCCESS_ROLE_DELETED = "Role deleted successfully"

# Error Codes
ERROR_CODE_ROLE_NOT_FOUND = "ROLE_NOT_FOUND"
ERROR_CODE_INVALID_REQUEST = "INVALID_REQUEST"
ERROR_CODE_VALIDATION_FAILED = "VALIDATION_FAILED"
ERROR_CODE_INVALID_ROLE_CODE = "INVALID_ROLE_CODE"
ERROR_CODE_DUPLICATE_ROLE_CODE = "DUPLICATE_ROLE_CODE"
ERROR_CODE_DUPLICATE_ROLE_NAME = "DUPLICATE_ROLE_NAME"
ERROR_CODE_INVALID_PERMISSIONS = "INVALID_PERMISSIONS"
ERROR_CODE_INVALID_SORT_FIELD = "INVALID_SORT_FIELD"
ERROR_CODE_INVALID_SORT_ORDER = "INVALID_SORT_ORDER"
ERROR_CODE_PRECONDITION_REQUIRED = "PRECONDITION_REQUIRED"
ERROR_CODE_PRECONDITION_FAILED = "PRECONDITION_FAILED"
ERROR_CODE_CANNOT_DELETE_ROLE_IN_USE = "CANNOT_DELETE_ROLE_IN_USE"

# Role Codes (from F2_db_spec.md Section 7.1)
ROLE_CODE_SUPERADMIN = "superadmin"
ROLE_CODE_CEO = "ceo"
ROLE_CODE_HR = "hr"
ROLE_CODE_MANAGER = "manager"
ROLE_CODE_EMPLOYEE = "employee"

# Valid Role Codes (predefined roles)
VALID_ROLE_CODES = [
    ROLE_CODE_SUPERADMIN,
    ROLE_CODE_CEO,
    ROLE_CODE_HR,
    ROLE_CODE_MANAGER,
    ROLE_CODE_EMPLOYEE,
]

# Sort Fields
SORT_FIELD_CREATED_AT = "created_at"
SORT_FIELD_UPDATED_AT = "updated_at"
SORT_FIELD_NAME = "name"
SORT_FIELD_CODE = "code"

# Valid Sort Fields
VALID_SORT_FIELDS = [SORT_FIELD_CREATED_AT, SORT_FIELD_UPDATED_AT, SORT_FIELD_NAME, SORT_FIELD_CODE]

# Sort Orders
SORT_ORDER_ASC = "asc"
SORT_ORDER_DESC = "desc"

# Valid Sort Orders
VALID_SORT_ORDERS = [SORT_ORDER_ASC, SORT_ORDER_DESC]

# Pagination Defaults
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
