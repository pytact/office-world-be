"""FastAPI endpoints for Notifications System module.

Based on F3_api_spec.md - All endpoints with proper authentication, authorization,
user scoping, company scoping, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from fastapi.responses import Response as FastAPIResponse, JSONResponse
from src.schemas import StandardResponse
from src.pagination import PagedCollection
from src.users.utils import generate_request_id
from src.notifications.schemas import (
    NotificationListQuery,
    NotificationRead,
    BulkMarkReadRequest,
    BulkMarkReadResponse,
    UnreadCountResponse,
)
from src.notifications.utils import format_last_modified, generate_etag
from src.notifications.exceptions import NotificationNotFound, PreconditionFailed, PreconditionRequired
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
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = None,
) -> StandardResponse[PagedCollection[NotificationRead]] | FastAPIResponse:
    """List in-app notifications for the authenticated user with pagination, filtering, and sorting.
    
    Based on F3_api_spec.md Section 4.3.1 - GET /api/v1/notifications.
    ETag logic in service layer per error_prevention.md RULE 19.
    """
    request_id = generate_request_id()
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company (from JWT org_id)
    # If company_id is None (SuperAdmin), they won't see any notifications
    # This is correct behavior per spec: "All notifications are strictly company-scoped"
    if company_id is None:
        # SuperAdmin without company context - return empty result
        empty_result = PagedCollection(
            items=[],
            total=0,
            page=query.page,
            page_size=query.page_size,
            total_pages=0,
            next_page=None,
            prev_page=None,
        )
        response_data = StandardResponse(
            data=empty_result,
            message=SUCCESS_NOTIFICATIONS_RETRIEVED,
        )
        json_response = JSONResponse(content=response_data.model_dump(mode='json'))
        json_response.headers["X-Request-ID"] = request_id
        return json_response
    
    result = await api.list_notifications(user.id, company_id, query, if_none_match=if_none_match)
    
    # If service returned 304 Not Modified, return it directly
    if isinstance(result, FastAPIResponse):
        result.headers["X-Request-ID"] = request_id
        return result
    
    # Set ETag and Last-Modified headers from service result
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_NOTIFICATIONS_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    return json_response


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
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = None,
) -> StandardResponse[NotificationRead] | FastAPIResponse:
    """Retrieve a single notification by ID.
    
    Based on F3_api_spec.md Section 4.3.2 - GET /api/v1/notifications/{notification_id}.
    ETag logic in service layer per error_prevention.md RULE 19.
    """
    request_id = generate_request_id()
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company
    if company_id is None:
        # SuperAdmin without company context - raise not found
        raise NotificationNotFound(str(notification_id))
    
    result = await api.get_notification_by_id(notification_id, user.id, company_id, if_none_match=if_none_match)
    
    # If service returned 304 Not Modified, return it directly
    if isinstance(result, FastAPIResponse):
        result.headers["X-Request-ID"] = request_id
        return result
    
    # Set ETag and Last-Modified headers from service result
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_NOTIFICATION_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    return json_response


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
    ETag validation in service layer per error_prevention.md RULE 19.
    """
    request_id = generate_request_id()
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company
    if company_id is None:
        raise NotificationNotFound(str(notification_id))
    
    # If-Match header validation (ETag from GET response)
    if if_match:
        # Get current notification to check ETag
        current_notification = await api.get_notification_by_id(notification_id, user.id, company_id)
        current_etag = generate_etag(current_notification.updated_at)
        if if_match != current_etag:
            raise PreconditionFailed()
    else:
        # If-Match header is required for update operations
        raise PreconditionRequired()
    
    result = await api.mark_notification_as_read(notification_id, user.id, company_id)
    
    # Set new ETag after update
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_NOTIFICATION_MARKED_READ,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    return json_response


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
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[BulkMarkReadResponse]:
    """Bulk mark notifications as read or unread.
    
    Based on F3_api_spec.md Section 4.3.4 - PATCH /api/v1/notifications/read.
    ETag validation in service layer per error_prevention.md RULE 19.
    """
    request_id = generate_request_id()
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company
    if company_id is None:
        # SuperAdmin without company context - return empty result
        empty_result = BulkMarkReadResponse(
            updated_count=0,
            action=data.action,
            notification_ids=data.notification_ids,
        )
        response_data = StandardResponse(
            data=empty_result,
            message=SUCCESS_NOTIFICATIONS_MARKED_READ if data.action == ACTION_READ else SUCCESS_NOTIFICATIONS_MARKED_UNREAD,
        )
        json_response = JSONResponse(content=response_data.model_dump(mode='json'))
        json_response.headers["X-Request-ID"] = request_id
        return json_response
    
    result = await api.bulk_mark_read(user.id, company_id, data, if_match=if_match)
    
    message = SUCCESS_NOTIFICATIONS_MARKED_READ if data.action == ACTION_READ else SUCCESS_NOTIFICATIONS_MARKED_UNREAD
    response_data = StandardResponse(
        data=result,
        message=message,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    return json_response


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
    Note: Count endpoints typically don't require ETag as they return aggregate data.
    """
    request_id = generate_request_id()
    user, company_id = user_company
    
    # Company-scoped: All notifications are scoped to the user's company
    if company_id is None:
        # SuperAdmin without company context - return zero count
        empty_result = UnreadCountResponse(unread_count=0)
        response_data = StandardResponse(
            data=empty_result,
            message=SUCCESS_UNREAD_COUNT_RETRIEVED,
        )
        json_response = JSONResponse(content=response_data.model_dump(mode='json'))
        json_response.headers["X-Request-ID"] = request_id
        return json_response
    
    result = await api.get_unread_count(user.id, company_id)
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_UNREAD_COUNT_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    return json_response
