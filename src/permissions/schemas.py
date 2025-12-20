"""Pydantic schemas for Permissions System API.

Based on F2_db_spec.md - Request schemas for input validation,
Response schemas for output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# REQUEST SCHEMAS (Input Validation)
# ============================================================================

class RoleListQuery(BaseModel):
    """Query schema for listing roles with pagination and filtering.
    
    Based on standard pagination pattern.
    """

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    code: Optional[str] = Field(None, description="Filter by role code")
    name: Optional[str] = Field(None, description="Filter by role name (partial match)")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, name, code")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    """Request schema for creating a role.
    
    Based on F2_db_spec.md Section 7.1 - Role entity.
    """

    name: str = Field(..., min_length=1, max_length=100, description="Role display name")
    code: str = Field(..., min_length=1, max_length=50, description="System identifier (immutable)")
    permissions: dict = Field(..., description="JSON object containing role permissions")

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: dict) -> dict:
        """Validate permissions structure."""
        if not isinstance(v, dict):
            raise ValueError("Permissions must be a JSON object")
        # Validate that values are lists of strings
        for resource, actions in v.items():
            if not isinstance(actions, list):
                raise ValueError(f"Permissions for resource '{resource}' must be a list")
            for action in actions:
                if not isinstance(action, str):
                    raise ValueError(f"Actions must be strings, got {type(action)}")
        return v

    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    """Request schema for updating a role.
    
    Based on F2_db_spec.md Section 7.1 - Role entity.
    Note: code is immutable, so it cannot be updated.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Role display name")
    permissions: Optional[dict] = Field(None, description="JSON object containing role permissions")

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: Optional[dict]) -> Optional[dict]:
        """Validate permissions structure."""
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("Permissions must be a JSON object")
        # Validate that values are lists of strings
        for resource, actions in v.items():
            if not isinstance(actions, list):
                raise ValueError(f"Permissions for resource '{resource}' must be a list")
            for action in actions:
                if not isinstance(action, str):
                    raise ValueError(f"Actions must be strings, got {type(action)}")
        return v

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RESPONSE SCHEMAS (Output Structure)
# ============================================================================

class RoleRead(BaseModel):
    """Response schema for role details.
    
    Based on F2_db_spec.md Section 7.1 - Role entity fields.
    """

    id: UUID = Field(..., description="Unique role identifier")
    name: str = Field(..., description="Role display name")
    code: str = Field(..., description="System identifier (immutable)")
    permissions: dict = Field(..., description="JSON object containing role permissions")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp (UTC)")
    created_by: Optional[UUID] = Field(None, description="User ID who created the role")
    updated_by: Optional[UUID] = Field(None, description="User ID who last updated the role")
    deleted_by: Optional[UUID] = Field(None, description="User ID who soft-deleted the role")

    model_config = ConfigDict(from_attributes=True)


class RoleListItem(BaseModel):
    """Response schema for role list item (simplified).
    
    Used in paginated list responses.
    """

    id: UUID = Field(..., description="Unique role identifier")
    name: str = Field(..., description="Role display name")
    code: str = Field(..., description="System identifier (immutable)")
    permissions: dict = Field(..., description="JSON object containing role permissions")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")

    model_config = ConfigDict(from_attributes=True)
