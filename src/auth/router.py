"""FastAPI endpoints for authentication."""

from uuid import UUID
from fastapi import APIRouter, Depends, Form, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from src.schemas import StandardResponse
from src.auth.dependencies import AuthApiDep, oauth2_scheme, get_current_user
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
from src.auth.exceptions import InvalidCredentials, AccountInactive
from src.users.models import User
from src.auth.documentations.auth_api_doc import AuthApiDocs

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# OAuth2 Token Endpoint for Swagger UI
@router.post("/token", status_code=status.HTTP_200_OK)
async def token(
    username: str = Form(...),  # OAuth2 uses 'username' but we treat it as email
    password: str = Form(...),
    api: AuthApiDep = Depends(),
):
    """OAuth2-compatible token endpoint for Swagger UI authorization.
    
    Based on auth_setup.md RULE 4 and error_prevention.md RULE 3.
    This endpoint accepts form data (username/password) and returns OAuth2-compatible response.
    """
    from src.auth.exceptions import (
        InvalidCredentials,
        AccountInactive,
        AccountDeleted,
        CompanyInactive,
    )
    
    try:
        login_request = LoginRequest(email=username, password=password)
        result = await api.login(login_request)
        # Return OAuth2-compatible response (just the access token)
        return {
            "access_token": result.access_token,
            "token_type": "bearer",
        }
    except (InvalidCredentials, AccountInactive, AccountDeleted, CompanyInactive):
        # Return OAuth2-compatible error response
        # Note: OAuth2 token endpoints require specific error format per error_prevention.md RULE 3
        # All authentication-related exceptions return 401 with WWW-Authenticate header
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Login Endpoint
@router.post(
    "/login",
    response_model=StandardResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary=AuthApiDocs.login["summary"],
    description=AuthApiDocs.login["description"],
)
async def login(
    request: LoginRequest,
    api: AuthApiDep = Depends(),
) -> StandardResponse[LoginResponse]:
    """Authenticate user with email and password."""
    result = await api.login(request)
    return StandardResponse(
        data=result,
        message="Login completed successfully",
    )


# Logout Endpoint
@router.post(
    "/logout",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary=AuthApiDocs.logout["summary"],
    description=AuthApiDocs.logout["description"],
)
async def logout(
    api: AuthApiDep = Depends(),
    token: str = Depends(oauth2_scheme),  # Require authentication
) -> StandardResponse[dict]:
    """Invalidate user session by blacklisting the JWT token."""
    result = await api.logout(token)
    return StandardResponse(
        data=result,
        message="Logout completed successfully",
    )


# Validate Invitation Token Endpoint
@router.get(
    "/invitations/{token}",
    response_model=StandardResponse[ActivationValidationResponse],
    status_code=status.HTTP_200_OK,
    summary=AuthApiDocs.get_activation["summary"],
    description=AuthApiDocs.get_activation["description"],
)
async def validate_invitation(
    token: UUID,
    api: AuthApiDep = Depends(),
) -> StandardResponse[ActivationValidationResponse]:
    """Validate invitation token and retrieve invitation details (email, company, role)."""
    result = await api.get_activation(token)
    return StandardResponse(
        data=result,
        message="Invitation token validated successfully",
    )


# Activate Account Endpoint
@router.post(
    "/activation/{token}",
    response_model=StandardResponse[ActivationResponse],
    status_code=status.HTTP_201_CREATED,
    summary=AuthApiDocs.activate_account["summary"],
    description=AuthApiDocs.activate_account["description"],
)
async def activate_account(
    token: UUID,
    request: ActivationRequest,
    api: AuthApiDep = Depends(),
) -> StandardResponse[ActivationResponse]:
    """Activate user account with name and password using invitation token."""
    result = await api.activate_account(token, request)
    return StandardResponse(
        data=result,
        message="Account activated successfully",
    )


# Request Password Reset Endpoint
@router.post(
    "/password-reset/request",
    response_model=StandardResponse[PasswordResetRequestResponse],
    status_code=status.HTTP_200_OK,
    summary=AuthApiDocs.request_password_reset["summary"],
    description=AuthApiDocs.request_password_reset["description"],
)
async def request_password_reset(
    request: PasswordResetRequestRequest,
    api: AuthApiDep = Depends(),
) -> StandardResponse[PasswordResetRequestResponse]:
    """Request password reset and send email with reset token."""
    result = await api.request_password_reset(request)
    return StandardResponse(
        data=result,
        message="Password reset email sent successfully",
    )


# Reset Password Endpoint
@router.post(
    "/password-reset/{token}",
    response_model=StandardResponse[PasswordResetResponse],
    status_code=status.HTTP_200_OK,
    summary=AuthApiDocs.reset_password["summary"],
    description=AuthApiDocs.reset_password["description"],
)
async def reset_password(
    token: UUID,
    request: PasswordResetRequest,
    api: AuthApiDep = Depends(),
) -> StandardResponse[PasswordResetResponse]:
    """Reset user password using reset token."""
    result = await api.reset_password(token, request)
    return StandardResponse(
        data=result,
        message="Password reset successfully",
    )


# Get User Permissions Endpoint
@router.get(
    "/me",
    response_model=StandardResponse[UserPermissionsResponse],
    status_code=status.HTTP_200_OK,
    summary=AuthApiDocs.get_me["summary"],
    description=AuthApiDocs.get_me["description"],
)
async def get_user_permissions(
    current_user: User = Depends(get_current_user),
    api: AuthApiDep = Depends(),
) -> StandardResponse[UserPermissionsResponse]:
    """Retrieve current user's details, permissions and context.
    
    Returns the authenticated user's user details (at the top), PermissionSet 
    (resource-action mappings), and AuthContext (role, company, status flags) 
    in a single response. User details include user_id, email, first_name, 
    last_name, is_active, created_at, and updated_at.
    """
    result = await api.get_user_permissions(current_user.id)
    return StandardResponse(
        data=result,
        message="User permissions and context retrieved successfully",
    )
