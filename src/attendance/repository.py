"""Database operations for Attendance Management module.

Repository layer - pure database operations only, no business logic.
All methods use eager loading for relationships to prevent MissingGreenlet errors.
All methods filter by is_deleted = False for soft-delete support.
"""

from uuid import UUID
from typing import Optional
from datetime import date, datetime
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.attendance.models import Attendance, AttendanceLog
from src.employees.models import Employee


class AttendanceRepository:
    """Repository for attendance database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, attendance_id: UUID, company_id: Optional[UUID] = None
    ) -> Optional[Attendance]:
        """Get attendance by ID with eager loading of relationships.
        
        Eager loads:
        - employee (Employee)
        - company (Company)
        - attendance_logs (list[AttendanceLog])
        
        Filters:
        - is_deleted = False (exclude soft-deleted)
        - Optional: company_id filter (for multi-tenant isolation)
        """
        query = (
            select(Attendance)
            .options(
                selectinload(Attendance.employee).selectinload(Employee.user),  # CRITICAL: Eager load employee and user
                selectinload(Attendance.company),  # CRITICAL: Eager load company
                selectinload(Attendance.attendance_logs),  # CRITICAL: Eager load logs
            )
            .where(
                Attendance.id == attendance_id,
                Attendance.is_deleted == False,
            )
        )
        
        if company_id is not None:
            query = query.where(Attendance.company_id == company_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_employee_and_date(
        self, employee_id: UUID, attendance_date: date, company_id: Optional[UUID] = None
    ) -> Optional[Attendance]:
        """Get attendance by employee ID and date with eager loading.
        
        Eager loads:
        - employee (Employee) with user relationship
        - company (Company)
        - attendance_logs (list[AttendanceLog])
        
        Filters:
        - is_deleted = False (exclude soft-deleted)
        - employee_id (required)
        - attendance_date (required)
        - Optional: company_id filter (for multi-tenant isolation)
        """
        query = (
            select(Attendance)
            .options(
                selectinload(Attendance.employee).selectinload(Employee.user),  # CRITICAL: Eager load employee and user
                selectinload(Attendance.company),  # CRITICAL: Eager load company
                selectinload(Attendance.attendance_logs),  # CRITICAL: Eager load logs
            )
            .where(
                Attendance.employee_id == employee_id,
                Attendance.attendance_date == attendance_date,
                Attendance.is_deleted == False,
            )
        )
        
        if company_id is not None:
            query = query.where(Attendance.company_id == company_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_employee(
        self,
        employee_id: UUID,
        company_id: UUID,
        page: int,
        page_size: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        sort_by: str = "attendance_date",
        sort_order: str = "desc",
    ) -> tuple[list[Attendance], int]:
        """List attendance records for an employee with pagination, filtering, and sorting.
        
        Eager loads:
        - employee (Employee) with user relationship
        - company (Company)
        
        Filters:
        - is_deleted = False (exclude soft-deleted)
        - employee_id (required)
        - company_id (required for multi-tenant isolation)
        - Optional: start_date filter
        - Optional: end_date filter
        - Optional: status filter (exact match, case-sensitive)
        
        Sorting:
        - sort_by: attendance_date, check_in_time, check_out_time, worked_time
        - sort_order: asc, desc
        """
        # Build base query with required filters and eager loading
        query = (
            select(Attendance)
            .options(
                selectinload(Attendance.employee).selectinload(Employee.user),  # CRITICAL: Eager load employee and user
                selectinload(Attendance.company),  # CRITICAL: Eager load company
            )
            .where(
                Attendance.employee_id == employee_id,
                Attendance.company_id == company_id,
                Attendance.is_deleted == False,
            )
        )

        # Apply optional filters
        if start_date is not None:
            query = query.where(Attendance.attendance_date >= start_date)
        
        if end_date is not None:
            query = query.where(Attendance.attendance_date <= end_date)
        
        if status is not None:
            query = query.where(Attendance.status == status)

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = None
        if sort_by == "attendance_date":
            sort_column = Attendance.attendance_date
        elif sort_by == "check_in_time":
            sort_column = Attendance.check_in_time
        elif sort_by == "check_out_time":
            sort_column = Attendance.check_out_time
        elif sort_by == "worked_time":
            # Note: worked_time is a string field, sorting may not be ideal
            # Default to attendance_date for worked_time sorting
            sort_column = Attendance.attendance_date
        else:
            # Default to attendance_date if invalid sort_by
            sort_column = Attendance.attendance_date

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

    async def list_by_company(
        self,
        company_id: UUID,
        page: int,
        page_size: int,
        employee_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        sort_by: str = "attendance_date",
        sort_order: str = "desc",
    ) -> tuple[list[Attendance], int]:
        """List attendance records for a company with pagination, filtering, and sorting.
        
        Eager loads:
        - employee (Employee) with user relationship
        - company (Company)
        
        Filters:
        - is_deleted = False (exclude soft-deleted)
        - company_id (required for multi-tenant isolation)
        - Optional: employee_id filter
        - Optional: start_date filter
        - Optional: end_date filter
        - Optional: status filter (exact match, case-sensitive)
        
        Sorting:
        - sort_by: attendance_date, check_in_time, check_out_time, worked_time, employee_name
        - sort_order: asc, desc
        
        Note: employee_name sorting requires join with employee and user tables.
        """
        # Build base query with required filters and eager loading
        query = (
            select(Attendance)
            .options(
                selectinload(Attendance.employee).selectinload(Employee.user),  # CRITICAL: Eager load employee and user
                selectinload(Attendance.company),  # CRITICAL: Eager load company
            )
            .where(
                Attendance.company_id == company_id,
                Attendance.is_deleted == False,
            )
        )

        # Apply optional filters
        if employee_id is not None:
            query = query.where(Attendance.employee_id == employee_id)
        
        if start_date is not None:
            query = query.where(Attendance.attendance_date >= start_date)
        
        if end_date is not None:
            query = query.where(Attendance.attendance_date <= end_date)
        
        if status is not None:
            query = query.where(Attendance.status == status)

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = None
        if sort_by == "attendance_date":
            sort_column = Attendance.attendance_date
        elif sort_by == "check_in_time":
            sort_column = Attendance.check_in_time
        elif sort_by == "check_out_time":
            sort_column = Attendance.check_out_time
        elif sort_by == "worked_time":
            # Note: worked_time is a string field, sorting may not be ideal
            # Default to attendance_date for worked_time sorting
            sort_column = Attendance.attendance_date
        elif sort_by == "employee_name":
            # Note: employee_name sorting requires join with employee and user tables
            # For now, default to attendance_date
            # TODO: Implement proper join-based sorting when needed
            sort_column = Attendance.attendance_date
        else:
            # Default to attendance_date if invalid sort_by
            sort_column = Attendance.attendance_date

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
        employee_id: UUID,
        company_id: UUID,
        attendance_date: date,
        check_in_time: datetime,
        status: str,
        created_by: Optional[UUID] = None,
    ) -> Attendance:
        """Create a new attendance record.
        
        Pure database operation - no business logic.
        """
        attendance = Attendance(
            employee_id=employee_id,
            company_id=company_id,
            attendance_date=attendance_date,
            check_in_time=check_in_time,
            status=status,
            created_by=created_by,
            updated_by=created_by,
        )
        self.session.add(attendance)
        await self.session.commit()
        await self.session.refresh(attendance)
        
        # Eager load relationships
        await self.session.execute(
            select(Attendance)
            .options(
                selectinload(Attendance.employee).selectinload(Employee.user),
                selectinload(Attendance.company),
                selectinload(Attendance.attendance_logs),
            )
            .where(Attendance.id == attendance.id)
        )
        await self.session.refresh(attendance)
        
        return attendance

    async def update(
        self,
        attendance_id: UUID,
        check_out_time: Optional[datetime] = None,
        status: Optional[str] = None,
        worked_time: Optional[str] = None,
        is_auto_check_out: Optional[bool] = None,
        updated_by: Optional[UUID] = None,
    ) -> Optional[Attendance]:
        """Update attendance fields.
        
        Pure database operation - no business logic.
        Updates only provided fields.
        """
        attendance = await self.get_by_id(attendance_id)
        if not attendance:
            return None
        
        if check_out_time is not None:
            attendance.check_out_time = check_out_time
        if status is not None:
            attendance.status = status
        if worked_time is not None:
            attendance.worked_time = worked_time
        if is_auto_check_out is not None:
            attendance.is_auto_check_out = is_auto_check_out
        if updated_by is not None:
            attendance.updated_by = updated_by
        
        await self.session.commit()
        await self.session.refresh(attendance)
        
        # Eager load relationships
        await self.session.execute(
            select(Attendance)
            .options(
                selectinload(Attendance.employee).selectinload(Employee.user),
                selectinload(Attendance.company),
                selectinload(Attendance.attendance_logs),
            )
            .where(Attendance.id == attendance.id)
        )
        await self.session.refresh(attendance)
        
        return attendance

    async def create_log(
        self,
        attendance_id: UUID,
        employee_id: UUID,
        action_type: str,
        action_time: datetime,
        location: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
        notes: Optional[str] = None,
        is_auto_action: bool = False,
        created_by: Optional[UUID] = None,
    ) -> AttendanceLog:
        """Create a new attendance log entry.
        
        Pure database operation - no business logic.
        """
        log = AttendanceLog(
            attendance_id=attendance_id,
            employee_id=employee_id,
            action_type=action_type,
            action_time=action_time,
            location=location,
            ip_address=ip_address,
            device_info=device_info,
            notes=notes,
            is_auto_action=is_auto_action,
            created_by=created_by,
            updated_by=created_by,
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        
        return log

    async def get_logs_by_attendance_id(
        self, attendance_id: UUID
    ) -> list[AttendanceLog]:
        """Get all attendance logs for an attendance record.
        
        Returns logs in chronological order (oldest first).
        
        Filters:
        - is_deleted = False (exclude soft-deleted)
        - attendance_id (required)
        """
        query = (
            select(AttendanceLog)
            .where(
                AttendanceLog.attendance_id == attendance_id,
                AttendanceLog.is_deleted == False,
            )
            .order_by(asc(AttendanceLog.action_time))  # Chronological order (oldest first)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
