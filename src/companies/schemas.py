"""Pydantic schemas for Companies System API.

Based on F4_api_spec.md - Request schemas for input validation,
Response schemas for output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
import re
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic_core import Url


# ============================================================================
# REQUEST SCHEMAS (Input Validation)
# ============================================================================

class CompanyListQuery(BaseModel):
    """Query schema for listing companies with pagination and filtering.
    
    Based on F4_api_spec.md Section 4.4.1 - GET /api/v1/companies.
    """

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    search: Optional[str] = Field(None, description="Search by company name or slug (case-insensitive partial match)")
    status: Optional[str] = Field(None, description="Filter by status: active, inactive")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, name, slug, is_active")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)


class CompanyCreate(BaseModel):
    """Request schema for creating a company.
    
    Based on F4_api_spec.md Section 4.4.2 - POST /api/v1/companies.
    """

    name: str = Field(..., min_length=1, max_length=255, description="Company name (unique, case-insensitive)")
    slug: str = Field(..., min_length=3, max_length=100, description="URL identifier (lowercase alphanumeric with hyphens, unique)")
    description: Optional[str] = Field(None, max_length=1000, description="Company description")
    address: Optional[str] = Field(None, max_length=255, description="Physical address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal/ZIP code")
    website: Optional[str] = Field(None, max_length=2048, description="Company website URL (HTTPS)")
    logo_url: Optional[str] = Field(None, max_length=2048, description="Company logo URL (HTTPS)")

    @field_validator('slug')
    @classmethod
    def validate_slug_pattern(cls, v: str) -> str:
        """Validate slug pattern: lowercase alphanumeric with hyphens only."""
        pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
        if not re.match(pattern, v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens only (e.g., acme-corp)")
        return v

    @field_validator('website', 'logo_url')
    @classmethod
    def validate_https_url(cls, v: str | None) -> str | None:
        """Validate that URL is HTTPS."""
        if v is None:
            return v
        try:
            url = Url(v)
            if url.scheme != 'https':
                raise ValueError("URL must use HTTPS protocol")
            return str(url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {str(e)}")

    model_config = ConfigDict(from_attributes=True)


class CompanyUpdate(BaseModel):
    """Request schema for updating a company (SuperAdmin only).
    
    Based on F4_api_spec.md Section 4.4.4 - PATCH /api/v1/companies/{company_id}.
    
    Note: name and slug are immutable and cannot be updated.
    """

    description: Optional[str] = Field(None, max_length=1000, description="Company description")
    address: Optional[str] = Field(None, max_length=255, description="Physical address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal/ZIP code")
    website: Optional[str] = Field(None, max_length=2048, description="Company website URL (HTTPS)")
    logo_url: Optional[str] = Field(None, max_length=2048, description="Company logo URL (HTTPS)")
    is_active: Optional[bool] = Field(None, description="Company active state (SuperAdmin-only)")

    @field_validator('website', 'logo_url')
    @classmethod
    def validate_https_url(cls, v: str | None) -> str | None:
        """Validate that URL is HTTPS."""
        if v is None:
            return v
        try:
            url = Url(v)
            if url.scheme != 'https':
                raise ValueError("URL must use HTTPS protocol")
            return str(url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {str(e)}")

    model_config = ConfigDict(from_attributes=True)


class CompanyProfileUpdate(BaseModel):
    """Request schema for updating company profile (CEO/HR only).
    
    Based on F4_api_spec.md Section 4.4.7 - PATCH /api/v1/company/profile.
    
    Note: Only profile fields can be updated. Governance fields (name, slug, is_active, is_deleted) cannot be updated.
    """

    description: Optional[str] = Field(None, max_length=1000, description="Company description")
    address: Optional[str] = Field(None, max_length=255, description="Physical address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal/ZIP code")
    website: Optional[str] = Field(None, max_length=2048, description="Company website URL (HTTPS)")
    logo_url: Optional[str] = Field(None, max_length=2048, description="Company logo URL (HTTPS)")

    @field_validator('website', 'logo_url')
    @classmethod
    def validate_https_url(cls, v: str | None) -> str | None:
        """Validate that URL is HTTPS."""
        if v is None:
            return v
        try:
            url = Url(v)
            if url.scheme != 'https':
                raise ValueError("URL must use HTTPS protocol")
            return str(url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {str(e)}")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RESPONSE SCHEMAS (Output Structure)
# ============================================================================

class CompanySummary(BaseModel):
    """Response schema for company list item (summary).
    
    Based on F4_api_spec.md Section 4.4.1 - GET /api/v1/companies response.
    Used in paginated list responses.
    """

    company_id: UUID = Field(..., description="Unique company identifier")
    name: str = Field(..., description="Company name")
    slug: str = Field(..., description="URL identifier")
    is_active: bool = Field(..., description="Company active state")
    is_deleted: bool = Field(..., description="Soft deletion marker (for visibility)")
    user_count: int = Field(..., description="Number of users associated with the company")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp (UTC)")

    model_config = ConfigDict(from_attributes=True)


class CompanyDetail(BaseModel):
    """Response schema for company details (SuperAdmin view).
    
    Based on F4_api_spec.md Section 4.4.3 - GET /api/v1/companies/{company_id} response.
    Includes all fields including governance fields and user count.
    """

    company_id: UUID = Field(..., description="Unique company identifier")
    name: str = Field(..., description="Company name (immutable)")
    slug: str = Field(..., description="URL identifier (immutable)")
    description: Optional[str] = Field(None, description="Company description")
    address: Optional[str] = Field(None, description="Physical address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    country: Optional[str] = Field(None, description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/ZIP code")
    website: Optional[str] = Field(None, description="Company website URL")
    logo_url: Optional[str] = Field(None, description="Company logo URL")
    is_active: bool = Field(..., description="Company active state")
    is_deleted: bool = Field(..., description="Soft deletion marker (for visibility)")
    user_count: int = Field(..., description="Number of users associated with the company")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp (UTC)")
    created_by: Optional[UUID] = Field(None, description="User ID who created the company")
    updated_by: Optional[UUID] = Field(None, description="User ID who last updated the company")

    model_config = ConfigDict(from_attributes=True)


class CompanyProfile(BaseModel):
    """Response schema for company profile (CEO/HR view).
    
    Based on F4_api_spec.md Section 4.4.6 - GET /api/v1/company/profile response.
    Excludes governance fields (is_deleted, audit fields, user_count).
    Name and slug are read-only (included for display purposes only).
    """

    name: str = Field(..., description="Company name (read-only)")
    slug: str = Field(..., description="URL identifier (read-only)")
    description: Optional[str] = Field(None, description="Company description")
    address: Optional[str] = Field(None, description="Physical address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    country: Optional[str] = Field(None, description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/ZIP code")
    website: Optional[str] = Field(None, description="Company website URL")
    logo_url: Optional[str] = Field(None, description="Company logo URL")
    is_active: bool = Field(..., description="Company active state (read-only)")

    model_config = ConfigDict(from_attributes=True)


class CompanyPaginatedResponse(BaseModel):
    """Paginated response wrapper for company list.
    
    Based on F4_api_spec.md Section 4.4.1 - GET /api/v1/companies response structure.
    """

    items: list[CompanySummary] = Field(..., description="List of companies")
    total: int = Field(..., description="Total number of companies")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")
    next_page: Optional[str] = Field(None, description="URL for next page (with all query parameters)")
    prev_page: Optional[str] = Field(None, description="URL for previous page (with all query parameters)")

    model_config = ConfigDict(from_attributes=True)


# Legacy aliases for backward compatibility (if needed)
CompanyRead = CompanyDetail
CompanyListItem = CompanySummary
