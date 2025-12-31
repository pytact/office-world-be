"""Domain-specific dependencies for User & Role Management module.

Based on F1A_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
"""

from uuid import UUID
from typing import Optional
from fastapi import Depends
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.auth.dependencies import get_current_user, oauth2_scheme
from src.auth.utils import decode_token, is_token_blacklisted
from src.auth.exceptions import InvalidCredentials
from src.users.models import User
from src.users.constants import ROLE_CODE_SUPERADMIN
from src.users.schemas import PlatformUserListQuery
from src.permissions.models import Role
from src.users.service import UserService
from src.users.exceptions import InsufficientPermissions
from src.permissions.models import UserRoleAssignment
from src.companies.models import Company


async def get_current_user_with_token(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, dict]:
    """Get current authenticated user and token payload.
    
    Returns tuple of (User, token_payload) for role and company_id extraction.
    Also checks if token is blacklisted (logged out).
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
        
        # Validate user is not soft-deleted (check deleted_at, not is_deleted)
        if user.deleted_at is not None:
            raise InvalidCredentials()
        
        # Validate user is active
        if not user.is_active:
            raise InvalidCredentials()
        
        return user, payload
    except (JWTError, ValueError, TypeError):
        raise InvalidCredentials()


async def get_current_superadmin(
    user_token: tuple[User, dict] = Depends(get_current_user_with_token),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get current authenticated user and verify SuperAdmin role.
    
    Based on F1A_api_spec.md Section 3.1 - SuperAdmin role definition.
    SuperAdmin has role="superadmin" (case-insensitive) and company_id=null in token.
    """
    
    user, payload = user_token
    
    # Extract role_id from token and fetch role from database
    role_id_str = payload.get("role_id")
    if not role_id_str:
        raise InsufficientPermissions("role_id is required in token")
    
    role_id = UUID(role_id_str)
    role_obj = await session.get(Role, role_id)
    if not role_obj:
        raise InsufficientPermissions("Invalid role_id in token")
    
    role_code = role_obj.code.lower()
    company_id = payload.get("company_id")
    
    # Case-insensitive comparison to handle "SuperAdmin" vs "superadmin"
    if role_code != ROLE_CODE_SUPERADMIN.lower() or company_id is not None:
        raise InsufficientPermissions("access platform-wide user list")
    
    return user


async def get_current_company_user(
    user_token: tuple[User, dict] = Depends(get_current_user_with_token),
) -> tuple[User, Optional[UUID]]:
    """Get current authenticated user and company_id from token.
    
    Returns tuple of (User, company_id) where company_id is:
    - None for SuperAdmin (company_id is null)
    - UUID for company-scoped users (company_id from token)
    
    Based on F1A_api_spec.md Section 2.1 - Multi-tenancy from token.
    """
    user, payload = user_token
    
    company_id_str = payload.get("company_id")
    company_id = UUID(company_id_str) if company_id_str else None
    
    return user, company_id


async def get_user_role_from_token(
    user_token: tuple[User, dict] = Depends(get_current_user_with_token),
    session: AsyncSession = Depends(get_session),
) -> str:
    """Extract role from token payload.
    
    Returns role code (superadmin, ceo, hr, manager, employee).
    """
    _, payload = user_token
    
    # Extract role_id from token and fetch role from database
    role_id_str = payload.get("role_id")
    if not role_id_str:
        return "employee"  # Default fallback
    
    role_id = UUID(role_id_str)
    role_obj = await session.get(Role, role_id)
    if not role_obj:
        return "employee"  # Default fallback
    
    return role_obj.code.lower()


class UserApiDep:
    """API dependency class for User & Role Management endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.service = UserService(session)
        self.session = session

    async def list_platform_users(self, query, if_none_match: Optional[str] = None):
        """List all users across platform (SuperAdmin only) with ETag support."""
        return await self.service.list_platform_users(query, if_none_match=if_none_match)

    async def list_company_users(self, company_id: Optional[UUID], query, include_sensitive: bool = True, if_none_match: Optional[str] = None):
        """List users in company with field visibility rules and ETag support."""
        if company_id is None:
            # SuperAdmin accessing company users - convert CompanyUserListQuery to PlatformUserListQuery
            platform_query = PlatformUserListQuery(
                page=query.page,
                page_size=query.page_size,
                search=query.search,
                company_slug=None,  # CompanyUserListQuery doesn't have company_slug
                role_code=query.role_code,
                status=query.status,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
            )
            return await self.service.list_platform_users(platform_query, if_none_match=if_none_match)
        return await self.service.list_company_users(company_id, query, include_sensitive=include_sensitive, if_none_match=if_none_match)

    async def get_user_by_id(self, user_id: UUID, include_sensitive: bool = True, if_none_match: Optional[str] = None):
        """Get user details by ID with field visibility rules."""
        return await self.service.get_user_by_id(user_id, include_sensitive=include_sensitive, if_none_match=if_none_match)

    async def invite_user(
        self,
        invite_data,
        inviter_id: UUID,
        inviter_company_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Invite new user with role and company assignment."""
        return await self.service.invite_user(
            invite_data,
            inviter_id,
            inviter_company_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def update_user(
        self, user_id: UUID, update_data, current_user: User, current_user_company_id: Optional[UUID], if_match: Optional[str] = None
    ):
        """Update user information."""
        return await self.service.update_user(user_id, update_data, current_user, current_user_company_id, if_match=if_match)

    async def list_roles(self):
        """List available roles for invitation form."""
        return await self.service.list_roles()

    # F1B Lifecycle Operations API Methods
    async def change_user_role(
        self,
        user_id: UUID,
        role_change_data,
        changer_id: UUID,
        changer_company_id: Optional[UUID] = None,
        if_match: Optional[str] = None,
    ):
        """Change user role within same company."""
        return await self.service.change_user_role(user_id, role_change_data, changer_id, changer_company_id=changer_company_id, if_match=if_match)

    async def reassign_user_company(
        self,
        user_id: UUID,
        company_id: UUID,
        reassign_data,
        reassigner_id: UUID,
        if_match: Optional[str] = None,
    ):
        """Reassign user to different company with optional role change."""
        return await self.service.reassign_user_company(user_id, company_id, reassign_data, reassigner_id, if_match=if_match)

    async def deactivate_user(
        self,
        user_id: UUID,
        deactivator_id: UUID,
        deactivator_company_id: Optional[UUID] = None,
        if_match: Optional[str] = None,
    ):
        """Deactivate user (set is_active=false)."""
        return await self.service.deactivate_user(user_id, deactivator_id, deactivator_company_id=deactivator_company_id, if_match=if_match)

    async def reactivate_user(
        self,
        user_id: UUID,
        reactivator_id: UUID,
        reactivator_company_id: Optional[UUID] = None,
        if_match: Optional[str] = None,
    ):
        """Reactivate user (set is_active=true)."""
        return await self.service.reactivate_user(user_id, reactivator_id, reactivator_company_id=reactivator_company_id, if_match=if_match)

    async def update_user_status(
        self,
        user_id: UUID,
        status_data,
        updater_id: UUID,
        updater_company_id: Optional[UUID] = None,
        if_match: Optional[str] = None,
    ):
        """Update user activation status (unified method for activate/deactivate)."""
        return await self.service.update_user_status(user_id, status_data, updater_id, updater_company_id=updater_company_id, if_match=if_match)

    async def resend_invitation(
        self,
        user_id: UUID,
        resender_id: UUID,
        resender_company_id: Optional[UUID] = None,
    ):
        """Resend invitation to user (generates new token and expiry)."""
        return await self.service.resend_invitation(user_id, resender_id, resender_company_id=resender_company_id)
