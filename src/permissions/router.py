"""FastAPI endpoints for Permissions System module.

Based on F2_db_spec.md - All endpoints with proper authentication, authorization,
user scoping, company scoping, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Response, Request
from src.schemas import StandardResponse
from src.pagination import PagedCollection
from src.permissions.schemas import (
    RoleListQuery,
    RoleRead,
    RoleListItem,
)
from src.permissions.dependencies import RoleApiDep, get_current_user_with_company
from src.permissions.constants import (
    SUCCESS_ROLES_RETRIEVED,
    SUCCESS_ROLE_RETRIEVED,
)
from src.users.models import User

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
    summary="List roles",
    description="List all roles with pagination, filtering, and sorting. Supports filtering by code and name, and sorting by created_at, updated_at, name, or code.",
)
async def list_roles(
    request: Request,
    query: RoleListQuery = Depends(RoleListQuery),
    api: RoleApiDep = Depends(RoleApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
) -> StandardResponse[PagedCollection[RoleListItem]]:
    """List roles with pagination, filtering, and sorting.
    
    Based on standard pagination pattern.
    """
    user, company_id = user_company
    
    result = await api.list_roles(query)
    return StandardResponse(
        data=result,
        message=SUCCESS_ROLES_RETRIEVED,
    )


@router.get(
    "/{role_id}",
    response_model=StandardResponse[RoleRead],
    summary="Get role by ID",
    description="Retrieve a single role by its unique identifier.",
)
async def get_role(
    request: Request,
    role_id: UUID,
    api: RoleApiDep = Depends(RoleApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
    response: Response = None,
) -> StandardResponse[RoleRead]:
    """Retrieve a single role by ID."""
    user, company_id = user_company
    
    result = await api.get_role_by_id(role_id)
    
    # Set ETag and Last-Modified headers (based on updated_at)
    if hasattr(result, 'updated_at'):
        from src.notifications.utils import generate_etag, format_last_modified
        response.headers["ETag"] = generate_etag(result.updated_at)
        response.headers["Last-Modified"] = format_last_modified(result.updated_at)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_ROLE_RETRIEVED,
    )
