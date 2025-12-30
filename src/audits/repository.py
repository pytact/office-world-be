"""Database operations for Audit Logging & Activity History module.

Repository layer - pure database operations only, no business logic.
All methods use eager loading for relationships to prevent MissingGreenlet errors.
Audit logs are immutable (append-only), so no update or delete methods.
"""

from uuid import UUID
from typing import Optional, Union
from datetime import datetime
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.audits.models import AuditLog
from src.users.models import User
from src.permissions.models import UserRoleAssignment


class AuditLogRepository:
    """Repository for audit log database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, audit_log_id: UUID, company_id: Optional[UUID] = None
    ) -> Optional[AuditLog]:
        """Get audit log by ID with eager loading of relationships.
        
        Eager loads:
        - company (Company)
        - actor (User) - nullable for SYSTEM actions
        
        Filters:
        - Optional: company_id filter (for multi-tenant isolation)
        """
        query = (
            select(AuditLog)
            .options(
                selectinload(AuditLog.company),  # CRITICAL: Eager load company
                selectinload(AuditLog.actor).selectinload(
                    User.role_assignments
                ).selectinload(UserRoleAssignment.role),  # CRITICAL: Eager load actor's role_assignments and role
            )
            .where(AuditLog.id == audit_log_id)
        )
        
        if company_id is not None:
            query = query.where(AuditLog.company_id == company_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_with_pagination(
        self,
        company_id: UUID,
        page: int,
        page_size: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action_code: Optional[str] = None,
        table_name: Optional[Union[str, list[str]]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[AuditLog], int]:
        """List audit logs with pagination, filtering, and sorting.
        
        Eager loads:
        - company (Company)
        - actor (User) - nullable for SYSTEM actions
        
        Filters:
        - company_id (required for multi-tenant isolation)
        - Optional: start_date (created_at >= start_date)
        - Optional: end_date (created_at <= end_date)
        - Optional: action_code (exact match, case-sensitive)
        - Optional: table_name (exact match for str, IN clause for list[str])
        
        Sorting:
        - sort_by: created_at (only allowed field per API spec)
        - sort_order: asc, desc
        """
        # Build base query with required filters and eager loading
        query = (
            select(AuditLog)
            .options(
                selectinload(AuditLog.company),  # CRITICAL: Eager load company
                selectinload(AuditLog.actor).selectinload(
                    User.role_assignments
                ).selectinload(UserRoleAssignment.role),  # CRITICAL: Eager load actor's role_assignments and role
            )
            .where(AuditLog.company_id == company_id)
        )

        # Apply optional filters
        if start_date is not None:
            query = query.where(AuditLog.created_at >= start_date)

        if end_date is not None:
            query = query.where(AuditLog.created_at <= end_date)

        if action_code is not None:
            query = query.where(AuditLog.action_code == action_code)

        if table_name is not None:
            if isinstance(table_name, list):
                # Manager role - filter by multiple tables (IN clause)
                query = query.where(AuditLog.table_name.in_(table_name))
            else:
                # Single table filter
                query = query.where(AuditLog.table_name == table_name)

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting (only created_at is allowed per API spec)
        sort_column = AuditLog.created_at
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
        company_id: UUID,
        action_code: str,
        table_name: str,
        record_id: Optional[UUID] = None,
        actor_id: Optional[UUID] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AuditLog:
        """Create a new audit log entry.
        
        Pure database operation - no business logic.
        Audit logs are immutable and append-only.
        
        Args:
            company_id: Company identifier (required)
            action_code: Action identifier (e.g., COMPANY_CREATED, COMPANY_UPDATED)
            table_name: Affected table name (e.g., companies)
            record_id: Identifier of affected record (optional)
            actor_id: User ID who performed the action (optional, null for SYSTEM actions)
            old_values: Changed fields before action (partial snapshot, optional)
            new_values: Changed fields after action (partial snapshot, optional)
            ip_address: Source IP address (optional)
            user_agent: Client metadata (optional)
            description: Human-readable summary (optional)
        
        Returns:
            Created AuditLog instance
        """
        audit_log = AuditLog(
            company_id=company_id,
            action_code=action_code,
            table_name=table_name,
            record_id=record_id,
            actor_id=actor_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
        self.session.add(audit_log)
        await self.session.commit()
        await self.session.refresh(audit_log)
        
        return audit_log
