"""Business logic for Attendance Management module.

Service layer - all business logic, validation, and orchestration.
Based on F10_api_spec.md - Attendance Management (F-010).
"""

from uuid import UUID
from typing import Optional
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from fastapi.responses import Response as FastAPIResponse
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

from src.attendance.repository import AttendanceRepository
from src.attendance.utils import generate_etag, format_last_modified
from src.attendance.schemas import (
    CheckInRequest,
    CheckOutRequest,
    AttendanceHistoryQuery,
    CompanyAttendanceListQuery,
    AttendanceRead,
    AttendanceSummary,
    AttendanceContext,
    AttendanceTodayResponse,
    AttendanceLogRead,
    EmployeeSummary,
    CompanyAttendanceSummary,
    AttendanceDetailResponse,
    AttendancePaginatedResponse,
    CompanyAttendancePaginatedResponse,
)
from src.attendance.models import Attendance, AttendanceLog
from src.attendance.exceptions import (
    AttendanceNotFound,
    EmployeeNotFound,
    AlreadyCheckedOut,
    CheckOutWithoutCheckIn,
    FutureDateCheckIn,
    FutureDateCheckOut,
    ManagerScopeViolation,
)
from src.attendance.constants import (
    STATUS_NOT_STARTED,
    STATUS_CHECKED_IN,
    STATUS_CHECKED_OUT,
    ACTION_TYPE_CHECK_IN,
    ACTION_TYPE_CHECK_OUT,
    ACTION_TYPE_AUTO_CHECK_OUT,
)
from src.employees.repository import EmployeeRepository
from src.employees.models import Employee


class AttendanceService:
    """Service for attendance management business logic.
    
    Based on F10_api_spec.md - All business rules in service layer.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = AttendanceRepository(session)
        self.employee_repository = EmployeeRepository(session)

    def _get_employee_timezone(self, employee: Employee) -> str:
        """Get employee timezone.
        
        Based on F10_api_spec.md Section 2.3 - Timezone Standard.
        Employee timezone is used for determining local calendar date.
        
        Note: If timezone is not stored in Employee model, defaults to UTC.
        TODO: Add timezone field to Employee model if not present.
        """
        # TODO: Get timezone from Employee model when available
        # For now, default to UTC
        return "UTC"

    def _get_local_date(self, utc_datetime: datetime, timezone_str: str) -> date:
        """Convert UTC datetime to local date using employee timezone.
        
        Based on F10_api_spec.md Section 2.3 - Timezone Standard.
        Attendance date is determined using employee's local timezone.
        """
        if not PYTZ_AVAILABLE or timezone_str == "UTC":
            # If pytz is not available or timezone is UTC, use UTC date
            return utc_datetime.date()
        
        try:
            tz = pytz.timezone(timezone_str)
            local_datetime = utc_datetime.astimezone(tz)
            return local_datetime.date()
        except Exception:
            # If timezone is invalid, use UTC
            return utc_datetime.date()

    def _calculate_worked_time(self, check_in_time: datetime, check_out_time: datetime) -> str:
        """Calculate worked time duration between check-in and check-out.
        
        Based on F10_api_spec.md Section 4.3.4 - worked_time format.
        Returns format: "9h 29m" or "0h 15m"
        """
        duration = check_out_time - check_in_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def _format_worked_time(self, hours: int, minutes: int) -> str:
        """Format worked time as string.
        
        Returns format: "9h 29m" or "0h 15m"
        """
        return f"{hours}h {minutes}m"

    async def _get_employee(self, employee_id: UUID, company_id: UUID) -> Employee:
        """Get employee by ID with validation.
        
        Raises EmployeeNotFound if employee doesn't exist or is not in company.
        """
        employee = await self.employee_repository.get_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        return employee

    async def get_today_attendance(
        self,
        employee_id: UUID,
        company_id: UUID,
        user_id: UUID,
        if_none_match: Optional[str] = None,
    ) -> AttendanceTodayResponse | FastAPIResponse:
        """Get today's attendance for authenticated employee.
        
        Based on F10_api_spec.md Section 4.3.1 - GET /v1/attendance/today.
        
        Business Logic:
        - Returns attendance record for today's local date (based on employee timezone)
        - Returns 404 if no attendance record exists for today
        - Includes context with server_time and employee_timezone
        """
        # Get employee to retrieve timezone
        employee = await self._get_employee(employee_id, company_id)
        timezone_str = self._get_employee_timezone(employee)
        
        # Get current server time (UTC)
        server_time = datetime.now(timezone.utc)
        
        # Calculate today's local date using employee timezone
        today_local = self._get_local_date(server_time, timezone_str)
        
        # Get attendance for today
        attendance = await self.repository.get_by_employee_and_date(
            employee_id=employee_id,
            attendance_date=today_local,
            company_id=company_id,
        )
        
        if not attendance:
            raise AttendanceNotFound(
                attendance_id=None,
                message="No attendance record found for today. Please check in to start tracking."
            )
        
        # Generate ETag from updated_at (business logic in service per RULE 19)
        etag = generate_etag(attendance.updated_at)
        
        # Check If-None-Match for cache validation (business logic in service per RULE 19)
        if if_none_match and if_none_match == etag:
            # Return 304 in service (business logic decision per RULE 19)
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Build response
        attendance_read = AttendanceRead.model_validate(attendance)
        context = AttendanceContext(
            server_time=server_time,
            employee_timezone=timezone_str,
        )
        
        result = AttendanceTodayResponse(
            attendance=attendance_read,
            context=context,
        )
        
        # Attach ETag metadata for router to set headers
        result.etag = etag
        result.last_modified = attendance.updated_at
        
        return result

    async def get_attendance_history(
        self,
        employee_id: UUID,
        company_id: UUID,
        query: AttendanceHistoryQuery,
    ) -> AttendancePaginatedResponse:
        """Get paginated attendance history for authenticated employee.
        
        Based on F10_api_spec.md Section 4.3.2 - GET /v1/attendance.
        
        Business Logic:
        - Returns only attendance records for the authenticated employee
        - Supports filtering by date range and status
        - Supports sorting by attendance_date, check_in_time, check_out_time, worked_time
        - Paginates results
        """
        # Parse date filters
        start_date = None
        if query.start_date:
            start_date = datetime.strptime(query.start_date, "%Y-%m-%d").date()
        
        end_date = None
        if query.end_date:
            end_date = datetime.strptime(query.end_date, "%Y-%m-%d").date()
        
        # Get attendance records
        attendances, total = await self.repository.list_by_employee(
            employee_id=employee_id,
            company_id=company_id,
            page=query.page,
            page_size=query.page_size,
            start_date=start_date,
            end_date=end_date,
            status=query.status,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        # Build summaries
        items = [
            AttendanceSummary.model_validate(attendance)
            for attendance in attendances
        ]
        
        # Calculate pagination
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build navigation URLs
        base_path = "/v1/attendance"
        next_page = None
        prev_page = None
        
        if query.page < total_pages:
            next_params = []
            if query.page_size != 20:
                next_params.append(f"page_size={query.page_size}")
            if query.start_date:
                next_params.append(f"start_date={query.start_date}")
            if query.end_date:
                next_params.append(f"end_date={query.end_date}")
            if query.status:
                next_params.append(f"status={query.status}")
            if query.sort_by != "attendance_date":
                next_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                next_params.append(f"sort_order={query.sort_order}")
            next_params.append(f"page={query.page + 1}")
            next_page = f"{base_path}?{'&'.join(next_params)}"
        
        if query.page > 1:
            prev_params = []
            if query.page_size != 20:
                prev_params.append(f"page_size={query.page_size}")
            if query.start_date:
                prev_params.append(f"start_date={query.start_date}")
            if query.end_date:
                prev_params.append(f"end_date={query.end_date}")
            if query.status:
                prev_params.append(f"status={query.status}")
            if query.sort_by != "attendance_date":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"
        
        return AttendancePaginatedResponse(
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def check_in(
        self,
        employee_id: UUID,
        company_id: UUID,
        request: CheckInRequest,
        user_id: UUID,
        ip_address: Optional[str] = None,
    ) -> AttendanceRead:
        """Record employee check-in for current day.
        
        Based on F10_api_spec.md Section 4.3.3 - POST /v1/attendance/check-in.
        
        Business Logic:
        - Only one check-in per day per employee
        - Check-in creates or updates attendance record to CHECKED_IN status
        - If already checked in for today, returns existing attendance record (idempotent)
        - Cannot check in if already checked out for today (returns 409 Conflict)
        - Attendance date is determined using employee's local timezone
        - Server timestamp (UTC) is authoritative for check_in_time
        - Creates AttendanceLog entry with action type CHECK_IN
        """
        # Get employee to retrieve timezone
        employee = await self._get_employee(employee_id, company_id)
        timezone_str = self._get_employee_timezone(employee)
        
        # Get current server time (UTC)
        server_time = datetime.now(timezone.utc)
        
        # Calculate today's local date using employee timezone
        today_local = self._get_local_date(server_time, timezone_str)
        
        # Check if attendance already exists for today
        existing_attendance = await self.repository.get_by_employee_and_date(
            employee_id=employee_id,
            attendance_date=today_local,
            company_id=company_id,
        )
        
        if existing_attendance:
            # Idempotent: If already checked in, return existing record
            if existing_attendance.status == STATUS_CHECKED_IN:
                return AttendanceRead.model_validate(existing_attendance)
            
            # Cannot check in if already checked out
            if existing_attendance.status == STATUS_CHECKED_OUT:
                raise AlreadyCheckedOut()
        
        # Create or update attendance record
        if existing_attendance:
            # Update existing record
            attendance = await self.repository.update(
                attendance_id=existing_attendance.id,
                status=STATUS_CHECKED_IN,
                updated_by=user_id,
            )
            if not attendance:
                raise AttendanceNotFound(str(existing_attendance.id))
        else:
            # Create new record
            attendance = await self.repository.create(
                employee_id=employee_id,
                company_id=company_id,
                attendance_date=today_local,
                check_in_time=server_time,
                status=STATUS_CHECKED_IN,
                created_by=user_id,
            )
        
        # Create attendance log entry
        await self.repository.create_log(
            attendance_id=attendance.id,
            employee_id=employee_id,
            action_type=ACTION_TYPE_CHECK_IN,
            action_time=server_time,
            location=request.location,
            ip_address=ip_address,
            device_info=request.device_info,
            is_auto_action=False,
            created_by=user_id,
        )
        
        return AttendanceRead.model_validate(attendance)

    async def check_out(
        self,
        employee_id: UUID,
        company_id: UUID,
        request: CheckOutRequest,
        user_id: UUID,
        ip_address: Optional[str] = None,
    ) -> AttendanceRead:
        """Record employee check-out for current day.
        
        Based on F10_api_spec.md Section 4.3.4 - POST /v1/attendance/check-out.
        
        Business Logic:
        - Only one check-out per day per employee
        - Check-out requires prior check-in (cannot check out without checking in)
        - Check-out updates attendance record to CHECKED_OUT status
        - If already checked out for today, returns existing attendance record (idempotent)
        - Attendance becomes immutable after CHECKED_OUT status
        - worked_time is calculated as duration between check_in_time and check_out_time
        - Server timestamp (UTC) is authoritative for check_out_time
        - Creates AttendanceLog entry with action type CHECK_OUT
        """
        # Get employee to retrieve timezone
        employee = await self._get_employee(employee_id, company_id)
        timezone_str = self._get_employee_timezone(employee)
        
        # Get current server time (UTC)
        server_time = datetime.now(timezone.utc)
        
        # Calculate today's local date using employee timezone
        today_local = self._get_local_date(server_time, timezone_str)
        
        # Get attendance for today
        attendance = await self.repository.get_by_employee_and_date(
            employee_id=employee_id,
            attendance_date=today_local,
            company_id=company_id,
        )
        
        if not attendance:
            raise CheckOutWithoutCheckIn()
        
        # Idempotent: If already checked out, return existing record
        if attendance.status == STATUS_CHECKED_OUT:
            return AttendanceRead.model_validate(attendance)
        
        # Check if checked in
        if attendance.status != STATUS_CHECKED_IN:
            raise CheckOutWithoutCheckIn()
        
        # Calculate worked time
        if attendance.check_in_time:
            worked_time = self._calculate_worked_time(attendance.check_in_time, server_time)
        else:
            worked_time = "0h 0m"
        
        # Update attendance record
        updated_attendance = await self.repository.update(
            attendance_id=attendance.id,
            check_out_time=server_time,
            status=STATUS_CHECKED_OUT,
            worked_time=worked_time,
            is_auto_check_out=False,
            updated_by=user_id,
        )
        
        if not updated_attendance:
            raise AttendanceNotFound(str(attendance.id))
        
        # Create attendance log entry
        await self.repository.create_log(
            attendance_id=updated_attendance.id,
            employee_id=employee_id,
            action_type=ACTION_TYPE_CHECK_OUT,
            action_time=server_time,
            location=request.location,
            ip_address=ip_address,
            device_info=request.device_info,
            is_auto_action=False,
            created_by=user_id,
        )
        
        return AttendanceRead.model_validate(updated_attendance)

    async def list_company_attendance(
        self,
        company_id: UUID,
        query: CompanyAttendanceListQuery,
        role: str,
        manager_employee_id: Optional[UUID] = None,
    ) -> CompanyAttendancePaginatedResponse:
        """Get paginated attendance records list with filters (Manager/HR/CEO only).
        
        Based on F10_api_spec.md Section 4.3.5 - GET /v1/company/attendance.
        
        Business Logic:
        - Manager: Can view attendance for all employees in their scope
        - HR/CEO: Full attendance visibility across the company
        - employee_id filter is only available for HR and CEO roles
        - Supports filtering by employee_id, date range, and status
        - Supports sorting by attendance_date, check_in_time, check_out_time, worked_time, employee_name
        - Paginates results
        """
        # Parse date filters
        start_date = None
        if query.start_date:
            start_date = datetime.strptime(query.start_date, "%Y-%m-%d").date()
        
        end_date = None
        if query.end_date:
            end_date = datetime.strptime(query.end_date, "%Y-%m-%d").date()
        
        # Parse employee_id filter (HR/CEO only)
        employee_id = None
        if query.employee_id:
            role_lower = role.lower() if role else ""
            if role_lower not in ["hr", "ceo"]:
                # Manager cannot filter by employee_id
                employee_id = None
            else:
                try:
                    employee_id = UUID(query.employee_id)
                except ValueError:
                    employee_id = None
        
        # Get attendance records
        attendances, total = await self.repository.list_by_company(
            company_id=company_id,
            page=query.page,
            page_size=query.page_size,
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            status=query.status,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        # Build summaries with employee information
        items = []
        for attendance in attendances:
            # Eager loading ensures employee and user are available
            employee = attendance.employee
            user = employee.user if hasattr(employee, 'user') else None
            
            if not user:
                # Skip if user is not available (should not happen with eager loading)
                continue
            
            employee_summary = EmployeeSummary(
                id=employee.id,
                first_name=user.first_name if hasattr(user, 'first_name') else "",
                last_name=user.last_name if hasattr(user, 'last_name') else "",
            )
            
            items.append(
                CompanyAttendanceSummary(
                    id=attendance.id,
                    employee=employee_summary,
                    attendance_date=attendance.attendance_date,
                    status=attendance.status,
                    worked_time=attendance.worked_time,
                    is_auto_check_out=attendance.is_auto_check_out,
                )
            )
        
        # Calculate pagination
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build navigation URLs
        base_path = "/v1/company/attendance"
        next_page = None
        prev_page = None
        
        if query.page < total_pages:
            next_params = []
            if query.page_size != 20:
                next_params.append(f"page_size={query.page_size}")
            if query.employee_id:
                next_params.append(f"employee_id={query.employee_id}")
            if query.start_date:
                next_params.append(f"start_date={query.start_date}")
            if query.end_date:
                next_params.append(f"end_date={query.end_date}")
            if query.status:
                next_params.append(f"status={query.status}")
            if query.sort_by != "attendance_date":
                next_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                next_params.append(f"sort_order={query.sort_order}")
            next_params.append(f"page={query.page + 1}")
            next_page = f"{base_path}?{'&'.join(next_params)}"
        
        if query.page > 1:
            prev_params = []
            if query.page_size != 20:
                prev_params.append(f"page_size={query.page_size}")
            if query.employee_id:
                prev_params.append(f"employee_id={query.employee_id}")
            if query.start_date:
                prev_params.append(f"start_date={query.start_date}")
            if query.end_date:
                prev_params.append(f"end_date={query.end_date}")
            if query.status:
                prev_params.append(f"status={query.status}")
            if query.sort_by != "attendance_date":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"
        
        return CompanyAttendancePaginatedResponse(
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def get_attendance_detail(
        self,
        employee_id: UUID,
        attendance_date: date,
        company_id: UUID,
        role: str,
        manager_employee_id: Optional[UUID] = None,
        if_none_match: Optional[str] = None,
    ) -> AttendanceDetailResponse | FastAPIResponse:
        """Get detailed attendance for specific employee and date (Manager/HR/CEO only).
        
        Based on F10_api_spec.md Section 4.3.6 - GET /v1/company/attendance/{employee_id}/{date}.
        
        Business Logic:
        - Manager: Can view attendance for employees in their scope
        - HR/CEO: Full attendance visibility across the company
        - Returns attendance record with employee information and logs
        - Logs are returned in chronological order (oldest first)
        - Date resolution respects employee's local timezone
        """
        # Get employee
        employee = await self._get_employee(employee_id, company_id)
        
        # Get attendance record
        attendance = await self.repository.get_by_employee_and_date(
            employee_id=employee_id,
            attendance_date=attendance_date,
            company_id=company_id,
        )
        
        if not attendance:
            raise AttendanceNotFound(
                attendance_id=None,
                message="No attendance record found for employee and date."
            )
        
        # Generate ETag from updated_at (business logic in service per RULE 19)
        etag = generate_etag(attendance.updated_at)
        
        # Check If-None-Match for cache validation (business logic in service per RULE 19)
        if if_none_match and if_none_match == etag:
            # Return 304 in service (business logic decision per RULE 19)
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Get employee information
        user = employee.user if hasattr(employee, 'user') else None
        if not user:
            raise EmployeeNotFound(str(employee_id))
        
        employee_summary = EmployeeSummary(
            id=employee.id,
            first_name=user.first_name if hasattr(user, 'first_name') else "",
            last_name=user.last_name if hasattr(user, 'last_name') else "",
        )
        
        # Get attendance logs
        logs = await self.repository.get_logs_by_attendance_id(attendance.id)
        log_reads = [AttendanceLogRead.model_validate(log) for log in logs]
        
        # Build response
        attendance_read = AttendanceRead.model_validate(attendance)
        
        result = AttendanceDetailResponse(
            attendance=attendance_read,
            employee=employee_summary,
            logs=log_reads,
        )
        
        # Attach ETag metadata for router to set headers
        result.etag = etag
        result.last_modified = attendance.updated_at
        
        return result
