"""API documentation for Company endpoints.

Based on F4_api_spec.md Section 4.3 - API Documentation Class (Rule 10).
All endpoint documentation MUST use this centralized class structure.
"""

from typing import ClassVar


class CompanyApiDocs:
    """API documentation for Company endpoints.
    
    Based on F4_api_spec.md Section 4.3 - API Documentation Class (Rule 10).
    Router endpoints MUST reference summary and description from this class,
    NOT hardcoded strings.
    """
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list all companies with pagination, search, filtering, and sorting",
        "description": "Retrieves a paginated list of all companies across the platform. Supports search by company name or slug, filtering by status (active/inactive), and sorting by various fields. Only SuperAdmin can access this endpoint. Soft-deleted companies remain visible to SuperAdmin."
    }
    
    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new company",
        "description": "Creates a new company with required metadata (name and slug). Company defaults to active state (is_active: true) on creation. Name and slug must be globally unique. Only SuperAdmin can create companies."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get company details with user count",
        "description": "Retrieves detailed company information including all profile fields, governance fields (is_active, is_deleted), user count aggregate, and audit fields. Only SuperAdmin can access this endpoint."
    }
    
    update: ClassVar[dict] = {
        "summary": "Purpose of this API is to update company information or activate/deactivate company",
        "description": "Updates company information including profile fields and governance fields. Can activate or deactivate company by setting is_active field. Name and slug are immutable and cannot be updated. Deactivation immediately blocks all associated user logins. Only SuperAdmin can update companies. Requires If-Match header for concurrency control."
    }
    
    delete: ClassVar[dict] = {
        "summary": "Purpose of this API is to hard delete a company",
        "description": "Permanently deletes a company and all associated data (users, employees, leaves, tasks, salaries, notifications, etc.). This operation is irreversible and proceeds even if company has active users. Only SuperAdmin can delete companies. Requires If-Match header for concurrency control."
    }
    
    get_profile: ClassVar[dict] = {
        "summary": "Purpose of this API is to get own company profile",
        "description": "Retrieves the authenticated user's company profile. Company is determined from JWT org_id claim. Response excludes governance fields (is_deleted, audit fields, user_count). Name and slug are read-only. Only CEO and HR can access this endpoint."
    }
    
    update_profile: ClassVar[dict] = {
        "summary": "Purpose of this API is to update company profile fields",
        "description": "Updates limited company profile fields (description, address, city, state, country, postal_code, website, logo_url). Governance fields (name, slug, is_active, is_deleted) cannot be updated. Updates are blocked when company is inactive (is_active: false). Only CEO and HR can update company profile. Requires If-Match header for concurrency control."
    }
