from typing import Literal

from fastapi import Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.admin import router
from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.admin.roles import PermissionType
from api.schemas.admin.routers import Router, Routers, UpdateRouter
from api.utils.dependencies import get_model_registry, get_postgres_session
from api.utils.variables import EndpointRoute


@router.delete(
    path=EndpointRoute.ADMIN_ROUTERS + "/{router}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def delete_router(
    request: Request,
    router: int = Path(description="The ID of the router to delete (router ID, eg. 123)."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> Response:
    """
    Delete a model and all its providers.
    """
    await model_registry.delete_router(router_id=router, postgres_session=postgres_session)

    return Response(status_code=204)


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


@router.get(
    path=EndpointRoute.ADMIN_ROUTERS + "/{router}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN, PermissionType.PROVIDE_MODELS]))],
    status_code=200,
    response_model=Router,
)
async def get_router(
    request: Request,
    router: int = Path(description="The ID of the router to get (router ID, eg. 123)."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> JSONResponse:
    """
    Get a router by ID.
    """
    routers = await model_registry.get_routers(router_id=router, name=None, postgres_session=postgres_session)

    return JSONResponse(status_code=200, content=routers[0].model_dump())


@router.get(
    path=EndpointRoute.ADMIN_ROUTERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN, PermissionType.PROVIDE_MODELS]))],
    status_code=200,
    response_model=Routers,
)
async def get_routers(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the tokens to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the tokens to get."),
    order_by: Literal["id", "name", "created"] = Query(default="id", description="The field to order the tokens by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the tokens by."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> JSONResponse:
    """
    Get all routers.
    """
    routers = await model_registry.get_routers(
        router_id=None,
        name=None,
        postgres_session=postgres_session,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )

    return JSONResponse(status_code=200, content=Routers(data=routers).model_dump())
