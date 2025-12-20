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
        self, user_id: UUID, company_id: UUID, query: NotificationListQuery
    ) -> PagedCollection[NotificationRead]:
        """List notifications with pagination, filtering, and sorting."""
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

        return PagedCollection(
            items=notification_reads,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def get_notification_by_id(
        self, notification_id: UUID, user_id: UUID, company_id: UUID
    ) -> NotificationRead:
        """Get notification by ID."""
        notification = await self.repository.get_by_id(notification_id, user_id, company_id)
        if not notification:
            raise NotificationNotFound(str(notification_id))

        return NotificationRead.model_validate(notification)

    async def mark_notification_as_read(
        self, notification_id: UUID, user_id: UUID, company_id: UUID
    ) -> NotificationRead:
        """Mark notification as read."""
        read_at = datetime.utcnow()
        notification = await self.repository.mark_as_read(notification_id, user_id, company_id, read_at)
        if not notification:
            raise NotificationNotFound(str(notification_id))

        return NotificationRead.model_validate(notification)

    async def bulk_mark_read(
        self, user_id: UUID, company_id: UUID, request: BulkMarkReadRequest
    ) -> BulkMarkReadResponse:
        """Bulk mark notifications as read or unread."""
        # Validate action
        self._validate_action(request.action)

        read_at = datetime.utcnow()

        if request.action == ACTION_READ:
            updated_count = await self.repository.bulk_mark_read(
                request.notification_ids, user_id, company_id, read_at
            )
        else:  # ACTION_UNREAD
            updated_count = await self.repository.bulk_mark_unread(
                request.notification_ids, user_id, company_id
            )

        return BulkMarkReadResponse(
            updated_count=updated_count,
            action=request.action,
            notification_ids=request.notification_ids,
        )

    async def get_unread_count(self, user_id: UUID, company_id: UUID) -> UnreadCountResponse:
        """Get unread notification count."""
        count = await self.repository.count_unread(user_id, company_id)
        return UnreadCountResponse(unread_count=count)
