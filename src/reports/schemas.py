"""Pydantic schemas for Reports & Analytics API.

Based on F12A_api_spec.md - Request and response schemas.
"""

from typing import Optional, Any
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# Request Schemas (Query Parameters)
# ============================================================================

class ReportListQuery(BaseModel):
    """Query schema for listing accessible report types.
    
    Based on F12A_api_spec.md Section 4.3.1 - No query parameters for this endpoint.
    Schema class still required for consistency with Depends() pattern.
    """
    
    model_config = ConfigDict(from_attributes=True)


class ReportViewQuery(BaseModel):
    """Query schema for viewing report data with filters and pagination.
    
    Based on F12A_api_spec.md Section 4.3.2 - Query Parameters.
    """
    
    # Date range filters
    start_date: Optional[str] = Field(None, description="Start date (ISO 8601 format, UTC: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (ISO 8601 format, UTC: YYYY-MM-DD)")
    
    # Status filter (varies by report type)
    status: Optional[str] = Field(None, description="Filter by status (varies by report type)")
    
    # Entity filters (role-restricted)
    employee_id: Optional[str] = Field(None, description="Filter by employee ID (UUID, role-restricted)")
    department: Optional[str] = Field(None, description="Filter by department name (exact match)")
    project_id: Optional[str] = Field(None, description="Filter by project ID (UUID)")
    
    # Pagination (only for list-style reports)
    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    
    # Sorting
    sort_by: str = Field("created_at", description="Sort field (varies by report type)")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    
    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort_order is 'asc' or 'desc'."""
        if v.lower() not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v.lower()
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Report Type Listing
# ============================================================================

class ReportTypeResponse(BaseModel):
    """Response schema for a single report type.
    
    Based on F12A_api_spec.md Section 4.3.1 - ReportType object.
    """
    
    code: str = Field(..., description="Report type code")
    label: str = Field(..., description="Human-readable report name")
    description: str = Field(..., description="Report description")
    is_accessible: bool = Field(True, description="Whether user can access this report type")
    
    model_config = ConfigDict(from_attributes=True)


class ReportTypeListResponse(BaseModel):
    """Response schema for list of report types with count.
    
    Based on F12A_api_spec.md Section 4.3.1 - includes available_report_count at root level.
    This is a custom response format that extends StandardResponse pattern to include
    available_report_count at root level as required by the spec.
    """
    
    data: list[ReportTypeResponse] = Field(..., description="Array of ReportType objects")
    available_report_count: int = Field(..., description="Total count of accessible report types", ge=0)
    message: str = Field(..., description="Human-friendly success message")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Report View Metadata
# ============================================================================

class DateRangeFilter(BaseModel):
    """Date range filter options."""
    
    min_date: Optional[str] = Field(None, description="Minimum available date (ISO 8601 format)")
    max_date: Optional[str] = Field(None, description="Maximum available date (ISO 8601 format)")
    
    model_config = ConfigDict(from_attributes=True)


class EmployeeFilterOption(BaseModel):
    """Employee filter option."""
    
    employee_id: UUID = Field(..., description="Employee ID")
    name: str = Field(..., description="Employee name")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectFilterOption(BaseModel):
    """Project filter option."""
    
    project_id: UUID = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    
    model_config = ConfigDict(from_attributes=True)


class FilterOptions(BaseModel):
    """Available filter options for a report."""
    
    date_range: Optional[DateRangeFilter] = Field(None, description="Available date range")
    status: Optional[list[str]] = Field(None, description="Available status values")
    departments: Optional[list[str]] = Field(None, description="Available departments")
    employees: Optional[list[EmployeeFilterOption]] = Field(None, description="Available employees (role-restricted)")
    projects: Optional[list[ProjectFilterOption]] = Field(None, description="Available projects")
    
    model_config = ConfigDict(from_attributes=True)


class ReportMetadata(BaseModel):
    """Report metadata including filter options.
    
    Based on F12A_api_spec.md Section 4.3.2 - Report metadata structure.
    """
    
    report_type: str = Field(..., description="Report type code")
    title: str = Field(..., description="Report title")
    description: str = Field(..., description="Report description")
    source_features: list[str] = Field(..., description="Source feature codes")
    filter_options: FilterOptions = Field(..., description="Available filter options")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Pagination
# ============================================================================

class ReportPagination(BaseModel):
    """Pagination metadata for report data.
    
    Based on F12A_api_spec.md Section 4.3.2 - Pagination structure.
    """
    
    items: list[dict[str, Any]] = Field(..., description="Paginated items (same as rows)")
    total: int = Field(..., description="Total number of items", ge=0)
    page: int = Field(..., description="Current page number", ge=1)
    page_size: int = Field(..., description="Items per page", ge=1, le=100)
    total_pages: int = Field(..., description="Total number of pages", ge=0)
    next_page: Optional[str] = Field(None, description="Full relative URL for next page or null")
    prev_page: Optional[str] = Field(None, description="Full relative URL for previous page or null")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Report View
# ============================================================================

class ReportViewResponse(BaseModel):
    """Response schema for report view data.
    
    Based on F12A_api_spec.md Section 4.3.2 - Report view structure.
    Supports both list-style reports (with pagination) and aggregate reports (without pagination).
    """
    
    metadata: ReportMetadata = Field(..., description="Report metadata")
    rows: Optional[list[dict[str, Any]]] = Field(None, description="Report data rows (null for aggregate reports)")
    totals: dict[str, Any] = Field(..., description="Aggregated totals")
    pagination: Optional[ReportPagination] = Field(None, description="Pagination metadata (null for aggregate reports)")
    row_count: Optional[int] = Field(None, description="Total number of rows before pagination (null for aggregate reports)", ge=0)
    has_export: bool = Field(True, description="Whether export functionality is available for this report")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Export Schemas (F12B_api_spec.md)
# ============================================================================

class ExportFilter(BaseModel):
    """Filter snapshot for export request.
    
    Based on F12B_api_spec.md Section 4.3.1 - Request Body filters.
    """
    
    start_date: Optional[str] = Field(None, description="Start date (ISO 8601 format, UTC: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (ISO 8601 format, UTC: YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="Filter by status (varies by report type)")
    employee_id: Optional[str] = Field(None, description="Filter by employee ID (UUID, role-restricted)")
    department: Optional[str] = Field(None, description="Filter by department name (exact match)")
    project_id: Optional[str] = Field(None, description="Filter by project ID (UUID)")
    
    model_config = ConfigDict(from_attributes=True)


class ExportCreate(BaseModel):
    """Request schema for creating an export.
    
    Based on F12B_api_spec.md Section 4.3.1 - Request Body.
    """
    
    filters: Optional[ExportFilter] = Field(None, description="Filter snapshot to apply to export")
    
    model_config = ConfigDict(from_attributes=True)


class ExportCreateResponse(BaseModel):
    """Response schema for export creation.
    
    Based on F12B_api_spec.md Section 4.3.1 - Success Response (201 Created).
    """
    
    export_id: UUID = Field(..., description="Unique export identifier")
    report_type: str = Field(..., description="Report type code")
    status: str = Field(..., description="Export status")
    created_at: datetime = Field(..., description="Export creation timestamp (ISO 8601 format, UTC)")
    expires_at: datetime = Field(..., description="Export expiration timestamp (ISO 8601 format, UTC)")
    
    model_config = ConfigDict(from_attributes=True)


class ExportStatusResponse(BaseModel):
    """Response schema for export status check.
    
    Based on F12B_api_spec.md Section 4.3.2 - Success Response (200 OK).
    Supports all status values: PENDING, PROCESSING, COMPLETED, FAILED, EXPIRED.
    """
    
    export_id: UUID = Field(..., description="Unique export identifier")
    report_type: str = Field(..., description="Report type code")
    status: str = Field(..., description="Export status")
    created_at: datetime = Field(..., description="Export creation timestamp (ISO 8601 format, UTC)")
    expires_at: datetime = Field(..., description="Export expiration timestamp (ISO 8601 format, UTC)")
    completed_at: Optional[datetime] = Field(None, description="Export completion timestamp (present if COMPLETED)")
    failed_at: Optional[datetime] = Field(None, description="Export failure timestamp (present if FAILED)")
    file_url: Optional[str] = Field(None, description="Download URL for completed export (present if COMPLETED)")
    file_size: Optional[int] = Field(None, description="PDF file size in bytes (present if COMPLETED)", ge=0)
    error_message: Optional[str] = Field(None, description="Error message if export failed (present if FAILED)")
    
    model_config = ConfigDict(from_attributes=True)

