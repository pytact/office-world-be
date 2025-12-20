"""API documentation for Notifications System endpoints.

Based on F3_api_spec.md - Swagger/OpenAPI documentation for all endpoints.
"""

from typing import ClassVar


class NotificationApiDocs:
    """API documentation for Notification endpoints."""

    list: ClassVar[dict] = {
        "summary": "List in-app notifications for the authenticated user with pagination, filtering, and sorting",
        "description": (
            "Retrieves a paginated list of in-app notifications for the authenticated user. "
            "Supports filtering by read status and notification type, and sorting by created_at, updated_at, or read_at. "
            "Only returns in-app notifications (task and leave types). Invitation notifications are email-only and excluded. "
            "All notifications are company-scoped and user-scoped - users can only view their own notifications."
        ),
    }

    get: ClassVar[dict] = {
        "summary": "Retrieve a single notification by ID",
        "description": (
            "Retrieves a single notification by ID. Users can only retrieve their own notifications. "
            "Returns 404 if notification not found or does not belong to the authenticated user."
        ),
    }

    mark_read: ClassVar[dict] = {
        "summary": "Mark a single notification as read",
        "description": (
            "Marks a single notification as read. Sets is_read=true and read_at=current timestamp. "
            "Users can only mark their own notifications as read. "
            "Requires If-Match header for concurrency control (ETag from GET response)."
        ),
    }

    bulk_mark_read: ClassVar[dict] = {
        "summary": "Bulk mark notifications as read or unread",
        "description": (
            "Bulk marks multiple notifications as read or unread. "
            "Supports marking up to 100 notifications at once. "
            "Only notifications belonging to the authenticated user are updated. "
            "Invalid or inaccessible notification IDs are silently skipped."
        ),
    }

    get_count: ClassVar[dict] = {
        "summary": "Get unread notification count for badge display",
        "description": (
            "Retrieves the count of unread in-app notifications for the authenticated user. "
            "Only includes in-app notifications (task and leave types) that are unread. "
            "Invitation notifications are email-only and excluded from count."
        ),
    }
