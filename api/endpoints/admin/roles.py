from fastapi import Depends, Path, Request, Security
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role.entities import PermissionType
from api.endpoints.admin import router
from api.helpers._accesscontroller import AccessController
from api.utils.context import global_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute


@router.delete(
    path=EndpointRoute.ADMIN_ROLES + "/{role}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def delete_role(
    request: Request,
    role: int = Path(description="The ID of the role to delete."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    """
    Delete a role.
    """

    await global_context.identity_access_manager.delete_role(postgres_session=postgres_session, role_id=role)

    return Response(status_code=204)
