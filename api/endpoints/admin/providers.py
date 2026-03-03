from fastapi import Body, Depends, Path, Request, Security
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.admin import router
from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.admin.providers import UpdateProvider
from api.schemas.admin.roles import PermissionType
from api.utils.dependencies import get_model_registry, get_postgres_session
from api.utils.variables import EndpointRoute


@router.patch(
    path=EndpointRoute.ADMIN_PROVIDERS + "/{provider}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN, PermissionType.PROVIDE_MODELS]))],
    status_code=204,
)
async def update_provider(
    request: Request,
    provider: int = Path(description="The ID of the provider to update."),
    body: UpdateProvider = Body(description="The provider update request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> Response:
    """
    Update a model provider.
    """
    await model_registry.update_provider(
        provider_id=provider,
        router_id=body.router,
        timeout=body.timeout,
        model_hosting_zone=body.model_hosting_zone,
        model_total_params=body.model_total_params,
        model_active_params=body.model_active_params,
        qos_metric=body.qos_metric,
        qos_limit=body.qos_limit,
        postgres_session=postgres_session,
    )

    return Response(status_code=204)
