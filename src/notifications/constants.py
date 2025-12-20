"""Domain-specific constants for Notifications System module.

Based on F3_api_spec.md - Notification types, channels, status values, and error messages.
"""

# Error Messages
ERROR_NOTIFICATION_NOT_FOUND = "Notification not found or you do not have access to this notification"
ERROR_INVALID_NOTIFICATION_TYPE = "Invalid notification type"
ERROR_INVALID_CHANNEL = "Invalid notification channel"
ERROR_INVALID_STATUS = "Invalid notification status"
ERROR_INVALID_ACTION = "Invalid action value. Must be 'read' or 'unread'"
ERROR_INVALID_SORT_FIELD = "Invalid sort field"
ERROR_INVALID_SORT_ORDER = "Invalid sort order"
ERROR_INVALID_REQUEST = "Invalid request format"
ERROR_VALIDATION_FAILED = "Request validation failed"
ERROR_PRECONDITION_REQUIRED = "If-Match header is required for update operations"
ERROR_PRECONDITION_FAILED = "Resource version mismatch. The resource was modified by another user"

# Success Messages
SUCCESS_NOTIFICATIONS_RETRIEVED = "Notifications retrieved successfully"
SUCCESS_NOTIFICATION_RETRIEVED = "Notification retrieved successfully"
SUCCESS_NOTIFICATION_MARKED_READ = "Notification marked as read successfully"
SUCCESS_NOTIFICATIONS_MARKED_READ = "Notifications marked as read successfully"
SUCCESS_NOTIFICATIONS_MARKED_UNREAD = "Notifications marked as unread successfully"
SUCCESS_UNREAD_COUNT_RETRIEVED = "Unread notification count retrieved successfully"

# Error Codes
ERROR_CODE_NOTIFICATION_NOT_FOUND = "NOTIFICATION_NOT_FOUND"
ERROR_CODE_INVALID_REQUEST = "INVALID_REQUEST"
ERROR_CODE_VALIDATION_FAILED = "VALIDATION_FAILED"
ERROR_CODE_INVALID_NOTIFICATION_TYPE = "INVALID_NOTIFICATION_TYPE"
ERROR_CODE_INVALID_SORT_FIELD = "INVALID_SORT_FIELD"
ERROR_CODE_INVALID_SORT_ORDER = "INVALID_SORT_ORDER"
ERROR_CODE_PRECONDITION_REQUIRED = "PRECONDITION_REQUIRED"
ERROR_CODE_PRECONDITION_FAILED = "PRECONDITION_FAILED"

# Notification Types (from F3_api_spec.md Section 4.1)
NOTIFICATION_TYPE_LEAVE_REQUEST = "leave_request"
NOTIFICATION_TYPE_LEAVE_APPROVAL = "leave_approval"
NOTIFICATION_TYPE_LEAVE_REJECTION = "leave_rejection"
NOTIFICATION_TYPE_LEAVE_MANAGER_APPROVAL = "leave_manager_approval"
NOTIFICATION_TYPE_TASK_ASSIGNMENT = "task_assignment"
NOTIFICATION_TYPE_TASK_PERMISSION_CHANGE = "task_permission_change"
NOTIFICATION_TYPE_TASK_STATUS_CHANGE = "task_status_change"
NOTIFICATION_TYPE_USER_ACTIVATION = "user_activation"
NOTIFICATION_TYPE_USER_DEACTIVATION = "user_deactivation"

# Valid Notification Types (for API filtering - excludes email-only invitation types)
VALID_NOTIFICATION_TYPES = [
    NOTIFICATION_TYPE_LEAVE_REQUEST,
    NOTIFICATION_TYPE_LEAVE_APPROVAL,
    NOTIFICATION_TYPE_LEAVE_REJECTION,
    NOTIFICATION_TYPE_LEAVE_MANAGER_APPROVAL,
    NOTIFICATION_TYPE_TASK_ASSIGNMENT,
    NOTIFICATION_TYPE_TASK_PERMISSION_CHANGE,
    NOTIFICATION_TYPE_TASK_STATUS_CHANGE,
    NOTIFICATION_TYPE_USER_ACTIVATION,
    NOTIFICATION_TYPE_USER_DEACTIVATION,
]

# Notification Channels
CHANNEL_EMAIL = "email"
CHANNEL_IN_APP = "in_app"

# Valid Channels
VALID_CHANNELS = [CHANNEL_EMAIL, CHANNEL_IN_APP]

# Notification Status
STATUS_SENT = "sent"
STATUS_FAILED = "failed"

# Valid Statuses
VALID_STATUSES = [STATUS_SENT, STATUS_FAILED]

# Related Tables (for polymorphic relationships)
RELATED_TABLE_LEAVES = "leaves"
RELATED_TABLE_TASKS = "tasks"

# Valid Related Tables
VALID_RELATED_TABLES = [RELATED_TABLE_LEAVES, RELATED_TABLE_TASKS]

# Bulk Action Types
ACTION_READ = "read"
ACTION_UNREAD = "unread"

# Valid Actions
VALID_ACTIONS = [ACTION_READ, ACTION_UNREAD]

# Sort Fields
SORT_FIELD_CREATED_AT = "created_at"
SORT_FIELD_UPDATED_AT = "updated_at"
SORT_FIELD_READ_AT = "read_at"

# Valid Sort Fields
VALID_SORT_FIELDS = [SORT_FIELD_CREATED_AT, SORT_FIELD_UPDATED_AT, SORT_FIELD_READ_AT]

# Sort Orders
SORT_ORDER_ASC = "asc"
SORT_ORDER_DESC = "desc"

# Valid Sort Orders
VALID_SORT_ORDERS = [SORT_ORDER_ASC, SORT_ORDER_DESC]

# API Filtering Rules (from F3_api_spec.md Section 3.2)
# API only returns in-app notifications (channel = "in_app")
API_CHANNEL_FILTER = CHANNEL_IN_APP
# API only returns task and leave type notifications (invitation notifications are email-only)
API_TYPE_FILTER = VALID_NOTIFICATION_TYPES  # Already excludes invitation types

# Pagination Defaults
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Bulk Operation Limits
MIN_BULK_NOTIFICATION_IDS = 1
MAX_BULK_NOTIFICATION_IDS = 100
