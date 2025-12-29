"""API documentation for Attendance Management endpoints.

Based on F10_api_spec.md Section 4 - Resources & Endpoints.
Centralized Swagger/OpenAPI documentation for all attendance endpoints.
"""

from typing import ClassVar


class AttendanceApiDocs:
    """API documentation for Attendance endpoints."""
    
    get_today: ClassVar[dict] = {
        "summary": "Get today's attendance data for the authenticated employee",
        "description": "Returns today's attendance record for the authenticated employee (only for today's local date). Includes attendance data and context (server_time, employee_timezone). Returns 404 if no attendance record exists for today. Only Employee, Manager, HR, CEO can access. SuperAdmin and deactivated employees are explicitly excluded."
    }
    
    get_history: ClassVar[dict] = {
        "summary": "Get paginated attendance history for the authenticated employee",
        "description": "Returns paginated attendance history for the authenticated employee (own records only). Supports filtering by date range and status, sorting by attendance_date, check_in_time, check_out_time, worked_time. Only Employee, Manager, HR, CEO can access. SuperAdmin and deactivated employees are explicitly excluded."
    }
    
    check_in: ClassVar[dict] = {
        "summary": "Record employee check-in for the current day",
        "description": "Records employee check-in for the current day. Only one check-in per day per employee. If already checked in for today, returns existing attendance record (idempotent). Cannot check in if already checked out for today (returns 409 Conflict). Attendance date is determined using employee's local timezone. Server timestamp (UTC) is authoritative for check_in_time. Creates AttendanceLog entry with action type CHECK_IN. Only Employee, Manager, HR, CEO can access. SuperAdmin and deactivated employees are explicitly excluded."
    }
    
    check_out: ClassVar[dict] = {
        "summary": "Record employee check-out for the current day",
        "description": "Records employee check-out for the current day. Only one check-out per day per employee. Check-out requires prior check-in (cannot check out without checking in). If already checked out for today, returns existing attendance record (idempotent). Attendance becomes immutable after CHECKED_OUT status. worked_time is calculated as duration between check_in_time and check_out_time. Server timestamp (UTC) is authoritative for check_out_time. Creates AttendanceLog entry with action type CHECK_OUT. Only Employee, Manager, HR, CEO can access. SuperAdmin and deactivated employees are explicitly excluded."
    }
    
    list_company: ClassVar[dict] = {
        "summary": "Get paginated attendance records list with filters (Manager/HR/CEO only)",
        "description": "Returns paginated attendance records list with filters. Manager: Can view attendance for all employees in their scope. HR/CEO: Full attendance visibility across the company. employee_id filter is only available for HR and CEO roles. Supports filtering by employee_id, date range, and status. Supports sorting by attendance_date, check_in_time, check_out_time, worked_time, employee_name. Only Manager, HR, CEO can access. SuperAdmin, Employee, and deactivated employees are explicitly excluded."
    }
    
    get_detail: ClassVar[dict] = {
        "summary": "Get detailed attendance for specific employee and date (Manager/HR/CEO only)",
        "description": "Returns detailed attendance record for specific employee and date. Includes attendance data, employee information, and attendance logs in chronological order. Manager: Can view attendance for employees in their scope. HR/CEO: Full attendance visibility across the company. Date resolution respects employee's local timezone. Only Manager, HR, CEO can access. SuperAdmin, Employee, and deactivated employees are explicitly excluded."
    }
