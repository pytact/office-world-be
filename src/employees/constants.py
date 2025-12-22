"""Domain-specific constants for Employee Management module.

Based on F5_api_spec.md - Employee Management (F-005).
Contains error messages, success messages, error codes, and status values.
"""

# Error Messages
ERROR_EMPLOYEE_NOT_FOUND = "Employee not found"
ERROR_USER_NOT_FOUND = "User not found"
ERROR_DUPLICATE_EMPLOYEE = "User already has an employee record. One-to-one constraint violation."
ERROR_DUPLICATE_WORK_EMAIL = "WorkEmail already exists in company (case-insensitive)"
ERROR_INVALID_EMPLOYMENT_STATUS = "Invalid employment status"
ERROR_INVALID_DEPARTMENT = "Invalid department"
ERROR_INVALID_EMPLOYMENT_TYPE = "Invalid employment type"
ERROR_INVALID_EMPLOYMENT_LEVEL = "Invalid employment level"
ERROR_INVALID_GENDER = "Invalid gender"
ERROR_INVALID_MARITAL_STATUS = "Invalid marital status"
ERROR_INVALID_BLOOD_GROUP = "Invalid blood group"
ERROR_INVALID_DOCUMENT_TYPE = "Invalid document type"
ERROR_SEPARATION_FIELDS_REQUIRED = "Separation fields (separation_initiated_date, separation_reason) are required when employment_status is RESIGNED or TERMINATED."
ERROR_CANNOT_SOFT_DELETE_OWN_EMPLOYEE = "You cannot soft delete your own employee record."
ERROR_CANNOT_DEACTIVATE_OWN_EMPLOYEE = "You cannot deactivate your own employee record."
ERROR_USER_DIFFERENT_COMPANY = "User belongs to a different company"
ERROR_INSUFFICIENT_PERMISSIONS = "Insufficient permissions to access employee endpoints"
ERROR_SUPERADMIN_NO_ACCESS = "SuperAdmin is explicitly excluded from employee endpoints"

# Success Messages
SUCCESS_EMPLOYEE_CREATED = "Employee created successfully"
SUCCESS_EMPLOYEE_RETRIEVED = "Employee retrieved successfully"
SUCCESS_EMPLOYEES_RETRIEVED = "Employees retrieved successfully"
SUCCESS_EMPLOYEE_UPDATED = "Employee updated successfully"
SUCCESS_EMPLOYEE_SOFT_DELETED = "Employee soft deleted successfully"

# Error Codes
ERROR_CODE_EMPLOYEE_NOT_FOUND = "EMPLOYEE_NOT_FOUND"
ERROR_CODE_USER_NOT_FOUND = "USER_NOT_FOUND"
ERROR_CODE_DUPLICATE_EMPLOYEE = "DUPLICATE_EMPLOYEE"
ERROR_CODE_DUPLICATE_WORK_EMAIL = "DUPLICATE_WORK_EMAIL"
ERROR_CODE_BUSINESS_RULE_FAILED = "BUSINESS_RULE_FAILED"
ERROR_CODE_INVALID_EMPLOYMENT_STATUS = "INVALID_EMPLOYMENT_STATUS"
ERROR_CODE_INVALID_DEPARTMENT = "INVALID_DEPARTMENT"
ERROR_CODE_INVALID_EMPLOYMENT_TYPE = "INVALID_EMPLOYMENT_TYPE"
ERROR_CODE_INVALID_EMPLOYMENT_LEVEL = "INVALID_EMPLOYMENT_LEVEL"
ERROR_CODE_INVALID_GENDER = "INVALID_GENDER"
ERROR_CODE_INVALID_MARITAL_STATUS = "INVALID_MARITAL_STATUS"
ERROR_CODE_INVALID_BLOOD_GROUP = "INVALID_BLOOD_GROUP"
ERROR_CODE_INVALID_DOCUMENT_TYPE = "INVALID_DOCUMENT_TYPE"
ERROR_CODE_INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

# ENUM Values
EMPLOYMENT_STATUS_VALUES = [
    "TRAINEE",
    "PROBATION",
    "CONFIRMED",
    "NOTICE_PERIOD",
    "ACTIVE",
    "ON_HOLD",
    "TERMINATED",
    "RESIGNED",
]

DEPARTMENT_VALUES = [
    "FRONTEND",
    "BACKEND",
    "FULLSTACK",
    "QA",
    "HR",
    "DEVOPS",
    "UIUX",
    "PRODUCT",
    "MARKETING",
    "DATA",
    "SUPPORT",
]

EMPLOYMENT_TYPE_VALUES = [
    "FULL_TIME",
    "PART_TIME",
    "CONTRACT",
    "FREELANCE",
    "TEMPORARY",
]

EMPLOYMENT_LEVEL_VALUES = [
    "INTERN",
    "JUNIOR",
    "MID",
    "SENIOR",
    "LEAD",
    "MANAGER",
]

GENDER_VALUES = [
    "MALE",
    "FEMALE",
    "OTHER",
]

MARITAL_STATUS_VALUES = [
    "SINGLE",
    "MARRIED",
    "DIVORCED",
    "WIDOWED",
    "SEPARATED",
]

BLOOD_GROUP_VALUES = [
    "A+",
    "A-",
    "B+",
    "B-",
    "AB+",
    "AB-",
    "O+",
    "O-",
]

DOCUMENT_TYPE_VALUES = [
    "AADHAAR",
    "PAN",
    "DL",
    "VOTER_ID",
    "PASSPORT",
]

# Sort Fields
VALID_SORT_FIELDS = [
    "created_at",
    "updated_at",
    "joining_date",
    "job_title",
    "department",
    "employment_status",
]

VALID_SORT_ORDERS = ["asc", "desc"]

# Roles
ROLE_CEO = "ceo"
ROLE_HR = "hr"
ROLE_MANAGER = "manager"
ROLE_EMPLOYEE = "employee"
ROLE_SUPERADMIN = "superadmin"
