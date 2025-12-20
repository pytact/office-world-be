"""FastAPI endpoints for User & Role Management module.

Based on F1A_api_spec.md - All endpoints with proper authentication, authorization,
field visibility rules, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from fastapi.responses import Response as FastAPIResponse, JSONResponse
from src.schemas import StandardResponse
from src.pagination import PagedCollection
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
from src.users.utils import generate_request_id, format_last_modified
from src.users.dependencies import (
    UserApiDep,
    get_current_superadmin,
    get_current_company_user,
    get_user_role_from_token,
)
from src.users.documentations.user_api_doc import UserApiDocs
from src.users.models import User
from src.users.constants import (
    SUCCESS_USERS_RETRIEVED,
    SUCCESS_USER_RETRIEVED,
    SUCCESS_USER_INVITED,
    SUCCESS_USER_UPDATED,
    SUCCESS_ROLES_RETRIEVED,
    SUCCESS_COMPANIES_RETRIEVED,
    SUCCESS_USER_ROLE_UPDATED,
    SUCCESS_USER_REASSIGNED,
    SUCCESS_USER_DEACTIVATED,
    SUCCESS_USER_REACTIVATED,
    SUCCESS_INVITATION_RESENT,
    ROLE_CODE_MANAGER,
    ROLE_CODE_EMPLOYEE,
    ROLE_CODE_SUPERADMIN,
    ROLE_CODE_CEO,
    ROLE_CODE_HR,
)
from src.users.exceptions import InsufficientPermissions

# Setup logger - will inherit from root logger configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="",
    tags=["Users"],
)


@router.get(
    "/users",
    response_model=StandardResponse[PagedCollection[UserListItem]],
    summary=UserApiDocs.list_platform_users["summary"],
    description=UserApiDocs.list_platform_users["description"],
)
async def list_platform_users(
    request: Request,
    query: PlatformUserListQuery = Depends(PlatformUserListQuery),
    api: UserApiDep = Depends(UserApiDep),
    current_user: User = Depends(get_current_superadmin),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[PagedCollection[UserListItem]]:
    """List all users across platform (SuperAdmin only).
    
    Based on F1A_api_spec.md Section 5.1 - GET /api/v1/users.
    """
    # X-Request-ID is handled by middleware
    result = await api.list_platform_users(query)
    return StandardResponse(
        data=result,
        message=SUCCESS_USERS_RETRIEVED,
    )


@router.get(
    "/company/users",
    response_model=StandardResponse[PagedCollection[UserListItem]],
    summary=UserApiDocs.list_company_users["summary"],
    description=UserApiDocs.list_company_users["description"],
)
async def list_company_users(
    request: Request,
    query: CompanyUserListQuery = Depends(CompanyUserListQuery),
    api: UserApiDep = Depends(UserApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_company_user),
    role: str = Depends(get_user_role_from_token),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[PagedCollection[UserListItem]]:
    """List users in authenticated user's company.
    
    Based on F1A_api_spec.md Section 5.2 - GET /api/v1/company/users.
    
    Field visibility rules:
    - SuperAdmin, CEO, HR: Full field set
    - Manager: Restricted field set (list-level visibility only)
    - Employee: Access denied (403)
    """
    # Generate or use provided X-Request-ID
    request_id = generate_request_id(x_request_id)
    if response:
        response.headers["X-Request-ID"] = request_id
    
    user, company_id = user_company
    
    # Employee cannot access user lists
    if role == ROLE_CODE_EMPLOYEE:
        raise InsufficientPermissions("view user lists")
    
    # Determine field visibility based on role
    include_sensitive = role != ROLE_CODE_MANAGER
    
    result = await api.list_company_users(company_id, query, include_sensitive=include_sensitive)
    return StandardResponse(
        data=result,
        message=SUCCESS_USERS_RETRIEVED,
    )


@router.get(
    "/users/{user_id}",
    response_model=StandardResponse[UserRead],
    summary=UserApiDocs.get_user_detail["summary"],
    description=UserApiDocs.get_user_detail["description"],
)
async def get_user_detail(
    request: Request,
    user_id: UUID,
    api: UserApiDep = Depends(UserApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_company_user),
    role: str = Depends(get_user_role_from_token),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = None,
) -> StandardResponse[UserRead] | FastAPIResponse:
    """Get user details with invitation status.
    
    Based on F1A_api_spec.md Section 5.3 - GET /api/v1/users/{user_id}.
    
    Field visibility rules:
    - SuperAdmin, CEO, HR: Full field set
    - Manager: Restricted field set (excludes sensitive fields)
    - Employee: Access denied (403)
    """
    # Generate or use provided X-Request-ID
    request_id = generate_request_id(x_request_id)
    if response:
        response.headers["X-Request-ID"] = request_id
    
    # Log the incoming request
    # Handle empty strings for If-None-Match
    if_none_match_display = if_none_match if if_none_match and if_none_match.strip() else "None"
    log_message = (
        f"GET /users/{user_id} - "
        f"X-Request-ID: {request_id} - "
        f"If-None-Match: {if_none_match_display} - "
        f"Role: {role}"
    )
    logger.info(log_message)
    print(f"[ENDPOINT] {log_message}", flush=True)  # Print to stdout for visibility
    
    user, company_id = user_company
    
    # Employee cannot access user detail
    if role == ROLE_CODE_EMPLOYEE:
        raise InsufficientPermissions("view user details")
    
    # Determine field visibility based on role
    include_sensitive = role != ROLE_CODE_MANAGER
    
    result = await api.get_user_by_id(user_id, include_sensitive=include_sensitive, if_none_match=if_none_match)
    
    # Check If-None-Match for cache validation (304 Not Modified)
    # Service returns user_read with etag, we check here and return 304 if match
    # Handle empty strings by treating them as None
    if_none_match_value = if_none_match.strip() if if_none_match and if_none_match.strip() else None
    if if_none_match_value and result.etag and if_none_match_value == result.etag:
        # Log 304 response
        log_304 = (
            f"304 Not Modified for GET /users/{user_id} - "
            f"X-Request-ID: {request_id} - "
            f"ETag match: {if_none_match_value}"
        )
        logger.info(log_304)
        print(f"[ENDPOINT] {log_304}", flush=True)  # Print to stdout for visibility
        # Return 304 Not Modified with X-Request-ID header
        # Note: For debugging, you can comment out the If-None-Match check to always return 200
        response_304 = FastAPIResponse(
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={
                "X-Request-ID": request_id,
                "Cache-Control": "no-cache, no-store, must-revalidate",  # Prevent caching
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
        return response_304
    
    # Set ETag and Last-Modified headers (REQUIRED per spec Section 5.3, lines 485-486)
    # Use JSONResponse to set custom headers
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_USER_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    # Prevent caching in Swagger UI (for development/debugging)
    json_response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    json_response.headers["Pragma"] = "no-cache"
    json_response.headers["Expires"] = "0"
    if result.etag:
        json_response.headers["ETag"] = result.etag
    if result.last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result.last_modified)
    
    # Log successful response
    log_200 = (
        f"200 OK for GET /users/{user_id} - "
        f"X-Request-ID: {request_id} - "
        f"ETag: {result.etag}"
    )
    logger.info(log_200)
    print(f"[ENDPOINT] {log_200}", flush=True)  # Print to stdout for visibility
    
    return json_response


@router.post(
    "/users/invite",
    response_model=StandardResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary=UserApiDocs.invite_user["summary"],
    description=UserApiDocs.invite_user["description"],
)
async def invite_user(
    request: Request,
    invite_data: UserInvite,
    api: UserApiDep = Depends(UserApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_company_user),
    role: str = Depends(get_user_role_from_token),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[UserRead]:
    """Invite new user with role and company assignment.
    
    Based on F1A_api_spec.md Section 5.4 - POST /api/v1/users/invite.
    
    Authorization:
    - SuperAdmin: Can invite to any company
    - CEO, HR: Can only invite to their own company
    - Manager, Employee: Access denied (403)
    """
    # Generate or use provided X-Request-ID
    request_id = generate_request_id(x_request_id)
    if response:
        response.headers["X-Request-ID"] = request_id
    
    user, company_id = user_company
    
    # Manager and Employee cannot invite users
    if role in [ROLE_CODE_MANAGER, ROLE_CODE_EMPLOYEE]:
        raise InsufficientPermissions("invite users")
    
    result = await api.invite_user(invite_data, user.id, company_id)
    return StandardResponse(
        data=result,
        message=SUCCESS_USER_INVITED,
    )


@router.patch(
    "/users/{user_id}",
    response_model=StandardResponse[UserRead],
    summary=UserApiDocs.update_user["summary"],
    description=UserApiDocs.update_user["description"],
)
async def update_user(
    request: Request,
    user_id: UUID,
    update_data: UserUpdate,
    api: UserApiDep = Depends(UserApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_company_user),
    role: str = Depends(get_user_role_from_token),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[UserRead]:
    """Update user information (name, etc.).
    
    Based on F1A_api_spec.md Section 5.5 - PATCH /api/v1/users/{user_id}.
    
    Authorization:
    - Users can update their own details
    - SuperAdmin can update any user's details
    - CEO and HR can update any user's details in their own company
    - Manager and Employee can only update their own details
    
    Note: If-Match header is REQUIRED and validated in service layer per RULE 19.
    """
    # X-Request-ID is handled by middleware
    current_user, company_id = user_company
    
    # Authorization logic is handled in service layer
    result = await api.update_user(user_id, update_data, current_user, company_id, if_match=if_match)
    
    # Set new ETag header after update (per spec Section 5.5, line 728)
    # Use JSONResponse to set custom headers
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_USER_UPDATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    if result.etag:
        json_response.headers["ETag"] = result.etag
    return json_response


@router.get(
    "/roles",
    response_model=StandardResponse[RolesListResponse],
    summary=UserApiDocs.list_roles["summary"],
    description=UserApiDocs.list_roles["description"],
)
async def list_roles(
    request: Request,
    api: UserApiDep = Depends(UserApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_company_user),
    role: str = Depends(get_user_role_from_token),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[RolesListResponse]:
    """List available roles for invitation form.
    
    Based on F1A_api_spec.md Section 5.6 - GET /api/v1/roles.
    
    Authorization:
    - SuperAdmin, CEO, HR: Can access
    - Manager, Employee: Access denied (403)
    """
    # X-Request-ID is handled by middleware
    # Manager and Employee cannot access roles
    if role in [ROLE_CODE_MANAGER, ROLE_CODE_EMPLOYEE]:
        raise InsufficientPermissions("view roles")
    
    result = await api.list_roles()
    return StandardResponse(
        data=result,
        message=SUCCESS_ROLES_RETRIEVED,
    )


@router.get(
    "/companies",
    response_model=StandardResponse[CompaniesListResponse],
    summary=UserApiDocs.list_companies["summary"],
    description=UserApiDocs.list_companies["description"],
)
async def list_companies(
    request: Request,
    api: UserApiDep = Depends(UserApiDep),
    current_user: User = Depends(get_current_superadmin),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[CompaniesListResponse]:
    """List all companies for SuperAdmin invitation form.
    
    Based on F1A_api_spec.md Section 5.7 - GET /api/v1/companies.
    
    Authorization:
    - SuperAdmin only
    """
    # X-Request-ID is handled by middleware
    result = await api.list_companies()
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANIES_RETRIEVED,
    )


# ============================================================================
# F1B Lifecycle Operations Endpoints
# ============================================================================

@router.patch(
    "/users/{user_id}/role",
    response_model=StandardResponse[UserRead],
    summary=UserApiDocs.change_user_role["summary"],
    description=UserApiDocs.change_user_role["description"],
)
async def change_user_role(
    request: Request,
    user_id: UUID,
    role_change_data: UserRoleChange,
    api: UserApiDep = Depends(UserApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_company_user),
    role: str = Depends(get_user_role_from_token),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[UserRead]:
    """Change user role within same company.
    
    Based on F1B_api_spec.md Section 5.1 - PATCH /api/v1/users/{user_id}/role.
    
    Authorization:
    - SuperAdmin: Can change any user's role across any company
    - CEO, HR: Can only change roles within their own company
    - Manager, Employee: Access denied (403)
    """
    # Generate or use provided X-Request-ID
    request_id = generate_request_id(x_request_id)
    if response:
        response.headers["X-Request-ID"] = request_id

    current_user, company_id = user_company

    # Authorization: Only SuperAdmin, CEO, HR can change roles
    if role not in [ROLE_CODE_SUPERADMIN, ROLE_CODE_CEO, ROLE_CODE_HR]:
        raise InsufficientPermissions("change user roles")

    # CEO and HR can only change roles within their own company
    # (SuperAdmin can change roles across any company, so company_id check is skipped for SuperAdmin)
    if role in [ROLE_CODE_CEO, ROLE_CODE_HR] and company_id is None:
        raise InsufficientPermissions("change user roles outside your company")

    result = await api.change_user_role(user_id, role_change_data, current_user.id, changer_company_id=company_id, if_match=if_match)

    # Set new ETag header after update
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_USER_ROLE_UPDATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if result.etag:
        json_response.headers["ETag"] = result.etag
    return json_response


@router.patch(
    "/users/{user_id}/companies/{company_id}/reassign",
    response_model=StandardResponse[UserRead],
    summary=UserApiDocs.reassign_user_company["summary"],
    description=UserApiDocs.reassign_user_company["description"],
)
async def reassign_user_company(
    request: Request,
    user_id: UUID,
    company_id: UUID,
    reassign_data: UserCompanyReassign,
    api: UserApiDep = Depends(UserApiDep),
    current_user: User = Depends(get_current_superadmin),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[UserRead]:
    """Reassign user to different company with optional role change (SuperAdmin only).
    
    Based on F1B_api_spec.md Section 5.2 - PATCH /api/v1/users/{user_id}/companies/{company_id}/reassign.
    
    Authorization:
    - SuperAdmin only
    """
    # Generate or use provided X-Request-ID
    request_id = generate_request_id(x_request_id)
    if response:
        response.headers["X-Request-ID"] = request_id

    result = await api.reassign_user_company(user_id, company_id, reassign_data, current_user.id, if_match=if_match)

    # Set new ETag header after update
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_USER_REASSIGNED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if result.etag:
        json_response.headers["ETag"] = result.etag
    return json_response


@router.patch(
    "/users/{user_id}/deactivate",
    response_model=StandardResponse[UserRead],
    summary=UserApiDocs.deactivate_user["summary"],
    description=UserApiDocs.deactivate_user["description"],
)
async def deactivate_user(
    request: Request,
    user_id: UUID,
    api: UserApiDep = Depends(UserApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_company_user),
    role: str = Depends(get_user_role_from_token),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[UserRead]:
    """Deactivate user (set is_active=false, blocks authentication).
    
    Based on F1B_api_spec.md Section 5.3 - PATCH /api/v1/users/{user_id}/deactivate.
    
    Authorization:
    - SuperAdmin: Can deactivate any user across any company
    - CEO, HR: Can only deactivate users in their own company
    - Manager, Employee: Access denied (403)
    """
    # Generate or use provided X-Request-ID
    request_id = generate_request_id(x_request_id)
    if response:
        response.headers["X-Request-ID"] = request_id

    current_user, company_id = user_company

    # Authorization: Only SuperAdmin, CEO, HR can deactivate users
    if role not in [ROLE_CODE_SUPERADMIN, ROLE_CODE_CEO, ROLE_CODE_HR]:
        raise InsufficientPermissions("deactivate users")

    # CEO and HR can only deactivate users in their own company
    # (SuperAdmin can deactivate users across any company, so company_id check is skipped for SuperAdmin)
    if role in [ROLE_CODE_CEO, ROLE_CODE_HR] and company_id is None:
        raise InsufficientPermissions("deactivate users outside your company")

    result = await api.deactivate_user(user_id, current_user.id, deactivator_company_id=company_id, if_match=if_match)

    # Set new ETag header after update
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_USER_DEACTIVATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if result.etag:
        json_response.headers["ETag"] = result.etag
    return json_response


@router.patch(
    "/users/{user_id}/reactivate",
    response_model=StandardResponse[UserRead],
    summary=UserApiDocs.reactivate_user["summary"],
    description=UserApiDocs.reactivate_user["description"],
)
async def reactivate_user(
    request: Request,
    user_id: UUID,
    api: UserApiDep = Depends(UserApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_company_user),
    role: str = Depends(get_user_role_from_token),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[UserRead]:
    """Reactivate user (set is_active=true, restores authentication).
    
    Based on F1B_api_spec.md Section 5.4 - PATCH /api/v1/users/{user_id}/reactivate.
    
    Authorization:
    - SuperAdmin: Can reactivate any user across any company
    - CEO, HR: Can only reactivate users in their own company
    - Manager, Employee: Access denied (403)
    """
    # Generate or use provided X-Request-ID
    request_id = generate_request_id(x_request_id)
    if response:
        response.headers["X-Request-ID"] = request_id

    current_user, company_id = user_company

    # Authorization: Only SuperAdmin, CEO, HR can reactivate users
    if role not in [ROLE_CODE_SUPERADMIN, ROLE_CODE_CEO, ROLE_CODE_HR]:
        raise InsufficientPermissions("reactivate users")

    # CEO and HR can only reactivate users in their own company
    # (SuperAdmin can reactivate users across any company, so company_id check is skipped for SuperAdmin)
    if role in [ROLE_CODE_CEO, ROLE_CODE_HR] and company_id is None:
        raise InsufficientPermissions("reactivate users outside your company")

    result = await api.reactivate_user(user_id, current_user.id, reactivator_company_id=company_id, if_match=if_match)

    # Set new ETag header after update
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_USER_REACTIVATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if result.etag:
        json_response.headers["ETag"] = result.etag
    return json_response


@router.post(
    "/users/{user_id}/resend-invite",
    response_model=StandardResponse[UserRead],
    summary=UserApiDocs.resend_invitation["summary"],
    description=UserApiDocs.resend_invitation["description"],
)
async def resend_invitation(
    request: Request,
    user_id: UUID,
    api: UserApiDep = Depends(UserApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_company_user),
    role: str = Depends(get_user_role_from_token),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[UserRead]:
    """Resend invitation to user (generates new token and expiry).
    
    Based on F1B_api_spec.md Section 5.5 - POST /api/v1/users/{user_id}/resend-invite.
    
    Authorization:
    - SuperAdmin: Can resend invitations to any user across any company
    - CEO, HR: Can only resend invitations to users in their own company
    - Manager, Employee: Access denied (403)
    
    Note: Unlike other PATCH endpoints, this POST endpoint does not require If-Match header.
    """
    # Generate or use provided X-Request-ID
    request_id = generate_request_id(x_request_id)
    if response:
        response.headers["X-Request-ID"] = request_id

    current_user, company_id = user_company

    # Authorization: Only SuperAdmin, CEO, HR can resend invitations
    if role not in [ROLE_CODE_SUPERADMIN, ROLE_CODE_CEO, ROLE_CODE_HR]:
        raise InsufficientPermissions("resend invitations")

    # CEO and HR can only resend invitations to users in their own company
    # (SuperAdmin can resend invitations to users across any company, so company_id check is skipped for SuperAdmin)
    if role in [ROLE_CODE_CEO, ROLE_CODE_HR] and company_id is None:
        raise InsufficientPermissions("resend invitations outside your company")

    result = await api.resend_invitation(user_id, current_user.id, resender_company_id=company_id)

    # Set X-Request-ID header (no ETag required for POST, but we still provide it if available)
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_INVITATION_RESENT,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if result.etag:
        json_response.headers["ETag"] = result.etag
    return json_response
