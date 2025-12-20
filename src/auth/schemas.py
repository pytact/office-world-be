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
    org_id: Optional[UUID] = None
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
    org_id: Optional[UUID] = None
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
