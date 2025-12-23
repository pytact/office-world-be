"""Business logic for authentication."""

from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.repository import AuthRepository
from src.auth.schemas import (
    LoginRequest,
    LoginResponse,
    UserInfo,
    ActivationRequest,
    ActivationResponse,
    ActivationValidationResponse,
    PasswordResetRequestRequest,
    PasswordResetRequestResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    UserPermissionsResponse,
)
from src.auth.exceptions import (
    InvalidCredentials,
    AccountInactive,
    AccountDeleted,
    CompanyInactive,
    InvalidToken,
    InvitationNotFound,
    InvitationExpired,
    AccountAlreadyActivated,
    PasswordMismatch,
    PasswordWeak,
    ResetTokenNotFound,
    ResetTokenExpired,
    ResetTokenUsed,
)
from src.auth.utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_token,
    is_token_expired,
)
from src.auth.constants import (
    INVITATION_TOKEN_EXPIRY_HOURS,
    PASSWORD_RESET_TOKEN_EXPIRY_HOURS,
    JWT_ACCESS_TOKEN_EXPIRY_SECONDS,
    ERROR_PASSWORD_WEAK,
)
from src.config import settings
from src.celery_worker import send_password_reset_email, send_welcome_email


class AuthService:
    """Service for authentication business logic."""

    def __init__(self, session: AsyncSession):
        self.repository = AuthRepository(session)
        self.session = session

    async def login(self, request: LoginRequest) -> LoginResponse:
        """Authenticate user and return JWT token."""
        # Get user by email with eager loading
        user = await self.repository.get_user_by_email(request.email)
        if not user:
            raise InvalidCredentials()

        # Validate password exists and is correct
        if not user.password:
            raise InvalidCredentials()
        
        # Validate password
        if not verify_password(request.password, user.password):
            raise InvalidCredentials()

        # Validate account is not soft-deleted
        if user.deleted_at is not None:
            raise AccountDeleted()

        # Validate account is active
        if not user.is_active:
            raise AccountInactive()

        # Get active role assignment with eager loading
        role_assignment = await self.repository.get_active_role_assignment(user.id)
        if not role_assignment:
            raise InvalidCredentials()

        # Validate company is active (for non-SuperAdmin users)
        if role_assignment.company_id and role_assignment.company:
            if not role_assignment.company.is_active:
                raise CompanyInactive()

        # Get role_id for JWT token (role_id is required, should never be None)
        if not role_assignment.role_id:
            raise InvalidCredentials("Role assignment missing role_id")
        
        role_id = role_assignment.role_id
        role_code = role_assignment.role.code if role_assignment.role else None

        # Create JWT token
        token_data = {
            "sub": str(user.id),
            "role_id": str(role_id),
            "company_id": str(role_assignment.company_id) if role_assignment.company_id else None,
        }
        access_token = create_access_token(token_data)

        # Build user info
        user_info = UserInfo(
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=role_code or "employee",
            company_id=role_assignment.company_id,
            company_slug=role_assignment.company.slug if role_assignment.company else None,
            company_is_active=role_assignment.company.is_active if role_assignment.company else None,
            is_super_admin=role_assignment.company_id is None,
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_ACCESS_TOKEN_EXPIRY_SECONDS,
            user=user_info,
        )

    async def logout(self, token: str) -> dict:
        """Logout user by blacklisting the JWT token."""
        from src.auth.utils import blacklist_token
        await blacklist_token(token)
        return {}

    async def get_activation(self, token: UUID) -> ActivationValidationResponse:
        """Validate invitation token and return activation details."""
        # Get user by token with eager loading
        user = await self.repository.get_user_by_token(token)
        if not user:
            raise InvitationNotFound(str(token))

        # Validate token matches
        if user.token != token:
            raise InvitationNotFound(str(token))

        # Check if already activated
        if user.activate_at is not None:
            raise AccountAlreadyActivated()

        # Check if token expired
        if is_token_expired(user.expiry):
            raise InvitationExpired()

        # Get role assignment for company name
        role_assignment = await self.repository.get_active_role_assignment(user.id)
        company_name = role_assignment.company.name if role_assignment and role_assignment.company else "Unknown"
        role_code = role_assignment.role.code if role_assignment and role_assignment.role else "employee"

        return ActivationValidationResponse(
            email=user.email,
            company_name=company_name,
            role=role_code,
            invitation_status="valid",
            expires_at=user.expiry or datetime.now(timezone.utc),
        )

    async def activate_account(self, token: UUID, request: ActivationRequest) -> ActivationResponse:
        """Activate user account with invitation token."""
        # Validate password match
        if request.password != request.password_confirm:
            raise PasswordMismatch()

        # Validate password complexity (already validated in schema, but double-check)
        password_issue = self._validate_password_complexity(request.password)
        if password_issue:
            raise PasswordWeak(password_issue)

        # Get user by token with eager loading
        user = await self.repository.get_user_by_token(token)
        if not user:
            raise InvitationNotFound(str(token))

        # Validate token matches
        if user.token != token:
            raise InvitationNotFound(str(token))

        # Check if already activated
        if user.activate_at is not None:
            raise AccountAlreadyActivated()

        # Check if token expired
        if is_token_expired(user.expiry):
            raise InvitationExpired()

        # Update user
        user.first_name = request.first_name
        user.last_name = request.last_name
        user.password = get_password_hash(request.password)
        user.activate_at = datetime.now(timezone.utc)
        user.is_active = True
        user.token = None  # Clear token after use
        user.expiry = None

        await self.repository.update_user(user)

        # Get role assignment for company_id
        role_assignment = await self.repository.get_active_role_assignment(user.id)
        role_code = role_assignment.role.code if role_assignment and role_assignment.role else "employee"

        # Send welcome email after successful activation
        user_name = f"{user.first_name} {user.last_name}".strip() if user.first_name or user.last_name else user.email.split("@")[0]
        send_welcome_email.delay(
            user_email=user.email,
            user_name=user_name,
        )

        return ActivationResponse(
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=role_code,
            company_id=role_assignment.company_id if role_assignment else None,
            activated_at=user.activate_at,
        )

    async def request_password_reset(self, request: PasswordResetRequestRequest) -> PasswordResetRequestResponse:
        """Request password reset and send email with reset token."""
        # Get user by email
        user = await self.repository.get_user_by_email(request.email)
        
        # Always return success to prevent email enumeration (even if user doesn't exist)
        if user and user.deleted_at is None:
            # Generate reset token
            reset_token = generate_token()
            user.token = reset_token
            user.expiry = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRY_HOURS)
            await self.repository.update_user(user)
            
            # Build reset URL using frontend_url from settings
            if hasattr(settings, 'frontend_url'):
                reset_url = f"{settings.frontend_url}/reset-password/{reset_token}"
            else:
                reset_url = f"http://localhost:3000/reset-password/{reset_token}"  # Fallback
            
            # Send password reset email asynchronously via Celery
            send_password_reset_email.delay(
                user_email=user.email,
                reset_token=str(reset_token),
                reset_url=reset_url,
            )

        return PasswordResetRequestResponse(
            email=request.email,
            reset_requested=True,
        )

    async def reset_password(self, token: UUID, request: PasswordResetRequest) -> PasswordResetResponse:
        """Reset user password using reset token."""
        # Validate password match
        if request.password != request.password_confirm:
            raise PasswordMismatch()

        # Validate password complexity
        password_issue = self._validate_password_complexity(request.password)
        if password_issue:
            raise PasswordWeak(password_issue)

        # Get user by token with eager loading
        user = await self.repository.get_user_by_token(token)
        if not user:
            raise ResetTokenNotFound(str(token))

        # Validate token matches
        if user.token != token:
            raise ResetTokenNotFound(str(token))

        # Check if token expired
        if is_token_expired(user.expiry):
            raise ResetTokenExpired()

        # Check if token already used (if activate_at is set, token was used for activation)
        # For password reset, we check if token was recently used by checking expiry
        # In a more sophisticated system, we'd track token usage separately

        # Update password and clear token
        user.password = get_password_hash(request.password)
        user.token = None
        user.expiry = None
        reset_at = datetime.now(timezone.utc)

        await self.repository.update_user(user)

        return PasswordResetResponse(
            email=user.email,
            password_reset=True,
            reset_at=reset_at,
        )

    def _validate_password_complexity(self, password: str) -> str | None:
        """Validate password complexity and return error message if invalid."""
        if len(password) < 8:
            return "Password must be at least 8 characters long"
        if not any(c.isupper() for c in password):
            return "Password must contain at least one uppercase letter"
        if not any(c.islower() for c in password):
            return "Password must contain at least one lowercase letter"
        if not any(c.isdigit() for c in password):
            return "Password must contain at least one number"
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return "Password must contain at least one special character"
        return None

    async def get_user_permissions(self, user_id: UUID) -> "UserPermissionsResponse":
        """Get user permissions and context for GET /api/v1/auth/me endpoint.
        
        Returns user details, PermissionSet and AuthContext after evaluating:
        - Role permissions (with inheritance resolved at seed time)
        - Company scoping (for non-SuperAdmin users)
        - User activation status (deactivated users get empty permissions)
        - Company activation status (inactive companies result in empty permissions)
        
        Based on F2_api_spec.md Section 4.3.1.
        """
        from src.auth.schemas import (
            UserPermissionsResponse,
            UserDetails,
            AuthContext,
            RoleInfo,
            CompanyInfo,
        )
        
        # Get user with all relationships loaded
        user = await self.repository.get_user_with_permissions_context(user_id)
        if not user:
            raise InvalidCredentials()
        
        # Get active role assignment
        role_assignment = await self.repository.get_active_role_assignment(user_id)
        if not role_assignment:
            raise InvalidCredentials()
        
        # Determine if SuperAdmin (company_id is None)
        is_super_admin = role_assignment.company_id is None
        
        # Check user activation status
        is_user_active = user.is_active
        
        # Check company activation status (null for SuperAdmin)
        is_company_active: bool | None = None
        if not is_super_admin and role_assignment.company:
            is_company_active = role_assignment.company.is_active
        
        # Build UserDetails
        user_details = UserDetails(
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        
        # Build AuthContext
        role_info = RoleInfo(
            code=role_assignment.role.code if role_assignment.role else "employee",
            name=role_assignment.role.name if role_assignment.role else "Employee",
        )
        
        company_info: CompanyInfo | None = None
        company_id: UUID | None = None
        if not is_super_admin and role_assignment.company:
            company_id = role_assignment.company_id
            company_info = CompanyInfo(slug=role_assignment.company.slug)
        
        context = AuthContext(
            role=role_info,
            company_id=company_id,
            company=company_info,
            is_super_admin=is_super_admin,
            is_company_active=is_company_active,
        )
        
        # Compute PermissionSet
        permissions: dict[str, list[str]] = {}
        
        # If user is deactivated, return empty permissions
        if not is_user_active:
            return UserPermissionsResponse(user=user_details, permissions=permissions, context=context)
        
        # If company is inactive (for company-scoped users), return empty permissions
        if not is_super_admin and is_company_active is False:
            return UserPermissionsResponse(user=user_details, permissions=permissions, context=context)
        
        # Get permissions from role (inheritance already resolved at seed time)
        if role_assignment.role and role_assignment.role.permissions:
            # Permissions are stored as JSONB: {"resource": ["action1", "action2"], ...}
            # Role inheritance is resolved at seed time, so permissions already include inherited permissions
            permissions = role_assignment.role.permissions.copy()
        
        return UserPermissionsResponse(user=user_details, permissions=permissions, context=context)
