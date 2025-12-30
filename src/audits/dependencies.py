"""Domain-specific dependencies for Audit Logging & Activity History module.

Based on F11_api_spec.md Section 2.1 - Authentication and Section 3 - Roles & Permissions.
"""

from uuid import UUID
from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.auth.dependencies import oauth2_scheme
from src.auth.utils import decode_token, is_token_blacklisted
from src.auth.exceptions import InvalidCredentials
from src.users.models import User
from src.permissions.models import Role
from src.audits.exceptions import (
    InsufficientPermissions,
    EmployeeNoAccess,
    SuperAdminBlocked,
)
from src.audits.service import AuditLogService
from jose import JWTError


async def get_current_user_with_company(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Optional[UUID], str]:
    """Get current authenticated user with company and role from JWT token.
    
    Based on F11_api_spec.md Section 2.1 - Authentication.
    
    Returns tuple of (User, company_id, role) where:
    - company_id is None for SuperAdmin (org_id is null in token)
    - company_id is UUID for company-scoped users (org_id from token)
    - role is the user's role from token (superadmin, ceo, hr, manager, employee)
    """
    # CRITICAL: Check if token is provided
    if not token:
        raise InvalidCredentials()
    
    # Check if token is blacklisted
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
        # F11_api_spec.md Section 2.1 specifies "org_id" claim
        # Support both for backward compatibility: try org_id first (per spec), then company_id
        company_id_str = payload.get("org_id") or payload.get("company_id")
        company_id = UUID(company_id_str) if company_id_str else None
        
        # Extract role from token
        # NOTE: F11_api_spec.md Section 2.1 specifies "role" claim should be encoded directly in token.
        # However, the codebase pattern (used in all other features) is to use "role_id" and fetch from database.
        # This implementation follows the codebase pattern for consistency. If spec compliance is required,
        # the token generation in auth/service.py would need to include "role" claim in addition to "role_id".
        role_id_str = payload.get("role_id")
        if not role_id_str:
            raise InvalidCredentials("role_id is required in token")
        
        role_id = UUID(role_id_str)
        role_obj = await session.get(Role, role_id)
        if not role_obj:
            raise InvalidCredentials("Invalid role_id in token")
        
        # Get role code from Role object
        role = role_obj.code.lower()
        
        return user, company_id, role
    except (JWTError, ValueError, TypeError):
        raise InvalidCredentials()


async def get_current_audit_log_user(
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
) -> tuple[User, UUID, str]:
    """Get current authenticated user for audit log endpoints with role validation.
    
    Based on F11_api_spec.md Section 3 - Roles & Permissions.
    
    Validates:
    - SuperAdmin is blocked (returns 403)
    - Employee has no access (returns 403)
    - Company-scoped users (CEO, HR, Manager) must have company_id
    
    Returns tuple of (User, company_id, role).
    Raises SuperAdminBlocked if user is SuperAdmin.
    Raises EmployeeNoAccess if user is Employee.
    Raises InsufficientPermissions if company_id is None for company-scoped roles.
    """
    user, company_id, role = user_company
    
    # CRITICAL: SuperAdmin is blocked from accessing audit logs
    if role == "superadmin" or company_id is None:
        raise SuperAdminBlocked()
    
    # CRITICAL: Employee has no access to audit logs
    if role == "employee":
        raise EmployeeNoAccess()
    
    # Company-scoped roles (CEO, HR, Manager) must have company_id
    if company_id is None:
        raise InsufficientPermissions("Company ID is required for audit log access.")
    
    return user, company_id, role


class AuditLogApiDep:
    """API dependency class for Audit Logging & Activity History endpoints.
    
    Based on setup.md RULE 8.6.7 - API Dependency Pattern.
    Handles service instantiation and business logic delegation.
    """
    
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session
        self.service = AuditLogService(session)
    
    async def list_audit_logs(
        self,
        company_id: UUID,
        query,
        role: str,
        if_none_match: Optional[str] = None,
    ):
        """List audit logs with pagination, filtering, and sorting."""
        return await self.service.list_audit_logs(
            company_id=company_id,
            query=query,
            role=role,
            if_none_match=if_none_match,
        )
    
    async def get_audit_log_by_id(
        self,
        audit_log_id: UUID,
        company_id: UUID,
        role: str,
        if_none_match: Optional[str] = None,
    ):
        """Get detailed audit log information."""
        return await self.service.get_audit_log_by_id(
            audit_log_id=audit_log_id,
            company_id=company_id,
            role=role,
            if_none_match=if_none_match,
        )
