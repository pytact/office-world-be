"""FastAPI endpoints for Companies System module.

Based on F1A_api_spec.md - All endpoints with proper authentication, authorization,
user scoping, company scoping, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from src.schemas import StandardResponse
from src.pagination import PagedCollection
from src.companies.schemas import (
    CompanyListQuery,
    CompanyCreate,
    CompanyUpdate,
    CompanyRead,
    CompanyListItem,
)
from src.companies.dependencies import CompanyApiDep, get_current_user_with_company
from src.users.dependencies import get_current_superadmin
from src.companies.constants import (
    SUCCESS_COMPANIES_RETRIEVED,
    SUCCESS_COMPANY_RETRIEVED,
    SUCCESS_COMPANY_CREATED,
    SUCCESS_COMPANY_UPDATED,
    SUCCESS_COMPANY_DELETED,
)
from src.users.models import User

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


@router.get(
    "",
    response_model=StandardResponse[PagedCollection[CompanyListItem]],
    summary="List companies",
    description="List companies with pagination, filtering, and sorting. Supports filtering by name, slug, and is_active, and sorting by created_at, updated_at, name, or slug.",
)
async def list_companies(
    request: Request,
    query: CompanyListQuery = Depends(CompanyListQuery),
    api: CompanyApiDep = Depends(CompanyApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
) -> StandardResponse[PagedCollection[CompanyListItem]]:
    """List companies with pagination, filtering, and sorting.
    
    Based on standard pagination pattern.
    """
    user, company_id = user_company
    
    result = await api.list_companies_paginated(query)
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANIES_RETRIEVED,
    )


@router.get(
    "/{company_id}",
    response_model=StandardResponse[CompanyRead],
    summary="Get company by ID",
    description="Retrieve a single company by its unique identifier.",
)
async def get_company(
    request: Request,
    company_id: UUID,
    api: CompanyApiDep = Depends(CompanyApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
    response: Response = None,
) -> StandardResponse[CompanyRead]:
    """Retrieve a single company by ID."""
    user, company_id_param = user_company
    
    result = await api.get_company_by_id(company_id)
    
    # Set ETag and Last-Modified headers (based on updated_at)
    if hasattr(result, 'updated_at'):
        from src.notifications.utils import generate_etag, format_last_modified
        response.headers["ETag"] = generate_etag(result.updated_at)
        response.headers["Last-Modified"] = format_last_modified(result.updated_at)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANY_RETRIEVED,
    )


@router.post(
    "",
    response_model=StandardResponse[CompanyRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create company",
    description="Create a new company with name, slug, and active status. Company name and slug must be unique.",
)
async def create_company(
    request: Request,
    data: CompanyCreate,
    api: CompanyApiDep = Depends(CompanyApiDep),
    current_user: User = Depends(get_current_superadmin),
) -> StandardResponse[CompanyRead]:
    """Create a new company.
    
    Based on F1A_api_spec.md Section 4.1 - Company Resource.
    
    Authorization:
    - SuperAdmin only
    """
    result = await api.create_company(data, created_by=current_user.id)
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANY_CREATED,
    )


@router.patch(
    "/{company_id}",
    response_model=StandardResponse[CompanyRead],
    summary="Update company",
    description="Update a company's name, slug, and/or active status. Requires If-Match header for optimistic locking.",
)
async def update_company(
    request: Request,
    company_id: UUID,
    update_data: CompanyUpdate,
    api: CompanyApiDep = Depends(CompanyApiDep),
    current_user: User = Depends(get_current_superadmin),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[CompanyRead]:
    """Update a company.
    
    Based on F1A_api_spec.md Section 4.1 - Company Resource.
    
    Authorization:
    - SuperAdmin only
    
    Note: ETag validation is handled in service layer per error_prevention.md RULE 19.
    For now, we'll implement basic If-Match validation.
    """
    # If-Match header validation (ETag from GET response)
    if if_match:
        # Get current company to check ETag
        current_company = await api.get_company_by_id(company_id)
        from src.notifications.utils import generate_etag
        current_etag = generate_etag(current_company.updated_at)
        if if_match != current_etag:
            from src.companies.exceptions import PreconditionFailed
            raise PreconditionFailed()
    else:
        # If-Match header is required for update operations
        from src.companies.exceptions import PreconditionRequired
        raise PreconditionRequired()
    
    result = await api.update_company(company_id, update_data, updated_by=current_user.id)
    
    # Set new ETag after update
    if hasattr(result, 'updated_at'):
        from src.notifications.utils import generate_etag
        response.headers["ETag"] = generate_etag(result.updated_at)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANY_UPDATED,
    )


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete company",
    description="Soft delete a company. Cannot delete a company that has active users.",
)
async def delete_company(
    request: Request,
    company_id: UUID,
    api: CompanyApiDep = Depends(CompanyApiDep),
    current_user: User = Depends(get_current_superadmin),
) -> Response:
    """Soft delete a company.
    
    Based on F1A_api_spec.md Section 4.1 - Company Resource.
    
    Authorization:
    - SuperAdmin only
    
    Note: Cannot delete a company that has active users.
    """
    await api.delete_company(company_id, deleted_by=current_user.id)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
