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
    SalaryOverviewQuery,
    SalaryPaymentListQuery,
    SalaryOverviewResponse,
    SalaryDetailsResponse,
    BankInfoResponse,
    SalaryPaymentResponse,
    SalaryPaymentPaginatedResponse,
)
from src.salaries.dependencies import (
    SalaryApiDep,
    get_current_ceo_or_hr,
)
from src.salaries.documentations.salaries_api_doc import SalaryApiDocs
from src.salaries.constants import (
    SUCCESS_SALARY_OVERVIEW_RETRIEVED,
    SUCCESS_SALARY_DETAILS_CREATED,
    SUCCESS_BANK_INFO_UPDATED,
    SUCCESS_SALARY_PAYMENT_CREATED,
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
    response_model=StandardResponse[SalaryOverviewResponse],
    summary=SalaryApiDocs.get_overview["summary"],
    description=SalaryApiDocs.get_overview["description"],
)
async def get_salary_overview(
    request: Request,
    employee_id: UUID,
    query: SalaryOverviewQuery = Depends(SalaryOverviewQuery),
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryOverviewResponse] | FastAPIResponse:
    """Get salary overview for an employee.
    
    Based on F6_api_spec.md Section 4.3.1 - GET /v1/company/employees/{employee_id}/salary.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    # Handle empty strings for If-None-Match
    if_none_match_value = if_none_match if if_none_match and if_none_match.strip() else None
    
    result = await api.get_salary_overview(
        employee_id=employee_id,
        company_id=company_id,
        query=query,
        if_none_match=if_none_match_value,
    )
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        if response:
            response.headers["X-Request-ID"] = request_id
        return result
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_SALARY_OVERVIEW_RETRIEVED,
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
    summary=SalaryApiDocs.create_or_update_salary["summary"],
    description=SalaryApiDocs.create_or_update_salary["description"],
)
async def create_or_update_salary(
    request: Request,
    employee_id: UUID,
    data: SalaryCreate,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryDetailsResponse]:
    """Create or update salary details.
    
    Based on F6_api_spec.md Section 4.3.2 - POST /v1/company/employees/{employee_id}/salary.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    # Handle empty strings for If-Match
    if_match_value = if_match if if_match and if_match.strip() else None
    
    result = await api.create_or_update_salary(
        employee_id=employee_id,
        company_id=company_id,
        data=data,
        user_id=user.id,
        if_match=if_match_value,
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


@router.patch(
    "/bank-info",
    response_model=StandardResponse[BankInfoResponse],
    summary=SalaryApiDocs.upsert_bank_info["summary"],
    description=SalaryApiDocs.upsert_bank_info["description"],
)
async def upsert_bank_info(
    request: Request,
    employee_id: UUID,
    data: BankInfoUpsert,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[BankInfoResponse]:
    """Create or update bank information.
    
    Based on F6_api_spec.md Section 4.3.3 - PATCH /v1/company/employees/{employee_id}/salary/bank-info.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    # Handle empty strings for If-Match
    if_match_value = if_match if if_match and if_match.strip() else None
    
    result = await api.upsert_bank_info(
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


@router.post(
    "/payments",
    response_model=StandardResponse[SalaryPaymentResponse],
    status_code=status.HTTP_201_CREATED,
    summary=SalaryApiDocs.create_payment["summary"],
    description=SalaryApiDocs.create_payment["description"],
)
async def create_salary_payment(
    request: Request,
    employee_id: UUID,
    data: SalaryPaymentCreate,
    api: SalaryApiDep = Depends(SalaryApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryPaymentResponse]:
    """Create salary payment.
    
    Based on F6_api_spec.md Section 4.3.4 - POST /v1/company/employees/{employee_id}/salary/payments.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
    """
    request_id = generate_request_id(x_request_id)
    user, company_id = user_company
    
    result = await api.create_salary_payment(
        employee_id=employee_id,
        company_id=company_id,
        data=data,
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
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_ceo_or_hr),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[SalaryPaymentPaginatedResponse]:
    """List salary payments for an employee.
    
    Based on F6_api_spec.md Section 4.3.5 - GET /v1/company/employees/{employee_id}/salary/payments.
    Authorization: CEO, HR, SuperAdmin only (Employee and Manager return 403).
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
