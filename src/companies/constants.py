"""Domain-specific constants for Companies System module.

Based on F1A_api_spec.md - Company management, error messages, and success messages.
"""

# Error Messages
ERROR_COMPANY_NOT_FOUND = "Company not found or you do not have access to this company"
ERROR_INVALID_REQUEST = "Invalid request format"
ERROR_VALIDATION_FAILED = "Request validation failed"
ERROR_DUPLICATE_COMPANY_NAME = "Company name already exists"
ERROR_DUPLICATE_COMPANY_SLUG = "Company slug already exists"
ERROR_INVALID_SORT_FIELD = "Invalid sort field"
ERROR_INVALID_SORT_ORDER = "Invalid sort order"
ERROR_PRECONDITION_REQUIRED = "If-Match header is required for update operations"
ERROR_PRECONDITION_FAILED = "Resource version mismatch. The resource was modified by another user"
ERROR_CANNOT_DELETE_COMPANY_IN_USE = "Cannot delete company that has active users"

# Success Messages
SUCCESS_COMPANIES_RETRIEVED = "Companies retrieved successfully"
SUCCESS_COMPANY_RETRIEVED = "Company retrieved successfully"
SUCCESS_COMPANY_CREATED = "Company created successfully"
SUCCESS_COMPANY_UPDATED = "Company updated successfully"
SUCCESS_COMPANY_DELETED = "Company deleted successfully"
SUCCESS_COMPANY_PROFILE_RETRIEVED = "Company profile retrieved successfully"
SUCCESS_COMPANY_PROFILE_UPDATED = "Company profile updated successfully"

# Error Codes
ERROR_CODE_COMPANY_NOT_FOUND = "COMPANY_NOT_FOUND"
ERROR_CODE_INVALID_REQUEST = "INVALID_REQUEST"
ERROR_CODE_VALIDATION_FAILED = "VALIDATION_FAILED"
ERROR_CODE_DUPLICATE_COMPANY_NAME = "DUPLICATE_COMPANY_NAME"
ERROR_CODE_DUPLICATE_COMPANY_SLUG = "DUPLICATE_COMPANY_SLUG"
ERROR_CODE_INVALID_SORT_FIELD = "INVALID_SORT_FIELD"
ERROR_CODE_INVALID_SORT_ORDER = "INVALID_SORT_ORDER"
ERROR_CODE_PRECONDITION_REQUIRED = "PRECONDITION_REQUIRED"
ERROR_CODE_PRECONDITION_FAILED = "PRECONDITION_FAILED"
ERROR_CODE_BUSINESS_RULE_FAILED = "BUSINESS_RULE_FAILED"
ERROR_CODE_CANNOT_DELETE_COMPANY_IN_USE = "CANNOT_DELETE_COMPANY_IN_USE"

# Sort Fields
SORT_FIELD_CREATED_AT = "created_at"
SORT_FIELD_UPDATED_AT = "updated_at"
SORT_FIELD_NAME = "name"
SORT_FIELD_SLUG = "slug"

# Valid Sort Fields (based on F4_api_spec.md)
VALID_SORT_FIELDS = [
    SORT_FIELD_CREATED_AT,
    SORT_FIELD_UPDATED_AT,
    SORT_FIELD_NAME,
    SORT_FIELD_SLUG,
    "is_active",  # Added per F4 spec
]

# Sort Orders
SORT_ORDER_ASC = "asc"
SORT_ORDER_DESC = "desc"

# Valid Sort Orders
VALID_SORT_ORDERS = [SORT_ORDER_ASC, SORT_ORDER_DESC]

# Pagination Defaults
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
