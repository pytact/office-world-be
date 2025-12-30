"""FastAPI endpoints for Companies System module.

Based on F4_api_spec.md - Platform Company Management (F-004).
All endpoints with proper authentication, authorization, and StandardResponse format.
ETag logic is in service layer per error_prevention.md RULE 19.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from fastapi.responses import Response as FastAPIResponse
from src.schemas import StandardResponse
from src.companies.schemas import (
    CompanyListQuery,
    CompanyCreate,
    CompanyUpdate,
    CompanyProfileUpdate,
    CompanySummary,
    CompanyDetail,
    CompanyProfile,
    CompanyPaginatedResponse,
)
from src.companies.dependencies import (
    CompanyApiDep,
    get_current_ceo_or_hr,
)
from src.users.dependencies import get_current_superadmin
from src.companies.documentations.companies_api_doc import CompanyApiDocs
from src.companies.constants import (
    SUCCESS_COMPANIES_RETRIEVED,
    SUCCESS_COMPANY_RETRIEVED,
    SUCCESS_COMPANY_CREATED,
    SUCCESS_COMPANY_UPDATED,
    SUCCESS_COMPANY_DELETED,
    SUCCESS_COMPANY_PROFILE_RETRIEVED,
    SUCCESS_COMPANY_PROFILE_UPDATED,
)
from src.companies.utils import format_last_modified
from src.users.models import User
from src.users.utils import generate_request_id

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


# ============================================================================
# SuperAdmin Endpoints
# ============================================================================

@router.get(
    "",
    response_model=StandardResponse[CompanyPaginatedResponse],
    summary=CompanyApiDocs.list["summary"],
    description=CompanyApiDocs.list["description"],
)
async def list_companies(
    request: Request,
    query: CompanyListQuery = Depends(CompanyListQuery),
    api: CompanyApiDep = Depends(CompanyApiDep),
    current_user: User = Depends(get_current_superadmin),
    response: Response = None,
) -> StandardResponse[CompanyPaginatedResponse]:
    """List all companies with pagination, search, filtering, and sorting.

    Based on F4_api_spec.md Section 4.4.1 - GET /api/v1/companies.
    Authorization: SuperAdmin only.
    """
    # Generate X-Request-ID
    request_id = generate_request_id()
    if response:
        response.headers["X-Request-ID"] = request_id
    
    result = await api.list_companies_paginated(query)
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANIES_RETRIEVED,
    )


@router.get(
    "/{company_id}",
    response_model=StandardResponse[CompanyDetail],
    summary=CompanyApiDocs.get["summary"],
    description=CompanyApiDocs.get["description"],
)
async def get_company(
    request: Request,
    company_id: UUID,
    api: CompanyApiDep = Depends(CompanyApiDep),
    current_user: User = Depends(get_current_superadmin),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = None,
) -> StandardResponse[CompanyDetail] | FastAPIResponse:
    """Get company details with user count.

    Based on F4_api_spec.md Section 4.4.3 - GET /api/v1/companies/{company_id}.
    Authorization: SuperAdmin only.
    ETag logic in service layer per error_prevention.md RULE 19.
    """
    # Generate X-Request-ID
    request_id = generate_request_id()
    if response:
        response.headers["X-Request-ID"] = request_id
    
    # Pass header to service (service handles ETag logic)
    result = await api.get_company_by_id(company_id, if_none_match=if_none_match)
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        result.headers["X-Request-ID"] = request_id
        return result
    
    # Set headers from service result (router sets HTTP headers)
    if hasattr(result, '_etag'):
        response.headers["ETag"] = result._etag
        response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANY_RETRIEVED,
    )


@router.post(
    "",
    response_model=StandardResponse[CompanyDetail],
    status_code=status.HTTP_201_CREATED,
    summary=CompanyApiDocs.create["summary"],
    description=CompanyApiDocs.create["description"],
)
async def create_company(
    request: Request,
    data: CompanyCreate,
    api: CompanyApiDep = Depends(CompanyApiDep),
    current_user: User = Depends(get_current_superadmin),
    response: Response = None,
) -> StandardResponse[CompanyDetail]:
    """Create a new company.

    Based on F4_api_spec.md Section 4.4.2 - POST /api/v1/companies.
    Authorization: SuperAdmin only.
    """
    # Generate X-Request-ID
    request_id = generate_request_id()
    if response:
        response.headers["X-Request-ID"] = request_id
    
    # Extract request metadata for audit logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    result = await api.create_company(
        data,
        created_by=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Set ETag and Last-Modified headers from service result
    if hasattr(result, '_etag'):
        response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified'):
        response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANY_CREATED,
    )


@router.patch(
    "/{company_id}",
    response_model=StandardResponse[CompanyDetail],
    summary=CompanyApiDocs.update["summary"],
    description=CompanyApiDocs.update["description"],
)
async def update_company(
    request: Request,
    company_id: UUID,
    update_data: CompanyUpdate,
    api: CompanyApiDep = Depends(CompanyApiDep),
    current_user: User = Depends(get_current_superadmin),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[CompanyDetail]:
    """Update company information or activate/deactivate company.

    Based on F4_api_spec.md Section 4.4.4 - PATCH /api/v1/companies/{company_id}.
    Authorization: SuperAdmin only.
    ETag validation in service layer per error_prevention.md RULE 19.
    """
    # Generate X-Request-ID
    request_id = generate_request_id()
    if response:
        response.headers["X-Request-ID"] = request_id
    
    # Extract request metadata for audit logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Pass header to service (service handles validation)
    result = await api.update_company(
        company_id,
        update_data,
        if_match=if_match,
        updated_by=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Set ETag header from service result
    if hasattr(result, '_etag'):
        response.headers["ETag"] = result._etag
    
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANY_UPDATED,
    )


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary=CompanyApiDocs.delete["summary"],
    description=CompanyApiDocs.delete["description"],
)
async def delete_company(
    request: Request,
    company_id: UUID,
    api: CompanyApiDep = Depends(CompanyApiDep),
    current_user: User = Depends(get_current_superadmin),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> Response:
    """Hard delete a company.

    Based on F4_api_spec.md Section 4.4.5 - DELETE /api/v1/companies/{company_id}.
    Authorization: SuperAdmin only.
    ETag validation in service layer per error_prevention.md RULE 19.
    """
    # Generate X-Request-ID
    request_id = generate_request_id()
    if response:
        response.headers["X-Request-ID"] = request_id
    
    # Pass header to service (service handles validation)
    await api.delete_company(company_id, if_match=if_match)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Company Profile Endpoints (CEO/HR only)
# ============================================================================

profile_router = APIRouter(
    prefix="/company",
    tags=["Companies"],
)


@profile_router.get(
    "/profile",
    response_model=StandardResponse[CompanyProfile],
    summary=CompanyApiDocs.get_profile["summary"],
    description=CompanyApiDocs.get_profile["description"],
)
async def get_company_profile(
    request: Request,
    api: CompanyApiDep = Depends(CompanyApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[CompanyProfile] | FastAPIResponse:
    """Get own company profile.
    
    Based on F4_api_spec.md Section 4.4.6 - GET /api/v1/company/profile.
    Authorization: CEO, HR only (own company from JWT org_id).
    ETag logic in service layer per error_prevention.md RULE 19.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    # Pass header to service (service handles ETag logic)
    result = await api.get_company_profile(company_id, if_none_match=if_none_match)
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        result.headers["X-Request-ID"] = request_id
        return result
    
    # Set headers from service result (router sets HTTP headers)
    if hasattr(result, '_etag'):
        response.headers["ETag"] = result._etag
        response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    response.headers["X-Request-ID"] = request_id
    
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANY_PROFILE_RETRIEVED,
    )


@profile_router.patch(
    "/profile",
    response_model=StandardResponse[CompanyProfile],
    summary=CompanyApiDocs.update_profile["summary"],
    description=CompanyApiDocs.update_profile["description"],
)
async def update_company_profile(
    request: Request,
    update_data: CompanyProfileUpdate,
    api: CompanyApiDep = Depends(CompanyApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[CompanyProfile]:
    """Update company profile fields.
    
    Based on F4_api_spec.md Section 4.4.7 - PATCH /api/v1/company/profile.
    Authorization: CEO, HR only (own company from JWT org_id, blocked if is_active: false).
    ETag validation in service layer per error_prevention.md RULE 19.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    # Extract request metadata for audit logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Pass header to service (service handles validation)
    result = await api.update_company_profile(
        company_id,
        update_data,
        if_match=if_match,
        updated_by=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Set ETag header from service result
    if hasattr(result, '_etag'):
        response.headers["ETag"] = result._etag
    response.headers["X-Request-ID"] = request_id
    
    return StandardResponse(
        data=result,
        message=SUCCESS_COMPANY_PROFILE_UPDATED,
    )
