"""Domain-specific exceptions for Permissions System module.

Based on F2_db_spec.md - All error responses and exception types.
"""

from src.exceptions import (
    NotFoundError,
    BadRequestError,
    ValidationError,
    PreconditionRequiredError,
    PreconditionFailedError,
)
from src.permissions.constants import (
    ERROR_ROLE_NOT_FOUND,
    ERROR_INVALID_REQUEST,
    ERROR_VALIDATION_FAILED,
    ERROR_INVALID_ROLE_CODE,
    ERROR_DUPLICATE_ROLE_CODE,
    ERROR_DUPLICATE_ROLE_NAME,
    ERROR_INVALID_PERMISSIONS,
    ERROR_INVALID_SORT_FIELD,
    ERROR_INVALID_SORT_ORDER,
    ERROR_PRECONDITION_REQUIRED,
    ERROR_PRECONDITION_FAILED,
    ERROR_CANNOT_DELETE_ROLE_IN_USE,
    ERROR_CODE_ROLE_NOT_FOUND,
    ERROR_CODE_INVALID_REQUEST,
    ERROR_CODE_VALIDATION_FAILED,
    ERROR_CODE_INVALID_ROLE_CODE,
    ERROR_CODE_DUPLICATE_ROLE_CODE,
    ERROR_CODE_DUPLICATE_ROLE_NAME,
    ERROR_CODE_INVALID_PERMISSIONS,
    ERROR_CODE_INVALID_SORT_FIELD,
    ERROR_CODE_PRECONDITION_REQUIRED,
    ERROR_CODE_PRECONDITION_FAILED,
    ERROR_CODE_CANNOT_DELETE_ROLE_IN_USE,
)


class RoleNotFound(NotFoundError):
    """Role not found exception."""

    def __init__(self, role_id: str):
        super().__init__(resource="Role", resource_id=role_id)


class InvalidRequest(BadRequestError):
    """Invalid request format exception."""

    def __init__(self, message: str = ERROR_INVALID_REQUEST, details: list[dict] | None = None):
        super().__init__(
            message=message,
            error_code=ERROR_CODE_INVALID_REQUEST,
            details=details or [],
        )


class ValidationFailed(BadRequestError):
    """Request validation failed exception."""

    def __init__(self, message: str = ERROR_VALIDATION_FAILED, details: list[dict] | None = None):
        super().__init__(
            message=message,
            error_code=ERROR_CODE_VALIDATION_FAILED,
            details=details or [],
        )


class InvalidRoleCode(ValidationError):
    """Invalid role code exception."""

    def __init__(self, role_code: str, valid_codes: list[str]):
        valid_codes_str = ", ".join(valid_codes)
        super().__init__(
            message=f"Invalid role code. Allowed values: {valid_codes_str}",
            error_code=ERROR_CODE_INVALID_ROLE_CODE,
            details=[
                {
                    "field": "code",
                    "issue": f"Invalid role code '{role_code}'. Allowed values: {valid_codes_str}",
                }
            ],
        )


class DuplicateRoleCode(BadRequestError):
    """Duplicate role code exception."""

    def __init__(self, role_code: str):
        super().__init__(
            message=f"Role code '{role_code}' already exists",
            error_code=ERROR_CODE_DUPLICATE_ROLE_CODE,
            details=[
                {
                    "field": "code",
                    "issue": f"Role code '{role_code}' already exists",
                }
            ],
        )


class DuplicateRoleName(BadRequestError):
    """Duplicate role name exception."""

    def __init__(self, role_name: str):
        super().__init__(
            message=f"Role name '{role_name}' already exists",
            error_code=ERROR_CODE_DUPLICATE_ROLE_NAME,
            details=[
                {
                    "field": "name",
                    "issue": f"Role name '{role_name}' already exists",
                }
            ],
        )


class InvalidPermissions(ValidationError):
    """Invalid permissions format exception."""

    def __init__(self, message: str = ERROR_INVALID_PERMISSIONS):
        super().__init__(
            message=message,
            error_code=ERROR_CODE_INVALID_PERMISSIONS,
            details=[
                {
                    "field": "permissions",
                    "issue": message,
                }
            ],
        )


class InvalidSortField(ValidationError):
    """Invalid sort field exception."""

    def __init__(self, sort_field: str, valid_fields: list[str]):
        valid_fields_str = ", ".join(valid_fields)
        super().__init__(
            message=f"Invalid sort field. Allowed values: {valid_fields_str}",
            error_code=ERROR_CODE_INVALID_SORT_FIELD,
            details=[
                {
                    "field": "sort_by",
                    "issue": f"Invalid sort field '{sort_field}'. Allowed values: {valid_fields_str}",
                }
            ],
        )


class InvalidSortOrder(ValidationError):
    """Invalid sort order exception."""

    def __init__(self, sort_order: str):
        super().__init__(
            message="Invalid sort order. Must be 'asc' or 'desc'",
            error_code=ERROR_CODE_VALIDATION_FAILED,
            details=[
                {
                    "field": "sort_order",
                    "issue": f"Invalid sort order '{sort_order}'. Must be 'asc' or 'desc'",
                }
            ],
        )


class PreconditionRequired(PreconditionRequiredError):
    """If-Match header required exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_PRECONDITION_REQUIRED,
            error_code=ERROR_CODE_PRECONDITION_REQUIRED,
            details=[{"field": "If-Match", "issue": "If-Match header is required for update operations"}],
        )


class PreconditionFailed(PreconditionFailedError):
    """ETag mismatch exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_PRECONDITION_FAILED,
            error_code=ERROR_CODE_PRECONDITION_FAILED,
            details=[
                {
                    "field": "etag",
                    "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry.",
                }
            ],
        )


class CannotDeleteRoleInUse(BadRequestError):
    """Cannot delete role that is in use exception."""

    def __init__(self, role_code: str):
        super().__init__(
            message=f"Cannot delete role '{role_code}' because it is assigned to users",
            error_code=ERROR_CODE_CANNOT_DELETE_ROLE_IN_USE,
            details=[
                {
                    "field": "role_id",
                    "issue": f"Cannot delete role '{role_code}' because it is assigned to users",
                }
            ],
        )
