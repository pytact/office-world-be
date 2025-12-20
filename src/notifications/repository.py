"""Database operations for Notifications System module.

Repository layer - pure database operations only, no business logic.
All methods filter by user_id and company_id for proper scoping.
All methods filter by channel = 'in_app' (API only returns in-app notifications).
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from src.notifications.models import Notification
from src.notifications.constants import CHANNEL_IN_APP


class NotificationRepository:
    """Repository for notification database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, notification_id: UUID, user_id: UUID, company_id: UUID
    ) -> Optional[Notification]:
        """Get notification by ID with user and company scoping.
        
        Filters:
        - user_id must match (user-scoped)
        - company_id must match (company-scoped)
        - channel = 'in_app' (API only returns in-app notifications)
        - deleted_at IS NULL (exclude soft-deleted)
        """
        result = await self.session.execute(
            select(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.company_id == company_id,
                Notification.channel == CHANNEL_IN_APP,
                Notification.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_with_pagination(
        self,
        user_id: UUID,
        company_id: UUID,
        page: int,
        page_size: int,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Notification], int]:
        """List notifications with pagination, filtering, and sorting.
        
        Filters:
        - user_id must match (user-scoped)
        - company_id must match (company-scoped)
        - channel = 'in_app' (API only returns in-app notifications)
        - deleted_at IS NULL (exclude soft-deleted)
        - Optional: is_read filter
        - Optional: type filter
        
        Sorting:
        - sort_by: created_at, updated_at, read_at
        - sort_order: asc, desc
        """
        # Build base query with required filters
        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.company_id == company_id,
            Notification.channel == CHANNEL_IN_APP,
            Notification.deleted_at.is_(None),
        )

        # Apply optional filters
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)

        if notification_type is not None:
            query = query.where(Notification.type == notification_type)

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = None
        if sort_by == "created_at":
            sort_column = Notification.created_at
        elif sort_by == "updated_at":
            sort_column = Notification.updated_at
        elif sort_by == "read_at":
            sort_column = Notification.read_at
        else:
            # Default to created_at if invalid sort_by
            sort_column = Notification.created_at

        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def count_unread(self, user_id: UUID, company_id: UUID) -> int:
        """Count unread notifications for user.
        
        Filters:
        - user_id must match (user-scoped)
        - company_id must match (company-scoped)
        - channel = 'in_app' (API only returns in-app notifications)
        - deleted_at IS NULL (exclude soft-deleted)
        - is_read = false (unread only)
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.company_id == company_id,
                Notification.channel == CHANNEL_IN_APP,
                Notification.deleted_at.is_(None),
                Notification.is_read == False,
            )
        )
        return result.scalar() or 0

    async def mark_as_read(
        self, notification_id: UUID, user_id: UUID, company_id: UUID, read_at: datetime
    ) -> Optional[Notification]:
        """Mark notification as read.
        
        Updates:
        - is_read = true
        - read_at = current timestamp
        
        Filters:
        - user_id must match (user-scoped)
        - company_id must match (company-scoped)
        - channel = 'in_app' (only in-app notifications can be marked as read)
        - deleted_at IS NULL (exclude soft-deleted)
        """
        notification = await self.get_by_id(notification_id, user_id, company_id)
        if not notification:
            return None

        notification.is_read = True
        notification.read_at = read_at

        await self.session.commit()
        await self.session.refresh(notification)

        return notification

    async def mark_as_unread(
        self, notification_id: UUID, user_id: UUID, company_id: UUID
    ) -> Optional[Notification]:
        """Mark notification as unread.
        
        Updates:
        - is_read = false
        - read_at = NULL
        
        Filters:
        - user_id must match (user-scoped)
        - company_id must match (company-scoped)
        - channel = 'in_app' (only in-app notifications can be marked as unread)
        - deleted_at IS NULL (exclude soft-deleted)
        """
        notification = await self.get_by_id(notification_id, user_id, company_id)
        if not notification:
            return None

        notification.is_read = False
        notification.read_at = None

        await self.session.commit()
        await self.session.refresh(notification)

        return notification

    async def bulk_mark_read(
        self, notification_ids: list[UUID], user_id: UUID, company_id: UUID, read_at: datetime
    ) -> int:
        """Bulk mark notifications as read.
        
        Updates all matching notifications:
        - is_read = true
        - read_at = current timestamp
        
        Filters:
        - notification_id IN (notification_ids)
        - user_id must match (user-scoped)
        - company_id must match (company-scoped)
        - channel = 'in_app' (only in-app notifications can be marked as read)
        - deleted_at IS NULL (exclude soft-deleted)
        
        Returns:
        - Number of notifications updated
        """
        if not notification_ids:
            return 0

        result = await self.session.execute(
            select(Notification)
            .where(
                Notification.id.in_(notification_ids),
                Notification.user_id == user_id,
                Notification.company_id == company_id,
                Notification.channel == CHANNEL_IN_APP,
                Notification.deleted_at.is_(None),
            )
        )
        notifications = result.scalars().all()

        updated_count = 0
        for notification in notifications:
            notification.is_read = True
            notification.read_at = read_at
            updated_count += 1

        if updated_count > 0:
            await self.session.commit()

        return updated_count

    async def bulk_mark_unread(
        self, notification_ids: list[UUID], user_id: UUID, company_id: UUID
    ) -> int:
        """Bulk mark notifications as unread.
        
        Updates all matching notifications:
        - is_read = false
        - read_at = NULL
        
        Filters:
        - notification_id IN (notification_ids)
        - user_id must match (user-scoped)
        - company_id must match (company-scoped)
        - channel = 'in_app' (only in-app notifications can be marked as unread)
        - deleted_at IS NULL (exclude soft-deleted)
        
        Returns:
        - Number of notifications updated
        """
        if not notification_ids:
            return 0

        result = await self.session.execute(
            select(Notification)
            .where(
                Notification.id.in_(notification_ids),
                Notification.user_id == user_id,
                Notification.company_id == company_id,
                Notification.channel == CHANNEL_IN_APP,
                Notification.deleted_at.is_(None),
            )
        )
        notifications = result.scalars().all()

        updated_count = 0
        for notification in notifications:
            notification.is_read = False
            notification.read_at = None
            updated_count += 1

        if updated_count > 0:
            await self.session.commit()

        return updated_count
