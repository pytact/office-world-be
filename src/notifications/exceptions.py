"""Domain-specific exceptions for Notifications System module.

Based on F3_api_spec.md - All error responses and exception types.
"""

from src.exceptions import (
    NotFoundError,
    BadRequestError,
    ValidationError,
    PreconditionRequiredError,
    PreconditionFailedError,
)
from src.notifications.constants import (
    ERROR_NOTIFICATION_NOT_FOUND,
    ERROR_INVALID_REQUEST,
    ERROR_VALIDATION_FAILED,
    ERROR_INVALID_NOTIFICATION_TYPE,
    ERROR_INVALID_SORT_FIELD,
    ERROR_INVALID_SORT_ORDER,
    ERROR_INVALID_ACTION,
    ERROR_PRECONDITION_REQUIRED,
    ERROR_PRECONDITION_FAILED,
    ERROR_CODE_NOTIFICATION_NOT_FOUND,
    ERROR_CODE_INVALID_REQUEST,
    ERROR_CODE_VALIDATION_FAILED,
    ERROR_CODE_INVALID_NOTIFICATION_TYPE,
    ERROR_CODE_INVALID_SORT_FIELD,
    ERROR_CODE_PRECONDITION_REQUIRED,
    ERROR_CODE_PRECONDITION_FAILED,
)


class NotificationNotFound(NotFoundError):
    """Notification not found exception."""

    def __init__(self, notification_id: str):
        super().__init__(resource="Notification", resource_id=notification_id)


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


class InvalidNotificationType(ValidationError):
    """Invalid notification type exception."""

    def __init__(self, notification_type: str, valid_types: list[str]):
        valid_types_str = ", ".join(valid_types)
        super().__init__(
            message=f"Invalid notification type. Allowed values: {valid_types_str}",
            error_code=ERROR_CODE_INVALID_NOTIFICATION_TYPE,
            details=[
                {
                    "field": "type",
                    "issue": f"Invalid notification type '{notification_type}'. Allowed values: {valid_types_str}",
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


class InvalidAction(ValidationError):
    """Invalid action exception for bulk operations."""

    def __init__(self, action: str):
        super().__init__(
            message=f"Invalid action value. Must be 'read' or 'unread'",
            error_code=ERROR_CODE_VALIDATION_FAILED,
            details=[
                {
                    "field": "action",
                    "issue": f"Invalid action value '{action}'. Must be 'read' or 'unread'",
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
