"""Business logic for Notifications System module.

Service layer - all business logic, validation, and orchestration.
No HTTP concerns, no database queries (uses repository).
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from src.notifications.models import Notification
from src.notifications.repository import NotificationRepository
from src.notifications.schemas import (
    NotificationListQuery,
    NotificationRead,
    BulkMarkReadRequest,
    BulkMarkReadResponse,
    UnreadCountResponse,
)
from src.notifications.exceptions import (
    NotificationNotFound,
    InvalidNotificationType,
    InvalidSortField,
    InvalidSortOrder,
    InvalidAction,
)
from src.notifications.constants import (
    VALID_NOTIFICATION_TYPES,
    VALID_SORT_FIELDS,
    VALID_SORT_ORDERS,
    VALID_ACTIONS,
    ACTION_READ,
    ACTION_UNREAD,
)
from src.pagination import PagedCollection
from src.config import settings
from src.notifications.utils import generate_etag
from fastapi.responses import Response as FastAPIResponse
from fastapi import status


class NotificationService:
    """Service for notification management business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = NotificationRepository(session)

    def _validate_notification_type(self, notification_type: Optional[str]) -> None:
        """Validate notification type."""
        if notification_type is not None and notification_type not in VALID_NOTIFICATION_TYPES:
            raise InvalidNotificationType(notification_type, VALID_NOTIFICATION_TYPES)

    def _validate_sort_field(self, sort_by: str) -> None:
        """Validate sort field."""
        if sort_by not in VALID_SORT_FIELDS:
            raise InvalidSortField(sort_by, VALID_SORT_FIELDS)

    def _validate_sort_order(self, sort_order: str) -> None:
        """Validate sort order."""
        if sort_order not in VALID_SORT_ORDERS:
            raise InvalidSortOrder(sort_order)

    def _validate_action(self, action: str) -> None:
        """Validate action for bulk operations."""
        if action not in VALID_ACTIONS:
            raise InvalidAction(action)


    async def list_notifications(
        self, user_id: UUID, company_id: UUID, query: NotificationListQuery, if_none_match: Optional[str] = None
    ) -> PagedCollection[NotificationRead] | FastAPIResponse:
        """List notifications with pagination, filtering, and sorting with ETag support.
        
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        # Validate inputs
        self._validate_notification_type(query.type)
        self._validate_sort_field(query.sort_by)
        self._validate_sort_order(query.sort_order)

        # Get notifications from repository
        items, total = await self.repository.list_with_pagination(
            user_id=user_id,
            company_id=company_id,
            page=query.page,
            page_size=query.page_size,
            is_read=query.is_read,
            notification_type=query.type,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )

        # Generate ETag based on most recent notification's updated_at (if any)
        # For empty results, use a fixed ETag
        if items:
            # Get the most recent updated_at from the result set
            # Since we're sorting, the first item should have the latest timestamp
            most_recent_updated_at = items[0].updated_at
            etag = generate_etag(most_recent_updated_at)
        else:
            # Empty result set - use a fixed ETag
            etag = generate_etag(datetime.utcnow())

        # Check If-None-Match header for conditional request
        if if_none_match and if_none_match == etag:
            # Resource hasn't changed - return 304 Not Modified
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)

        # Convert to response schemas
        notification_reads = [NotificationRead.model_validate(item) for item in items]

        # Calculate pagination metadata
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0

        # Build pagination URLs
        # Full API path: /api/v1/notifications
        base_path = f"/api{settings.api_prefix}/notifications"
        
        next_page = None
        prev_page = None
        
        if query.page < total_pages:
            # Build next_page URL with all query parameters
            next_params = []
            if query.page_size != 20:
                next_params.append(f"page_size={query.page_size}")
            if query.is_read is not None:
                next_params.append(f"is_read={str(query.is_read).lower()}")
            if query.type is not None:
                next_params.append(f"type={query.type}")
            if query.sort_by != "created_at":
                next_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                next_params.append(f"sort_order={query.sort_order}")
            next_params.append(f"page={query.page + 1}")
            next_page = f"{base_path}?{'&'.join(next_params)}"

        if query.page > 1:
            # Build prev_page URL with all query parameters
            prev_params = []
            if query.page_size != 20:
                prev_params.append(f"page_size={query.page_size}")
            if query.is_read is not None:
                prev_params.append(f"is_read={str(query.is_read).lower()}")
            if query.type is not None:
                prev_params.append(f"type={query.type}")
            if query.sort_by != "created_at":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"

        result = PagedCollection(
            items=notification_reads,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )
        
        # Attach ETag metadata for router to set header
        result._etag = etag
        if items:
            result._last_modified = items[0].updated_at
        
        return result

    async def get_notification_by_id(
        self, notification_id: UUID, user_id: UUID, company_id: UUID, if_none_match: Optional[str] = None
    ) -> NotificationRead | FastAPIResponse:
        """Get notification by ID with ETag support.
        
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        notification = await self.repository.get_by_id(notification_id, user_id, company_id)
        if not notification:
            raise NotificationNotFound(str(notification_id))

        # Generate ETag in service (business logic)
        etag = generate_etag(notification.updated_at)

        # Check If-None-Match header for conditional request
        if if_none_match and if_none_match == etag:
            # Resource hasn't changed - return 304 Not Modified
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)

        # Return notification with ETag metadata
        result = NotificationRead.model_validate(notification)
        result._etag = etag
        result._last_modified = notification.updated_at
        
        return result

    async def mark_notification_as_read(
        self, notification_id: UUID, user_id: UUID, company_id: UUID
    ) -> NotificationRead:
        """Mark notification as read.
        
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        read_at = datetime.utcnow()
        notification = await self.repository.mark_as_read(notification_id, user_id, company_id, read_at)
        if not notification:
            raise NotificationNotFound(str(notification_id))

        # Return notification with ETag metadata
        result = NotificationRead.model_validate(notification)
        result._etag = generate_etag(notification.updated_at)
        result._last_modified = notification.updated_at
        
        return result

    async def bulk_mark_read(
        self, user_id: UUID, company_id: UUID, request: BulkMarkReadRequest, if_match: Optional[str] = None
    ) -> BulkMarkReadResponse:
        """Bulk mark notifications as read or unread with ETag validation.
        
        ETag validation in service layer per error_prevention.md RULE 19.
        For bulk operations, If-Match is optional but recommended for consistency.
        """
        from src.notifications.exceptions import PreconditionFailed
        
        # Validate action
        self._validate_action(request.action)

        # If-Match header validation (optional for bulk operations)
        if if_match:
            # Get the most recent notification from the set to validate ETag
            # This is a simplified validation - in production, you might want to check all
            if request.notification_ids:
                first_notification = await self.repository.get_by_id(
                    request.notification_ids[0], user_id, company_id
                )
                if first_notification:
                    current_etag = generate_etag(first_notification.updated_at)
                    if if_match != current_etag:
                        raise PreconditionFailed()

        read_at = datetime.utcnow()

        if request.action == ACTION_READ:
            updated_count = await self.repository.bulk_mark_read(
                request.notification_ids, user_id, company_id, read_at
            )
        else:  # ACTION_UNREAD
            updated_count = await self.repository.bulk_mark_unread(
                request.notification_ids, user_id, company_id
            )

        result = BulkMarkReadResponse(
            updated_count=updated_count,
            action=request.action,
            notification_ids=request.notification_ids,
        )
        
        # Attach ETag metadata (based on current timestamp after update)
        result._etag = generate_etag(datetime.utcnow())
        
        return result

    async def get_unread_count(self, user_id: UUID, company_id: UUID) -> UnreadCountResponse:
        """Get unread notification count."""
        count = await self.repository.count_unread(user_id, company_id)
        return UnreadCountResponse(unread_count=count)
