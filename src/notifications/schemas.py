"""Pydantic schemas for Notifications System API.

Based on F3_api_spec.md - Request schemas for input validation,
Response schemas for output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# REQUEST SCHEMAS (Input Validation)
# ============================================================================

class NotificationListQuery(BaseModel):
    """Query schema for listing notifications with pagination and filtering.
    
    Based on F3_api_spec.md Section 4.3.1 - GET /api/v1/notifications query parameters.
    """

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    is_read: Optional[bool] = Field(None, description="Filter by read status: true (read), false (unread)")
    type: Optional[str] = Field(
        None,
        description="Filter by notification type: leave_request, leave_approval, leave_rejection, leave_manager_approval, task_assignment, task_permission_change, task_status_change, user_activation, user_deactivation",
    )
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, read_at")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)


class BulkMarkReadRequest(BaseModel):
    """Request schema for bulk mark notifications as read/unread.
    
    Based on F3_api_spec.md Section 4.3.4 - PATCH /api/v1/notifications/read request body.
    """

    action: str = Field(..., description="Action to perform: 'read' or 'unread' (case-sensitive)")
    notification_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Array of notification IDs to update (min 1, max 100)",
    )

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RESPONSE SCHEMAS (Output Structure)
# ============================================================================

class NotificationRead(BaseModel):
    """Response schema for notification details.
    
    Based on F3_api_spec.md Section 4.1 - Notification Resource fields.
    """

    id: UUID = Field(..., description="Unique notification identifier")
    type: str = Field(..., description="Notification event type")
    title: str = Field(..., description="Short message title")
    message: str = Field(..., description="Notification body content")
    channel: str = Field(..., description="Delivery channel: 'email' or 'in_app'")
    is_read: bool = Field(..., description="Read state (in-app only)")
    read_at: Optional[datetime] = Field(None, description="Read timestamp (in-app only, UTC)")
    status: str = Field(..., description="Delivery state: 'sent' or 'failed'")
    related_record_id: Optional[UUID] = Field(None, description="Related domain record ID (leave_id, task_id)")
    related_table: Optional[str] = Field(None, description="Source table name ('leaves', 'tasks')")
    data: Optional[dict] = Field(None, description="Structured payload (includes rejection reason, etc.)")
    user_id: UUID = Field(..., description="Recipient user ID")
    company_id: UUID = Field(..., description="Company ID")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")

    model_config = ConfigDict(from_attributes=True)


class BulkMarkReadResponse(BaseModel):
    """Response schema for bulk mark read/unread operation.
    
    Based on F3_api_spec.md Section 4.3.4 - PATCH /api/v1/notifications/read response.
    """

    updated_count: int = Field(..., description="Number of notifications updated")
    action: str = Field(..., description="Action performed: 'read' or 'unread'")
    notification_ids: list[UUID] = Field(..., description="Array of notification IDs that were updated")

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    """Response schema for unread notification count.
    
    Based on F3_api_spec.md Section 4.3.5 - GET /api/v1/notifications/count response.
    """

    unread_count: int = Field(..., description="Number of unread notifications")

    model_config = ConfigDict(from_attributes=True)
