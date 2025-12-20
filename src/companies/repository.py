"""Database operations for Companies System module.

Repository layer - pure database operations only, no business logic.
Based on F4_api_spec.md - Hard deletion support (no soft delete).
"""

from uuid import UUID
from typing import Optional
from sqlalchemy import select, func, desc, asc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.companies.models import Company
from src.permissions.models import UserRoleAssignment


class CompanyRepository:
    """Repository for company database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, company_id: UUID) -> Optional[Company]:
        """Get company by ID.
        
        Based on F4_api_spec.md - Hard deletion (no soft delete filtering).
        """
        result = await self.session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Company]:
        """Get company by slug.
        
        Based on F4_api_spec.md - Hard deletion (no soft delete filtering).
        """
        result = await self.session.execute(
            select(Company).where(Company.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_with_pagination(
        self,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Company], int]:
        """List companies with pagination, filtering, and sorting.
        
        Based on F4_api_spec.md Section 4.4.1 - GET /api/v1/companies.
        
        Filters:
        - search: Search by company name or slug (case-insensitive partial match)
        - status: Filter by status (active, inactive)
        
        Sorting:
        - sort_by: created_at, updated_at, name, slug, is_active
        - sort_order: asc, desc
        """
        # Build base query
        query = select(Company)

        # Apply search filter (name or slug)
        if search is not None:
            query = query.where(
                or_(
                    Company.name.ilike(f"%{search}%"),
                    Company.slug.ilike(f"%{search}%"),
                )
            )

        # Apply status filter
        if status == "active":
            query = query.where(Company.is_active == True)
        elif status == "inactive":
            query = query.where(Company.is_active == False)

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
        elif sort_by == "is_active":
            sort_column = Company.is_active
        else:
            # Default to created_at if invalid sort_by
            sort_column = Company.created_at

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

    async def get_user_count(self, company_id: UUID) -> int:
        """Get user count for a company.
        
        Based on F4_api_spec.md - user_count is a derived field (aggregate).
        Counts active user role assignments for the company.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(UserRoleAssignment)
            .where(
                UserRoleAssignment.company_id == company_id,
                UserRoleAssignment.is_active == True,
            )
        )
        count = result.scalar() or 0
        return count

    async def create(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        postal_code: Optional[str] = None,
        website: Optional[str] = None,
        logo_url: Optional[str] = None,
        created_by: Optional[UUID] = None,
    ) -> Company:
        """Create a new company.
        
        Based on F4_api_spec.md Section 4.4.2 - POST /api/v1/companies.
        Company defaults to is_active: true on creation.
        """
        company = Company(
            name=name,
            slug=slug,
            description=description,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            website=website,
            logo_url=logo_url,
            is_active=True,  # Defaults to true per F4 spec
            created_by=created_by,
        )
        self.session.add(company)
        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def update(
        self,
        company_id: UUID,
        description: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        postal_code: Optional[str] = None,
        website: Optional[str] = None,
        logo_url: Optional[str] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[UUID] = None,
    ) -> Optional[Company]:
        """Update a company.
        
        Based on F4_api_spec.md Section 4.4.4 - PATCH /api/v1/companies/{company_id}.
        Note: name and slug are immutable and cannot be updated.
        """
        company = await self.get_by_id(company_id)
        if not company:
            return None

        # Update profile fields
        if description is not None:
            company.description = description
        if address is not None:
            company.address = address
        if city is not None:
            company.city = city
        if state is not None:
            company.state = state
        if country is not None:
            company.country = country
        if postal_code is not None:
            company.postal_code = postal_code
        if website is not None:
            company.website = website
        if logo_url is not None:
            company.logo_url = logo_url
        
        # Update governance fields
        if is_active is not None:
            company.is_active = is_active
        if updated_by is not None:
            company.updated_by = updated_by

        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def hard_delete(self, company_id: UUID) -> bool:
        """Hard delete a company.
        
        Based on F4_api_spec.md Section 4.4.5 - DELETE /api/v1/companies/{company_id}.
        Permanently deletes company and all associated data (cascade).
        No dependency checks - proceeds even if company has active users.
        """
        company = await self.get_by_id(company_id)
        if not company:
            return False

        await self.session.delete(company)
        await self.session.commit()
        return True

    async def check_name_exists(self, name: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if company name already exists.
        
        Based on F4_api_spec.md - Case-insensitive unique constraint.
        Returns True if name exists, False otherwise.
        Optionally excludes a specific company ID.
        """
        query = select(func.count()).select_from(Company).where(
            Company.name.ilike(name)
        )
        if exclude_id is not None:
            query = query.where(Company.id != exclude_id)

        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def check_slug_exists(self, slug: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if company slug already exists.
        
        Based on F4_api_spec.md - Case-insensitive unique constraint.
        Returns True if slug exists, False otherwise.
        Optionally excludes a specific company ID.
        """
        query = select(func.count()).select_from(Company).where(
            Company.slug.ilike(slug)
        )
        if exclude_id is not None:
            query = query.where(Company.id != exclude_id)

        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
