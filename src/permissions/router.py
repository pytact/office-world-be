"""FastAPI endpoints for Permissions System module.

Based on F2_db_spec.md - All endpoints with proper authentication, authorization,
user scoping, company scoping, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Response, Request, Header
from fastapi.responses import Response as FastAPIResponse, JSONResponse
from src.schemas import StandardResponse
from src.pagination import PagedCollection
from src.permissions.schemas import (
    RoleListQuery,
    RoleRead,
    RoleListItem,
)
from src.permissions.dependencies import RoleApiDep, get_current_user_with_company
from src.permissions.documentations.permissions_api_doc import PermissionApiDocs
from src.permissions.constants import (
    SUCCESS_ROLES_RETRIEVED,
    SUCCESS_ROLE_RETRIEVED,
)
from src.users.models import User
from src.users.utils import generate_request_id

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
)


@router.get(
    "",
    response_model=StandardResponse[PagedCollection[RoleListItem]],
    summary=PermissionApiDocs.list["summary"],
    description=PermissionApiDocs.list["description"],
)
async def list_roles(
    request: Request,
    query: RoleListQuery = Depends(RoleListQuery),
    api: RoleApiDep = Depends(RoleApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = None,
) -> StandardResponse[PagedCollection[RoleListItem]] | FastAPIResponse:
    """List roles with pagination, filtering, and sorting.
    
    Based on standard pagination pattern.
    ETag logic in service layer per error_prevention.md RULE 19.
    """
    request_id = generate_request_id()
    user, company_id = user_company
    
    result = await api.list_roles(query, if_none_match=if_none_match)
    
    # If service returned 304 Not Modified, return it directly
    if isinstance(result, FastAPIResponse):
        result.headers["X-Request-ID"] = request_id
        return result
    
    # Set ETag and Last-Modified headers from service result
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_ROLES_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        from src.permissions.utils import format_last_modified
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    return json_response


@router.get(
    "/{role_id}",
    response_model=StandardResponse[RoleRead],
    summary=PermissionApiDocs.get["summary"],
    description=PermissionApiDocs.get["description"],
)
async def get_role(
    request: Request,
    role_id: UUID,
    api: RoleApiDep = Depends(RoleApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    response: Response = None,
) -> StandardResponse[RoleRead] | FastAPIResponse:
    """Retrieve a single role by ID.
    
    ETag logic in service layer per error_prevention.md RULE 19.
    """
    request_id = generate_request_id()
    user, company_id = user_company
    
    result = await api.get_role_by_id(role_id, if_none_match=if_none_match)
    
    # If service returned 304 Not Modified, return it directly
    if isinstance(result, FastAPIResponse):
        result.headers["X-Request-ID"] = request_id
        return result
    
    # Set ETag and Last-Modified headers from service result
    response_data = StandardResponse(
        data=result,
        message=SUCCESS_ROLE_RETRIEVED,
    )
    json_response = JSONResponse(content=response_data.model_dump(mode='json'))
    json_response.headers["X-Request-ID"] = request_id
    if hasattr(result, '_etag') and result._etag:
        json_response.headers["ETag"] = result._etag
    if hasattr(result, '_last_modified') and result._last_modified:
        from src.permissions.utils import format_last_modified
        json_response.headers["Last-Modified"] = format_last_modified(result._last_modified)
    return json_response
