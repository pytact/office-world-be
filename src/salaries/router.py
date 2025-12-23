"""FastAPI endpoints for Salary Management module.

Based on F6_api_spec.md - Salary Management (F-006).
All endpoints with proper authentication, authorization, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from fastapi.responses import JSONResponse, Response as FastAPIResponse
from src.schemas import StandardResponse
from src.salaries.schemas import (
    SalaryCreate,
    BankInfoUpsert,
    SalaryPaymentCreate,
    SalaryPaymentRun,
    SalaryPaymentUpdate,
    SalaryOverviewQuery,
    SalaryPaymentListQuery,
    SalaryOverviewResponse,
    SalaryDetailsOnlyResponse,
    SalaryDetailsResponse,
    SalaryHistoryResponse,
    BankInfoResponse,
    SalaryPaymentResponse,
    SalaryPaymentPaginatedResponse,
)
from src.salaries.dependencies import (
    SalaryApiDep,
    get_current_ceo_or_hr,
    get_current_user_with_employee_access,
)
from src.salaries.documentations.salaries_api_doc import SalaryApiDocs
from src.salaries.constants import (
    SUCCESS_SALARY_OVERVIEW_RETRIEVED,
    SUCCESS_ACTIVE_SALARY_RETRIEVED,
    SUCCESS_SALARY_DETAILS_CREATED,
    SUCCESS_SALARY_REVISED,
    SUCCESS_SALARY_HISTORY_RETRIEVED,
    SUCCESS_SALARY_DETAILS_UPDATED,
    SUCCESS_SALARY_DETAILS_DELETED,
    SUCCESS_BANK_INFO_RETRIEVED,
    SUCCESS_BANK_INFO_CREATED,
    SUCCESS_BANK_INFO_UPDATED,
    SUCCESS_BANK_INFO_DELETED,
    SUCCESS_SALARY_PAYMENT_CREATED,
    SUCCESS_SALARY_PAYMENT_UPDATED,
    SUCCESS_SALARY_PAYMENT_DELETED,
    SUCCESS_SALARY_PAYMENTS_RETRIEVED,
)
from src.users.models import User
from src.salaries.utils import format_last_modified
from src.users.utils import generate_request_id

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/company/employees/{employee_id}/salary",
    tags=["Salaries"],
)


# ============================================================================
# Salary Endpoints
# ============================================================================

@router.get(
    "",
    response_model=StandardResponse[SalaryDetailsResponse],
    summary=SalaryApiDocs.get_active_salary["summary"],
    description=SalaryApiDocs.get_active_salary["description"],
)
async def get_active_salary(
    request: Request,
    employee_id: UUID,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryDetailsResponse] | FastAPIResponse:
    """Get active salary for an employee.
    
    Used for:
    - Payroll
    - Employee view
    - Offer confirmation
    
    Based on F6_api_spec.md - GET /v1/company/employees/{employee_id}/salary.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    Returns 404 if no active salary exists.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    # Handle empty strings for If-None-Match
    if_none_match_value = if_none_match if if_none_match and if_none_match.strip() else None
    
    result = await api.get_active_salary(
        employee_id=employee_id,
        company_id=company_id,
        if_none_match=if_none_match_value,
    )
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        if response:
            response.headers["X-Request-ID"] = request_id
        return result
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_ACTIVE_SALARY_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.post(
    "",
    response_model=StandardResponse[SalaryDetailsResponse],
    status_code=status.HTTP_201_CREATED,
    summary=SalaryApiDocs.create_salary["summary"],
    description=SalaryApiDocs.create_salary["description"],
)
async def create_salary(
    request: Request,
    employee_id: UUID,
    data: SalaryCreate,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryDetailsResponse]:
    """Create initial salary.
    
    Based on F6_api_spec.md - POST /v1/company/employees/{employee_id}/salary.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    
    Validations:
    - No active salary exists (returns 409 if active salary exists - use revise endpoint instead)
    - effective_from >= today
    
    Creating First Salary:
    - effective_from = today (or provided date, must be >= today)
    - effective_to = NULL (active)
    - This becomes the employee's current salary
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    result = await api.create_salary(
        employee_id=employee_id,
        company_id=company_id,
        data=data,
        user_id=user.id,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_SALARY_DETAILS_CREATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag header if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    
    return json_response


@router.post(
    "/revise",
    response_model=StandardResponse[SalaryDetailsResponse],
    summary=SalaryApiDocs.revise_salary["summary"],
    description=SalaryApiDocs.revise_salary["description"],
)
async def revise_salary(
    request: Request,
    employee_id: UUID,
    data: SalaryCreate,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryDetailsResponse]:
    """Revise salary (increment/change).
    
    Why separate endpoint?
    Because revise ≠ update.
    
    Backend Logic:
    - Fetch active salary
    - Set effective_to = yesterday
    - Insert new salary record
    
    Based on F6_api_spec.md - POST /v1/company/employees/{employee_id}/salary/revise.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    # Handle empty strings for If-Match
    if_match_value = if_match if if_match and if_match.strip() else None
    
    result = await api.revise_salary(
        employee_id=employee_id,
        company_id=company_id,
        data=data,
        user_id=user.id,
        if_match=if_match_value,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_SALARY_REVISED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag header if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    
    return json_response


@router.get(
    "/history",
    response_model=StandardResponse[list[SalaryHistoryResponse]],
    summary=SalaryApiDocs.get_salary_history["summary"],
    description=SalaryApiDocs.get_salary_history["description"],
)
async def get_salary_history(
    request: Request,
    employee_id: UUID,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[list[SalaryHistoryResponse]]:
    """Get salary history for an employee.
    
    HR / CEO only.
    
    Based on F6_api_spec.md - GET /v1/company/employees/{employee_id}/salary/history.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    result = await api.get_salary_history(
        employee_id=employee_id,
        company_id=company_id,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_SALARY_HISTORY_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    return json_response


@router.get(
    "/bank-info",
    response_model=StandardResponse[BankInfoResponse],
    summary=SalaryApiDocs.get_bank_info["summary"],
    description=SalaryApiDocs.get_bank_info["description"],
)
async def get_bank_info(
    request: Request,
    employee_id: UUID,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[BankInfoResponse] | FastAPIResponse:
    """Get bank information for an employee.
    
    Based on F6_api_spec.md - GET /v1/company/employees/{employee_id}/salary/bank-info.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    result = await api.get_bank_info(
        employee_id=employee_id,
        company_id=company_id,
        if_none_match=if_none_match,
    )
    
    # Check if service returned 304 Not Modified
    if isinstance(result, FastAPIResponse):
        result.headers["X-Request-ID"] = request_id
        return result
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_BANK_INFO_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.post(
    "/bank-info",
    response_model=StandardResponse[BankInfoResponse],
    status_code=status.HTTP_201_CREATED,
    summary=SalaryApiDocs.create_bank_info["summary"],
    description=SalaryApiDocs.create_bank_info["description"],
)
async def create_bank_info(
    request: Request,
    employee_id: UUID,
    data: BankInfoUpsert,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[BankInfoResponse]:
    """Create bank information.
    
    POST /v1/company/employees/{employee_id}/salary/bank-info
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    
    Key Rules:
    1. One bank account per employee (active at a time) - returns 409 if already exists
    2. Never hard deleted (only soft delete) - record preserved for audit
    3. Used only for future payments - updates don't affect past payments
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    result = await api.create_bank_info(
        employee_id=employee_id,
        company_id=company_id,
        data=data,
        user_id=user.id,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_BANK_INFO_CREATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag header if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    
    return json_response


@router.patch(
    "/bank-info",
    response_model=StandardResponse[BankInfoResponse],
    summary=SalaryApiDocs.update_bank_info["summary"],
    description=SalaryApiDocs.update_bank_info["description"],
)
async def update_bank_info(
    request: Request,
    employee_id: UUID,
    data: BankInfoUpsert,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[BankInfoResponse]:
    """Update bank information.
    
    PATCH /v1/company/employees/{employee_id}/salary/bank-info
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    
    Key Rules:
    1. One bank account per employee (active at a time) - updates existing active bank info
    2. Never hard deleted (only soft delete) - record preserved for audit
    3. Used only for future payments - updates don't affect past payments
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    # Handle empty strings for If-Match
    if_match_value = if_match if if_match and if_match.strip() else None
    
    result = await api.update_bank_info(
        employee_id=employee_id,
        company_id=company_id,
        data=data,
        user_id=user.id,
        if_match=if_match_value,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_BANK_INFO_UPDATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag header if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    
    return json_response


@router.delete(
    "/bank-info",
    status_code=status.HTTP_204_NO_CONTENT,
    summary=SalaryApiDocs.delete_bank_info["summary"],
    description=SalaryApiDocs.delete_bank_info["description"],
)
async def delete_bank_info(
    request: Request,
    employee_id: UUID,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> Response:
    """Delete bank information.
    
    DELETE /v1/company/employees/{employee_id}/salary/bank-info
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    
    Key Rules:
    1. One bank account per employee (active at a time) - soft deletes active bank info
    2. Never hard deleted (only soft delete) - sets deleted_at, preserves record for audit
    3. Used only for future payments - soft deletion doesn't affect past payments
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    await api.delete_bank_info(
        employee_id=employee_id,
        company_id=company_id,
        user_id=user.id,
    )
    
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.headers["X-Request-ID"] = request_id
    
    return response


@router.get(
    "/payments",
    response_model=StandardResponse[SalaryPaymentPaginatedResponse],
    summary=SalaryApiDocs.list_payments["summary"],
    description=SalaryApiDocs.list_payments["description"],
)
async def list_salary_payments(
    request: Request,
    employee_id: UUID,
    query: SalaryPaymentListQuery = Depends(SalaryPaymentListQuery),
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_employee_access),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryPaymentPaginatedResponse]:
    """Get employee salary payments.
    
    Role Scope:
    - Employee → self only
    - HR / CEO → company scope
    
    Based on F6_api_spec.md - GET /v1/company/employees/{employee_id}/salary/payments.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    result = await api.list_salary_payments(
        employee_id=employee_id,
        company_id=company_id,
        query=query,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_SALARY_PAYMENTS_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    return json_response


@router.post(
    "/salary-payments/run",
    response_model=StandardResponse[SalaryPaymentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Execute salary payment",
    description="Execute salary payment for an employee. Used by HR and automated payroll jobs. Checks payment not already done, fetches active salary_details and bank_info, inserts salary_payment, and triggers async slip generation.",
)
async def run_salary_payment(
    request: Request,
    data: SalaryPaymentRun,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryPaymentResponse]:
    """Execute salary payment.
    
    Backend Logic:
    1. Check payment not already done
    2. Fetch active salary_details
    3. Fetch active bank_info
    4. Insert salary_payment
    5. Trigger async slip generation
    
    Used By:
    - HR
    - Automated payroll job
    
    Based on F6_api_spec.md - POST /v1/company/employees/{employee_id}/salary/salary-payments/run.
    Authorization: CEO, HR, SuperAdmin only.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    result = await api.run_salary_payment(
        data=data,
        company_id=company_id,
        user_id=user.id,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_SALARY_PAYMENT_CREATED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    return json_response


@router.get(
    "/payments/{payment_id}/slip",
    summary=SalaryApiDocs.get_salary_slip["summary"],
    description=SalaryApiDocs.get_salary_slip["description"],
)
async def get_salary_slip(
    request: Request,
    employee_id: UUID,
    payment_id: UUID,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
):
    """Download salary slip PDF.
    
    Based on F6_api_spec.md Section 4.3.6 - GET /v1/company/employees/{employee_id}/salary/payments/{payment_id}/slip.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    Returns raw PDF file binary data.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    # Get PDF bytes and payment metadata from service
    # Service returns tuple of (pdf_bytes, year, month) for filename generation
    result = await api.get_salary_slip(
        employee_id=employee_id,
        payment_id=payment_id,
        company_id=company_id,
    )
    
    # Unpack result: (pdf_bytes, year, month)
    pdf_bytes, year, month = result
    
    # Build filename in spec format: salary_slip_YYYY_MM.pdf (e.g., salary_slip_2024_03.pdf)
    filename = f"salary_slip_{year}_{month:02d}.pdf"
    
    # Return PDF response
    from fastapi.responses import Response as PDFResponse
    pdf_response = PDFResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "X-Request-ID": request_id,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
    
    return pdf_response


# ============================================================================
# Company-wide Salary Payment Endpoints
# ============================================================================

salary_payments_router = APIRouter(
    prefix="/salary-payments",
    tags=["Salaries"],
)


@salary_payments_router.get(
    "",
    response_model=StandardResponse[SalaryPaymentPaginatedResponse],
    summary="Get salary payments by month/year",
    description="Get salary payments by month and year across company. Used for payroll reports, compliance, and finance reconciliation.",
)
async def get_salary_payments_by_month_year(
    request: Request,
    month: int,
    year: int,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "paid_on",
    sort_order: str = "desc",
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryPaymentPaginatedResponse]:
    """Get salary payments by month/year.
    
    Used for:
    - Payroll reports
    - Compliance
    - Finance reconciliation
    
    Based on F6_api_spec.md - GET /v1/salary-payments?month={month}&year={year}.
    Authorization: CEO, HR, SuperAdmin only.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    result = await api.list_salary_payments_by_month_year(
        company_id=company_id,
        month=month,
        year=year,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_SALARY_PAYMENTS_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    return json_response


# Export both routers
__all__ = ["router", "salary_payments_router"]
