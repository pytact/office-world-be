"""Business logic for User & Role Management module.

Service layer - all business logic, validation, and orchestration.
No HTTP concerns, no database queries (uses repository).
"""

from uuid import UUID, uuid4
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from src.users.models import User
from src.permissions.models import UserRoleAssignment, Role
from src.companies.models import Company
from src.users.repository import UserRepository
from src.users.schemas import (
    PlatformUserListQuery,
    CompanyUserListQuery,
    UserInvite,
    UserUpdate,
    UserRoleChange,
    UserCompanyReassign,
    UserRead,
    UserListItem,
    RoleRead,
    CompanyRead,
    RolesListResponse,
    CompaniesListResponse,
)
from src.users.utils import generate_etag, format_last_modified
from src.users.exceptions import (
    UserNotFound,
    DuplicateEmail,
    CompanyNotFound,
    RoleNotFound,
    CompanyHasCEO,
    CannotChangeOwnRole,
    CannotDeactivateOwnAccount,
    CannotReassignSuperAdmin,
    PreconditionRequired,
    PreconditionFailed,
    TargetCompanyHasCEO,
    InsufficientPermissions,
    InvalidCurrentPassword,
)
from src.exceptions import ValidationError
from src.auth.utils import verify_password, get_password_hash
from src.users.constants import (
    INVITATION_STATUS_PENDING,
    INVITATION_STATUS_EXPIRED,
    INVITATION_STATUS_ACTIVATED,
    INVITATION_EXPIRY_SECONDS,
    ROLE_CODE_SUPERADMIN,
    ROLE_CODE_CEO,
    ROLE_CODE_HR,
    ROLE_CODE_CEO,
)
from src.pagination import PagedCollection


class UserService:
    """Service for user management business logic."""
    
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
    """Service for user management business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)

    def _calculate_invitation_status(
        self, invite_at: Optional[datetime], activate_at: Optional[datetime], expiry: Optional[datetime]
    ) -> Optional[str]:
        """Calculate invitation status from user fields.
        
        Based on F1A_api_spec.md Section 8.5 - Invitation Status Calculation.
        """
        if activate_at is not None:
            return INVITATION_STATUS_ACTIVATED
        elif invite_at is not None and expiry is not None:
            if datetime.utcnow() > expiry.replace(tzinfo=None) if expiry.tzinfo else expiry:
                return INVITATION_STATUS_EXPIRED
            else:
                return INVITATION_STATUS_PENDING
        return None

    def _calculate_can_resend_invite(
        self, is_active: bool, invite_at: Optional[datetime], expiry: Optional[datetime]
    ) -> bool:
        """Calculate if re-invitation is allowed.
        
        Based on F1A_api_spec.md Section 5.3 - can_resend_invite field.
        - true if user is inactive OR invitation is expired
        - false if user is active and invitation is not expired
        """
        if not is_active:
            return True
        if invite_at is not None and expiry is not None:
            if datetime.utcnow() > expiry.replace(tzinfo=None) if expiry.tzinfo else expiry:
                return True
        return False

    def _get_active_role_assignment(self, user: User) -> Optional[UserRoleAssignment]:
        """Get active role assignment for user."""
        if not user.role_assignments:
            return None
        for assignment in user.role_assignments:
            if assignment.is_active and assignment.deleted_at is None:
                return assignment
        return None

    def _build_user_read(
        self, user: User, include_sensitive: bool = True
    ) -> UserRead:
        """Build UserRead response schema from User model.
        
        Args:
            user: User model instance
            include_sensitive: If False, excludes sensitive fields (Manager view)
        """
        active_assignment = self._get_active_role_assignment(user)
        
        # Build role info
        role_info = None
        if active_assignment and active_assignment.role:
            role_info = {
                "code": active_assignment.role.code,
                "name": active_assignment.role.name,
            }
        
        # Build company info
        company_info = None
        if include_sensitive and active_assignment and active_assignment.company:
            company_info = {
                "company_id": active_assignment.company.id,
                "name": active_assignment.company.name,
                "slug": active_assignment.company.slug,
            }
        
        # Calculate derived fields
        invitation_status = None
        can_resend_invite = None
        if include_sensitive:
            invitation_status = self._calculate_invitation_status(
                user.invite_at, user.activate_at, user.expiry
            )
            can_resend_invite = self._calculate_can_resend_invite(
                user.is_active, user.invite_at, user.expiry
            )
        
        # Build response
        user_data = {
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "role": role_info,
            "updated_at": user.updated_at,
        }
        
        # Add sensitive fields only if include_sensitive is True
        if include_sensitive:
            user_data["is_deleted"] = user.deleted_at is not None
            user_data["invite_at"] = user.invite_at
            user_data["activate_at"] = user.activate_at
            user_data["expiry"] = user.expiry
            user_data["reinvite_count"] = user.reinvite_count
            user_data["last_reinvite_at"] = user.last_reinvite_at
            user_data["invitation_status"] = invitation_status
            user_data["can_resend_invite"] = can_resend_invite
            user_data["company"] = company_info
        else:
            # Manager view - exclude sensitive fields
            user_data["company"] = None
        
        # Generate ETag and Last-Modified from updated_at
        user_read = UserRead(**user_data)
        if user.updated_at:
            user_read.etag = generate_etag(user.updated_at)
            user_read.last_modified = user.updated_at
        
        return user_read

    def _build_user_list_item(
        self, user: User, include_sensitive: bool = True
    ) -> UserListItem:
        """Build UserListItem response schema from User model.
        
        Args:
            user: User model instance
            include_sensitive: If False, excludes sensitive fields (Manager view)
        """
        active_assignment = self._get_active_role_assignment(user)
        
        # Build role info
        role_info = None
        if active_assignment and active_assignment.role:
            role_info = {
                "code": active_assignment.role.code,
                "name": active_assignment.role.name,
            }
        
        # Build company info
        company_info = None
        if include_sensitive and active_assignment and active_assignment.company:
            company_info = {
                "company_id": active_assignment.company.id,
                "name": active_assignment.company.name,
                "slug": active_assignment.company.slug,
            }
        
        # Calculate invitation status
        invitation_status = None
        if include_sensitive:
            invitation_status = self._calculate_invitation_status(
                user.invite_at, user.activate_at, user.expiry
            )
        
        # Build response
        user_data = {
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "role": role_info,
            "updated_at": user.updated_at,
        }
        
        # Add sensitive fields only if include_sensitive is True
        if include_sensitive:
            user_data["is_deleted"] = user.deleted_at is not None
            user_data["invite_at"] = user.invite_at
            user_data["activate_at"] = user.activate_at
            user_data["expiry"] = user.expiry
            user_data["invitation_status"] = invitation_status
            user_data["company"] = company_info
        else:
            # Manager view - exclude sensitive fields
            user_data["company"] = None
        
        return UserListItem(**user_data)

    def _build_pagination_url(
        self,
        base_path: str,
        page: int,
        page_size: int,
        query_params: dict,
    ) -> tuple[Optional[str], Optional[str]]:
        """Build next_page and prev_page URLs with all query parameters."""
        # Build query string from all params
        params = {k: v for k, v in query_params.items() if v is not None}
        params["page"] = page
        params["page_size"] = page_size
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{base_path}?{query_string}" if query_string else base_path
        
        next_page = f"{base_path}?page={page + 1}&page_size={page_size}&{query_string.replace(f'page={page}', '')}" if page > 0 else None
        prev_page = f"{base_path}?page={page - 1}&page_size={page_size}&{query_string.replace(f'page={page}', '')}" if page > 1 else None
        
        # Simplified approach
        next_page = f"{base_path}?page={page + 1}&page_size={page_size}" if query_string else f"{base_path}?page={page + 1}&page_size={page_size}"
        prev_page = f"{base_path}?page={page - 1}&page_size={page_size}" if page > 1 and query_string else None
        
        return next_page, prev_page

    async def list_platform_users(
        self, query: PlatformUserListQuery
    ) -> PagedCollection[UserListItem]:
        """List all users across platform with pagination and filtering.
        
        Based on F1A_api_spec.md Section 5.1 - GET /api/v1/users.
        """
        users, total = await self.repository.list_platform_users(
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            company_slug=query.company_slug,
            role_code=query.role_code,
            status=query.status,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        # Build list items (full field set for SuperAdmin)
        items = [self._build_user_list_item(user, include_sensitive=True) for user in users]
        
        # Calculate pagination
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build navigation URLs (simplified - full implementation would preserve all query params)
        next_page = f"/api/v1/users?page={query.page + 1}&page_size={query.page_size}" if query.page < total_pages else None
        prev_page = f"/api/v1/users?page={query.page - 1}&page_size={query.page_size}" if query.page > 1 else None
        
        return PagedCollection[UserListItem](
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def list_company_users(
        self, company_id: UUID, query: CompanyUserListQuery, include_sensitive: bool = True
    ) -> PagedCollection[UserListItem]:
        """List users in a specific company with pagination and filtering.
        
        Based on F1A_api_spec.md Section 5.2 - GET /api/v1/company/users.
        
        Args:
            company_id: Company ID to filter users
            query: Query parameters
            include_sensitive: If False, excludes sensitive fields (Manager view)
        """
        users, total = await self.repository.list_company_users(
            company_id=company_id,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            role_code=query.role_code,
            status=query.status,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        # Build list items with field visibility rules
        items = [self._build_user_list_item(user, include_sensitive=include_sensitive) for user in users]
        
        # Calculate pagination
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build navigation URLs
        next_page = f"/api/v1/company/users?page={query.page + 1}&page_size={query.page_size}" if query.page < total_pages else None
        prev_page = f"/api/v1/company/users?page={query.page - 1}&page_size={query.page_size}" if query.page > 1 else None
        
        return PagedCollection[UserListItem](
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def get_user_by_id(
        self, user_id: UUID, include_sensitive: bool = True, if_none_match: Optional[str] = None
    ) -> UserRead:
        """Get user details by ID with invitation status.
        
        Based on F1A_api_spec.md Section 5.3 - GET /api/v1/users/{user_id}.
        
        Args:
            user_id: User ID
            include_sensitive: If False, excludes sensitive fields (Manager view)
            if_none_match: If-None-Match header value for cache validation
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(str(user_id))
        
        user_read = self._build_user_read(user, include_sensitive=include_sensitive)
        
        # Note: If-None-Match validation is handled in router layer
        # Service just returns user_read with etag attached for router to check
        
        return user_read

    async def invite_user(
        self, invite_data: UserInvite, inviter_id: UUID, inviter_company_id: Optional[UUID] = None
    ) -> UserRead:
        """Invite a new user with role and company assignment.
        
        Based on F1A_api_spec.md Section 5.4 - POST /api/v1/users/invite.
        
        Business Rules:
        - Email must be unique (case-insensitive)
        - If user exists and is active: Return 409 Conflict
        - If user exists and is inactive: Re-invitation logic (see F-001B)
        - Role must be valid
        - Company must exist and be active
        - For CEO role: Company must not already have an active CEO
        - SuperAdmin can invite to any company
        - CEO and HR can only invite to their own company
        """
        # Validate role exists
        role = await self.repository.get_role_by_code(invite_data.role_code)
        if not role:
            raise RoleNotFound(invite_data.role_code)
        
        # Determine company_id based on role and inviter context
        company_id = None
        if invite_data.role_code != ROLE_CODE_SUPERADMIN:
            # Non-SuperAdmin roles require a company
            if invite_data.company_slug:
                company = await self.repository.get_company_by_slug(invite_data.company_slug)
                if not company:
                    raise CompanyNotFound(invite_data.company_slug)
                if not company.is_active:
                    raise CompanyNotFound(invite_data.company_slug)  # Inactive company treated as not found
                company_id = company.id
            else:
                # CEO/HR can only invite to their own company (company_slug ignored, use inviter's company)
                if inviter_company_id:
                    company_id = inviter_company_id
                else:
                    raise CompanyNotFound("")  # Company required for non-SuperAdmin roles
        
        # Check if company already has CEO (for CEO role assignment)
        if invite_data.role_code == ROLE_CODE_CEO and company_id:
            has_ceo = await self.repository.check_company_has_ceo(company_id)
            if has_ceo:
                company = await self.repository.get_company_by_slug(invite_data.company_slug or "")
                company_name = company.name if company else "Company"
                raise CompanyHasCEO(company_name)
        
        # Check if user with email already exists
        existing_user = await self.repository.get_by_email(invite_data.email)
        if existing_user:
            if existing_user.is_active:
                raise DuplicateEmail(invite_data.email)
            # If user exists but is inactive, this is re-invitation (handled in F-001B)
            # For F-001A, we'll treat it as an error
            raise DuplicateEmail(invite_data.email)
        
        # Create new user
        now = datetime.utcnow()
        expiry = now + timedelta(seconds=INVITATION_EXPIRY_SECONDS)
        
        user = User(
            email=invite_data.email.lower(),  # Normalize email to lowercase
            first_name=None,
            last_name=None,
            is_active=False,
            invite_at=now,
            activate_at=None,
            expiry=expiry,
            token=str(uuid4()),  # Generate invitation token
            reinvite_count=0,
            last_reinvite_at=None,
            created_by=inviter_id,
        )
        
        user = await self.repository.create_user(user)
        
        # Create role assignment
        assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=role.id,
            company_id=company_id,
            is_active=True,
            created_by=inviter_id,
        )
        self.session.add(assignment)
        await self.session.commit()
        
        # Refresh user with relationships
        user = await self.repository.get_by_id(user.id)
        return self._build_user_read(user, include_sensitive=True)

    async def update_user(
        self,
        user_id: UUID,
        update_data: UserUpdate,
        current_user: User,
        current_user_company_id: Optional[UUID],
        if_match: Optional[str] = None,
    ) -> UserRead:
        """Update user information (name, etc.).
        
        Based on F1A_api_spec.md Section 5.5 - PATCH /api/v1/users/{user_id}.
        
        Business Rules:
        - At least one field (first_name or last_name) must be provided
        - Email is immutable and cannot be updated
        - If-Match header is REQUIRED for concurrency control
        - Authorization: Users can update own profile, SuperAdmin can update any, CEO/HR can update in their company
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(str(user_id))
        
        # Authorization: Check if current user can update this user
        # Get current user's role from active role assignment
        current_user_assignment = await self.repository.get_active_role_assignment(current_user.id)
        current_user_role = current_user_assignment.role.code if current_user_assignment and current_user_assignment.role else None
        
        # Users can always update their own details
        can_update = current_user.id == user_id
        
        # SuperAdmin can update any user
        if current_user_role == ROLE_CODE_SUPERADMIN:
            can_update = True
        # CEO and HR can update users in their own company
        elif current_user_role in [ROLE_CODE_CEO, ROLE_CODE_HR]:
            # Get target user's company
            target_user_assignment = await self.repository.get_active_role_assignment(user_id)
            target_user_company_id = target_user_assignment.company_id if target_user_assignment else None
            # Allow if updating own profile or if both users are in same company
            can_update = can_update or (current_user_company_id is not None and target_user_company_id == current_user_company_id)
        # Manager and Employee can only update own profile (handled by can_update = current_user.id == user_id)
        
        if not can_update:
            raise InsufficientPermissions("update this user")
        
        # Validate If-Match header (REQUIRED per spec Section 5.5, line 725)
        if not if_match:
            raise PreconditionRequired()
        
        # Generate current ETag and validate
        current_etag = generate_etag(user.updated_at) if user.updated_at else None
        if current_etag and if_match != current_etag:
            raise PreconditionFailed()
        
        # Validate at least one field is provided (name fields or password fields)
        has_name_update = update_data.first_name is not None or update_data.last_name is not None
        has_password_update = update_data.current_password is not None or update_data.new_password is not None
        
        if not has_name_update and not has_password_update:
            raise ValidationError(
                message="At least one field must be provided (first_name, last_name, or password fields)",
                error_code="VALIDATION_FAILED",
                details=[{"field": "general", "issue": "At least one field must be provided"}],
            )
        
        # Validate password update requirements
        if has_password_update:
            # Both current_password and new_password must be provided together
            if not update_data.current_password or not update_data.new_password:
                raise ValidationError(
                    message="Both current_password and new_password must be provided together",
                    error_code="VALIDATION_FAILED",
                    details=[{"field": "current_password", "issue": "Both current_password and new_password must be provided"}],
                )
            
            # Validate user has a password (not a new user without password)
            if not user.password:
                raise ValidationError(
                    message="User does not have a password set. Please use password reset flow.",
                    error_code="VALIDATION_FAILED",
                    details=[{"field": "current_password", "issue": "User does not have a password set"}],
                )
            
            # Verify current password matches
            if not verify_password(update_data.current_password, user.password):
                raise InvalidCurrentPassword()
            
            # Validate password complexity
            password_issue = self._validate_password_complexity(update_data.new_password)
            if password_issue:
                from src.auth.exceptions import PasswordWeak
                raise PasswordWeak(password_issue)
            
            # Update password
            user.password = get_password_hash(update_data.new_password)
        
        # Update name fields
        if update_data.first_name is not None:
            user.first_name = update_data.first_name
        if update_data.last_name is not None:
            user.last_name = update_data.last_name
        
        user.updated_by = current_user.id
        
        user = await self.repository.update_user(user)
        
        # Refresh with relationships
        user = await self.repository.get_by_id(user.id)
        return self._build_user_read(user, include_sensitive=True)

    async def list_roles(self) -> RolesListResponse:
        """List available roles for invitation form.
        
        Based on F1A_api_spec.md Section 5.6 - GET /api/v1/roles.
        Response structure: {"data": {"items": [...]}}
        """
        roles = await self.repository.list_roles()
        role_reads = [RoleRead(id=role.id, code=role.code, name=role.name) for role in roles]
        return RolesListResponse(items=role_reads)

    async def list_companies(self) -> CompaniesListResponse:
        """List all active companies for SuperAdmin invitation form.
        
        Based on F1A_api_spec.md Section 5.7 - GET /api/v1/companies.
        Response structure: {"data": {"items": [...]}}
        """
        companies = await self.repository.list_companies()
        company_reads = [
            CompanyRead(
                company_id=company.id,
                name=company.name,
                slug=company.slug,
                is_active=company.is_active,
            )
            for company in companies
        ]
        return CompaniesListResponse(items=company_reads)

    # ============================================================================
    # F1B Lifecycle Operations Service Methods
    # ============================================================================

    async def change_user_role(
        self,
        user_id: UUID,
        role_change_data: UserRoleChange,
        changer_id: UUID,
        changer_company_id: Optional[UUID] = None,
        if_match: Optional[str] = None,
    ) -> UserRead:
        """Change user role within same company.
        
        Based on F1B_api_spec.md Section 5.1 - PATCH /api/v1/users/{user_id}/role.
        
        Business Rules:
        - User must exist and belong to a company (cannot change SuperAdmin role via this endpoint)
        - CEO Cardinality Rule: If assigning CEO role, company must not already have an active CEO
        - Exception: If the user being assigned CEO role is the current CEO, allow the change (no-op)
        - Users cannot change their own role
        - If-Match header is REQUIRED for concurrency control
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(str(user_id))

        # Validate If-Match header (REQUIRED)
        if not if_match:
            raise PreconditionRequired()

        # Generate current ETag and validate
        current_etag = generate_etag(user.updated_at) if user.updated_at else None
        if current_etag and if_match != current_etag:
            raise PreconditionFailed()

        # Get active role assignment
        active_assignment = self._get_active_role_assignment(user)
        if not active_assignment:
            raise UserNotFound(str(user_id))  # User has no active role assignment

        # Check if user is SuperAdmin (cannot change SuperAdmin role via this endpoint)
        if active_assignment.company_id is None:
            raise ValidationError(
                message="Cannot change SuperAdmin role via this endpoint",
                error_code="BUSINESS_RULE_FAILED",
                details=[{"field": "user_id", "issue": "SuperAdmin users cannot have their role changed via this endpoint"}],
            )

        # Check if user is trying to change their own role
        if user_id == changer_id:
            raise CannotChangeOwnRole()

        # Validate CEO/HR can only change roles in their own company
        # (SuperAdmin has changer_company_id=None and can change roles across any company)
        if changer_company_id is not None:  # CEO or HR (not SuperAdmin)
            if active_assignment.company_id != changer_company_id:
                raise InsufficientPermissions("change user roles outside your company")

        # Validate role exists
        role = await self.repository.get_role_by_code(role_change_data.role_code)
        if not role:
            raise RoleNotFound(role_change_data.role_code)

        # CEO Cardinality Rule: Check if assigning CEO role
        if role_change_data.role_code == ROLE_CODE_CEO:
            # Check if company already has an active CEO
            has_ceo = await self.repository.check_company_has_ceo(active_assignment.company_id)
            if has_ceo:
                # Exception: If the user being assigned CEO role is the current CEO, allow the change (no-op)
                current_ceo = await self.repository.get_active_ceo_for_company(active_assignment.company_id)
                if current_ceo and current_ceo.id != user_id:
                    # Company has a different CEO, raise error
                    company = await self.repository.get_company_by_id(active_assignment.company_id)
                    company_name = company.name if company else "Company"
                    raise CompanyHasCEO(company_name)
                # User is the current CEO, allow the change (no-op)

        # Update role assignment
        active_assignment.role_id = role.id
        active_assignment.updated_by = changer_id
        await self.session.commit()

        # Refresh user with relationships
        user = await self.repository.get_by_id(user.id)
        user_read = self._build_user_read(user, include_sensitive=True)
        
        # Attach ETag for router
        if user.updated_at:
            user_read.etag = generate_etag(user.updated_at)
            user_read.last_modified = user.updated_at

        return user_read

    async def reassign_user_company(
        self,
        user_id: UUID,
        company_id: UUID,
        reassign_data: UserCompanyReassign,
        reassigner_id: UUID,
        if_match: Optional[str] = None,
    ) -> UserRead:
        """Reassign user to different company with optional role change (SuperAdmin only).
        
        Based on F1B_api_spec.md Section 5.2 - PATCH /api/v1/users/{user_id}/companies/{company_id}/reassign.
        
        Business Rules:
        - Only SuperAdmin can reassign users to different companies
        - User must exist
        - Target company must exist and be active
        - If role_code is provided: Role must be valid, CEO cardinality rule applies
        - If role_code is not provided: User keeps current role, CEO cardinality rule applies if current role is CEO
        - Cannot reassign SuperAdmin users (they have null company_id)
        - Cannot reassign user to their current company (no-op, but returns success)
        - If-Match header is REQUIRED for concurrency control
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(str(user_id))

        # Validate If-Match header (REQUIRED)
        if not if_match:
            raise PreconditionRequired()

        # Generate current ETag and validate
        current_etag = generate_etag(user.updated_at) if user.updated_at else None
        if current_etag and if_match != current_etag:
            raise PreconditionFailed()

        # Get active role assignment
        active_assignment = self._get_active_role_assignment(user)
        if not active_assignment:
            raise UserNotFound(str(user_id))  # User has no active role assignment

        # Cannot reassign SuperAdmin users
        if active_assignment.company_id is None:
            raise CannotReassignSuperAdmin()

        # Check if target company exists
        target_company = await self.repository.get_company_by_id(company_id)
        if not target_company:
            raise CompanyNotFound(str(company_id))

        # Check if target company is active
        if not target_company.is_active:
            raise ValidationError(
                message="Target company is not active",
                error_code="COMPANY_INACTIVE",
                details=[{"field": "company_id", "issue": "Cannot reassign user to inactive company"}],
            )

        # Check if user is already in target company (no-op, but return success)
        if active_assignment.company_id == company_id:
            # User is already in target company, return current state
            user_read = self._build_user_read(user, include_sensitive=True)
            if user.updated_at:
                user_read.etag = generate_etag(user.updated_at)
                user_read.last_modified = user.updated_at
            return user_read

        # Get current role for CEO cardinality check
        current_role = active_assignment.role
        if not current_role:
            raise RoleNotFound("unknown")

        # Determine new role
        new_role_code = reassign_data.role_code
        if not new_role_code:
            # Keep current role (role_code not provided)
            new_role_code = current_role.code

        # Validate role if provided
        if new_role_code:
            role = await self.repository.get_role_by_code(new_role_code)
            if not role:
                raise RoleNotFound(new_role_code)

        # CEO Cardinality Rule: Check if assigning CEO role OR user has CEO role
        # Case 1: role_code is provided and it's CEO
        # Case 2: role_code is NOT provided and user's current role is CEO
        if new_role_code == ROLE_CODE_CEO:
            # Check if target company already has an active CEO
            has_ceo = await self.repository.check_company_has_ceo(company_id)
            if has_ceo:
                # Check if current user is the CEO (exception: if reassigning current CEO, allow)
                current_ceo = await self.repository.get_active_ceo_for_company(company_id)
                if current_ceo and current_ceo.id != user_id:
                    # Target company has a different CEO, raise error
                    raise TargetCompanyHasCEO(target_company.name)

        # Update role assignment
        active_assignment.company_id = company_id
        if new_role_code:
            role = await self.repository.get_role_by_code(new_role_code)
            active_assignment.role_id = role.id
        active_assignment.updated_by = reassigner_id
        await self.session.commit()

        # Refresh user with relationships
        user = await self.repository.get_by_id(user.id)
        user_read = self._build_user_read(user, include_sensitive=True)
        
        # Attach ETag for router
        if user.updated_at:
            user_read.etag = generate_etag(user.updated_at)
            user_read.last_modified = user.updated_at

        return user_read

    async def deactivate_user(
        self,
        user_id: UUID,
        deactivator_id: UUID,
        deactivator_company_id: Optional[UUID] = None,
        if_match: Optional[str] = None,
    ) -> UserRead:
        """Deactivate user (set is_active=false, blocks authentication).
        
        Based on F1B_api_spec.md Section 5.3 - PATCH /api/v1/users/{user_id}/deactivate.
        
        Business Rules:
        - User must exist
        - Deactivated users cannot log in (is_active=false blocks authentication)
        - Deactivated users retain all historical data (soft deactivation)
        - Users cannot deactivate their own account
        - If user is already deactivated, operation is idempotent (returns success)
        - If-Match header is REQUIRED for concurrency control
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(str(user_id))

        # Validate If-Match header (REQUIRED)
        if not if_match:
            raise PreconditionRequired()

        # Generate current ETag and validate
        current_etag = generate_etag(user.updated_at) if user.updated_at else None
        if current_etag and if_match != current_etag:
            raise PreconditionFailed()

        # Check if user is trying to deactivate their own account
        if user_id == deactivator_id:
            raise CannotDeactivateOwnAccount()

        # Validate CEO/HR can only deactivate users in their own company
        # (SuperAdmin has deactivator_company_id=None and can deactivate users across any company)
        if deactivator_company_id is not None:  # CEO or HR (not SuperAdmin)
            active_assignment = self._get_active_role_assignment(user)
            if active_assignment and active_assignment.company_id != deactivator_company_id:
                raise InsufficientPermissions("deactivate users outside your company")

        # Deactivate user (idempotent - if already deactivated, no change)
        user.is_active = False
        user.updated_by = deactivator_id
        await self.repository.update_user(user)

        # Refresh user with relationships
        user = await self.repository.get_by_id(user.id)
        user_read = self._build_user_read(user, include_sensitive=True)
        
        # Attach ETag for router
        if user.updated_at:
            user_read.etag = generate_etag(user.updated_at)
            user_read.last_modified = user.updated_at

        return user_read

    async def reactivate_user(
        self,
        user_id: UUID,
        reactivator_id: UUID,
        reactivator_company_id: Optional[UUID] = None,
        if_match: Optional[str] = None,
    ) -> UserRead:
        """Reactivate user (set is_active=true, restores authentication).
        
        Based on F1B_api_spec.md Section 5.4 - PATCH /api/v1/users/{user_id}/reactivate.
        
        Business Rules:
        - User must exist
        - Reactivated users can log in (is_active=true restores authentication)
        - Reactivated users do not need to reset passwords
        - If user is already active, operation is idempotent (returns success)
        - If-Match header is REQUIRED for concurrency control
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(str(user_id))

        # Validate If-Match header (REQUIRED)
        if not if_match:
            raise PreconditionRequired()

        # Generate current ETag and validate
        current_etag = generate_etag(user.updated_at) if user.updated_at else None
        if current_etag and if_match != current_etag:
            raise PreconditionFailed()

        # Validate CEO/HR can only reactivate users in their own company
        # (SuperAdmin has reactivator_company_id=None and can reactivate users across any company)
        if reactivator_company_id is not None:  # CEO or HR (not SuperAdmin)
            active_assignment = self._get_active_role_assignment(user)
            if active_assignment and active_assignment.company_id != reactivator_company_id:
                raise InsufficientPermissions("reactivate users outside your company")

        # Reactivate user (idempotent - if already active, no change)
        user.is_active = True
        user.updated_by = reactivator_id
        await self.repository.update_user(user)

        # Refresh user with relationships
        user = await self.repository.get_by_id(user.id)
        user_read = self._build_user_read(user, include_sensitive=True)
        
        # Attach ETag for router
        if user.updated_at:
            user_read.etag = generate_etag(user.updated_at)
            user_read.last_modified = user.updated_at

        return user_read

    async def resend_invitation(
        self,
        user_id: UUID,
        resender_id: UUID,
        resender_company_id: Optional[UUID] = None,
    ) -> UserRead:
        """Resend invitation to user (generates new token and expiry, increments reinvite_count).
        
        Based on F1B_api_spec.md Section 5.5 - POST /api/v1/users/{user_id}/resend-invite.
        
        Business Rules:
        - User must exist
        - Re-invitation is allowed for any user (even if previously activated and deactivated)
        - Generates new invitation token
        - Sets new expiry (24 hours from current time)
        - Increments reinvite_count
        - Updates last_reinvite_at to current timestamp
        - Updates invite_at if this is the first invitation (user was created without invitation)
        - Re-invitation does not change user's role, company, or is_active status
        - Note: Unlike other PATCH endpoints, this POST endpoint does not require If-Match header
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(str(user_id))

        # Validate CEO/HR can only resend invitations to users in their own company
        # (SuperAdmin has resender_company_id=None and can resend invitations to users across any company)
        if resender_company_id is not None:  # CEO or HR (not SuperAdmin)
            active_assignment = self._get_active_role_assignment(user)
            if active_assignment and active_assignment.company_id != resender_company_id:
                raise InsufficientPermissions("resend invitations outside your company")

        # Generate new invitation token and expiry
        now = datetime.utcnow()
        expiry = now + timedelta(seconds=INVITATION_EXPIRY_SECONDS)

        # Update invitation fields
        user.token = str(uuid4())  # Generate new invitation token
        user.expiry = expiry
        user.reinvite_count = (user.reinvite_count or 0) + 1
        user.last_reinvite_at = now

        # Update invite_at if this is the first invitation (user was created without invitation)
        if user.invite_at is None:
            user.invite_at = now

        user.updated_by = resender_id
        await self.repository.update_user(user)

        # Refresh user with relationships
        user = await self.repository.get_by_id(user.id)
        user_read = self._build_user_read(user, include_sensitive=True)
        
        # Attach ETag for router (even though POST doesn't require If-Match, we still provide ETag)
        if user.updated_at:
            user_read.etag = generate_etag(user.updated_at)
            user_read.last_modified = user.updated_at

        return user_read
