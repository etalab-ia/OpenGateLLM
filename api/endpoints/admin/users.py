from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.schemas.admin.roles import PermissionType
from api.schemas.admin.users import CreateUser, Users, UsersResponse, UserUpdateRequest
from api.utils.context import global_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import ENDPOINT__ADMIN_USERS, ROUTER__ADMIN

router = APIRouter(prefix="/v1", tags=[ROUTER__ADMIN.title()])


@router.post(
    path=ENDPOINT__ADMIN_USERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=201,
    response_model=UsersResponse,
)
async def create_user(
    request: Request,
    body: CreateUser = Body(description="The user creation request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Create a new user.
    """

    user_id = await global_context.identity_access_manager.create_user(
        postgres_session=postgres_session,
        email=body.email,
        password=body.password,
        name=body.name,
        role_id=body.role,
        organization_id=body.organization,
        budget=body.budget,
        expires=body.expires,
        priority=body.priority if body.priority is not None else 0,
    )

    return JSONResponse(status_code=201, content={"id": user_id})


@router.delete(
    path=ENDPOINT__ADMIN_USERS + "/{user:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def delete_user(
    request: Request,
    user: int = Path(description="The ID of the user to delete."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    """
    Delete a user.
    """
    await global_context.identity_access_manager.delete_user(postgres_session=postgres_session, user_id=user)

    return Response(status_code=204)


@router.patch(
    path=ENDPOINT__ADMIN_USERS + "/{user:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def update_user(
    request: Request,
    user: int = Path(description="The ID of the user to update."),
    body: UserUpdateRequest = Body(description="The user update request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    """
    Update a user.
    """
    await global_context.identity_access_manager.update_user(
        postgres_session=postgres_session,
        user_id=user,
        email=body.email,
        name=body.name,
        current_password=body.current_password,
        password=body.password,
        role_id=body.role,
        organization_id=body.organization,
        budget=body.budget,
        expires=body.expires,
        priority=body.priority,
    )

    return Response(status_code=204)


@router.get(
    path=ENDPOINT__ADMIN_USERS + "/{user:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
)
async def get_user(
    request: Request,
    user: int = Path(description="The ID of the user to get."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Get a user by id.
    """

    users = await global_context.identity_access_manager.get_users(postgres_session=postgres_session, user_id=user)

    return JSONResponse(content=users[0].model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__ADMIN_USERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
)
async def get_users(
    request: Request,
    role: int | None = Query(default=None, description="The ID of the role to filter the users by."),
    organization: int | None = Query(default=None, description="The ID of the organization to filter the users by."),
    email: str | None = Query(default=None, description="The email of the user to filter the users by."),
    offset: int = Query(default=0, ge=0, description="The offset of the users to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the users to get."),
    order_by: Literal["id", "name", "created", "updated"] = Query(default="id", description="The field to order the users by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the users by."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Get all users.
    """

    data = await global_context.identity_access_manager.get_users(
        postgres_session=postgres_session,
        role_id=role,
        organization_id=organization,
        email=email,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )

    return JSONResponse(content=Users(data=data).model_dump(), status_code=200)
