"""Domain-specific dependencies for authentication."""

from uuid import UUID
from typing import TYPE_CHECKING, Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from src.database import get_session
from src.auth.service import AuthService
from src.auth.utils import decode_token
from src.auth.exceptions import InvalidCredentials
from src.users.models import User

if TYPE_CHECKING:
    from src.auth.schemas import (
        LoginRequest,
        LoginResponse,
        ActivationRequest,
        ActivationResponse,
        ActivationValidationResponse,
        PasswordResetRequestRequest,
        PasswordResetRequestResponse,
        PasswordResetRequest,
        PasswordResetResponse,
        UserPermissionsResponse,
    )

# OAuth2 scheme for Swagger UI
# CRITICAL: MUST use OAuth2PasswordBearer (NOT HTTPBearer) for Swagger UI integration
# Based on auth_setup.md RULE 3.1.1 and error_prevention.md RULE 3.1.2
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/auth/token",  # Full path including main router prefix (/v1/api/auth/token)
    auto_error=False,  # CRITICAL: Don't auto-raise if token missing (allows graceful handling)
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get current authenticated user from JWT token.
    
    CRITICAL: Checks if token is None before decoding to prevent AttributeError.
    Also checks if token is blacklisted (logged out).
    """
    from src.auth.exceptions import InvalidCredentials
    from src.auth.utils import is_token_blacklisted
    
    # CRITICAL: Check if token is None before decoding
    if not token:
        raise InvalidCredentials()
    
    # Check if token is blacklisted (user has logged out)
    if await is_token_blacklisted(token):
        raise InvalidCredentials()
    
    try:
        # Decode and validate JWT token
        payload = decode_token(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise InvalidCredentials()
        
        # Fetch user from database
        user = await session.get(User, UUID(user_id))
        if user is None:
            raise InvalidCredentials()
        
        # Validate user is not soft-deleted
        if user.deleted_at is not None:
            raise InvalidCredentials()
        
        # Validate user is active
        if not user.is_active:
            raise InvalidCredentials()
        
        return user
    except (JWTError, ValueError, TypeError):
        raise InvalidCredentials()


class AuthApiDep:
    """API dependency class for authentication endpoints."""

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = AuthService(session)
        self.session = session

    async def login(self, request: "LoginRequest") -> "LoginResponse":
        """Login user."""
        return await self.service.login(request)

    async def logout(self, token: str) -> dict:
        """Logout user."""
        return await self.service.logout(token)

    async def get_activation(self, token: UUID) -> "ActivationValidationResponse":
        """Get activation token validation."""
        return await self.service.get_activation(token)

    async def activate_account(self, token: UUID, request: "ActivationRequest") -> "ActivationResponse":
        """Activate user account."""
        return await self.service.activate_account(token, request)

    async def request_password_reset(self, request: "PasswordResetRequestRequest") -> "PasswordResetRequestResponse":
        """Request password reset."""
        return await self.service.request_password_reset(request)

    async def reset_password(self, token: UUID, request: "PasswordResetRequest") -> "PasswordResetResponse":
        """Reset user password."""
        return await self.service.reset_password(token, request)

    async def get_user_permissions(self, user_id: UUID) -> "UserPermissionsResponse":
        """Get user permissions and context."""
        return await self.service.get_user_permissions(user_id)
