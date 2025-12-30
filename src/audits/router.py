"""FastAPI endpoints for Audit Logging & Activity History module.

Based on F11_api_spec.md - Audit Logging & Activity History (F-011).
All endpoints with proper authentication, authorization, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import JSONResponse, Response as FastAPIResponse
from src.schemas import StandardResponse
from src.audits.schemas import (
    AuditLogListQuery,
    AuditLogSummary,
    AuditLogDetail,
    AuditLogPaginatedResponse,
)
from src.audits.dependencies import (
    AuditLogApiDep,
    get_current_audit_log_user,
)
from src.audits.documentations.audits_api_doc import AuditLogApiDocs
from src.audits.constants import (
    SUCCESS_AUDIT_LOGS_RETRIEVED,
    SUCCESS_AUDIT_LOG_RETRIEVED,
)
from src.audits.utils import format_last_modified
from src.users.models import User
from src.users.utils import generate_request_id

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/company/audit-logs",
    tags=["Audit Logs"],
)


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.get(
    "",
    response_model=StandardResponse[AuditLogPaginatedResponse],
    summary=AuditLogApiDocs.list["summary"],
    description=AuditLogApiDocs.list["description"],
)
async def list_audit_logs(
    request: Request,
    query: AuditLogListQuery = Depends(AuditLogListQuery),
    api: AuditLogApiDep = Depends(AuditLogApiDep),
    user_company_role: tuple[User, UUID, str] = Depends(get_current_audit_log_user),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[AuditLogPaginatedResponse] | FastAPIResponse:
    """List audit logs with pagination, filtering, and sorting.
    
    Based on F11_api_spec.md Section 4.4.1 - GET /api/v1/company/audit-logs.
    Visibility is role-based: CEO/HR see all; Manager sees only allowed tables.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role = user_company_role
    
    # Handle empty strings for If-None-Match
    if_none_match_value = if_none_match if if_none_match and if_none_match.strip() else None
    
    result = await api.list_audit_logs(
        company_id=company_id,
        query=query,
        role=role,
        if_none_match=if_none_match_value,
    )
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        if response:
            response.headers["X-Request-ID"] = request_id
        return result
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_AUDIT_LOGS_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response


@router.get(
    "/{audit_log_id}",
    response_model=StandardResponse[AuditLogDetail],
    summary=AuditLogApiDocs.get["summary"],
    description=AuditLogApiDocs.get["description"],
)
async def get_audit_log(
    request: Request,
    audit_log_id: UUID,
    api: AuditLogApiDep = Depends(AuditLogApiDep),
    user_company_role: tuple[User, UUID, str] = Depends(get_current_audit_log_user),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    response: Response = None,
) -> StandardResponse[AuditLogDetail] | FastAPIResponse:
    """Get detailed audit log information.
    
    Based on F11_api_spec.md Section 4.4.2 - GET /api/v1/company/audit-logs/{audit_log_id}.
    Visibility is role-based: CEO/HR see all; Manager sees only allowed tables.
    """
    request_id = generate_request_id(x_request_id)
    user, company_id, role = user_company_role
    
    # Handle empty strings for If-None-Match
    if_none_match_value = if_none_match if if_none_match and if_none_match.strip() else None
    
    result = await api.get_audit_log_by_id(
        audit_log_id=audit_log_id,
        company_id=company_id,
        role=role,
        if_none_match=if_none_match_value,
    )
    
    # If service returned 304, return it directly
    if isinstance(result, FastAPIResponse):
        if response:
            response.headers["X-Request-ID"] = request_id
        return result
    
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_AUDIT_LOG_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    
    # Set ETag and Last-Modified headers if available
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    
    return json_response
