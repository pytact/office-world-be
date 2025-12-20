"""Pydantic schemas for Companies System API.

Based on F1A_api_spec.md - Request schemas for input validation,
Response schemas for output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# REQUEST SCHEMAS (Input Validation)
# ============================================================================

class CompanyListQuery(BaseModel):
    """Query schema for listing companies with pagination and filtering.
    
    Based on standard pagination pattern.
    """

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    name: Optional[str] = Field(None, description="Filter by company name (partial match)")
    slug: Optional[str] = Field(None, description="Filter by company slug (exact match)")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    sort_by: str = Field("name", description="Sort field: created_at, updated_at, name, slug")
    sort_order: str = Field("asc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)


class CompanyCreate(BaseModel):
    """Request schema for creating a company.
    
    Based on F1A_api_spec.md Section 4.1 - Company Resource.
    """

    name: str = Field(..., min_length=1, max_length=255, description="Company name (unique, case-insensitive)")
    slug: str = Field(..., min_length=1, max_length=255, description="URL identifier (unique, case-insensitive)")
    is_active: bool = Field(True, description="Company availability (blocks access if false)")

    model_config = ConfigDict(from_attributes=True)


class CompanyUpdate(BaseModel):
    """Request schema for updating a company.
    
    Based on F1A_api_spec.md Section 4.1 - Company Resource.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Company name (unique, case-insensitive)")
    slug: Optional[str] = Field(None, min_length=1, max_length=255, description="URL identifier (unique, case-insensitive)")
    is_active: Optional[bool] = Field(None, description="Company availability (blocks access if false)")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RESPONSE SCHEMAS (Output Structure)
# ============================================================================

class CompanyRead(BaseModel):
    """Response schema for company details.
    
    Based on F1A_api_spec.md Section 4.1 - Company Resource fields.
    """

    company_id: UUID = Field(..., description="Unique company identifier")
    name: str = Field(..., description="Company name (unique, case-insensitive)")
    slug: str = Field(..., description="URL identifier (unique, case-insensitive)")
    is_active: bool = Field(..., description="Company availability (blocks access if false)")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp (UTC)")
    created_by: Optional[UUID] = Field(None, description="User ID who created the company")
    updated_by: Optional[UUID] = Field(None, description="User ID who last updated the company")
    deleted_by: Optional[UUID] = Field(None, description="User ID who soft-deleted the company")

    model_config = ConfigDict(from_attributes=True)


class CompanyListItem(BaseModel):
    """Response schema for company list item (simplified).
    
    Used in paginated list responses.
    Based on F1A_api_spec.md Section 5.7 - GET /api/v1/companies response.
    """

    company_id: UUID = Field(..., description="Unique company identifier")
    name: str = Field(..., description="Company name (unique, case-insensitive)")
    slug: str = Field(..., description="URL identifier (unique, case-insensitive)")
    is_active: bool = Field(..., description="Company availability (blocks access if false)")

    model_config = ConfigDict(from_attributes=True)


class CompaniesListResponse(BaseModel):
    """Companies list response wrapper.
    
    Based on F1A_api_spec.md Section 5.7 - GET /api/v1/companies response structure.
    Wraps companies array in items field.
    """

    items: list[CompanyListItem] = Field(..., description="List of available companies")

    model_config = ConfigDict(from_attributes=True)
