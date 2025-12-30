"""FastAPI endpoints for Reports & Analytics.

Based on F12A_api_spec.md - Reports & Analytics (F-012 Part A: Core Reporting).
Based on F12B_api_spec.md - Export functionality (F-012 Part B).
"""

from uuid import UUID
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, status, Response
from fastapi.responses import FileResponse
from src.schemas import StandardResponse
from src.reports.dependencies import (
    ReportApiDep,
    get_current_user_with_company,
    get_current_user_with_employee,
)
from src.reports.schemas import (
    ReportListQuery,
    ReportViewQuery,
    ReportTypeListResponse,
    ReportViewResponse,
    ExportCreate,
    ExportCreateResponse,
    ExportStatusResponse,
)
from src.reports.documentations.reports_api_doc import ReportsApiDocs
from src.users.models import User

router = APIRouter(
    prefix="/reports",
    tags=["Reports & Analytics"],
)


@router.get(
    "",
    response_model=ReportTypeListResponse,
    status_code=status.HTTP_200_OK,
    summary=ReportsApiDocs.list_reports["summary"],
    description=ReportsApiDocs.list_reports["description"],
)
async def list_reports(
    query: ReportListQuery = Depends(ReportListQuery),
    api: ReportApiDep = Depends(),
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
) -> ReportTypeListResponse:
    """List accessible report types based on user role.
    
    Based on F12A_api_spec.md Section 4.3.1.
    Returns only report types accessible to the authenticated user's role.
    
    Note: This endpoint uses ReportTypeListResponse directly (not StandardResponse)
    because the spec requires available_report_count at root level alongside data and message.
    """
    user, company_id, role = user_company
    
    result = await api.list_report_types(role=role)
    
    # Return ReportTypeListResponse directly (includes data, available_report_count, and message)
    return ReportTypeListResponse(
        data=result.data,
        available_report_count=result.available_report_count,
        message="Report types retrieved successfully" if result.available_report_count > 0 else "No accessible report types found",
    )


@router.get(
    "/{report_type}",
    response_model=StandardResponse[ReportViewResponse],
    status_code=status.HTTP_200_OK,
    summary=ReportsApiDocs.get_report["summary"],
    description=ReportsApiDocs.get_report["description"],
)
async def get_report(
    report_type: str,
    query: ReportViewQuery = Depends(ReportViewQuery),
    api: ReportApiDep = Depends(),
    user_employee: tuple[User, Optional[UUID], str, Optional[UUID]] = Depends(get_current_user_with_employee),
) -> StandardResponse[ReportViewResponse]:
    """Get report data with optional filters.
    
    Based on F12A_api_spec.md Section 4.3.2.
    Supports role-based access control, filtering, pagination, and sorting.
    """
    user, company_id, role, employee_id = user_employee
    
    result = await api.get_report_data(
        report_type=report_type,
        company_id=company_id,
        role=role,
        employee_id=employee_id,
        query=query,
    )
    
    return StandardResponse(
        data=result,
        message="Report data retrieved successfully",
    )


# ============================================================================
# Export Endpoints (F12B_api_spec.md)
# ============================================================================

@router.post(
    "/{report_type}/exports",
    response_model=StandardResponse[ExportCreateResponse],
    status_code=status.HTTP_201_CREATED,
    summary=ReportsApiDocs.create_export["summary"],
    description=ReportsApiDocs.create_export["description"],
)
async def create_export(
    report_type: str,
    data: ExportCreate,
    api: ReportApiDep = Depends(),
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
    response: Response = None,
) -> StandardResponse[ExportCreateResponse]:
    """Create an asynchronous PDF export request.
    
    Based on F12B_api_spec.md Section 4.3.1.
    Creates an export request with applied filters. Export is generated asynchronously.
    """
    user, company_id, role = user_company
    
    result = await api.create_export(
        report_type=report_type,
        user_id=user.id,
        company_id=company_id,
        role=role,
        filters=data.filters,
    )
    
    # Set Location header (RECOMMENDED per spec Section 4.3.1)
    if response:
        response.headers["Location"] = f"/api/v1/reports/{report_type.lower()}/exports/{result.export_id}"
    
    return StandardResponse(
        data=result,
        message="Export request created successfully",
    )


@router.get(
    "/{report_type}/exports/{export_id}",
    response_model=StandardResponse[ExportStatusResponse],
    status_code=status.HTTP_200_OK,
    summary=ReportsApiDocs.get_export_status["summary"],
    description=ReportsApiDocs.get_export_status["description"],
)
async def get_export_status(
    report_type: str,
    export_id: UUID,
    api: ReportApiDep = Depends(),
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
) -> StandardResponse[ExportStatusResponse]:
    """Check export status (polling endpoint for async export processing).
    
    Based on F12B_api_spec.md Section 4.3.2.
    Returns current export status and download URL if completed.
    """
    user, company_id, role = user_company
    
    result = await api.get_export_status(
        export_id=export_id,
        report_type=report_type,
        user_id=user.id,
        role=role,
        company_id=company_id,
    )
    
    # Determine message based on status
    status_messages = {
        "PENDING": "Export is pending",
        "PROCESSING": "Export is being processed",
        "COMPLETED": "Export completed successfully",
        "FAILED": "Export generation failed",
        "EXPIRED": "Export has expired",
    }
    message = status_messages.get(result.status, "Export status retrieved successfully")
    
    return StandardResponse(
        data=result,
        message=message,
    )


@router.get(
    "/{report_type}/exports/{export_id}/download",
    status_code=status.HTTP_200_OK,
    summary=ReportsApiDocs.download_export["summary"],
    description=ReportsApiDocs.download_export["description"],
)
async def download_export(
    report_type: str,
    export_id: UUID,
    api: ReportApiDep = Depends(),
    user_company: tuple[User, Optional[UUID], str] = Depends(get_current_user_with_company),
) -> FileResponse:
    """Download generated PDF export.
    
    Based on F12B_api_spec.md Section 4.3.3.
    Returns PDF file for completed exports only.
    """
    user, company_id, role = user_company
    
    # Get file path, size, and creation date (includes validation and access checks)
    file_path, file_size, created_at = await api.get_export_file_path(
        export_id=export_id,
        report_type=report_type,
        user_id=user.id,
        role=role,
        company_id=company_id,
    )
    
    # Generate filename based on report type and export creation date
    # Format: report_{report_type}_{date}.pdf (spec Section 4.3.3, line 490-493)
    date_str = created_at.date().strftime("%Y-%m-%d")
    filename = f"report_{report_type.lower()}_{date_str}.pdf"
    
    # Return file response with required headers
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(file_size),  # REQUIRED per spec Section 4.3.3, line 465
        },
    )

