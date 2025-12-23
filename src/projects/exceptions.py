"""Domain-specific exceptions for Project Management module.

Based on F7_api_spec.md Section 7 - Error Handling.
All exceptions extend base exception classes from src.exceptions.
"""

from uuid import UUID
from src.exceptions import (
    NotFoundError,
    ConflictError,
    ForbiddenError,
    ValidationError,
    PreconditionRequiredError,
    PreconditionFailedError,
)
from src.projects.constants import (
    ERROR_PROJECT_NOT_FOUND,
    ERROR_DUPLICATE_PROJECT_NAME,
    ERROR_INSUFFICIENT_PERMISSIONS,
    ERROR_EMPLOYEE_PROJECT_ACCESS,
    ERROR_PROJECT_ALREADY_DELETED,
    ERROR_CODE_PROJECT_NOT_FOUND,
    ERROR_CODE_DUPLICATE_PROJECT_NAME,
    ERROR_CODE_INSUFFICIENT_PERMISSIONS,
    ERROR_CODE_PRECONDITION_FAILED,
    ERROR_CODE_PRECONDITION_REQUIRED,
)


class ProjectNotFound(NotFoundError):
    """404 Not Found - Project not found or belongs to different company.
    
    Based on F7_api_spec.md Section 7.1 - PROJECT_NOT_FOUND error code.
    """
    
    def __init__(self, project_id: str):
        super().__init__(
            resource="Project",
            resource_id=project_id
        )


class DuplicateProjectName(ConflictError):
    """409 Conflict - Project name already exists in company (case-insensitive).
    
    Based on F7_api_spec.md Section 6.1 - Project Name Uniqueness.
    """
    
    def __init__(self, project_name: str):
        super().__init__(
            message=ERROR_DUPLICATE_PROJECT_NAME,
            error_code=ERROR_CODE_DUPLICATE_PROJECT_NAME,
            details=[{"field": "name", "issue": ERROR_DUPLICATE_PROJECT_NAME}]
        )


class InsufficientPermissions(ForbiddenError):
    """403 Forbidden - User lacks required permissions for operation.
    
    Based on F7_api_spec.md Section 3.2 - Permission Matrix.
    """
    
    def __init__(self, message: str = None):
        super().__init__(
            message=message or ERROR_INSUFFICIENT_PERMISSIONS,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[{"field": "permission", "issue": message or ERROR_INSUFFICIENT_PERMISSIONS}]
        )


class EmployeeProjectAccessDenied(ForbiddenError):
    """403 Forbidden - Employee attempting to access project without assigned tasks.
    
    Based on F7_api_spec.md Section 3.3 - Visibility Rules.
    """
    
    def __init__(self):
        super().__init__(
            message=ERROR_EMPLOYEE_PROJECT_ACCESS,
            error_code=ERROR_CODE_INSUFFICIENT_PERMISSIONS,
            details=[{"field": "project", "issue": ERROR_EMPLOYEE_PROJECT_ACCESS}]
        )


class PreconditionRequired(PreconditionRequiredError):
    """428 Precondition Required - If-Match header required for update/delete operations.
    
    Based on F7_api_spec.md Section 2.3 - Conditional Requests (ETags).
    """
    
    def __init__(self):
        super().__init__(
            message="If-Match header is required for this operation.",
            error_code=ERROR_CODE_PRECONDITION_REQUIRED,
            details=[{"field": "etag", "issue": "If-Match header is required for this operation."}]
        )


class PreconditionFailed(PreconditionFailedError):
    """412 Precondition Failed - ETag mismatch.
    
    Based on F7_api_spec.md Section 2.3 - Conditional Requests (ETags).
    """
    
    def __init__(self):
        super().__init__(
            message="Resource has been modified since retrieval. Please fetch the latest version and retry.",
            error_code=ERROR_CODE_PRECONDITION_FAILED,
            details=[{"field": "etag", "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry."}]
        )
