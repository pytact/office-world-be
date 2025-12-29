"""Domain-specific constants for Task Management module.

Based on F8_api_spec.md - Task Management & Assignment (F-008).
"""

# Error Messages
ERROR_TASK_NOT_FOUND = "Task not found"
ERROR_TASK_ALREADY_DELETED = "Task is already deleted"
ERROR_TASK_TERMINAL_STATE = "Task is in terminal state (DONE or CANCELLED) and cannot be modified"
ERROR_TASK_PROJECT_INACTIVE = "Cannot edit task. Task is linked to an INACTIVE or COMPLETED project"
ERROR_ASSIGNMENT_NOT_FOUND = "Assignment not found"
ERROR_DUPLICATE_ASSIGNMENT = "Employee is already assigned to this task"
ERROR_EMPLOYEE_NOT_FOUND = "Employee not found or not in same company"
ERROR_PROJECT_NOT_FOUND = "Project not found"
ERROR_PROJECT_NOT_ACTIVE = "Cannot link task to project. Project is not ACTIVE"
ERROR_INVALID_STATUS = "Invalid task status"
ERROR_INVALID_INITIAL_STATUS = "Initial task status must be TODO. Cannot create task with other statuses"
ERROR_INVALID_PERMISSION = "Invalid assignment permission. Must be VIEWER or EDITOR"
ERROR_CANNOT_REMOVE_OWNER = "Cannot remove task owner from assignments"
ERROR_EDITOR_CANNOT_REMOVE_SELF = "Editors cannot remove themselves from task assignments"
ERROR_INSUFFICIENT_PERMISSIONS_VIEW = "You do not have permission to access this task. You can only access tasks you own or are assigned to"
ERROR_INSUFFICIENT_PERMISSIONS_EDIT = "Only task owner and editors can edit task name and description"
ERROR_INSUFFICIENT_PERMISSIONS_STATUS = "Only the task owner or editor can change task status"
ERROR_INSUFFICIENT_PERMISSIONS_ASSIGNMENTS = "Only the task owner can manage task assignments"
ERROR_INSUFFICIENT_PERMISSIONS_DELETE = "Only task owners, CEOs, and Managers can delete tasks"
ERROR_HR_READ_ONLY = "HR role has read-only access. Cannot create, edit, or delete tasks"

# Success Messages
SUCCESS_TASK_CREATED = "Task created successfully"
SUCCESS_TASK_RETRIEVED = "Task retrieved successfully"
SUCCESS_TASKS_RETRIEVED = "Tasks retrieved successfully"
SUCCESS_TASK_UPDATED = "Task updated successfully"
SUCCESS_TASK_STATUS_UPDATED = "Task status updated successfully"
SUCCESS_TASK_ASSIGNMENTS_UPDATED = "Task assignments updated successfully"
SUCCESS_TASK_DELETED = "Task deleted successfully"

# Status Values
STATUS_TODO = "TODO"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_HALT = "HALT"
STATUS_REVIEW = "REVIEW"
STATUS_DONE = "DONE"
STATUS_CANCELLED = "CANCELLED"

# Permission Values
PERMISSION_VIEWER = "VIEWER"
PERMISSION_EDITOR = "EDITOR"
PERMISSION_OWNER = "OWNER"  # Derived permission (not stored in DB)

# Terminal States (read-only)
TERMINAL_STATES = [STATUS_DONE, STATUS_CANCELLED]

# Error Codes
ERROR_CODE_TASK_NOT_FOUND = "TASK_NOT_FOUND"
ERROR_CODE_TASK_ALREADY_DELETED = "TASK_ALREADY_DELETED"
ERROR_CODE_TASK_TERMINAL_STATE = "TASK_TERMINAL_STATE"
ERROR_CODE_TASK_PROJECT_INACTIVE = "TASK_PROJECT_INACTIVE"
ERROR_CODE_ASSIGNMENT_NOT_FOUND = "ASSIGNMENT_NOT_FOUND"
ERROR_CODE_DUPLICATE_ASSIGNMENT = "DUPLICATE_ASSIGNMENT"
ERROR_CODE_EMPLOYEE_NOT_FOUND = "EMPLOYEE_NOT_FOUND"
ERROR_CODE_PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
ERROR_CODE_PROJECT_NOT_ACTIVE = "PROJECT_NOT_ACTIVE"
ERROR_CODE_INVALID_STATUS = "INVALID_STATUS"
ERROR_CODE_INVALID_INITIAL_STATUS = "INVALID_INITIAL_STATUS"
ERROR_CODE_INVALID_PERMISSION = "INVALID_PERMISSION"
ERROR_CODE_CANNOT_REMOVE_OWNER = "CANNOT_REMOVE_OWNER"
ERROR_CODE_EDITOR_CANNOT_REMOVE_SELF = "EDITOR_CANNOT_REMOVE_SELF"
ERROR_CODE_INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
ERROR_CODE_HR_READ_ONLY = "HR_READ_ONLY"
