"""Pydantic schemas for User & Role Management API.

Based on F1A_api_spec.md - Request schemas for input validation,
Response schemas for output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator


# ============================================================================
# REQUEST SCHEMAS (Input Validation)
# ============================================================================

class PlatformUserListQuery(BaseModel):
    """Query schema for listing platform users with pagination and filtering.
    
    Based on F1A_api_spec.md Section 5.1 - GET /api/v1/users query parameters.
    """

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    search: Optional[str] = Field(None, description="Search by email, first_name, or last_name (case-insensitive partial match)")
    company_slug: Optional[str] = Field(None, description="Filter by company slug (exact match)")
    role_code: Optional[str] = Field(None, description="Filter by role code (exact match)")
    status: Optional[str] = Field(None, description="Filter by status: active, inactive, pending, expired, activated")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, email, first_name, last_name, role_code")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)


class CompanyUserListQuery(BaseModel):
    """Query schema for listing company users with pagination and filtering.
    
    Based on F1A_api_spec.md Section 5.2 - GET /api/v1/company/users query parameters.
    """

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    search: Optional[str] = Field(None, description="Search by email, first_name, or last_name (case-insensitive partial match)")
    role_code: Optional[str] = Field(None, description="Filter by role code (exact match)")
    status: Optional[str] = Field(None, description="Filter by status: active, inactive, pending, expired, activated")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, email, first_name, last_name, role_code")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)


class UserInvite(BaseModel):
    """Request schema for inviting a new user.
    
    Based on F1A_api_spec.md Section 5.4 - POST /api/v1/users/invite request body.
    """

    email: EmailStr = Field(..., description="User email address (RFC 5322 format, max 254 characters)")
    role_id: UUID = Field(..., description="Role ID for assignment")
    company_id: Optional[UUID] = Field(None, description="Company ID (required for non-SuperAdmin roles, optional for SuperAdmin)")

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Request schema for updating user information.
    
    Based on F1A_api_spec.md Section 5.5 - PATCH /api/v1/users/{user_id} request body.
    """

    first_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User first name (alphanumeric and spaces only)")
    last_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User last name (alphanumeric and spaces only)")
    current_password: Optional[str] = Field(None, description="Current password (required if new_password is provided)")
    new_password: Optional[str] = Field(None, min_length=8, description="New password (required if current_password is provided)")

    model_config = ConfigDict(from_attributes=True)


class UserRoleChange(BaseModel):
    """Request schema for changing user role within same company.
    
    Based on F1B_api_spec.md Section 5.1 - PATCH /api/v1/users/{user_id}/role request body.
    """

    role_id: UUID = Field(..., description="New role ID for user")

    model_config = ConfigDict(from_attributes=True)


class UserStatusUpdate(BaseModel):
    """Request schema for updating user activation status.
    
    Unified endpoint for activating and deactivating users.
    """

    status: str = Field(..., description="User status: 'ACTIVE' or 'INACTIVE'")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        v_upper = v.upper()
        if v_upper not in ["ACTIVE", "INACTIVE"]:
            raise ValueError("Status must be 'ACTIVE' or 'INACTIVE'")
        return v_upper


class UserCompanyReassign(BaseModel):
    """Request schema for reassigning user to different company with optional role change.
    
    Based on F1B_api_spec.md Section 5.2 - PATCH /api/v1/users/{user_id}/companies/{company_id}/reassign request body.
    """

    role_code: Optional[str] = Field(None, description="New role code for user in target company (if not provided, keeps current role)")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RESPONSE SCHEMAS (Output Structure)
# ============================================================================

class RoleRead(BaseModel):
    """Role response schema.
    
    Based on F1A_api_spec.md Section 4.1 - Role Resource.
    """

    id: UUID = Field(..., description="Unique role identifier")
    code: str = Field(..., description="System identifier (immutable)")
    name: str = Field(..., description="Role display name")

    model_config = ConfigDict(from_attributes=True)


class CompanyRead(BaseModel):
    """Company response schema.
    
    Based on F1A_api_spec.md Section 4.1 - Company Resource.
    """

    company_id: UUID = Field(..., description="Unique company identifier")
    name: str = Field(..., description="Company name (unique, case-insensitive)")
    slug: str = Field(..., description="URL identifier (unique, case-insensitive)")
    is_active: bool = Field(..., description="Company availability (blocks access if false)")

    model_config = ConfigDict(from_attributes=True)


class UserRoleInfo(BaseModel):
    """User role assignment information in user responses.
    
    Based on F1A_api_spec.md Section 4.1 - UserRoleAssignment Resource.
    """

    code: str = Field(..., description="Assigned role code (immutable system identifier)")
    name: str = Field(..., description="Assigned role name")

    model_config = ConfigDict(from_attributes=True)


class UserCompanyInfo(BaseModel):
    """User company information in user responses.
    
    Based on F1A_api_spec.md Section 4.1 - UserRoleAssignment Resource company fields.
    """

    company_id: UUID = Field(..., description="Context company identifier")
    name: str = Field(..., description="Company name")
    slug: str = Field(..., description="Company URL identifier")

    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    """User list item schema (for paginated list responses).
    
    Based on F1A_api_spec.md Section 5.1 and 5.2 - List response structure.
    Supports both full field set (SuperAdmin, CEO, HR) and restricted field set (Manager).
    """

    user_id: UUID = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    is_active: bool = Field(..., description="Login eligibility")
    # Optional fields for full access (SuperAdmin, CEO, HR)
    is_deleted: Optional[bool] = Field(None, description="Soft delete flag (excluded for Manager)")
    invite_at: Optional[datetime] = Field(None, description="Initial invitation timestamp (excluded for Manager)")
    activate_at: Optional[datetime] = Field(None, description="Activation timestamp (excluded for Manager)")
    expiry: Optional[datetime] = Field(None, description="Invitation expiry timestamp (excluded for Manager)")
    invitation_status: Optional[str] = Field(None, description="Invitation status: pending, expired, activated (excluded for Manager)")
    role: UserRoleInfo = Field(..., description="User role information")
    company: Optional[UserCompanyInfo] = Field(None, description="Company information (excluded for Manager, null for SuperAdmin)")
    updated_at: datetime = Field(..., description="Last update timestamp (used for ETag generation)")

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    """User detail response schema.
    
    Based on F1A_api_spec.md Section 5.3 - GET /api/v1/users/{user_id} response.
    Supports both full field set (SuperAdmin, CEO, HR) and restricted field set (Manager).
    """

    user_id: UUID = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    is_active: bool = Field(..., description="Login eligibility")
    # Optional fields for full access (SuperAdmin, CEO, HR)
    is_deleted: Optional[bool] = Field(None, description="Soft delete flag (excluded for Manager)")
    invite_at: Optional[datetime] = Field(None, description="Initial invitation timestamp (excluded for Manager)")
    activate_at: Optional[datetime] = Field(None, description="Activation timestamp (excluded for Manager)")
    expiry: Optional[datetime] = Field(None, description="Invitation expiry timestamp (excluded for Manager)")
    reinvite_count: Optional[int] = Field(None, description="Number of re-invitations (excluded for Manager)")
    last_reinvite_at: Optional[datetime] = Field(None, description="Last re-invite timestamp (excluded for Manager)")
    invitation_status: Optional[str] = Field(None, description="Invitation status: pending, expired, activated (excluded for Manager)")
    can_resend_invite: Optional[bool] = Field(None, description="Re-invitation eligibility (excluded for Manager)")
    role: UserRoleInfo = Field(..., description="User role information")
    company: Optional[UserCompanyInfo] = Field(None, description="Company information (excluded for Manager, null for SuperAdmin)")
    updated_at: datetime = Field(..., description="Last update timestamp (used for ETag generation)")
    # Internal fields for ETag (not exposed in JSON, used for headers)
    etag: Optional[str] = Field(None, exclude=True, description="ETag for response header")
    last_modified: Optional[datetime] = Field(None, exclude=True, description="Last-Modified for response header")

    model_config = ConfigDict(from_attributes=True)


class RolesListResponse(BaseModel):
    """Roles list response wrapper.
    
    Based on F1A_api_spec.md Section 5.6 - GET /api/v1/roles response structure.
    Wraps roles array in items field.
    """

    items: list[RoleRead] = Field(..., description="List of available roles")

    model_config = ConfigDict(from_attributes=True)


class CompaniesListResponse(BaseModel):
    """Companies list response wrapper.
    
    Based on F1A_api_spec.md Section 5.7 - GET /api/v1/companies response structure.
    Wraps companies array in items field.
    """

    items: list[CompanyRead] = Field(..., description="List of active companies")

    model_config = ConfigDict(from_attributes=True)
