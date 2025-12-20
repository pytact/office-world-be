"""Database operations for Companies System module.

Repository layer - pure database operations only, no business logic.
All methods filter by deleted_at IS NULL for soft-delete support.
"""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from src.companies.models import Company
from src.permissions.models import UserRoleAssignment


class CompanyRepository:
    """Repository for company database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, company_id: UUID) -> Optional[Company]:
        """Get company by ID.
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        """
        result = await self.session.execute(
            select(Company)
            .where(
                Company.id == company_id,
                Company.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Company]:
        """Get company by slug.
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        """
        result = await self.session.execute(
            select(Company)
            .where(
                Company.slug == slug,
                Company.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_companies(
        self,
        is_active: Optional[bool] = None,
    ) -> list[Company]:
        """List all active companies (for SuperAdmin reference data).
        
        Based on F1A_api_spec.md Section 5.7 - GET /api/v1/companies.
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        - Optional: is_active filter
        - Ordered by name ascending
        """
        query = select(Company).where(
            Company.deleted_at.is_(None),
        )

        # Apply optional filter
        if is_active is not None:
            query = query.where(Company.is_active == is_active)

        # Order by name ascending
        query = query.order_by(Company.name.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_with_pagination(
        self,
        page: int,
        page_size: int,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> tuple[list[Company], int]:
        """List companies with pagination, filtering, and sorting.
        
        Filters:
        - deleted_at IS NULL (exclude soft-deleted)
        - Optional: name filter (partial match, case-insensitive)
        - Optional: slug filter (exact match)
        - Optional: is_active filter
        
        Sorting:
        - sort_by: created_at, updated_at, name, slug
        - sort_order: asc, desc
        """
        # Build base query with required filters
        query = select(Company).where(
            Company.deleted_at.is_(None),
        )

        # Apply optional filters
        if name is not None:
            query = query.where(Company.name.ilike(f"%{name}%"))

        if slug is not None:
            query = query.where(Company.slug == slug)

        if is_active is not None:
            query = query.where(Company.is_active == is_active)

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = None
        if sort_by == "created_at":
            sort_column = Company.created_at
        elif sort_by == "updated_at":
            sort_column = Company.updated_at
        elif sort_by == "name":
            sort_column = Company.name
        elif sort_by == "slug":
            sort_column = Company.slug
        else:
            # Default to name if invalid sort_by
            sort_column = Company.name

        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def create(
        self,
        name: str,
        slug: str,
        is_active: bool = True,
        created_by: Optional[UUID] = None,
    ) -> Company:
        """Create a new company."""
        company = Company(
            name=name,
            slug=slug,
            is_active=is_active,
            created_by=created_by,
        )
        self.session.add(company)
        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def update(
        self,
        company_id: UUID,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[UUID] = None,
    ) -> Optional[Company]:
        """Update a company."""
        company = await self.get_by_id(company_id)
        if not company:
            return None

        if name is not None:
            company.name = name
        if slug is not None:
            company.slug = slug
        if is_active is not None:
            company.is_active = is_active
        if updated_by is not None:
            company.updated_by = updated_by

        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def soft_delete(
        self,
        company_id: UUID,
        deleted_by: Optional[UUID] = None,
    ) -> Optional[Company]:
        """Soft delete a company."""
        company = await self.get_by_id(company_id)
        if not company:
            return None

        company.deleted_at = datetime.now(timezone.utc)
        if deleted_by is not None:
            company.deleted_by = deleted_by

        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def check_company_in_use(self, company_id: UUID) -> bool:
        """Check if company has active users.
        
        Returns True if company has active user role assignments, False otherwise.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(UserRoleAssignment)
            .where(
                UserRoleAssignment.company_id == company_id,
                UserRoleAssignment.is_active == True,
                UserRoleAssignment.deleted_at.is_(None),
            )
        )
        count = result.scalar() or 0
        return count > 0

    async def check_name_exists(self, name: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if company name already exists.
        
        Returns True if name exists, False otherwise.
        Excludes soft-deleted companies and optionally excludes a specific company ID.
        Case-insensitive comparison.
        """
        query = select(func.count()).select_from(Company).where(
            Company.name.ilike(name),
            Company.deleted_at.is_(None),
        )
        if exclude_id is not None:
            query = query.where(Company.id != exclude_id)

        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def check_slug_exists(self, slug: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if company slug already exists.
        
        Returns True if slug exists, False otherwise.
        Excludes soft-deleted companies and optionally excludes a specific company ID.
        Case-insensitive comparison.
        """
        query = select(func.count()).select_from(Company).where(
            Company.slug.ilike(slug),
            Company.deleted_at.is_(None),
        )
        if exclude_id is not None:
            query = query.where(Company.id != exclude_id)

        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
