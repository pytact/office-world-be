"""Pydantic schemas for authentication endpoints."""

from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


# Request Schemas

class LoginRequest(BaseModel):
    """Request schema for login endpoint."""

    email: EmailStr = Field(..., description="User email address", max_length=254)
    password: str = Field(..., description="User password", max_length=128)


class ActivationRequest(BaseModel):
    """Request schema for account activation endpoint."""

    first_name: str = Field(..., description="User first name", min_length=1, max_length=50)
    last_name: str = Field(..., description="User last name", min_length=1, max_length=50)
    password: str = Field(..., description="Account password", min_length=8, max_length=128)
    password_confirm: str = Field(..., description="Password confirmation", min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("password_confirm")
    @classmethod
    def validate_password_confirm(cls, v: str) -> str:
        """Validate password confirmation format."""
        # Password match validation will be done in service layer
        return v


class PasswordResetRequestRequest(BaseModel):
    """Request schema for password reset request endpoint."""

    email: EmailStr = Field(..., description="User email address", max_length=254)


class PasswordResetRequest(BaseModel):
    """Request schema for password reset endpoint."""

    password: str = Field(..., description="New password", min_length=8, max_length=128)
    password_confirm: str = Field(..., description="Password confirmation", min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("password_confirm")
    @classmethod
    def validate_password_confirm(cls, v: str) -> str:
        """Validate password confirmation format."""
        # Password match validation will be done in service layer
        return v


# Response Schemas

class UserInfo(BaseModel):
    """User information in login response."""

    user_id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    company_id: Optional[UUID] = None
    company_slug: Optional[str] = None
    company_is_active: Optional[bool] = None
    is_super_admin: bool

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    """Response schema for login endpoint."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class ActivationValidationResponse(BaseModel):
    """Response schema for activation token validation endpoint."""

    email: str
    company_name: str
    role: str
    invitation_status: str
    expires_at: datetime


class ActivationResponse(BaseModel):
    """Response schema for account activation endpoint."""

    user_id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    company_id: Optional[UUID] = None
    activated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequestResponse(BaseModel):
    """Response schema for password reset request endpoint."""

    email: str
    reset_requested: bool = True


class PasswordResetResponse(BaseModel):
    """Response schema for password reset endpoint."""

    email: str
    password_reset: bool = True
    reset_at: datetime


# Permission & Context Schemas for GET /api/v1/auth/me

class UserDetails(BaseModel):
    """User details information in permissions response."""

    user_id: UUID = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    is_active: bool = Field(..., description="Login eligibility")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class RoleInfo(BaseModel):
    """Role information in permissions response."""

    code: str = Field(..., description="Role code identifier", examples=["ceo", "hr", "manager", "employee", "superadmin"])
    name: str = Field(..., description="Role display name", examples=["CEO", "HR", "Manager", "Employee", "SuperAdmin"])


class CompanyInfo(BaseModel):
    """Company information in permissions response."""

    slug: str = Field(..., description="Company slug identifier")


class AuthContext(BaseModel):
    """Authentication context for permission evaluation.
    
    Represents contextual information about the authenticated user used to 
    qualify permission evaluation. Based on F2_api_spec.md Section 4.1.
    """

    role: RoleInfo = Field(..., description="User role information")
    company_id: Optional[UUID] = Field(None, description="Company identifier (null for SuperAdmin)")
    company: Optional[CompanyInfo] = Field(None, description="Company information (null for SuperAdmin)")
    is_super_admin: bool = Field(..., description="Whether user is SuperAdmin")
    is_company_active: Optional[bool] = Field(None, description="Whether user's company is active (null for SuperAdmin)")


class UserPermissionsResponse(BaseModel):
    """Response schema for GET /api/v1/auth/me endpoint.
    
    Returns the authenticated user's user details, PermissionSet (resource-action mappings) 
    and AuthContext (role, company, status flags) in a single response.
    User details are at the top, followed by permissions, then context.
    """

    user: UserDetails = Field(..., description="User details")
    permissions: dict[str, list[str]] = Field(
        ...,
        description="Resource-action permission mapping",
        examples=[{"tasks": ["create", "read", "update", "delete"], "salary": ["read"]}],
    )
    context: AuthContext = Field(..., description="User authentication context")
