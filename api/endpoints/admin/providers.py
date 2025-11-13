from fastapi import APIRouter, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.admin.providers import (
    CreateProvider,
    CreateProviderResponse,
    Provider,
    Providers,
)
from api.schemas.admin.roles import PermissionType
from api.sql.session import get_db_session
from api.utils.context import request_context
from api.utils.dependencies import get_model_registry
from api.utils.variables import ENDPOINT__ADMIN_PROVIDERS, ROUTER__ADMIN

router = APIRouter(prefix="/v1", tags=[ROUTER__ADMIN.title()])


@router.post(
    path=ENDPOINT__ADMIN_PROVIDERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.PROVIDE_MODELS]))],
    status_code=201,
)
async def create_provider(
    request: Request,
    body: CreateProvider,
    session: AsyncSession = Depends(get_db_session),
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
        qos_value=body.qos_value,
        session=session,
    )
    return JSONResponse(status_code=201, content=CreateProviderResponse(id=provider_id).model_dump())


@router.delete(
    path=ENDPOINT__ADMIN_PROVIDERS + "/{provider}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.PROVIDE_MODELS]))],
    status_code=204,
)
async def delete_provider(
    request: Request,
    provider: int = Path(description="The ID of the provider to delete."),
    session: AsyncSession = Depends(get_db_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> Response:
    """
    Delete a router provider.
    """
    await model_registry.delete_provider(provider_id=provider, user_id=request_context.get().user_info.id, session=session)

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
    session: AsyncSession = Depends(get_db_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> JSONResponse:
    """
    Get a model provider by router and provider IDs.
    """
    providers = await model_registry.get_providers(router_id=router, provider_id=provider, session=session)
    provider = providers[0]

    return JSONResponse(status_code=200, content=provider.model_dump())


@router.get(
    path=ENDPOINT__ADMIN_PROVIDERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.PROVIDE_MODELS]))],
    status_code=200,
    response_model=Providers,
)
async def get_providers(
    request: Request,
    router: int | None = Query(default=None, description="Filter providers by router ID."),
    session: AsyncSession = Depends(get_db_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> JSONResponse:
    """
    Get all model providers for a router.
    """
    providers = await model_registry.get_providers(router_id=router, provider_id=None, session=session)

    return JSONResponse(status_code=200, content=Providers(data=providers).model_dump())
