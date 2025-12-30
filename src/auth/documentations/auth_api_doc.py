"""API documentation for Authentication endpoints."""

from typing import ClassVar


class AuthApiDocs:
    """API documentation for Authentication endpoints."""

    token: ClassVar[dict] = {
        "summary": "OAuth2 token endpoint for Swagger UI",
        "description": "OAuth2-compatible token endpoint for Swagger UI authorization. Accepts Form parameters (username/password) and returns OAuth2-compatible response (access_token, token_type). This endpoint enables the 'Authorize' button in Swagger UI. Users can authenticate via Swagger UI using this endpoint. MUST accept Form(...) parameters (not JSON) and MUST return OAuth2-compatible response format.",
    }

    login: ClassVar[dict] = {
        "summary": "Authenticate user with email and password",
        "description": "Validates user credentials and returns JWT access token with role and organization context. Validates user account is active, not soft-deleted, and company is active (for non-SuperAdmin users).",
    }

    logout: ClassVar[dict] = {
        "summary": "Invalidate user session",
        "description": "Logs out the authenticated user by invalidating their session token. This endpoint requires JWT Bearer token authentication.",
    }

    get_activation: ClassVar[dict] = {
        "summary": "Validate invitation token",
        "description": "Validates invitation token and returns activation details for account setup. Token must be valid, not expired (24 hours from invite_at), and user must not be already activated.",
    }

    activate_account: ClassVar[dict] = {
        "summary": "Activate user account",
        "description": "Completes user account activation using invitation token and provided credentials. Validates token, checks expiry, verifies user is not already activated, and validates password complexity requirements.",
    }

    request_password_reset: ClassVar[dict] = {
        "summary": "Request password reset",
        "description": "Initiates password reset process by sending reset token via email. Response is identical regardless of whether email exists to prevent email enumeration attacks.",
    }

    reset_password: ClassVar[dict] = {
        "summary": "Reset user password",
        "description": "Resets user password using valid reset token and new password. Validates token, checks expiry, verifies token is not already used, and validates password complexity requirements.",
    }

    get_me: ClassVar[dict] = {
        "summary": "Retrieve current user's details, permissions and context",
        "description": "Returns the authenticated user's user details (at the top), PermissionSet (resource-action mappings), and AuthContext (role, company, status flags) in a single response. User details include user_id, email, first_name, last_name, is_active, created_at, and updated_at. This endpoint provides all authorization data needed by the frontend for UI gating and permission checks. Permission data is cached per user and automatically recomputed after cache invalidation triggered by role changes, user activation/deactivation, or company reassignment.",
    }
