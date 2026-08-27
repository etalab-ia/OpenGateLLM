from fastapi import Body, Depends, Path, Request, Security
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role.entities import PermissionType
from api.endpoints.admin import router
from api.helpers._accesscontroller import AccessController
from api.schemas.admin.organizations import OrganizationUpdateRequest
from api.utils.context import global_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute


@router.patch(
    path=EndpointRoute.ADMIN_ORGANIZATIONS + "/{organization}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def update_organization(
    request: Request,
    organization: int = Path(description="The ID of the organization to update."),
    body: OrganizationUpdateRequest = Body(description="The organization update request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    await global_context.identity_access_manager.update_organization(postgres_session=postgres_session, organization_id=organization, name=body.name)
    return Response(status_code=204)
