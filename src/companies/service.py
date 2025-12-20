"""Business logic for Companies System module.

Service layer - all business logic, validation, and orchestration.
No HTTP concerns, no database queries (uses repository).
"""

from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.companies.models import Company
from src.companies.repository import CompanyRepository
from src.companies.schemas import (
    CompanyListQuery,
    CompanyCreate,
    CompanyUpdate,
    CompanyRead,
    CompanyListItem,
)
from src.companies.exceptions import (
    CompanyNotFound,
    DuplicateCompanyName,
    DuplicateCompanySlug,
    InvalidSortField,
    InvalidSortOrder,
    CannotDeleteCompanyInUse,
)
from src.companies.constants import (
    VALID_SORT_FIELDS,
    VALID_SORT_ORDERS,
)
from src.pagination import PagedCollection
from src.config import settings


class CompanyService:
    """Service for company management business logic."""

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

    async def list_companies_paginated(self, query: CompanyListQuery) -> PagedCollection[CompanyListItem]:
        """List companies with pagination, filtering, and sorting."""
        # Validate inputs
        self._validate_sort_field(query.sort_by)
        self._validate_sort_order(query.sort_order)

        # Get companies from repository
        items, total = await self.repository.list_with_pagination(
            page=query.page,
            page_size=query.page_size,
            name=query.name,
            slug=query.slug,
            is_active=query.is_active,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )

        # Convert to response schemas
        company_items = [CompanyListItem.model_validate(item) for item in items]

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
            if query.name is not None:
                next_params.append(f"name={query.name}")
            if query.slug is not None:
                next_params.append(f"slug={query.slug}")
            if query.is_active is not None:
                next_params.append(f"is_active={str(query.is_active).lower()}")
            if query.sort_by != "name":
                next_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "asc":
                next_params.append(f"sort_order={query.sort_order}")
            next_params.append(f"page={query.page + 1}")
            next_page = f"{base_path}?{'&'.join(next_params)}"

        if query.page > 1:
            # Build prev_page URL with all query parameters
            prev_params = []
            if query.page_size != 20:
                prev_params.append(f"page_size={query.page_size}")
            if query.name is not None:
                prev_params.append(f"name={query.name}")
            if query.slug is not None:
                prev_params.append(f"slug={query.slug}")
            if query.is_active is not None:
                prev_params.append(f"is_active={str(query.is_active).lower()}")
            if query.sort_by != "name":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "asc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"

        return PagedCollection(
            items=company_items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def get_company_by_id(self, company_id: UUID) -> CompanyRead:
        """Get company by ID."""
        company = await self.repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(str(company_id))

        return CompanyRead(
            company_id=company.id,
            name=company.name,
            slug=company.slug,
            is_active=company.is_active,
            created_at=company.created_at,
            updated_at=company.updated_at,
            deleted_at=company.deleted_at,
            created_by=company.created_by,
            updated_by=company.updated_by,
            deleted_by=company.deleted_by,
        )

    async def create_company(self, data: CompanyCreate, created_by: Optional[UUID] = None) -> CompanyRead:
        """Create a new company."""
        # Check for duplicate name
        if await self.repository.check_name_exists(data.name):
            raise DuplicateCompanyName(data.name)

        # Check for duplicate slug
        if await self.repository.check_slug_exists(data.slug):
            raise DuplicateCompanySlug(data.slug)

        # Create company
        company = await self.repository.create(
            name=data.name,
            slug=data.slug,
            is_active=data.is_active,
            created_by=created_by,
        )

        return CompanyRead(
            company_id=company.id,
            name=company.name,
            slug=company.slug,
            is_active=company.is_active,
            created_at=company.created_at,
            updated_at=company.updated_at,
            deleted_at=company.deleted_at,
            created_by=company.created_by,
            updated_by=company.updated_by,
            deleted_by=company.deleted_by,
        )

    async def update_company(
        self, company_id: UUID, data: CompanyUpdate, updated_by: Optional[UUID] = None
    ) -> CompanyRead:
        """Update a company."""
        company = await self.repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(str(company_id))

        # Check for duplicate name if name is being updated
        if data.name is not None and data.name.lower() != company.name.lower():
            if await self.repository.check_name_exists(data.name, exclude_id=company_id):
                raise DuplicateCompanyName(data.name)

        # Check for duplicate slug if slug is being updated
        if data.slug is not None and data.slug.lower() != company.slug.lower():
            if await self.repository.check_slug_exists(data.slug, exclude_id=company_id):
                raise DuplicateCompanySlug(data.slug)

        # Update company
        updated_company = await self.repository.update(
            company_id=company_id,
            name=data.name,
            slug=data.slug,
            is_active=data.is_active,
            updated_by=updated_by,
        )

        if not updated_company:
            raise CompanyNotFound(str(company_id))

        return CompanyRead(
            company_id=updated_company.id,
            name=updated_company.name,
            slug=updated_company.slug,
            is_active=updated_company.is_active,
            created_at=updated_company.created_at,
            updated_at=updated_company.updated_at,
            deleted_at=updated_company.deleted_at,
            created_by=updated_company.created_by,
            updated_by=updated_company.updated_by,
            deleted_by=updated_company.deleted_by,
        )

    async def delete_company(self, company_id: UUID, deleted_by: Optional[UUID] = None) -> None:
        """Soft delete a company."""
        company = await self.repository.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(str(company_id))

        # Check if company is in use
        if await self.repository.check_company_in_use(company_id):
            raise CannotDeleteCompanyInUse(company.name)

        # Soft delete company
        await self.repository.soft_delete(company_id, deleted_by=deleted_by)
