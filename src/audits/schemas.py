"""Pydantic schemas for Audit Logging & Activity History module.

Based on F11_api_spec.md Section 5 - Response Schema Details.
Request schemas define input validation, Response schemas define output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# Request Schemas (Input Validation)
# ============================================================================

class AuditLogListQuery(BaseModel):
    """Query schema for listing audit logs with pagination and filtering.
    
    Based on F11_api_spec.md Section 4.4.1 - GET /api/v1/company/audit-logs.
    Query parameters MUST be defined using query schema class with Depends() pattern.
    """
    
    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    start_date: Optional[str] = Field(None, description="Filter by start date (ISO 8601 datetime with UTC, e.g., 2024-01-20T10:30:00Z)")
    end_date: Optional[str] = Field(None, description="Filter by end date (ISO 8601 datetime with UTC, e.g., 2024-01-20T10:30:00Z)")
    action_code: Optional[str] = Field(None, description="Filter by action code (exact match, case-sensitive)")
    table_name: Optional[str] = Field(None, description="Filter by table name (exact match, case-sensitive)")
    sort_by: str = Field("created_at", description="Sort field: created_at (only allowed field)")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    
    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate that sort_by is only 'created_at'."""
        if v != "created_at":
            raise ValueError("Invalid sort field. Only 'created_at' is allowed.")
        return v
    
    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate that sort_order is 'asc' or 'desc'."""
        if v not in ["asc", "desc"]:
            raise ValueError("Sort order must be 'asc' or 'desc'.")
        return v
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas (Output Structure)
# ============================================================================

class ActorInfo(BaseModel):
    """Actor information schema for audit log responses.
    
    Based on F11_api_spec.md Section 5.1 - Actor Object.
    Nullable for SYSTEM-generated actions.
    
    Note: first_name and last_name are Optional to match User model structure,
    but service layer ensures non-empty strings are provided when actor exists.
    """
    
    id: UUID = Field(..., description="User ID")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    role_code: str = Field(..., description="Role code (e.g., 'ceo', 'hr', 'manager')")
    
    model_config = ConfigDict(from_attributes=True)


class AuditLogSummary(BaseModel):
    """Audit log summary for list response.
    
    Based on F11_api_spec.md Section 5.1 - AuditLogSummary (List Response).
    """
    
    id: UUID = Field(..., description="Audit log identifier")
    action_code: str = Field(..., description="Action identifier")
    table_name: str = Field(..., description="Affected table name")
    record_id: Optional[UUID] = Field(None, description="Affected record identifier")
    description: Optional[str] = Field(None, description="Human-readable summary")
    created_at: datetime = Field(..., description="Action timestamp (ISO 8601 format, UTC timezone)")
    actor: Optional[ActorInfo] = Field(None, description="Actor information (null for SYSTEM actions)")
    actor_display_name: str = Field(..., description="Human-readable actor name (e.g., 'Jane Doe (HR)' or 'SYSTEM')")
    
    model_config = ConfigDict(from_attributes=True)


class AuditLogDetail(BaseModel):
    """Audit log detail for detail response.
    
    Based on F11_api_spec.md Section 5.2 - AuditLogDetail (Detail Response).
    """
    
    id: UUID = Field(..., description="Audit log identifier")
    action_code: str = Field(..., description="Action identifier")
    table_name: str = Field(..., description="Affected table name")
    record_id: Optional[UUID] = Field(None, description="Affected record identifier")
    description: Optional[str] = Field(None, description="Human-readable summary")
    old_values: Optional[dict] = Field(None, description="Changed fields before action (JSON object, only changed fields)")
    new_values: Optional[dict] = Field(None, description="Changed fields after action (JSON object, only changed fields)")
    ip_address: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="Client metadata")
    created_at: datetime = Field(..., description="Action timestamp (ISO 8601 format, UTC timezone)")
    actor: Optional[ActorInfo] = Field(None, description="Actor information (null for SYSTEM actions)")
    actor_display_name: str = Field(..., description="Human-readable actor name (e.g., 'Jane Doe (HR)' or 'SYSTEM')")
    has_value_changes: bool = Field(..., description="Indicates if values changed (true when old_values or new_values are non-empty)")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Paginated Response
# ============================================================================

class AuditLogPaginatedResponse(BaseModel):
    """Paginated response wrapper for audit log list.
    
    Based on F11_api_spec.md Section 5.3 - Pagination Response Structure.
    """
    
    items: list[AuditLogSummary] = Field(..., description="Array of AuditLogSummary objects")
    total: int = Field(..., description="Total number of audit logs across all pages")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    next_page: Optional[str] = Field(None, description="Full relative URL for next page (includes all query parameters) or null if no next page")
    prev_page: Optional[str] = Field(None, description="Full relative URL for previous page (includes all query parameters) or null if no previous page")
    
    model_config = ConfigDict(from_attributes=True)
