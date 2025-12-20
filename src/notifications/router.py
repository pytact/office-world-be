"""FastAPI endpoints for Notifications System module.

Based on F3_api_spec.md - All endpoints with proper authentication, authorization,
user scoping, company scoping, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from src.schemas import StandardResponse
from src.pagination import PagedCollection
from src.notifications.schemas import (
    NotificationListQuery,
    NotificationRead,
    BulkMarkReadRequest,
    BulkMarkReadResponse,
    UnreadCountResponse,
)
from src.notifications.dependencies import NotificationApiDep, get_current_user_with_company
from src.notifications.documentations.notifications_api_doc import NotificationApiDocs
from src.notifications.constants import (
    SUCCESS_NOTIFICATIONS_RETRIEVED,
    SUCCESS_NOTIFICATION_RETRIEVED,
    SUCCESS_NOTIFICATION_MARKED_READ,
    SUCCESS_NOTIFICATIONS_MARKED_READ,
    SUCCESS_NOTIFICATIONS_MARKED_UNREAD,
    SUCCESS_UNREAD_COUNT_RETRIEVED,
    ACTION_READ,
)
from src.users.models import User

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=StandardResponse[PagedCollection[NotificationRead]],
    summary=NotificationApiDocs.list["summary"],
    description=NotificationApiDocs.list["description"],
)
async def list_notifications(
    request: Request,
    query: NotificationListQuery = Depends(NotificationListQuery),
    api: NotificationApiDep = Depends(NotificationApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
) -> StandardResponse[PagedCollection[NotificationRead]]:
    """List in-app notifications for the authenticated user with pagination, filtering, and sorting.
    
    Based on F3_api_spec.md Section 4.3.1 - GET /api/v1/notifications.
    """
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company (from JWT org_id)
    # If company_id is None (SuperAdmin), they won't see any notifications
    # This is correct behavior per spec: "All notifications are strictly company-scoped"
    if company_id is None:
        # SuperAdmin without company context - return empty result
        from src.pagination import PagedCollection
        empty_result = PagedCollection(
            items=[],
            total=0,
            page=query.page,
            page_size=query.page_size,
            total_pages=0,
            next_page=None,
            prev_page=None,
        )
        return StandardResponse(
            data=empty_result,
            message=SUCCESS_NOTIFICATIONS_RETRIEVED,
        )
    
    result = await api.list_notifications(user.id, company_id, query)
    return StandardResponse(
        data=result,
        message=SUCCESS_NOTIFICATIONS_RETRIEVED,
    )


@router.get(
    "/{notification_id}",
    response_model=StandardResponse[NotificationRead],
    summary=NotificationApiDocs.get["summary"],
    description=NotificationApiDocs.get["description"],
)
async def get_notification(
    request: Request,
    notification_id: UUID,
    api: NotificationApiDep = Depends(NotificationApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
    response: Response = None,
) -> StandardResponse[NotificationRead]:
    """Retrieve a single notification by ID.
    
    Based on F3_api_spec.md Section 4.3.2 - GET /api/v1/notifications/{notification_id}.
    """
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company
    if company_id is None:
        # SuperAdmin without company context - raise not found
        from src.notifications.exceptions import NotificationNotFound
        raise NotificationNotFound(str(notification_id))
    
    result = await api.get_notification_by_id(notification_id, user.id, company_id)
    
    # Set ETag and Last-Modified headers (based on updated_at)
    if hasattr(result, 'updated_at'):
        from src.notifications.utils import generate_etag, format_last_modified
        response.headers["ETag"] = generate_etag(result.updated_at)
        response.headers["Last-Modified"] = format_last_modified(result.updated_at)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_NOTIFICATION_RETRIEVED,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=StandardResponse[NotificationRead],
    summary=NotificationApiDocs.mark_read["summary"],
    description=NotificationApiDocs.mark_read["description"],
)
async def mark_notification_as_read(
    request: Request,
    notification_id: UUID,
    api: NotificationApiDep = Depends(NotificationApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[NotificationRead]:
    """Mark a single notification as read.
    
    Based on F3_api_spec.md Section 4.3.3 - PATCH /api/v1/notifications/{notification_id}/read.
    
    Note: ETag validation is handled in service layer per error_prevention.md RULE 19.
    For now, we'll implement basic If-Match validation.
    """
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company
    if company_id is None:
        from src.notifications.exceptions import NotificationNotFound
        raise NotificationNotFound(str(notification_id))
    
    # If-Match header validation (ETag from GET response)
    if if_match:
        # Get current notification to check ETag
        current_notification = await api.get_notification_by_id(notification_id, user.id, company_id)
        from src.notifications.utils import generate_etag
        current_etag = generate_etag(current_notification.updated_at)
        if if_match != current_etag:
            from src.notifications.exceptions import PreconditionFailed
            raise PreconditionFailed()
    else:
        # If-Match header is required for update operations
        from src.notifications.exceptions import PreconditionRequired
        raise PreconditionRequired()
    
    result = await api.mark_notification_as_read(notification_id, user.id, company_id)
    
    # Set new ETag after update
    if hasattr(result, 'updated_at'):
        from src.notifications.utils import generate_etag
        response.headers["ETag"] = generate_etag(result.updated_at)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_NOTIFICATION_MARKED_READ,
    )


@router.patch(
    "/read",
    response_model=StandardResponse[BulkMarkReadResponse],
    summary=NotificationApiDocs.bulk_mark_read["summary"],
    description=NotificationApiDocs.bulk_mark_read["description"],
)
async def bulk_mark_read(
    request: Request,
    data: BulkMarkReadRequest,
    api: NotificationApiDep = Depends(NotificationApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
) -> StandardResponse[BulkMarkReadResponse]:
    """Bulk mark notifications as read or unread.
    
    Based on F3_api_spec.md Section 4.3.4 - PATCH /api/v1/notifications/read.
    """
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company
    if company_id is None:
        # SuperAdmin without company context - return empty result
        from src.notifications.schemas import BulkMarkReadResponse
        empty_result = BulkMarkReadResponse(
            updated_count=0,
            action=data.action,
            notification_ids=data.notification_ids,
        )
        return StandardResponse(
            data=empty_result,
            message=SUCCESS_NOTIFICATIONS_MARKED_READ if data.action == ACTION_READ else SUCCESS_NOTIFICATIONS_MARKED_UNREAD,
        )
    
    result = await api.bulk_mark_read(user.id, company_id, data)
    
    message = SUCCESS_NOTIFICATIONS_MARKED_READ if data.action == ACTION_READ else SUCCESS_NOTIFICATIONS_MARKED_UNREAD
    return StandardResponse(
        data=result,
        message=message,
    )


@router.get(
    "/count",
    response_model=StandardResponse[UnreadCountResponse],
    summary=NotificationApiDocs.get_count["summary"],
    description=NotificationApiDocs.get_count["description"],
)
async def get_unread_count(
    request: Request,
    api: NotificationApiDep = Depends(NotificationApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
) -> StandardResponse[UnreadCountResponse]:
    """Get unread notification count for badge display.
    
    Based on F3_api_spec.md Section 4.3.5 - GET /api/v1/notifications/count.
    """
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company
    if company_id is None:
        # SuperAdmin without company context - return zero count
        from src.notifications.schemas import UnreadCountResponse
        empty_result = UnreadCountResponse(unread_count=0)
        return StandardResponse(
            data=empty_result,
            message=SUCCESS_UNREAD_COUNT_RETRIEVED,
        )
    
    result = await api.get_unread_count(user.id, company_id)
    return StandardResponse(
        data=result,
        message=SUCCESS_UNREAD_COUNT_RETRIEVED,
    )
