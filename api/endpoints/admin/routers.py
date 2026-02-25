from fastapi import Body, Depends, Path, Request, Security
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.admin import router
from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.admin.roles import PermissionType
from api.schemas.admin.routers import UpdateRouter
from api.utils.dependencies import get_model_registry, get_postgres_session
from api.utils.variables import EndpointRoute


@router.patch(
    path=EndpointRoute.ADMIN_ROUTERS + "/{router}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN, PermissionType]))],
    status_code=204,
)
async def update_router(
    request: Request,
    router: int = Path(description="The ID of the router to update (router ID, eg. 123)."),
    body: UpdateRouter = Body(description="The router update request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> Response:
    """
    Update a router.
    """
    await model_registry.update_router(
        router_id=router,
        name=body.name,
        type=body.type,
        aliases=body.aliases,
        load_balancing_strategy=body.load_balancing_strategy,
        cost_prompt_tokens=body.cost_prompt_tokens,
        cost_completion_tokens=body.cost_completion_tokens,
        postgres_session=postgres_session,
    )

    return Response(status_code=204)
