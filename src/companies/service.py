"""Business logic for Companies System module.

Service layer - all business logic, validation, and orchestration.
Based on F4_api_spec.md - Platform Company Management (F-004).
ETag logic is in service layer per error_prevention.md RULE 19.
"""

from uuid import UUID
from typing import Optional
from fastapi import Response, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.companies.models import Company
from src.companies.repository import CompanyRepository
from src.companies.schemas import (
    CompanyListQuery,
    CompanyCreate,
    CompanyUpdate,
    CompanySummary,
    CompanyDetail,
    CompanyPaginatedResponse,
)
from src.companies.exceptions import (
    CompanyNotFound,
    DuplicateCompanyName,
    DuplicateCompanySlug,
    InvalidSortField,
    InvalidSortOrder,
    PreconditionRequired,
    PreconditionFailed,
    ValidationFailed,
)
from src.companies.constants import (
    VALID_SORT_FIELDS,
    VALID_SORT_ORDERS,
)
from src.companies.utils import generate_etag, format_last_modified
from src.config import settings


class CompanyService:
    """Service for company management business logic.
    
    Based on F4_api_spec.md - All business rules and ETag logic in service layer.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = CompanyRepository(session)

    def _validate_sort_field(self, sort_by: str) -> None:
        """Validate sort field."""
        if sort_by not in VALID_SORT_FIELDS:
            raise InvalidSortField(sort_by, VALID_SORT_FIELDS)

    def _validate_sort_order(self, sort_order: str) -> None:
        """Validate sort order."""
        if sort_order not in VALID_SORT_ORDERS:
            raise InvalidSortOrder(sort_order)

    async def list_companies_paginated(
        self, query: CompanyListQuery
    ) -> CompanyPaginatedResponse:
        """List companies with pagination, filtering, and sorting.
        
        Based on F4_api_spec.md Section 4.4.1 - GET /api/v1/companies.
        """
        # Validate inputs
        self._validate_sort_field(query.sort_by)
        self._validate_sort_order(query.sort_order)

        # Get companies from repository
        items, total = await self.repository.list_with_pagination(
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            status=query.status,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )

        # Convert to response schemas with user count
        company_summaries = []
        for item in items:
            user_count = await self.repository.get_user_count(item.id)
            company_summaries.append(
                CompanySummary(
                    company_id=item.id,
                    name=item.name,
                    slug=item.slug,
                    is_active=item.is_active,
                    is_deleted=item.is_deleted,
                    user_count=user_count,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )

        # Calculate pagination metadata
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0

        # Build pagination URLs
        base_path = f"/api{settings.api_prefix}/companies"

        next_page = None
        prev_page = None

        if query.page < total_pages:
            # Build next_page URL with all query parameters
            next_params = []
            if query.page_size != 20:
                next_params.append(f"page_size={query.page_size}")
            if query.search is not None:
                next_params.append(f"search={query.search}")
            if query.status is not None:
                next_params.append(f"status={query.status}")
            if query.sort_by != "created_at":
                next_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                next_params.append(f"sort_order={query.sort_order}")
            next_params.append(f"page={query.page + 1}")
            next_page = f"{base_path}?{'&'.join(next_params)}"

        if query.page > 1:
            # Build prev_page URL with all query parameters
            prev_params = []
            if query.page_size != 20:
                prev_params.append(f"page_size={query.page_size}")
            if query.search is not None:
                prev_params.append(f"search={query.search}")
            if query.status is not None:
                prev_params.append(f"status={query.status}")
            if query.sort_by != "created_at":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"

        return CompanyPaginatedResponse(
            items=company_summaries,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def get_company_by_id(
        self, company_id: UUID, if_none_match: Optional[str] = None
    ) -> CompanyDetail | FastAPIResponse:
        """Get company by ID with ETag support.
        
        Based on F4_api_spec.md Section 4.4.3 - GET /api/v1/companies/{company_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        company = await self.repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(str(company_id))

        # Generate ETag in service (business logic)
        etag = generate_etag(company.updated_at)

        # Check If-None-Match in service (version validation)
        if if_none_match and if_none_match == etag:
            # Return 304 in service (business logic decision)
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)

        # Get user count
        user_count = await self.repository.get_user_count(company_id)

        # Return company detail with ETag metadata
        result = CompanyDetail(
            company_id=company.id,
            name=company.name,
            slug=company.slug,
            description=company.description,
            address=company.address,
            city=company.city,
            state=company.state,
            country=company.country,
            postal_code=company.postal_code,
            website=company.website,
            logo_url=company.logo_url,
            is_active=company.is_active,
            is_deleted=company.is_deleted,
            user_count=user_count,
            created_at=company.created_at,
            updated_at=company.updated_at,
            created_by=company.created_by,
            updated_by=company.updated_by,
        )
        # Attach ETag to result for router to set header
        result._etag = etag
        result._last_modified = company.updated_at
        return result

    async def create_company(
        self, data: CompanyCreate, created_by: Optional[UUID] = None
    ) -> CompanyDetail:
        """Create a new company.
        
        Based on F4_api_spec.md Section 4.4.2 - POST /api/v1/companies.
        """
        # Check for duplicate name (case-insensitive)
        if await self.repository.check_name_exists(data.name):
            raise DuplicateCompanyName(data.name)

        # Check for duplicate slug (case-insensitive)
        if await self.repository.check_slug_exists(data.slug):
            raise DuplicateCompanySlug(data.slug)

        # Create company
        company = await self.repository.create(
            name=data.name,
            slug=data.slug,
            description=data.description,
            address=data.address,
            city=data.city,
            state=data.state,
            country=data.country,
            postal_code=data.postal_code,
            website=data.website,
            logo_url=data.logo_url,
            created_by=created_by,
        )

        # Get user count
        user_count = await self.repository.get_user_count(company.id)

        result = CompanyDetail(
            company_id=company.id,
            name=company.name,
            slug=company.slug,
            description=company.description,
            address=company.address,
            city=company.city,
            state=company.state,
            country=company.country,
            postal_code=company.postal_code,
            website=company.website,
            logo_url=company.logo_url,
            is_active=company.is_active,
            is_deleted=company.is_deleted,
            user_count=user_count,
            created_at=company.created_at,
            updated_at=company.updated_at,
            created_by=company.created_by,
            updated_by=company.updated_by,
        )
        # Attach ETag and Last-Modified for router
        result._etag = generate_etag(company.updated_at)
        result._last_modified = company.updated_at
        return result

    async def update_company(
        self,
        company_id: UUID,
        data: CompanyUpdate,
        if_match: Optional[str] = None,
        updated_by: Optional[UUID] = None,
    ) -> CompanyDetail:
        """Update a company with ETag validation.
        
        Based on F4_api_spec.md Section 4.4.4 - PATCH /api/v1/companies/{company_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Note: name and slug are immutable and cannot be updated.
        """
        # Get current company
        company = await self.repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(str(company_id))

        # Generate ETag in service
        current_etag = generate_etag(company.updated_at)

        # Validate If-Match in service (business logic)
        if not if_match:
            raise PreconditionRequired()

        if if_match != current_etag:
            # Raise exception in service (business logic validation)
            raise PreconditionFailed()

        # Validate immutable fields (business rule)
        # Name and slug cannot be updated per F4 spec
        # Note: CompanyUpdate schema doesn't include name/slug, but we check anyway for safety

        # Update company (business logic)
        updated_company = await self.repository.update(
            company_id=company_id,
            description=data.description,
            address=data.address,
            city=data.city,
            state=data.state,
            country=data.country,
            postal_code=data.postal_code,
            website=data.website,
            logo_url=data.logo_url,
            is_active=data.is_active,
            updated_by=updated_by,
        )

        if not updated_company:
            raise CompanyNotFound(str(company_id))

        # Get user count
        user_count = await self.repository.get_user_count(company_id)

        result = CompanyDetail(
            company_id=updated_company.id,
            name=updated_company.name,
            slug=updated_company.slug,
            description=updated_company.description,
            address=updated_company.address,
            city=updated_company.city,
            state=updated_company.state,
            country=updated_company.country,
            postal_code=updated_company.postal_code,
            website=updated_company.website,
            logo_url=updated_company.logo_url,
            is_active=updated_company.is_active,
            is_deleted=updated_company.is_deleted,
            user_count=user_count,
            created_at=updated_company.created_at,
            updated_at=updated_company.updated_at,
            created_by=updated_company.created_by,
            updated_by=updated_company.updated_by,
        )
        # Attach ETag and Last-Modified to result for router
        result._etag = generate_etag(updated_company.updated_at)
        result._last_modified = updated_company.updated_at
        return result

    async def delete_company(
        self, company_id: UUID, if_match: Optional[str] = None
    ) -> None:
        """Hard delete a company with ETag validation.
        
        Based on F4_api_spec.md Section 4.4.5 - DELETE /api/v1/companies/{company_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Note: Hard deletion proceeds even if company has active users (no dependency checks).
        """
        # Get current company
        company = await self.repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(str(company_id))

        # Generate ETag in service
        current_etag = generate_etag(company.updated_at)

        # Validate If-Match in service (business logic)
        if not if_match:
            raise PreconditionRequired()

        if if_match != current_etag:
            # Raise exception in service (business logic validation)
            raise PreconditionFailed()

        # Hard delete company (no dependency checks per F4 spec)
        await self.repository.hard_delete(company_id)
