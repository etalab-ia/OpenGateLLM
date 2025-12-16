from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.admin.providers import (
    CreateProvider,
    CreateProviderResponse,
    Provider,
    Providers,
    UpdateProvider,
)
from api.schemas.admin.roles import PermissionType
from api.utils.context import request_context
from api.utils.dependencies import get_model_registry, get_postgres_session
from api.utils.variables import ENDPOINT__ADMIN_PROVIDERS, ROUTER__ADMIN

router = APIRouter(prefix="/v1", tags=[ROUTER__ADMIN.title()])


@router.post(
    path=ENDPOINT__ADMIN_PROVIDERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN, PermissionType.PROVIDE_MODELS]))],
    status_code=201,
)
async def create_provider(
    request: Request,
    body: CreateProvider,
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> CreateProviderResponse:
    """
    Create a model provider.
    """
    provider_id = await model_registry.create_provider(
        router_id=body.router,
        user_id=request_context.get().user_info.id,
        type=body.type,
        url=body.url,
        key=body.key,
        timeout=body.timeout,
        model_name=body.model_name,
        model_carbon_footprint_zone=body.model_carbon_footprint_zone,
        model_carbon_footprint_total_params=body.model_carbon_footprint_total_params,
        model_carbon_footprint_active_params=body.model_carbon_footprint_active_params,
        qos_metric=body.qos_metric,
        qos_limit=body.qos_limit,
        postgres_session=postgres_session,
    )
    return JSONResponse(status_code=201, content=CreateProviderResponse(id=provider_id).model_dump())


@router.delete(
    path=ENDPOINT__ADMIN_PROVIDERS + "/{provider}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN, PermissionType.PROVIDE_MODELS]))],
    status_code=204,
)
async def delete_provider(
    request: Request,
    provider: int = Path(description="The ID of the provider to delete."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> Response:
    """
    Delete a router provider.
    """
    await model_registry.delete_provider(provider_id=provider, postgres_session=postgres_session)

    return Response(status_code=204)


@router.patch(
    path=ENDPOINT__ADMIN_PROVIDERS + "/{provider}",
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
        model_carbon_footprint_zone=body.model_carbon_footprint_zone,
        model_carbon_footprint_total_params=body.model_carbon_footprint_total_params,
        model_carbon_footprint_active_params=body.model_carbon_footprint_active_params,
        qos_metric=body.qos_metric,
        qos_limit=body.qos_limit,
        postgres_session=postgres_session,
    )

    return Response(status_code=204)


@router.get(
    path=ENDPOINT__ADMIN_PROVIDERS + "/{provider}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.PROVIDE_MODELS]))],
    status_code=200,
    response_model=Provider,
)
async def get_provider(
    request: Request,
    provider: int = Path(description="The ID of the provider to get."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> JSONResponse:
    """
    Get a model provider by router and provider IDs.
    """
    providers = await model_registry.get_providers(router_id=router, provider_id=provider, postgres_session=postgres_session)
    provider = providers[0]

    return JSONResponse(status_code=200, content=provider.model_dump())


@router.get(
    path=ENDPOINT__ADMIN_PROVIDERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN, PermissionType.PROVIDE_MODELS]))],
    status_code=200,
    response_model=Providers,
)
async def get_providers(
    request: Request,
    router: int | None = Query(default=None, description="Filter providers by router ID."),
    offset: int = Query(default=0, ge=0, description="The offset of the tokens to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the tokens to get."),
    order_by: Literal["id", "name", "created"] = Query(default="id", description="The field to order the tokens by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the tokens by."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> JSONResponse:
    """
    Get all model providers for a router.
    """
    providers = await model_registry.get_providers(
        router_id=router,
        provider_id=None,
        postgres_session=postgres_session,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )

    return JSONResponse(status_code=200, content=Providers(data=providers).model_dump())
