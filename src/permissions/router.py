"""FastAPI endpoints for Permissions System module.

Based on F2_db_spec.md - All endpoints with proper authentication, authorization,
user scoping, company scoping, and StandardResponse format.
"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Header, Response, Request
from src.schemas import StandardResponse
from src.pagination import PagedCollection
from src.permissions.schemas import (
    RoleListQuery,
    RoleCreate,
    RoleUpdate,
    RoleRead,
    RoleListItem,
)
from src.permissions.dependencies import RoleApiDep, get_current_user_with_company
from src.permissions.constants import (
    SUCCESS_ROLES_RETRIEVED,
    SUCCESS_ROLE_RETRIEVED,
    SUCCESS_ROLE_CREATED,
    SUCCESS_ROLE_UPDATED,
    SUCCESS_ROLE_DELETED,
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


@router.post(
    "",
    response_model=StandardResponse[RoleRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create role",
    description="Create a new role with name, code, and permissions. Role code must be one of the predefined values: superadmin, ceo, hr, manager, employee.",
)
async def create_role(
    request: Request,
    data: RoleCreate,
    api: RoleApiDep = Depends(RoleApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
) -> StandardResponse[RoleRead]:
    """Create a new role.
    
    Based on F2_db_spec.md Section 7.1 - Role entity.
    """
    user, company_id = user_company
    
    result = await api.create_role(data, created_by=user.id)
    return StandardResponse(
        data=result,
        message=SUCCESS_ROLE_CREATED,
    )


@router.patch(
    "/{role_id}",
    response_model=StandardResponse[RoleRead],
    summary="Update role",
    description="Update a role's name and/or permissions. Role code is immutable and cannot be updated. Requires If-Match header for optimistic locking.",
)
async def update_role(
    request: Request,
    role_id: UUID,
    update_data: RoleUpdate,
    api: RoleApiDep = Depends(RoleApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    response: Response = None,
) -> StandardResponse[RoleRead]:
    """Update a role.
    
    Based on F2_db_spec.md Section 7.1 - Role entity.
    Note: ETag validation is handled in service layer per error_prevention.md RULE 19.
    For now, we'll implement basic If-Match validation.
    """
    user, company_id = user_company
    
    # If-Match header validation (ETag from GET response)
    if if_match:
        # Get current role to check ETag
        current_role = await api.get_role_by_id(role_id)
        from src.notifications.utils import generate_etag
        current_etag = generate_etag(current_role.updated_at)
        if if_match != current_etag:
            from src.permissions.exceptions import PreconditionFailed
            raise PreconditionFailed()
    else:
        # If-Match header is required for update operations
        from src.permissions.exceptions import PreconditionRequired
        raise PreconditionRequired()
    
    result = await api.update_role(role_id, update_data, updated_by=user.id)
    
    # Set new ETag after update
    if hasattr(result, 'updated_at'):
        from src.notifications.utils import generate_etag
        response.headers["ETag"] = generate_etag(result.updated_at)
    
    return StandardResponse(
        data=result,
        message=SUCCESS_ROLE_UPDATED,
    )


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete role",
    description="Soft delete a role. Cannot delete a role that is assigned to users.",
)
async def delete_role(
    request: Request,
    role_id: UUID,
    api: RoleApiDep = Depends(RoleApiDep),
    user_company: tuple[User, Optional[UUID]] = Depends(get_current_user_with_company),
) -> Response:
    """Soft delete a role.
    
    Based on F2_db_spec.md Section 7.1 - Role entity.
    Note: Cannot delete a role that is assigned to users.
    """
    user, company_id = user_company
    
    await api.delete_role(role_id, deleted_by=user.id)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
