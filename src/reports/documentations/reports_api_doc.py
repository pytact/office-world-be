"""API documentation for Reports & Analytics endpoints.

Based on F12A_api_spec.md - Swagger/OpenAPI documentation (Part A: Core Reporting).
Based on F12B_api_spec.md - Swagger/OpenAPI documentation (Part B: Export Functionality).
"""

from typing import ClassVar


class ReportsApiDocs:
    """API documentation for Reports & Analytics endpoints."""
    
    list_reports: ClassVar[dict] = {
        "summary": "List accessible report types based on user role",
        "description": "Returns all report types accessible to the authenticated user's role. Report types are filtered server-side based on role-based access control. CEO and HR can access all report types. Manager can access ATTENDANCE, PROJECT, and TASK reports. Employee can access ATTENDANCE, LEAVE, and TASK reports (self-scoped). SuperAdmin has no access to reports (empty list returned - blocked by BR-1203).",
    }
    
    get_report: ClassVar[dict] = {
        "summary": "Get report data with optional filters",
        "description": "Retrieves report data for the specified report type with optional filters, pagination, and sorting. Includes filter options in metadata response. Supports role-based access control and filter scope restrictions. Employees can only filter by their own data. Managers can filter within their company. HR and CEO can filter across entire company. SuperAdmin has no access (403 Forbidden - blocked by BR-1203). List-style reports (ATTENDANCE, LEAVE, TASK, PROJECT, EMPLOYEE, AUDIT_SUMMARY) support pagination. Aggregate reports (SALARY_SUMMARY) return single aggregate object without pagination.",
    }
    
    # Export Endpoints (F12B_api_spec.md)
    create_export: ClassVar[dict] = {
        "summary": "Create an asynchronous PDF export of a report view with applied filters",
        "description": "Creates an asynchronous PDF export request for the specified report type with optional filters. Export is generated asynchronously (non-blocking) and has a 24-hour time-to-live (TTL). Export access follows the same role-based rules as report views. CEO and HR can export all report types. Manager can export ATTENDANCE, PROJECT, and TASK reports. Employee can export ATTENDANCE, LEAVE, and TASK reports (self-scoped). SuperAdmin has no access (403 Forbidden). Export filters must respect the same role-based scope restrictions as report views. Returns export_id and status for polling. Export artifacts are immutable snapshots that do not update when underlying data changes.",
    }
    
    get_export_status: ClassVar[dict] = {
        "summary": "Check export status (polling endpoint for async export processing)",
        "description": "Retrieves the current status of an export request. Used for polling to check when export generation is complete. Returns export status (PENDING, PROCESSING, COMPLETED, FAILED, EXPIRED), timestamps, and download URL if completed. User must own the export or have admin access to the report type. Export must not be expired (410 Gone if expired). Status transitions: PENDING → PROCESSING → COMPLETED (or FAILED). Exports expire after 24 hours from creation.",
    }
    
    download_export: ClassVar[dict] = {
        "summary": "Download generated PDF export",
        "description": "Downloads the generated PDF export file. Export must be in COMPLETED status (422 Unprocessable Entity if not ready). Export must not be expired (410 Gone if expired). User must own the export or have admin access to the report type. Returns PDF file with Content-Type: application/pdf and Content-Disposition header. Filename format: report_{report_type}_{date}.pdf. Export artifacts are immutable snapshots that do not update when underlying data changes.",
    }

