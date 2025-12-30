"""Domain-specific dependencies for Notifications System module.

Based on F3_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
"""

from uuid import UUID
from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.auth.dependencies import get_current_user, oauth2_scheme
from src.auth.utils import decode_token, is_token_blacklisted
from src.auth.exceptions import InvalidCredentials
from src.users.models import User
from src.notifications.service import NotificationService
from jose import JWTError


async def get_current_user_with_company(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Optional[UUID]]:
    """Get current authenticated user and company_id from JWT token.
    
    Returns tuple of (User, company_id) where company_id is:
    - None for SuperAdmin (company_id is null in token)
    - UUID for company-scoped users (company_id from token)
    
    Based on F3_api_spec.md Section 2.1 - Multi-tenancy from token.
    """
    # CRITICAL: Check if token is None before decoding
    if not token:
        raise InvalidCredentials()
    
    # Check if token is blacklisted (user has logged out)
    if await is_token_blacklisted(token):
        raise InvalidCredentials()
    
    try:
        # Decode token to get payload
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
        
        # Extract company_id from token
        # Note: JWT token uses "company_id" (not "org_id") - see auth/service.py line 98
        # F3_api_spec.md mentions "org_id" but actual implementation uses "company_id"
        company_id_str = payload.get("company_id")  # JWT token uses company_id
        company_id = UUID(company_id_str) if company_id_str else None
        
        return user, company_id
    except (JWTError, ValueError, TypeError):
        raise InvalidCredentials()


class NotificationApiDep:
    """API dependency class for Notifications System endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = NotificationService(session)
        self.session = session

    async def list_notifications(self, user_id: UUID, company_id: UUID, query, if_none_match: Optional[str] = None):
        """List notifications with pagination, filtering, and sorting with ETag support."""
        return await self.service.list_notifications(user_id, company_id, query, if_none_match=if_none_match)

    async def get_notification_by_id(self, notification_id: UUID, user_id: UUID, company_id: UUID, if_none_match: Optional[str] = None):
        """Get notification by ID with ETag support."""
        return await self.service.get_notification_by_id(notification_id, user_id, company_id, if_none_match=if_none_match)

    async def mark_notification_as_read(self, notification_id: UUID, user_id: UUID, company_id: UUID):
        """Mark notification as read."""
        return await self.service.mark_notification_as_read(notification_id, user_id, company_id)

    async def bulk_mark_read(self, user_id: UUID, company_id: UUID, request, if_match: Optional[str] = None):
        """Bulk mark notifications as read or unread with ETag validation."""
        return await self.service.bulk_mark_read(user_id, company_id, request, if_match=if_match)

    async def get_unread_count(self, user_id: UUID, company_id: UUID):
        """Get unread notification count."""
        return await self.service.get_unread_count(user_id, company_id)
