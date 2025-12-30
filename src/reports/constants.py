"""Constants for Reports & Analytics module.

Based on F12A_api_spec.md - Report types, error messages, and status values.
"""

# ============================================================================
# Report Types
# ============================================================================

REPORT_TYPE_ATTENDANCE = "ATTENDANCE"
REPORT_TYPE_LEAVE = "LEAVE"
REPORT_TYPE_SALARY_SUMMARY = "SALARY_SUMMARY"
REPORT_TYPE_EMPLOYEE = "EMPLOYEE"
REPORT_TYPE_TASK = "TASK"
REPORT_TYPE_PROJECT = "PROJECT"
REPORT_TYPE_AUDIT_SUMMARY = "AUDIT_SUMMARY"

# All report types
REPORT_TYPES = [
    REPORT_TYPE_ATTENDANCE,
    REPORT_TYPE_LEAVE,
    REPORT_TYPE_SALARY_SUMMARY,
    REPORT_TYPE_EMPLOYEE,
    REPORT_TYPE_TASK,
    REPORT_TYPE_PROJECT,
    REPORT_TYPE_AUDIT_SUMMARY,
]

# ============================================================================
# Report Type Labels and Descriptions
# ============================================================================

REPORT_TYPE_LABELS = {
    REPORT_TYPE_ATTENDANCE: "Attendance Report",
    REPORT_TYPE_LEAVE: "Leave Report",
    REPORT_TYPE_SALARY_SUMMARY: "Salary Summary Report",
    REPORT_TYPE_EMPLOYEE: "Employee Report",
    REPORT_TYPE_TASK: "Task Report",
    REPORT_TYPE_PROJECT: "Project Report",
    REPORT_TYPE_AUDIT_SUMMARY: "Audit Summary Report",
}

REPORT_TYPE_DESCRIPTIONS = {
    REPORT_TYPE_ATTENDANCE: "Daily and monthly attendance reports with employee-wise breakdown",
    REPORT_TYPE_LEAVE: "Leave applications, approvals, and rejections",
    REPORT_TYPE_SALARY_SUMMARY: "Company-wide salary totals (aggregated only)",
    REPORT_TYPE_EMPLOYEE: "Employee headcount and department-wise reports",
    REPORT_TYPE_TASK: "Task status, progress, and assignments",
    REPORT_TYPE_PROJECT: "Project status, progress, and assignments",
    REPORT_TYPE_AUDIT_SUMMARY: "Audit summary reports (counts and trends)",
}

# ============================================================================
# Source Features
# ============================================================================

REPORT_SOURCE_FEATURES = {
    REPORT_TYPE_ATTENDANCE: ["F-010"],
    REPORT_TYPE_LEAVE: ["F-009"],
    REPORT_TYPE_SALARY_SUMMARY: ["F-006"],
    REPORT_TYPE_EMPLOYEE: ["F-005"],
    REPORT_TYPE_TASK: ["F-008"],
    REPORT_TYPE_PROJECT: ["F-007"],
    REPORT_TYPE_AUDIT_SUMMARY: ["F-011"],
}

# ============================================================================
# Role-Based Access
# ============================================================================

# Roles that can access each report type
REPORT_ACCESS_BY_ROLE = {
    "ceo": [
        REPORT_TYPE_ATTENDANCE,
        REPORT_TYPE_LEAVE,
        REPORT_TYPE_SALARY_SUMMARY,
        REPORT_TYPE_EMPLOYEE,
        REPORT_TYPE_TASK,
        REPORT_TYPE_PROJECT,
        REPORT_TYPE_AUDIT_SUMMARY,
    ],
    "hr": [
        REPORT_TYPE_ATTENDANCE,
        REPORT_TYPE_LEAVE,
        REPORT_TYPE_SALARY_SUMMARY,
        REPORT_TYPE_EMPLOYEE,
        REPORT_TYPE_TASK,
        REPORT_TYPE_PROJECT,
        REPORT_TYPE_AUDIT_SUMMARY,
    ],
    "manager": [
        REPORT_TYPE_ATTENDANCE,
        REPORT_TYPE_PROJECT,
        REPORT_TYPE_TASK,
    ],
    "employee": [
        REPORT_TYPE_ATTENDANCE,
        REPORT_TYPE_LEAVE,
        REPORT_TYPE_TASK,
    ],
    "superadmin": [],  # BR-1203: SuperAdmin has no access to reports
}

# ============================================================================
# Status Values (for filtering)
# ============================================================================

# Attendance status values
ATTENDANCE_STATUS_PRESENT = "PRESENT"
ATTENDANCE_STATUS_ABSENT = "ABSENT"
ATTENDANCE_STATUS_LATE = "LATE"
ATTENDANCE_STATUS_HALF_DAY = "HALF_DAY"

ATTENDANCE_STATUS_VALUES = [
    ATTENDANCE_STATUS_PRESENT,
    ATTENDANCE_STATUS_ABSENT,
    ATTENDANCE_STATUS_LATE,
    ATTENDANCE_STATUS_HALF_DAY,
]

# Leave status values
LEAVE_STATUS_APPLIED = "APPLIED"
LEAVE_STATUS_APPROVED = "APPROVED"
LEAVE_STATUS_REJECTED = "REJECTED"
LEAVE_STATUS_CANCELLED = "CANCELLED"

LEAVE_STATUS_VALUES = [
    LEAVE_STATUS_APPLIED,
    LEAVE_STATUS_APPROVED,
    LEAVE_STATUS_REJECTED,
    LEAVE_STATUS_CANCELLED,
]

# Employee status values
EMPLOYEE_STATUS_ACTIVE = "ACTIVE"
EMPLOYEE_STATUS_INACTIVE = "INACTIVE"
EMPLOYEE_STATUS_TERMINATED = "TERMINATED"

EMPLOYEE_STATUS_VALUES = [
    EMPLOYEE_STATUS_ACTIVE,
    EMPLOYEE_STATUS_INACTIVE,
    EMPLOYEE_STATUS_TERMINATED,
]

# Task status values
TASK_STATUS_PENDING = "PENDING"
TASK_STATUS_IN_PROGRESS = "IN_PROGRESS"
TASK_STATUS_COMPLETED = "COMPLETED"
TASK_STATUS_CANCELLED = "CANCELLED"

TASK_STATUS_VALUES = [
    TASK_STATUS_PENDING,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_CANCELLED,
]

# Project status values
PROJECT_STATUS_PLANNING = "PLANNING"
PROJECT_STATUS_IN_PROGRESS = "IN_PROGRESS"
PROJECT_STATUS_COMPLETED = "COMPLETED"
PROJECT_STATUS_CANCELLED = "CANCELLED"
PROJECT_STATUS_ON_HOLD = "ON_HOLD"

PROJECT_STATUS_VALUES = [
    PROJECT_STATUS_PLANNING,
    PROJECT_STATUS_IN_PROGRESS,
    PROJECT_STATUS_COMPLETED,
    PROJECT_STATUS_CANCELLED,
    PROJECT_STATUS_ON_HOLD,
]

# Audit status values
AUDIT_STATUS_SUCCESS = "SUCCESS"
AUDIT_STATUS_FAILURE = "FAILURE"
AUDIT_STATUS_ERROR = "ERROR"

AUDIT_STATUS_VALUES = [
    AUDIT_STATUS_SUCCESS,
    AUDIT_STATUS_FAILURE,
    AUDIT_STATUS_ERROR,
]

# ============================================================================
# Error Messages
# ============================================================================

ERROR_REPORT_TYPE_NOT_FOUND = "Report type not found"
ERROR_INSUFFICIENT_PERMISSIONS = "You do not have permission to access this report type"
ERROR_INVALID_REPORT_TYPE = "Invalid report type"
ERROR_FILTER_VALIDATION_FAILED = "Filter validation failed"
ERROR_EMPLOYEE_FILTER_RESTRICTED = "You can only filter by your own employee_id"
ERROR_CROSS_COMPANY_FILTER = "Cross-company filtering is not allowed"
ERROR_DATE_RANGE_INVALID = "End date must be greater than or equal to start date"
ERROR_INVALID_STATUS = "Invalid status value for this report type"
ERROR_EXPORT_NOT_FOUND = "Export not found"
ERROR_EXPORT_EXPIRED = "Export has expired. Please create a new export."
ERROR_EXPORT_NOT_READY = "Export is not ready for download"
ERROR_EXPORT_NOT_COMPLETED = "Export is not in COMPLETED status"
ERROR_EXPORT_ACCESS_DENIED = "You do not have access to this export"
ERROR_ASYNC_OPERATION_FAILED = "Async export generation failed"

# ============================================================================
# Error Codes
# ============================================================================

ERROR_CODE_REPORT_TYPE_NOT_FOUND = "REPORT_TYPE_NOT_FOUND"
ERROR_CODE_INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
ERROR_CODE_INVALID_REPORT_TYPE = "INVALID_REPORT_TYPE"
ERROR_CODE_VALIDATION_ERROR = "VALIDATION_ERROR"
ERROR_CODE_BUSINESS_RULE_FAILED = "BUSINESS_RULE_FAILED"
ERROR_CODE_INVALID_REQUEST = "INVALID_REQUEST"
ERROR_CODE_EXPORT_NOT_FOUND = "EXPORT_NOT_FOUND"
ERROR_CODE_EXPORT_EXPIRED = "EXPORT_EXPIRED"
ERROR_CODE_EXPORT_NOT_READY = "EXPORT_NOT_READY"
ERROR_CODE_ASYNC_OPERATION_FAILED = "ASYNC_OPERATION_FAILED"

# ============================================================================
# Export Status Values
# ============================================================================

EXPORT_STATUS_PENDING = "PENDING"
EXPORT_STATUS_PROCESSING = "PROCESSING"
EXPORT_STATUS_COMPLETED = "COMPLETED"
EXPORT_STATUS_FAILED = "FAILED"
EXPORT_STATUS_EXPIRED = "EXPIRED"

EXPORT_STATUS_VALUES = [
    EXPORT_STATUS_PENDING,
    EXPORT_STATUS_PROCESSING,
    EXPORT_STATUS_COMPLETED,
    EXPORT_STATUS_FAILED,
    EXPORT_STATUS_EXPIRED,
]

# ============================================================================
# Export TTL (Time-to-Live)
# ============================================================================

EXPORT_TTL_HOURS = 24  # Exports expire after 24 hours

# ============================================================================
# Export Role-Based Access
# ============================================================================

# Roles that can export each report type (same as report view access)
EXPORT_ACCESS_BY_ROLE = REPORT_ACCESS_BY_ROLE  # Same access rules as report views

# ============================================================================
# Success Messages
# ============================================================================

SUCCESS_REPORT_TYPES_RETRIEVED = "Report types retrieved successfully"
SUCCESS_REPORT_DATA_RETRIEVED = "Report data retrieved successfully"
SUCCESS_NO_ACCESSIBLE_REPORTS = "No accessible report types found"
SUCCESS_EXPORT_CREATED = "Export request created successfully"
SUCCESS_EXPORT_STATUS_RETRIEVED = "Export status retrieved successfully"
SUCCESS_EXPORT_COMPLETED = "Export completed successfully"
SUCCESS_EXPORT_DOWNLOADED = "Export downloaded successfully"
SUCCESS_EXPORT_IS_PROCESSING = "Export is being processed"
SUCCESS_EXPORT_HAS_EXPIRED = "Export has expired"
SUCCESS_EXPORT_GENERATION_FAILED = "Export generation failed"

