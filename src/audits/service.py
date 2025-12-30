"""Business logic for Audit Logging & Activity History module.

Service layer - all business logic, validation, and orchestration.
Based on F11_api_spec.md - Audit Logging & Activity History (F-011).
ETag logic in service layer per error_prevention.md RULE 19.
"""

from uuid import UUID
from typing import Optional, Union
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from fastapi.responses import Response as FastAPIResponse

from src.audits.repository import AuditLogRepository
from src.audits.schemas import (
    AuditLogListQuery,
    AuditLogSummary,
    AuditLogDetail,
    AuditLogPaginatedResponse,
    ActorInfo,
)
from src.audits.models import AuditLog
from src.audits.exceptions import (
    AuditLogNotFound,
    InsufficientPermissions,
    ManagerTableRestriction,
    InvalidDateFormat,
    InvalidDateRange,
)
from src.audits.utils import (
    generate_etag,
    format_last_modified,
)
from src.audits.constants import (
    MANAGER_ALLOWED_TABLES,
    ACTOR_DISPLAY_NAME_SYSTEM,
)


class AuditLogService:
    """Service for audit log business logic.
    
    Based on F11_api_spec.md - All business rules in service layer.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = AuditLogRepository(session)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 datetime string with UTC timezone.
        
        Based on F11_api_spec.md Section 2.4 - UTC Timezone Standard.
        Raises InvalidDateFormat if date format is invalid.
        """
        if date_str is None:
            return None
        
        try:
            # Parse ISO 8601 datetime with UTC (Z suffix)
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # Ensure UTC timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except (ValueError, AttributeError):
            raise InvalidDateFormat("date")

    def _validate_date_range(
        self, start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> None:
        """Validate that start_date <= end_date.
        
        Raises InvalidDateRange if start_date > end_date.
        """
        if start_date is not None and end_date is not None:
            if start_date > end_date:
                raise InvalidDateRange()

    def _get_user_role_code(self, user) -> str:
        """Get user's active role code from role_assignments.
        
        Returns role code from active role assignment, or "unknown" if not found.
        """
        if not user or not user.role_assignments:
            return "unknown"
        
        # Find active role assignment
        for assignment in user.role_assignments:
            if assignment.is_active and assignment.deleted_at is None and assignment.role:
                return assignment.role.code.lower()
        
        return "unknown"

    def _build_actor_display_name(self, audit_log: AuditLog) -> str:
        """Build actor display name from audit log.
        
        Based on F11_api_spec.md Section 5.1 - actor_display_name.
        Returns "FirstName LastName (Role)" for user actions, "SYSTEM" for SYSTEM actions.
        """
        if audit_log.actor is None:
            return ACTOR_DISPLAY_NAME_SYSTEM
        
        # Get role code from actor's role_assignments
        role_code = self._get_user_role_code(audit_log.actor)
        
        first_name = audit_log.actor.first_name or ""
        last_name = audit_log.actor.last_name or ""
        name = f"{first_name} {last_name}".strip()
        
        if name:
            return f"{name} ({role_code.upper()})"
        else:
            return f"{role_code.upper()}"

    def _build_actor_info(self, audit_log: AuditLog) -> Optional[ActorInfo]:
        """Build actor info schema from audit log model.
        
        Returns None for SYSTEM actions (actor is None).
        """
        if audit_log.actor is None:
            return None
        
        # Get role code from actor's role_assignments
        role_code = self._get_user_role_code(audit_log.actor)
        
        return ActorInfo(
            id=audit_log.actor.id,
            first_name=audit_log.actor.first_name,  # Can be None, schema allows Optional[str]
            last_name=audit_log.actor.last_name,  # Can be None, schema allows Optional[str]
            role_code=role_code,
        )

    def _apply_role_based_filter(
        self, query_table_name: Optional[str], role: str
    ) -> Optional[Union[str, list[str]]]:
        """Apply role-based filtering for Manager role.
        
        Based on F11_api_spec.md Section 3.2 - Visibility Rules.
        Manager can only access logs where table_name ∈ {tasks, projects, task_assignments}.
        
        Returns:
        - For Manager: list of allowed tables (even when no filter provided) or single table if filter provided
        - For CEO/HR: original query_table_name (no restriction)
        
        Raises ManagerTableRestriction if Manager tries to access non-allowed table.
        """
        role_lower = role.lower() if role else ""
        
        if role_lower == "manager":
            # Manager can only see specific tables
            if query_table_name is not None:
                # Manager provided table_name filter - validate it's allowed
                if query_table_name not in MANAGER_ALLOWED_TABLES:
                    raise ManagerTableRestriction(query_table_name)
                return query_table_name
            else:
                # CRITICAL: Manager querying without filter - automatically restrict to allowed tables
                # This enforces RBAC rule: Manager sees only logs for tasks, projects, task_assignments
                return MANAGER_ALLOWED_TABLES  # Return list for IN clause in repository
        else:
            # CEO and HR can see all tables
            return query_table_name

    async def list_audit_logs(
        self,
        company_id: UUID,
        query: AuditLogListQuery,
        role: str,
        if_none_match: Optional[str] = None,
    ) -> AuditLogPaginatedResponse | FastAPIResponse:
        """List audit logs with pagination, filtering, and sorting.
        
        Based on F11_api_spec.md Section 4.4.1 - GET /api/v1/company/audit-logs.
        
        Business Logic:
        - Role-based visibility: CEO/HR see all; Manager sees only allowed tables
        - Filters by company_id (multi-tenant isolation)
        - Filters by date range (optional)
        - Filters by action_code (optional, exact match)
        - Filters by table_name (optional, exact match, role-based for Manager)
        - Sorts by created_at (only allowed field)
        - Paginates results
        - Builds pagination URLs with all query parameters
        - Generates ETag from latest created_at
        """
        # Parse and validate dates
        start_date = self._parse_date(query.start_date)
        end_date = self._parse_date(query.end_date)
        self._validate_date_range(start_date, end_date)
        
        # Apply role-based filtering for Manager
        table_name = self._apply_role_based_filter(query.table_name, role)
        
        # Get audit logs from repository
        audit_logs, total = await self.repository.list_with_pagination(
            company_id=company_id,
            page=query.page,
            page_size=query.page_size,
            start_date=start_date,
            end_date=end_date,
            action_code=query.action_code,
            table_name=table_name,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        # Build audit log summaries
        items = []
        latest_created_at = None
        for audit_log in audit_logs:
            # Build actor info
            actor_info = self._build_actor_info(audit_log)
            actor_display_name = self._build_actor_display_name(audit_log)
            
            items.append(
                AuditLogSummary(
                    id=audit_log.id,
                    action_code=audit_log.action_code,
                    table_name=audit_log.table_name,
                    record_id=audit_log.record_id,
                    description=audit_log.description,
                    created_at=audit_log.created_at,
                    actor=actor_info,
                    actor_display_name=actor_display_name,
                )
            )
            # Track latest created_at for ETag generation
            if latest_created_at is None or audit_log.created_at > latest_created_at:
                latest_created_at = audit_log.created_at
        
        # Generate ETag from latest created_at (if audit logs exist)
        if latest_created_at:
            etag = generate_etag(latest_created_at)
            
            # Check If-None-Match for cache validation
            if if_none_match and if_none_match == etag:
                # Return 304 in service (business logic decision)
                return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Calculate pagination
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build navigation URLs with all query parameters
        base_path = "/api/v1/company/audit-logs"
        next_page = None
        prev_page = None
        
        if query.page < total_pages:
            # Build next_page URL with all query parameters
            next_params = []
            if query.page_size != 20:
                next_params.append(f"page_size={query.page_size}")
            if query.start_date is not None:
                next_params.append(f"start_date={query.start_date}")
            if query.end_date is not None:
                next_params.append(f"end_date={query.end_date}")
            if query.action_code is not None:
                next_params.append(f"action_code={query.action_code}")
            if query.table_name is not None:
                next_params.append(f"table_name={query.table_name}")
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
            if query.start_date is not None:
                prev_params.append(f"start_date={query.start_date}")
            if query.end_date is not None:
                prev_params.append(f"end_date={query.end_date}")
            if query.action_code is not None:
                prev_params.append(f"action_code={query.action_code}")
            if query.table_name is not None:
                prev_params.append(f"table_name={query.table_name}")
            if query.sort_by != "created_at":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"
        
        result = AuditLogPaginatedResponse(
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )
        
        # Attach ETag and Last-Modified for router to set headers
        if latest_created_at:
            result._etag = generate_etag(latest_created_at)
            result._last_modified = latest_created_at
        
        return result

    async def get_audit_log_by_id(
        self,
        audit_log_id: UUID,
        company_id: UUID,
        role: str,
        if_none_match: Optional[str] = None,
    ) -> AuditLogDetail | FastAPIResponse:
        """Get detailed audit log information.
        
        Based on F11_api_spec.md Section 4.4.2 - GET /api/v1/company/audit-logs/{audit_log_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        
        Business Logic:
        - Validates audit log exists and belongs to company
        - Role-based access: Manager can only access if table_name is allowed
        - Generates ETag from created_at (immutable resource)
        - Handles If-None-Match for cache validation
        - Includes old_values, new_values, IP address, user agent
        - Calculates has_value_changes
        """
        # Get audit log from repository
        audit_log = await self.repository.get_by_id(audit_log_id, company_id)
        if not audit_log:
            raise AuditLogNotFound(str(audit_log_id))
        
        # Role-based access control for Manager
        role_lower = role.lower() if role else ""
        if role_lower == "manager":
            # Manager can only access logs for allowed tables
            if audit_log.table_name not in MANAGER_ALLOWED_TABLES:
                raise ManagerTableRestriction(audit_log.table_name)
        
        # Generate ETag in service (business logic)
        etag = generate_etag(audit_log.created_at)
        
        # Check If-None-Match in service (version validation)
        if if_none_match and if_none_match == etag:
            # Return 304 in service (business logic decision)
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Build actor info
        actor_info = self._build_actor_info(audit_log)
        actor_display_name = self._build_actor_display_name(audit_log)
        
        # Calculate has_value_changes
        has_value_changes = bool(
            (audit_log.old_values and len(audit_log.old_values) > 0)
            or (audit_log.new_values and len(audit_log.new_values) > 0)
        )
        
        # Build response
        result = AuditLogDetail(
            id=audit_log.id,
            action_code=audit_log.action_code,
            table_name=audit_log.table_name,
            record_id=audit_log.record_id,
            description=audit_log.description,
            old_values=audit_log.old_values,
            new_values=audit_log.new_values,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent,
            created_at=audit_log.created_at,
            actor=actor_info,
            actor_display_name=actor_display_name,
            has_value_changes=has_value_changes,
        )
        
        # Attach ETag and Last-Modified for router to set headers
        result._etag = etag
        result._last_modified = audit_log.created_at
        
        return result
