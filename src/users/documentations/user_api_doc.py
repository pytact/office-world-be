"""API documentation for User & Role Management endpoints.

Based on F1A_api_spec.md Section 6 - Documentation Classes (Rule 10 Compliance).
"""

from typing import ClassVar


class UserApiDocs:
    """API documentation for User & Role Management endpoints."""

    list_platform_users: ClassVar[dict] = {
        "summary": "Purpose of this API is to list all users across the platform",
        "description": "Retrieves a paginated list of all users across all companies. Only SuperAdmin can access this endpoint. Supports filtering by company, role, status, and search by name/email. Includes pagination, sorting, and navigation URLs. Supports ETag-based caching with If-None-Match header.",
    }

    list_company_users: ClassVar[dict] = {
        "summary": "Purpose of this API is to list users in authenticated user's company",
        "description": "Retrieves a paginated list of users in the authenticated user's company. Accessible by SuperAdmin, CEO, HR, and Manager. Managers receive restricted field sets (list-level visibility only, excluding sensitive fields). Employees cannot access this endpoint. Supports filtering by role, status, and search by name/email. Supports ETag-based caching with If-None-Match header.",
    }

    get_user_detail: ClassVar[dict] = {
        "summary": "Purpose of this API is to get user details with invitation status",
        "description": "Retrieves detailed information about a specific user, including invitation status and re-invitation eligibility. Accessible by SuperAdmin, CEO, HR, and Manager. Managers receive restricted field sets (excluding sensitive fields). Employees cannot access this endpoint.",
    }

    invite_user: ClassVar[dict] = {
        "summary": "Purpose of this API is to invite a new user with role and company assignment",
        "description": "Creates a new user invitation with role and company assignment. Accessible by SuperAdmin, CEO, and HR. SuperAdmin can invite to any company. CEO and HR can only invite to their own company. Generates invitation token with 24-hour expiry. Returns 409 Conflict if email already exists for active user.",
    }

    update_user: ClassVar[dict] = {
        "summary": "Purpose of this API is to update user information",
        "description": "Updates user information such as first name and last name. Users can update their own details. SuperAdmin can update any user's details. CEO and HR can update any user's details in their own company. Requires If-Match header for concurrency control. Email is immutable and cannot be updated.",
    }

    list_roles: ClassVar[dict] = {
        "summary": "Purpose of this API is to list available roles for invitation form",
        "description": "Retrieves a list of all available roles (code and name) for use in invitation form dropdowns. Accessible by SuperAdmin, CEO, and HR. Role codes are immutable system identifiers.",
    }

    list_companies: ClassVar[dict] = {
        "summary": "Purpose of this API is to list all companies for SuperAdmin invitation form",
        "description": "Retrieves a list of all active companies (name and slug) for use in SuperAdmin invitation form. Only SuperAdmin can access this endpoint. Returns only active companies.",
    }

    # F1B Lifecycle Operations Documentation
    change_user_role: ClassVar[dict] = {
        "summary": "Purpose of this API is to change user role within the same company",
        "description": "Changes a user's role within their current company. Accessible by SuperAdmin, CEO, and HR. SuperAdmin can change roles across any company. CEO and HR can only change roles within their own company. Enforces CEO cardinality rule (only one CEO per company). Requires If-Match header for concurrency control. Users cannot change their own role.",
    }

    reassign_user_company: ClassVar[dict] = {
        "summary": "Purpose of this API is to reassign user to different company with optional role change",
        "description": "Reassigns a user to a different company with an optional role change. Only SuperAdmin can access this endpoint. If role_code is provided, assigns the specified role in the target company. If role_code is not provided, user keeps their current role. Enforces CEO cardinality rule for target company. Cannot reassign SuperAdmin users. Requires If-Match header for concurrency control.",
    }

    deactivate_user: ClassVar[dict] = {
        "summary": "Purpose of this API is to deactivate user and block authentication",
        "description": "Deactivates a user by setting is_active=false, which blocks authentication. Accessible by SuperAdmin, CEO, and HR. SuperAdmin can deactivate any user across any company. CEO and HR can only deactivate users in their own company. Deactivated users retain all historical data. Users cannot deactivate their own accounts. Requires If-Match header for concurrency control.",
    }

    reactivate_user: ClassVar[dict] = {
        "summary": "Purpose of this API is to reactivate user and restore authentication",
        "description": "Reactivates a user by setting is_active=true, which restores authentication. Accessible by SuperAdmin, CEO, and HR. SuperAdmin can reactivate any user across any company. CEO and HR can only reactivate users in their own company. Reactivated users do not need to reset passwords. Requires If-Match header for concurrency control.",
    }

    resend_invitation: ClassVar[dict] = {
        "summary": "Purpose of this API is to resend invitation to user with new token",
        "description": "Resends an invitation to a user by generating a new invitation token and expiry (24 hours from current time). Accessible by SuperAdmin, CEO, and HR. SuperAdmin can resend invitations to any user across any company. CEO and HR can only resend invitations to users in their own company. Re-invitation is allowed for any user (even if previously activated and deactivated). Increments reinvite_count and updates last_reinvite_at. Does not change user's role, company, or is_active status.",
    }

    update_user_status: ClassVar[dict] = {
        "summary": "Purpose of this API is to update user activation status",
        "description": "Unified endpoint for activating and deactivating users. Use status 'ACTIVE' to activate or 'INACTIVE' to deactivate. Accessible by SuperAdmin, CEO, and HR. SuperAdmin can update any user's status across any company. CEO and HR can only update users in their own company. Deactivated users retain all historical data. Users cannot deactivate their own accounts. Requires If-Match header for concurrency control.",
    }

