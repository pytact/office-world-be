"""Business logic for Reports & Analytics module.

Service layer - all business logic, validation, and orchestration.
Based on F12A_api_spec.md - Reports & Analytics (F-012 Part A).
"""

from typing import Optional, Any
from uuid import UUID
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import traceback

from src.reports.repository import ReportRepository, ExportRepository
from src.employees.repository import EmployeeRepository
from src.celery_worker import generate_report_export_pdf
from src.reports.schemas import (
    ReportTypeResponse,
    ReportTypeListResponse,
    ReportViewResponse,
    ReportMetadata,
    FilterOptions,
    DateRangeFilter,
    ReportPagination,
    ExportCreate,
    ExportCreateResponse,
    ExportStatusResponse,
    ExportFilter,
)
from src.reports.constants import (
    REPORT_TYPES,
    REPORT_TYPE_LABELS,
    REPORT_TYPE_DESCRIPTIONS,
    REPORT_SOURCE_FEATURES,
    REPORT_ACCESS_BY_ROLE,
    EXPORT_ACCESS_BY_ROLE,
    EXPORT_TTL_HOURS,
    EXPORT_STATUS_PENDING,
    EXPORT_STATUS_PROCESSING,
    EXPORT_STATUS_COMPLETED,
    EXPORT_STATUS_FAILED,
    EXPORT_STATUS_EXPIRED,
    REPORT_TYPE_ATTENDANCE,
    REPORT_TYPE_LEAVE,
    REPORT_TYPE_SALARY_SUMMARY,
    REPORT_TYPE_EMPLOYEE,
    REPORT_TYPE_TASK,
    REPORT_TYPE_PROJECT,
    REPORT_TYPE_AUDIT_SUMMARY,
    ATTENDANCE_STATUS_VALUES,
    LEAVE_STATUS_VALUES,
    EMPLOYEE_STATUS_VALUES,
    TASK_STATUS_VALUES,
    PROJECT_STATUS_VALUES,
    AUDIT_STATUS_VALUES,
)
from src.reports.exceptions import (
    ReportTypeNotFound,
    InsufficientPermissions,
    FilterValidationError,
    BusinessRuleFailed,
    DateRangeValidationError,
    EmployeeFilterRestricted,
    CrossCompanyFilterError,
    InvalidStatusValue,
    ExportNotFound,
    ExportExpired,
    ExportNotReady,
    ExportAccessDenied,
)


class ReportService:
    """Service for reports & analytics business logic.
    
    Based on F12A_api_spec.md - All business rules in service layer.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ReportRepository(session)
        self.export_repository = ExportRepository(session)
    
    # ========================================================================
    # List Report Types
    # ========================================================================
    
    async def list_report_types(
        self,
        role: str,
    ) -> ReportTypeListResponse:
        """List accessible report types based on user role.
        
        Based on F12A_api_spec.md Section 4.3.1.
        Returns only report types accessible to the user's role.
        
        Note: Returns ReportTypeListResponse (not wrapped in StandardResponse)
        because the spec requires available_report_count at root level.
        """
        # Get accessible report types for role
        accessible_types = REPORT_ACCESS_BY_ROLE.get(role.lower(), [])
        
        # Build response
        report_types = []
        for report_type in accessible_types:
            report_types.append(ReportTypeResponse(
                code=report_type,
                label=REPORT_TYPE_LABELS.get(report_type, report_type),
                description=REPORT_TYPE_DESCRIPTIONS.get(report_type, ""),
                is_accessible=True,
            ))
        
        # Return ReportTypeListResponse (message will be set in router)
        return ReportTypeListResponse(
            data=report_types,
            available_report_count=len(report_types),
            message="",  # Message will be set in router based on count
        )
    
    # ========================================================================
    # Get Report Data
    # ========================================================================
    
    async def get_report_data(
        self,
        report_type: str,
        company_id: Optional[UUID],
        role: str,
        employee_id: Optional[UUID],
        query: Any,  # ReportViewQuery
    ) -> ReportViewResponse:
        """Get report data with optional filters.
        
        Based on F12A_api_spec.md Section 4.3.2.
        Handles role-based access, filter validation, and data aggregation.
        """
        # Normalize report type (case-insensitive)
        report_type_upper = report_type.upper()
        
        # Validate report type
        if report_type_upper not in REPORT_TYPES:
            raise ReportTypeNotFound(report_type)
        
        # Check role-based access
        accessible_types = REPORT_ACCESS_BY_ROLE.get(role.lower(), [])
        if report_type_upper not in accessible_types:
            raise InsufficientPermissions(report_type_upper, role)
        
        # BR-1203: SuperAdmin has no access
        if role.lower() == "superadmin":
            raise InsufficientPermissions(report_type_upper, role)
        
        # Validate and parse filters
        filters = await self._validate_and_parse_filters(
            report_type_upper,
            company_id,
            role,
            employee_id,
            query,
        )
        
        # Get report data based on type
        if report_type_upper == REPORT_TYPE_ATTENDANCE:
            return await self._get_attendance_report(
                company_id,
                filters,
                query,
            )
        elif report_type_upper == REPORT_TYPE_LEAVE:
            return await self._get_leave_report(
                company_id,
                filters,
                query,
            )
        elif report_type_upper == REPORT_TYPE_SALARY_SUMMARY:
            return await self._get_salary_summary_report(
                company_id,
                filters,
                query,
            )
        elif report_type_upper == REPORT_TYPE_EMPLOYEE:
            return await self._get_employee_report(
                company_id,
                filters,
                query,
            )
        elif report_type_upper == REPORT_TYPE_TASK:
            return await self._get_task_report(
                company_id,
                filters,
                query,
            )
        elif report_type_upper == REPORT_TYPE_PROJECT:
            return await self._get_project_report(
                company_id,
                filters,
                query,
            )
        elif report_type_upper == REPORT_TYPE_AUDIT_SUMMARY:
            return await self._get_audit_summary_report(
                company_id,
                filters,
                query,
            )
        else:
            raise ReportTypeNotFound(report_type)
    
    # ========================================================================
    # Filter Validation
    # ========================================================================
    
    async def _validate_and_parse_filters(
        self,
        report_type: str,
        company_id: Optional[UUID],
        role: str,
        employee_id: Optional[UUID],
        query: Any,  # ReportViewQuery
    ) -> dict[str, Any]:
        """Validate and parse filters based on role and report type."""
        filters = {}
        
        # Parse dates
        start_date = None
        end_date = None
        if query.start_date:
            try:
                start_date = datetime.fromisoformat(query.start_date.replace("Z", "+00:00")).date()
            except ValueError:
                raise FilterValidationError("start_date", "Invalid date format. Use ISO 8601 format (YYYY-MM-DD)")
        
        if query.end_date:
            try:
                end_date = datetime.fromisoformat(query.end_date.replace("Z", "+00:00")).date()
            except ValueError:
                raise FilterValidationError("end_date", "Invalid date format. Use ISO 8601 format (YYYY-MM-DD)")
        
        # Validate date range
        if start_date and end_date and end_date < start_date:
            raise DateRangeValidationError()
        
        filters["start_date"] = start_date
        filters["end_date"] = end_date
        
        # Validate status
        if query.status:
            valid_statuses = self._get_valid_statuses(report_type)
            if query.status not in valid_statuses:
                raise InvalidStatusValue(query.status, report_type)
            filters["status"] = query.status
        
        # Validate employee_id (role-restricted)
        if query.employee_id:
            try:
                emp_id = UUID(query.employee_id)
            except ValueError:
                raise FilterValidationError("employee_id", "Invalid UUID format")
            
            # BR-1204: Employees can only filter own data
            if role.lower() == "employee":
                if employee_id and emp_id != employee_id:
                    raise EmployeeFilterRestricted()
                filters["employee_id"] = employee_id  # Force to own ID
            else:
                # For other roles, validate employee belongs to company
                # This validation will be done in repository/service when querying
                filters["employee_id"] = emp_id
        else:
            # For employees, always restrict to own data
            if role.lower() == "employee" and employee_id:
                filters["employee_id"] = employee_id
        
        # Validate project_id
        if query.project_id:
            try:
                filters["project_id"] = UUID(query.project_id)
            except ValueError:
                raise FilterValidationError("project_id", "Invalid UUID format")
        
        # Department filter
        if query.department:
            filters["department"] = query.department
        
        return filters
    
    def _get_valid_statuses(self, report_type: str) -> list[str]:
        """Get valid status values for a report type."""
        status_map = {
            REPORT_TYPE_ATTENDANCE: ATTENDANCE_STATUS_VALUES,
            REPORT_TYPE_LEAVE: LEAVE_STATUS_VALUES,
            REPORT_TYPE_EMPLOYEE: EMPLOYEE_STATUS_VALUES,
            REPORT_TYPE_TASK: TASK_STATUS_VALUES,
            REPORT_TYPE_PROJECT: PROJECT_STATUS_VALUES,
            REPORT_TYPE_AUDIT_SUMMARY: AUDIT_STATUS_VALUES,
        }
        return status_map.get(report_type, [])
    
    async def _validate_export_filters(
        self,
        report_type: str,
        company_id: Optional[UUID],
        role: str,
        user_id: UUID,
        filters: ExportFilter,
    ) -> dict:
        """Validate export filters using same rules as report view filters.
        
        Based on F12B_api_spec.md Section 7.3 - Filter validation.
        
        Args:
            report_type: Report type code
            company_id: Company ID (for validation)
            role: User role (for role-based restrictions)
            user_id: User ID (for employee_id validation)
            filters: ExportFilter object to validate
        
        Returns:
            Validated filters dict
        
        Raises:
            FilterValidationError: Invalid filter format or value
            BusinessRuleFailed: Business rule violation (e.g., employee_id outside scope)
        """
        validated_filters = {}
        
        # Parse and validate dates
        start_date = None
        end_date = None
        if filters.start_date:
            try:
                start_date = datetime.fromisoformat(filters.start_date.replace("Z", "+00:00")).date()
            except ValueError:
                raise FilterValidationError("filters.start_date", "Invalid date format. Use ISO 8601 format (YYYY-MM-DD)")
        
        if filters.end_date:
            try:
                end_date = datetime.fromisoformat(filters.end_date.replace("Z", "+00:00")).date()
            except ValueError:
                raise FilterValidationError("filters.end_date", "Invalid date format. Use ISO 8601 format (YYYY-MM-DD)")
        
        # Validate date range (end_date >= start_date)
        if start_date and end_date and end_date < start_date:
            raise DateRangeValidationError()
        
        if start_date:
            validated_filters["start_date"] = start_date.isoformat()
        if end_date:
            validated_filters["end_date"] = end_date.isoformat()
        
        # Validate status
        if filters.status:
            valid_statuses = self._get_valid_statuses(report_type)
            if filters.status not in valid_statuses:
                raise InvalidStatusValue(filters.status, report_type)
            validated_filters["status"] = filters.status
        
        # Validate employee_id (role-restricted)
        if filters.employee_id:
            try:
                emp_id = UUID(filters.employee_id)
            except ValueError:
                raise FilterValidationError("filters.employee_id", "Invalid UUID format")
            
            # BR-1204: Employees can only filter own data
            if role.lower() == "employee":
                # Get employee_id for this user
                employee_repo = EmployeeRepository(self.session)
                if company_id:
                    employee = await employee_repo.get_by_user_id(user_id, company_id)
                    if not employee or employee.id != emp_id:
                        raise EmployeeFilterRestricted()
                    # Force to own employee_id
                    validated_filters["employee_id"] = str(employee.id)
                else:
                    raise BusinessRuleFailed(
                        field="filters.employee_id",
                        issue="Employee role requires company_id",
                    )
            else:
                # For other roles, employee_id will be validated during PDF generation
                # (to ensure employee belongs to company)
                validated_filters["employee_id"] = filters.employee_id
        
        # Validate project_id
        if filters.project_id:
            try:
                UUID(filters.project_id)  # Validate format
                validated_filters["project_id"] = filters.project_id
            except ValueError:
                raise FilterValidationError("filters.project_id", "Invalid UUID format")
        
        # Department filter (no validation needed, just store)
        if filters.department:
            validated_filters["department"] = filters.department
        
        return validated_filters
    
    # ========================================================================
    # Report Type Handlers
    # ========================================================================
    
    async def _get_attendance_report(
        self,
        company_id: UUID,
        filters: dict[str, Any],
        query: Any,
    ) -> ReportViewResponse:
        """Get attendance report data."""
        # Get data and totals
        rows, total = await self.repository.get_attendance_data(
            company_id=company_id,
            start_date=filters.get("start_date"),
            end_date=filters.get("end_date"),
            status=filters.get("status"),
            employee_id=filters.get("employee_id"),
            department=filters.get("department"),
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        totals = await self.repository.get_attendance_totals(
            company_id=company_id,
            start_date=filters.get("start_date"),
            end_date=filters.get("end_date"),
            employee_id=filters.get("employee_id"),
            department=filters.get("department"),
        )
        
        # Get filter options
        filter_options = await self._get_attendance_filter_options(company_id, filters.get("employee_id"))
        
        # Build pagination
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        pagination = ReportPagination(
            items=rows,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=self._build_next_page_url(query, total_pages) if query.page < total_pages else None,
            prev_page=self._build_prev_page_url(query) if query.page > 1 else None,
        )
        
        # Build metadata
        metadata = ReportMetadata(
            report_type=REPORT_TYPE_ATTENDANCE,
            title=REPORT_TYPE_LABELS[REPORT_TYPE_ATTENDANCE],
            description=REPORT_TYPE_DESCRIPTIONS[REPORT_TYPE_ATTENDANCE],
            source_features=REPORT_SOURCE_FEATURES[REPORT_TYPE_ATTENDANCE],
            filter_options=filter_options,
        )
        
        return ReportViewResponse(
            metadata=metadata,
            rows=rows,
            totals=totals,
            pagination=pagination,
            row_count=total,
            has_export=True,
        )
    
    async def _get_leave_report(
        self,
        company_id: Optional[UUID],
        filters: dict[str, Any],
        query: Any,
    ) -> ReportViewResponse:
        """Get leave report data."""
        # TODO: Implement leave report
        return self._build_empty_report(REPORT_TYPE_LEAVE)
    
    async def _get_salary_summary_report(
        self,
        company_id: UUID,
        filters: dict[str, Any],
        query: Any,
    ) -> ReportViewResponse:
        """Get salary summary report (aggregate only, no pagination)."""
        # TODO: Implement salary summary report
        return self._build_empty_aggregate_report(REPORT_TYPE_SALARY_SUMMARY)
    
    async def _get_employee_report(
        self,
        company_id: UUID,
        filters: dict[str, Any],
        query: Any,
    ) -> ReportViewResponse:
        """Get employee report data."""
        # TODO: Implement employee report
        return self._build_empty_report(REPORT_TYPE_EMPLOYEE)
    
    async def _get_task_report(
        self,
        company_id: UUID,
        filters: dict[str, Any],
        query: Any,
    ) -> ReportViewResponse:
        """Get task report data."""
        # TODO: Implement task report
        return self._build_empty_report(REPORT_TYPE_TASK)
    
    async def _get_project_report(
        self,
        company_id: UUID,
        filters: dict[str, Any],
        query: Any,
    ) -> ReportViewResponse:
        """Get project report data."""
        # TODO: Implement project report
        return self._build_empty_report(REPORT_TYPE_PROJECT)
    
    async def _get_audit_summary_report(
        self,
        company_id: Optional[UUID],
        filters: dict[str, Any],
        query: Any,
    ) -> ReportViewResponse:
        """Get audit summary report data."""
        # TODO: Implement audit summary report
        return self._build_empty_report(REPORT_TYPE_AUDIT_SUMMARY)
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _get_attendance_filter_options(
        self,
        company_id: UUID,
        employee_id: Optional[UUID],
    ) -> FilterOptions:
        """Get filter options for attendance report."""
        departments = await self.repository.get_available_departments(company_id)
        employees = await self.repository.get_available_employees(company_id, employee_id)
        
        return FilterOptions(
            date_range=DateRangeFilter(
                min_date=None,  # TODO: Get from actual data
                max_date=None,  # TODO: Get from actual data
            ),
            status=ATTENDANCE_STATUS_VALUES,
            departments=departments,
            employees=employees,
        )
    
    def _build_next_page_url(self, query: Any, total_pages: int) -> Optional[str]:
        """Build next page URL with all query parameters."""
        if query.page >= total_pages:
            return None
        
        # TODO: Build full relative URL with all query parameters
        # For now, return None (will be implemented when router is ready)
        return None
    
    def _build_prev_page_url(self, query: Any) -> Optional[str]:
        """Build previous page URL with all query parameters."""
        if query.page <= 1:
            return None
        
        # TODO: Build full relative URL with all query parameters
        # For now, return None (will be implemented when router is ready)
        return None
    
    def _build_empty_report(self, report_type: str) -> ReportViewResponse:
        """Build empty report response for unimplemented report types."""
        metadata = ReportMetadata(
            report_type=report_type,
            title=REPORT_TYPE_LABELS.get(report_type, report_type),
            description=REPORT_TYPE_DESCRIPTIONS.get(report_type, ""),
            source_features=REPORT_SOURCE_FEATURES.get(report_type, []),
            filter_options=FilterOptions(),
        )
        
        return ReportViewResponse(
            metadata=metadata,
            rows=[],
            totals={},
            pagination=ReportPagination(
                items=[],
                total=0,
                page=1,
                page_size=20,
                total_pages=0,
                next_page=None,
                prev_page=None,
            ),
            row_count=0,
            has_export=True,
        )
    
    def _build_empty_aggregate_report(self, report_type: str) -> ReportViewResponse:
        """Build empty aggregate report response (no pagination)."""
        metadata = ReportMetadata(
            report_type=report_type,
            title=REPORT_TYPE_LABELS.get(report_type, report_type),
            description=REPORT_TYPE_DESCRIPTIONS.get(report_type, ""),
            source_features=REPORT_SOURCE_FEATURES.get(report_type, []),
            filter_options=FilterOptions(),
        )
        
        return ReportViewResponse(
            metadata=metadata,
            rows=None,
            totals={},
            pagination=None,
            row_count=None,
            has_export=True,
        )
    
    # ========================================================================
    # Export Methods (F12B_api_spec.md)
    # ========================================================================
    
    async def create_export(
        self,
        report_type: str,
        user_id: UUID,
        company_id: Optional[UUID],
        role: str,
        filters: Optional[ExportFilter] = None,
    ) -> ExportCreateResponse:
        """Create an asynchronous PDF export request.
        
        Based on F12B_api_spec.md Section 4.3.1.
        
        Args:
            report_type: Report type code
            user_id: User creating the export
            company_id: Company ID (tenant boundary)
            role: User role for authorization check
            filters: Optional filter snapshot
        
        Returns:
            ExportCreateResponse with export_id and status
        
        Raises:
            ReportTypeNotFound: Invalid report type
            InsufficientPermissions: User role cannot export this report type
            FilterValidationError: Invalid filters
        """
        # Validate report type
        report_type_upper = report_type.upper()
        if report_type_upper not in REPORT_TYPES:
            raise ReportTypeNotFound(report_type)
        
        # Check export permissions (same as report view access)
        accessible_types = EXPORT_ACCESS_BY_ROLE.get(role.lower(), [])
        if report_type_upper not in accessible_types:
            raise InsufficientPermissions(report_type_upper, role)
        
        # Validate company_id for non-SuperAdmin users
        if role.lower() != "superadmin" and not company_id:
            raise BusinessRuleFailed(
                field="company_id",
                issue="Company ID is required for non-SuperAdmin users",
            )
        
        # Validate and convert filters if provided
        filters_dict = None
        if filters:
            # Validate filters using same rules as report view filters (spec Section 7.3)
            filters_dict = await self._validate_export_filters(
                report_type=report_type_upper,
                company_id=company_id,
                role=role,
                user_id=user_id,
                filters=filters,
            )
        
        # Calculate expiration (24 hours from now)
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=EXPORT_TTL_HOURS)
        
        # Create export
        export = await self.export_repository.create(
            user_id=user_id,
            company_id=company_id,
            report_type=report_type_upper,
            expires_at=expires_at,
            filters=filters_dict,
        )
        
        # Trigger async PDF generation via Celery task
        try:
            task_result = generate_report_export_pdf.delay(str(export.id))
            print(f"[EXPORT SERVICE] Celery task triggered: {task_result.id} for export {export.id}")
        except Exception as e:
            print(f"[EXPORT SERVICE ERROR] Failed to trigger Celery task: {str(e)}")
            traceback.print_exc()
            # Don't fail the request, but log the error
            # The export will remain in PENDING status
        
        return ExportCreateResponse(
            export_id=export.id,
            report_type=export.report_type,
            status=export.status,
            created_at=export.created_at,
            expires_at=export.expires_at,
        )
    
    async def get_export_status(
        self,
        export_id: UUID,
        report_type: str,
        user_id: UUID,
        role: str,
        company_id: Optional[UUID],
    ) -> ExportStatusResponse:
        """Get export status.
        
        Based on F12B_api_spec.md Section 4.3.2.
        
        Args:
            export_id: Export ID
            report_type: Report type code (for validation)
            user_id: User requesting status
            role: User role
            company_id: Company ID (for authorization)
        
        Returns:
            ExportStatusResponse with current status
        
        Raises:
            ExportNotFound: Export not found or access denied
            ExportExpired: Export has expired
        """
        # Get export with eager loading
        export = await self.export_repository.get_by_id(export_id, user_id=user_id)
        
        if not export:
            raise ExportNotFound(str(export_id))
        
        # Validate report_type matches
        if export.report_type.upper() != report_type.upper():
            raise ExportNotFound(str(export_id))
        
        # Check access (user must own export OR have admin access)
        if export.user_id != user_id:
            # Check if user has admin access to this report type
            accessible_types = EXPORT_ACCESS_BY_ROLE.get(role.lower(), [])
            if export.report_type not in accessible_types:
                raise ExportAccessDenied(str(export_id))
        
        # Check if expired
        now = datetime.now(timezone.utc)
        if export.expires_at < now and export.status != EXPORT_STATUS_EXPIRED:
            # Mark as expired
            export = await self.export_repository.mark_expired(export_id)
        
        if export.status == EXPORT_STATUS_EXPIRED:
            raise ExportExpired(str(export_id))
        
        # Build file_url if completed
        file_url = None
        if export.status == EXPORT_STATUS_COMPLETED:
            file_url = f"/api/v1/reports/{report_type.lower()}/exports/{export_id}/download"
        
        return ExportStatusResponse(
            export_id=export.id,
            report_type=export.report_type,
            status=export.status,
            created_at=export.created_at,
            expires_at=export.expires_at,
            completed_at=export.completed_at,
            failed_at=export.failed_at,
            file_url=file_url,
            file_size=export.file_size,
            error_message=export.error_message,
        )
    
    async def get_export_file_path(
        self,
        export_id: UUID,
        report_type: str,
        user_id: UUID,
        role: str,
        company_id: Optional[UUID],
    ) -> tuple[str, int, datetime]:
        """Get export file path, size, and creation date for download.
        
        Based on F12B_api_spec.md Section 4.3.3.
        
        Args:
            export_id: Export ID
            report_type: Report type code
            user_id: User requesting download
            role: User role
            company_id: Company ID
        
        Returns:
            Tuple of (file_path, file_size, created_at)
        
        Raises:
            ExportNotFound: Export not found
            ExportExpired: Export has expired
            ExportNotReady: Export is not in COMPLETED status
        """
        # Get export status (includes validation and access checks)
        export_status = await self.get_export_status(
            export_id=export_id,
            report_type=report_type,
            user_id=user_id,
            role=role,
            company_id=company_id,
        )
        
        # Check if export is ready for download
        if export_status.status != EXPORT_STATUS_COMPLETED:
            raise ExportNotReady(export_status.status)
        
        # Get export to access file_path, file_size, and created_at
        export = await self.export_repository.get_by_id(export_id, user_id=user_id)
        if not export or not export.file_path:
            raise ExportNotFound(str(export_id))
        
        if not export.file_size:
            raise ExportNotFound(str(export_id))
        
        return export.file_path, export.file_size, export.created_at

