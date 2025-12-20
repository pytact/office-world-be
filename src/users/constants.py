"""Domain-specific constants for User & Role Management module."""

# Error Messages
ERROR_USER_NOT_FOUND = "User not found"
ERROR_DUPLICATE_EMAIL = "A user with this email already exists and is active"
ERROR_COMPANY_NOT_FOUND = "Company not found"
ERROR_ROLE_NOT_FOUND = "Role not found"
ERROR_INVALID_ROLE_CODE = "Invalid role code"
ERROR_COMPANY_ALREADY_HAS_CEO = "Company already has an active CEO. Only one CEO is allowed per company"
ERROR_INSUFFICIENT_PERMISSIONS = "You do not have permission to perform this action"
ERROR_INVALID_INVITATION_STATUS = "Invalid invitation status"
ERROR_CANNOT_UPDATE_EMAIL = "Email is immutable and cannot be updated"
# F1B Lifecycle Operations Error Messages
ERROR_CANNOT_CHANGE_OWN_ROLE = "You cannot change your own role"
ERROR_CANNOT_DEACTIVATE_OWN_ACCOUNT = "You cannot deactivate your own account"
ERROR_CANNOT_REASSIGN_SUPERADMIN = "Cannot reassign SuperAdmin users. SuperAdmin users are not tied to any company"
ERROR_PRECONDITION_REQUIRED = "If-Match header is required for concurrency control"
ERROR_PRECONDITION_FAILED = "Resource version mismatch. The resource was modified by another user"
ERROR_TARGET_COMPANY_HAS_CEO = "Target company already has an active CEO. Only one CEO is allowed per company"

# Success Messages
SUCCESS_USER_RETRIEVED = "User retrieved successfully"
SUCCESS_USERS_RETRIEVED = "Users retrieved successfully"
SUCCESS_USER_INVITED = "User invitation sent successfully"
SUCCESS_USER_UPDATED = "User updated successfully"
SUCCESS_ROLES_RETRIEVED = "Roles retrieved successfully"
SUCCESS_COMPANIES_RETRIEVED = "Companies retrieved successfully"
# F1B Lifecycle Operations Success Messages
SUCCESS_USER_ROLE_UPDATED = "User role updated successfully"
SUCCESS_USER_REASSIGNED = "User reassigned to company successfully"
SUCCESS_USER_DEACTIVATED = "User deactivated successfully"
SUCCESS_USER_REACTIVATED = "User reactivated successfully"
SUCCESS_INVITATION_RESENT = "Invitation resent successfully"

# Error Codes
ERROR_CODE_USER_NOT_FOUND = "USER_NOT_FOUND"
ERROR_CODE_DUPLICATE_EMAIL = "DUPLICATE_EMAIL"
ERROR_CODE_COMPANY_NOT_FOUND = "COMPANY_NOT_FOUND"
ERROR_CODE_ROLE_NOT_FOUND = "ROLE_NOT_FOUND"
ERROR_CODE_INVALID_ROLE_CODE = "INVALID_ROLE_CODE"
ERROR_CODE_COMPANY_HAS_CEO = "COMPANY_HAS_CEO"
ERROR_CODE_INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
ERROR_CODE_BUSINESS_RULE_FAILED = "BUSINESS_RULE_FAILED"
# F1B Lifecycle Operations Error Codes
ERROR_CODE_CANNOT_CHANGE_OWN_ROLE = "CANNOT_CHANGE_OWN_ROLE"
ERROR_CODE_CANNOT_DEACTIVATE_OWN_ACCOUNT = "CANNOT_DEACTIVATE_OWN_ACCOUNT"
ERROR_CODE_CANNOT_REASSIGN_SUPERADMIN = "CANNOT_REASSIGN_SUPERADMIN"
ERROR_CODE_PRECONDITION_REQUIRED = "PRECONDITION_REQUIRED"
ERROR_CODE_PRECONDITION_FAILED = "PRECONDITION_FAILED"
ERROR_CODE_TARGET_COMPANY_HAS_CEO = "TARGET_COMPANY_HAS_CEO"

# Invitation Status Values
INVITATION_STATUS_PENDING = "pending"
INVITATION_STATUS_EXPIRED = "expired"
INVITATION_STATUS_ACTIVATED = "activated"

# Role Codes
ROLE_CODE_SUPERADMIN = "superadmin"
ROLE_CODE_CEO = "ceo"
ROLE_CODE_HR = "hr"
ROLE_CODE_MANAGER = "manager"
ROLE_CODE_EMPLOYEE = "employee"

# Status Filter Values
STATUS_FILTER_ACTIVE = "active"
STATUS_FILTER_INACTIVE = "inactive"
STATUS_FILTER_PENDING = "pending"
STATUS_FILTER_EXPIRED = "expired"
STATUS_FILTER_ACTIVATED = "activated"

# Sort Fields
SORT_FIELD_CREATED_AT = "created_at"
SORT_FIELD_UPDATED_AT = "updated_at"
SORT_FIELD_EMAIL = "email"
SORT_FIELD_FIRST_NAME = "first_name"
SORT_FIELD_LAST_NAME = "last_name"
SORT_FIELD_ROLE_CODE = "role_code"

# Sort Orders
SORT_ORDER_ASC = "asc"
SORT_ORDER_DESC = "desc"

# Invitation Expiry (24 hours in seconds)
INVITATION_EXPIRY_HOURS = 24
INVITATION_EXPIRY_SECONDS = INVITATION_EXPIRY_HOURS * 3600
