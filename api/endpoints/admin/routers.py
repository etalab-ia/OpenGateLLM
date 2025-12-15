from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.admin.roles import PermissionType
from api.schemas.admin.routers import CreateRouter, CreateRouterResponse, Router, Routers, UpdateRouter
from api.utils.context import request_context
from api.utils.dependencies import get_model_registry, get_postgres_session
from api.utils.variables import ENDPOINT__ADMIN_ROUTERS, ROUTER__ADMIN

router = APIRouter(prefix="/v1", tags=[ROUTER__ADMIN.title()])


@router.post(path=ENDPOINT__ADMIN_ROUTERS, dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))], status_code=201)
async def create_router(
    request: Request,
    body: CreateRouter = Body(description="The router creation request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> CreateRouterResponse:
    """
    Create a model (without any providers).
    """
    router_id = await model_registry.create_router(
        name=body.name,
        type=body.type,
        aliases=body.aliases,
        load_balancing_strategy=body.load_balancing_strategy,
        cost_prompt_tokens=body.cost_prompt_tokens,
        cost_completion_tokens=body.cost_completion_tokens,
        user_id=request_context.get().user_info.id,
        postgres_session=postgres_session,
    )
    return JSONResponse(status_code=201, content=CreateRouterResponse(id=router_id).model_dump())


@router.delete(
    path=ENDPOINT__ADMIN_ROUTERS + "/{router}",
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
    path=ENDPOINT__ADMIN_ROUTERS + "/{router}",
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
        user_id=request_context.get().user_info.id,
        postgres_session=postgres_session,
    )

    return Response(status_code=204)


@router.get(
    path=ENDPOINT__ADMIN_ROUTERS + "/{router}",
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
    path=ENDPOINT__ADMIN_ROUTERS,
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
