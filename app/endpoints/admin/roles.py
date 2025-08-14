from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.schemas.admin.roles import PermissionType, Role, RoleRequest, Roles, RolesResponse, RoleUpdateRequest
from app.sql.session import get_db_session
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__ADMIN_ROLES

router = APIRouter()


@router.post(
    path=ENDPOINT__ADMIN_ROLES,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=201,
    response_model=RolesResponse,
)
async def create_role(
    request: Request,
    body: RoleRequest = Body(description="The role creation request."),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Create a new role.
    """

    role_id = await global_context.identity_access_manager.create_role(
        session=session, name=body.name, permissions=body.permissions, limits=body.limits
    )

    return JSONResponse(status_code=201, content={"id": role_id})


@router.delete(
    path=ENDPOINT__ADMIN_ROLES + "/{role}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def delete_role(
    request: Request,
    role: int = Path(description="The ID of the role to delete."),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Delete a role.
    """

    await global_context.identity_access_manager.delete_role(session=session, role_id=role)

    return Response(status_code=204)


@router.patch(
    path=ENDPOINT__ADMIN_ROLES + "/{role:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def update_role(
    request: Request,
    role: int = Path(description="The ID of the role to update."),
    body: RoleUpdateRequest = Body(description="The role update request."),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Update a role.
    """

    await global_context.identity_access_manager.update_role(
        session=session,
        role_id=role,
        name=body.name,
        permissions=body.permissions,
        limits=body.limits,
    )

    return Response(status_code=204)


@router.get(
    path=ENDPOINT__ADMIN_ROLES + "/{role:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
    response_model=Role,
)
async def get_role(
    request: Request,
    role: int = Path(description="The ID of the role to get."),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Get a role by id.
    """

    roles = await global_context.identity_access_manager.get_roles(session=session, role_id=role)

    return JSONResponse(content=roles[0].model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__ADMIN_ROLES,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
    response_model=Roles,
)
async def get_roles(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the roles to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the roles to get."),
    order_by: Literal["id", "name", "created_at", "updated_at"] = Query(default="id", description="The field to order the roles by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the roles by."),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Get all roles.
    """
    data = await global_context.identity_access_manager.get_roles(
        session=session,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )

    return JSONResponse(content=Roles(data=data).model_dump(), status_code=200)
