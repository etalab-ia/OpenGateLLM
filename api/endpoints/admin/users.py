from fastapi import Body, Depends, Path, Request, Security
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role.entities import PermissionType
from api.endpoints.admin import router
from api.helpers._accesscontroller import AccessController
from api.schemas.admin.users import UserUpdateRequest
from api.utils.context import global_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute


@router.delete(
    path=EndpointRoute.ADMIN_USERS + "/{user_id}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def delete_user(
    request: Request,
    user_id: int = Path(description="The ID of the user to delete."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    """
    Delete a user.
    """
    await global_context.identity_access_manager.delete_user(postgres_session=postgres_session, user_id=user_id)

    return Response(status_code=204)


@router.patch(
    path=EndpointRoute.ADMIN_USERS + "/{user}",
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
