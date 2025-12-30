"""Repository for Reports & Analytics data aggregation.

Based on F12A_api_spec.md - Aggregates data from operational domains (F-005 through F-011).
This is a read-only repository that queries data from other modules.
"""

from typing import Optional, Any
from uuid import UUID
from datetime import date, datetime, timezone, timedelta
import re
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Import models from other modules
from src.attendance.models import Attendance
from src.leaves.models import LeaveRequest
from src.employees.models import Employee
from src.tasks.models import Task
from src.projects.models import Project
from src.audits.models import AuditLog
from src.users.models import User
from src.salaries.models import SalaryDetails
from src.reports.models import Export


class ReportRepository:
    """Repository for report data aggregation.
    
    This repository aggregates data from multiple operational domains:
    - F-005: Employee Management (employees)
    - F-006: Salary & History Management (salaries)
    - F-007: Project Management (projects)
    - F-008: Task Management (tasks)
    - F-009: Leave Management (leaves)
    - F-010: Attendance Management (attendance)
    - F-011: Audit Logging (audits)
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ========================================================================
    # ATTENDANCE Report Methods
    # ========================================================================
    
    async def get_attendance_data(
        self,
        company_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        employee_id: Optional[UUID] = None,
        department: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "date",
        sort_order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """Get attendance report data with filters and pagination.
        
        Returns tuple of (rows, total_count).
        """
        # Base query with eager loading
        # Eager load employee and employee.user for name access
        query = (
            select(Attendance)
            .options(
                selectinload(Attendance.employee).selectinload(Employee.user)
            )
            .where(Attendance.company_id == company_id)
        )
        
        # Apply filters
        if start_date:
            query = query.where(Attendance.attendance_date >= start_date)
        if end_date:
            query = query.where(Attendance.attendance_date <= end_date)
        if employee_id:
            query = query.where(Attendance.employee_id == employee_id)
        if status:
            # Map report status to attendance status
            # Report status: PRESENT, ABSENT, LATE, HALF_DAY
            # Attendance status: CHECKED_OUT, NOT_STARTED, etc.
            # This mapping needs to be implemented based on actual attendance status values
            pass
        
        # Apply department filter (via employee relationship)
        if department:
            query = query.join(Employee).where(Employee.department == department)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0
        
        # Apply sorting
        if sort_by == "date":
            order_by = Attendance.attendance_date.desc() if sort_order == "desc" else Attendance.attendance_date.asc()
        elif sort_by == "employee_name":
            # Need to join with Employee and User for sorting by name
            query = query.join(Employee).join(User, Employee.user_id == User.id)
            order_by = User.first_name.desc() if sort_order == "desc" else User.first_name.asc()
        else:
            order_by = Attendance.created_at.desc() if sort_order == "desc" else Attendance.created_at.asc()
        
        query = query.order_by(order_by)
        
        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await self.session.execute(query)
        attendances = result.scalars().all()
        
        # Transform to report format
        rows = []
        for att in attendances:
            employee = att.employee
            # Employee name comes from User model (employee.user.first_name, employee.user.last_name)
            if employee and employee.user:
                employee_name = f"{employee.user.first_name or ''} {employee.user.last_name or ''}".strip()
                if not employee_name:
                    employee_name = "Unknown"
            else:
                employee_name = "Unknown"
            
            # Parse worked_time string (e.g., "9h 29m") to hours as float
            hours_worked = 0.0
            if att.worked_time:
                # Parse format like "9h 29m" or "8h" or "30m"
                hours_match = re.search(r'(\d+)h', att.worked_time)
                minutes_match = re.search(r'(\d+)m', att.worked_time)
                hours = float(hours_match.group(1)) if hours_match else 0.0
                minutes = float(minutes_match.group(1)) if minutes_match else 0.0
                hours_worked = hours + (minutes / 60.0)
            
            rows.append({
                "employee_id": str(att.employee_id),
                "employee_name": employee_name,
                "date": att.attendance_date.isoformat() if att.attendance_date else None,
                "status": self._map_attendance_status(att.status),
                "check_in_time": att.check_in_time.isoformat() if att.check_in_time else None,
                "check_out_time": att.check_out_time.isoformat() if att.check_out_time else None,
                "hours_worked": hours_worked,
            })
        
        return rows, total
    
    async def get_attendance_totals(
        self,
        company_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        employee_id: Optional[UUID] = None,
        department: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get attendance report totals/aggregates."""
        # This will be implemented to calculate totals
        # For now, return placeholder
        return {
            "total_employees": 0,
            "total_present": 0,
            "total_absent": 0,
            "total_late": 0,
            "total_hours": 0.0,
        }
    
    def _map_attendance_status(self, attendance_status: str) -> str:
        """Map attendance status to report status format."""
        # This mapping needs to be implemented based on actual attendance status values
        # Report expects: PRESENT, ABSENT, LATE, HALF_DAY
        # Attendance model may have different status values
        status_map = {
            "CHECKED_OUT": "PRESENT",
            "NOT_STARTED": "ABSENT",
            # Add more mappings as needed
        }
        return status_map.get(attendance_status, attendance_status)
    
    # ========================================================================
    # Placeholder methods for other report types
    # These will be implemented step by step
    # ========================================================================
    
    async def get_leave_data(
        self,
        company_id: Optional[UUID],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        employee_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "applied_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """Get leave report data."""
        # TODO: Implement leave data aggregation
        return [], 0
    
    async def get_leave_totals(
        self,
        company_id: Optional[UUID],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        employee_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get leave report totals."""
        # TODO: Implement leave totals
        return {}
    
    async def get_salary_summary_totals(
        self,
        company_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """Get salary summary report totals (company-total only)."""
        # TODO: Implement salary summary aggregation
        return {}
    
    async def get_employee_data(
        self,
        company_id: UUID,
        department: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "employee_name",
        sort_order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """Get employee report data."""
        # TODO: Implement employee data aggregation
        return [], 0
    
    async def get_employee_totals(
        self,
        company_id: UUID,
        department: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get employee report totals."""
        # TODO: Implement employee totals
        return {}
    
    async def get_task_data(
        self,
        company_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        employee_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        department: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "task_name",
        sort_order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """Get task report data."""
        # TODO: Implement task data aggregation
        return [], 0
    
    async def get_task_totals(
        self,
        company_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        employee_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        department: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get task report totals."""
        # TODO: Implement task totals
        return {}
    
    async def get_project_data(
        self,
        company_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        department: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "project_name",
        sort_order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """Get project report data."""
        # TODO: Implement project data aggregation
        return [], 0
    
    async def get_project_totals(
        self,
        company_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        department: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get project report totals."""
        # TODO: Implement project totals
        return {}
    
    async def get_audit_data(
        self,
        company_id: Optional[UUID],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """Get audit summary report data."""
        # TODO: Implement audit data aggregation
        return [], 0
    
    async def get_audit_totals(
        self,
        company_id: Optional[UUID],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get audit summary report totals."""
        # TODO: Implement audit totals
        return {}
    
    # ========================================================================
    # Filter Options Methods (for metadata)
    # ========================================================================
    
    async def get_available_departments(self, company_id: UUID) -> list[str]:
        """Get list of available departments for filtering."""
        query = (
            select(Employee.department)
            .where(
                Employee.company_id == company_id,
                Employee.is_deleted == False,
                Employee.department.isnot(None),
            )
            .distinct()
        )
        result = await self.session.execute(query)
        return [dept for dept in result.scalars().all() if dept]
    
    async def get_available_employees(
        self,
        company_id: UUID,
        employee_id: Optional[UUID] = None,  # For role-based filtering
    ) -> list[dict[str, Any]]:
        """Get list of available employees for filtering (role-restricted)."""
        query = (
            select(Employee)
            .options(selectinload(Employee.user))
            .where(
                Employee.company_id == company_id,
                Employee.is_deleted == False,
            )
        )
        
        # Role-based filtering: if employee_id provided, only return that employee
        if employee_id:
            query = query.where(Employee.id == employee_id)
        
        result = await self.session.execute(query)
        employees = result.scalars().all()
        
        return [
            {
                "employee_id": str(emp.id),
                "name": f"{emp.user.first_name or ''} {emp.user.last_name or ''}".strip() if emp.user else "Unknown",
            }
            for emp in employees
        ]
    
    async def get_available_projects(self, company_id: UUID) -> list[dict[str, Any]]:
        """Get list of available projects for filtering."""
        query = (
            select(Project)
            .where(
                Project.company_id == company_id,
                Project.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        projects = result.scalars().all()
        
        return [
            {
                "project_id": str(proj.id),
                "name": proj.name,
            }
            for proj in projects
        ]


# ============================================================================
# Export Repository (F12B_api_spec.md)
# ============================================================================

class ExportRepository:
    """Repository for export operations.
    
    Based on F12B_api_spec.md - Export resource CRUD operations.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: UUID,
        company_id: UUID,
        report_type: str,
        expires_at: datetime,
        filters: Optional[dict] = None,
    ) -> Export:
        """Create a new export request.
        
        Args:
            user_id: User who created the export
            company_id: Company ID (tenant boundary)
            report_type: Report type code
            expires_at: Expiration timestamp (24 hours from creation)
            filters: Filter snapshot (JSON dict)
        
        Returns:
            Created Export model instance
        """
        export = Export(
            user_id=user_id,
            company_id=company_id,
            report_type=report_type,
            filters=filters,
            status="PENDING",
            expires_at=expires_at,
        )
        self.session.add(export)
        await self.session.commit()
        await self.session.refresh(export)
        return export
    
    async def get_by_id(
        self,
        export_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Export]:
        """Get export by ID with eager loading.
        
        Args:
            export_id: Export ID
            user_id: Optional user ID for ownership check
        
        Returns:
            Export model instance or None if not found
        """
        query = (
            select(Export)
            .options(
                selectinload(Export.user),
                selectinload(Export.company),
            )
            .where(Export.id == export_id)
        )
        
        # Optional: Filter by user_id for ownership check
        if user_id:
            query = query.where(Export.user_id == user_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        export_id: UUID,
        status: str,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        failed_at: Optional[datetime] = None,
    ) -> Export:
        """Update export status and related fields.
        
        Args:
            export_id: Export ID
            status: New status (PROCESSING, COMPLETED, FAILED, EXPIRED)
            file_path: File path for completed exports
            file_size: File size in bytes for completed exports
            error_message: Error message for failed exports
            completed_at: Completion timestamp
            failed_at: Failure timestamp
        
        Returns:
            Updated Export model instance
        """
        export = await self.get_by_id(export_id)
        if not export:
            raise ValueError(f"Export {export_id} not found")
        
        export.status = status
        if file_path:
            export.file_path = file_path
        if file_size is not None:
            export.file_size = file_size
        if error_message:
            export.error_message = error_message
        if completed_at:
            export.completed_at = completed_at
        if failed_at:
            export.failed_at = failed_at
        
        await self.session.commit()
        await self.session.refresh(export)
        return export
    
    async def mark_expired(self, export_id: UUID) -> Export:
        """Mark export as expired.
        
        Args:
            export_id: Export ID
        
        Returns:
            Updated Export model instance
        """
        return await self.update_status(export_id, "EXPIRED")
    
    async def check_expired(self) -> list[Export]:
        """Get all expired exports (for cleanup job).
        
        Returns:
            List of expired Export instances
        """
        now = datetime.now(timezone.utc)
        query = (
            select(Export)
            .where(
                Export.expires_at < now,
                Export.status != "EXPIRED",
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

