"""Pydantic schemas for Project Management module.

Based on F7_api_spec.md Section 5 - Data Models.
Request schemas define input validation, Response schemas define output structure.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from src.pagination import PagedCollection


# ============================================================================
# Request Schemas (Input Validation)
# ============================================================================

class ProjectListQuery(BaseModel):
    """Query schema for listing projects with pagination and filtering.
    
    Based on F7_api_spec.md Section 4.3.1 - GET /api/v1/company/projects.
    Query parameters MUST be defined using query schema class with Depends() pattern.
    """
    
    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    status: Optional[str] = Field(None, description="Filter by project status: ACTIVE, INACTIVE, COMPLETED (case-sensitive)")
    search: Optional[str] = Field(None, description="Search by project name (case-insensitive partial match)")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, name, status, task_count")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    """Request schema for creating a new project.
    
    Based on F7_api_spec.md Section 5.4 - Project Create Request.
    """
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Project name (case-insensitive unique within company)"
    )
    status: str = Field(
        ...,
        description="Initial project status: ACTIVE, INACTIVE, COMPLETED (case-sensitive)"
    )
    
    model_config = ConfigDict(from_attributes=True)


class ProjectUpdate(BaseModel):
    """Request schema for updating a project.
    
    Based on F7_api_spec.md Section 5.5 - Project Update Request.
    At least one field (name or status) must be provided.
    """
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Project name (case-insensitive unique within company, if provided)"
    )
    status: Optional[str] = Field(
        None,
        description="Project status: ACTIVE, INACTIVE, COMPLETED (case-sensitive, if provided)"
    )
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas (Output Structure)
# ============================================================================

class TaskSummary(BaseModel):
    """Task summary nested in project detail response.
    
    Based on F7_api_spec.md Section 5.3 - Task Summary.
    Read-only data from F-008 (Task Management & Assignment).
    """
    
    id: UUID = Field(..., description="Task identifier")
    title: str = Field(..., description="Task title")
    status: str = Field(..., description="Task status")
    assignee_id: UUID = Field(..., description="Assigned user ID")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectSummary(BaseModel):
    """Project summary for list response.
    
    Based on F7_api_spec.md Section 5.1 - Project Summary (List Response).
    """
    
    id: UUID = Field(..., description="Project identifier")
    name: str = Field(..., description="Project name")
    status: str = Field(..., description="Project status: ACTIVE, INACTIVE, COMPLETED")
    task_count: int = Field(..., description="Number of associated tasks", ge=0)
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectDetail(BaseModel):
    """Project detail for detail response.
    
    Based on F7_api_spec.md Section 5.2 - Project Detail (Detail Response).
    """
    
    id: UUID = Field(..., description="Project identifier")
    name: str = Field(..., description="Project name")
    status: str = Field(..., description="Project status: ACTIVE, INACTIVE, COMPLETED")
    task_count: int = Field(..., description="Number of associated tasks", ge=0)
    is_frozen: bool = Field(..., description="Whether project is frozen (true if status is INACTIVE or COMPLETED)")
    tasks: list[TaskSummary] = Field(..., description="Task summaries (read-only from F-008)")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    created_by: UUID = Field(..., description="Creator user ID")
    updated_by: UUID = Field(..., description="Last updater user ID")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Paginated Response
# ============================================================================

class ProjectPaginatedResponse(BaseModel):
    """Paginated response wrapper for project list.
    
    Based on F7_api_spec.md Section 5.6 - Paginated Response Structure.
    """
    
    items: list[ProjectSummary] = Field(..., description="Array of ProjectSummary objects")
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    next_page: Optional[str] = Field(None, description="Full relative URL for next page (or null if no next page)")
    prev_page: Optional[str] = Field(None, description="Full relative URL for previous page (or null if no previous page)")
    
    model_config = ConfigDict(from_attributes=True)
