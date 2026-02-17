import logging
from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import create_provider_use_case_factory, get_request_context
from api.domain.model import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider import InvalidProviderTypeError, ProviderNotReachableError
from api.domain.provider.errors import ProviderAlreadyExistsError
from api.domain.router.errors import RouterNotFoundError
from api.helpers.models import ModelRegistry
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.endpoints.exceptions import (
    InconsistentModelMaxContextLengthHTTPException,
    InconsistentModelVectorSizeHTTPException,
    InternalServerHTTPException,
    InvalidProviderTypeHTTPException,
    ProviderAlreadyExistsHTTPException,
    ProviderNotReachableHTTPException,
    RouterNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.providers import (
    CreateProvider,
    CreateProviderResponse,
    Provider,
    Providers,
    UpdateProvider,
)
from api.use_cases.admin.providers import CreateProviderUseCase
from api.use_cases.admin.providers._createproviderusecase import CreateProviderUseCaseSuccess
from api.utils.dependencies import get_model_registry, get_postgres_session
from api.utils.variables import ENDPOINT__ADMIN_PROVIDERS, ROUTER__ADMIN

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=[ROUTER__ADMIN.title()])


@router.post(
    path=ENDPOINT__ADMIN_PROVIDERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=201,
)
async def create_provider(
    request: Request,
    body: CreateProvider,
    create_provider_use_case: CreateProviderUseCase = Depends(create_provider_use_case_factory),
    request_context: RequestContext = Depends(get_request_context),
) -> CreateProviderResponse:
    try:
        result = await create_provider_use_case.execute(
            router_id=body.router,
            user_id=request_context.get().user_id,
            provider_type=body.type,
            url=body.url,
            key=body.key,
            timeout=body.timeout,
            model_name=body.model_name,
            model_hosting_zone=body.model_hosting_zone,
            model_total_params=body.model_total_params,
            model_active_params=body.model_active_params,
            qos_metric=body.qos_metric,
            qos_limit=body.qos_limit,
        )
    except Exception as e:
        logger.exception(
            "Unexpected error while executing create_router use case",
            extra={
                "user_id": request_context.get().user_id,
                "router_name": body.name,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateProviderUseCaseSuccess(created_provider):
            return CreateProviderResponse.model_validate(created_provider, from_attributes=True)
        case InvalidProviderTypeError(provider_type, router_type):
            raise InvalidProviderTypeHTTPException(provider_type, router_type)
        case ProviderNotReachableError(name):
            raise ProviderNotReachableHTTPException(name)
        case ProviderAlreadyExistsError(model_name, url, router_id):
            raise ProviderAlreadyExistsHTTPException(model_name, url, router_id)
        case InconsistentModelMaxContextLengthError(actual_max_context_length, expected_max_context_length, router_name):
            raise InconsistentModelMaxContextLengthHTTPException(
                input_max_context_length=actual_max_context_length, model_max_context_length=expected_max_context_length, model_name=router_name
            )
        case InconsistentModelVectorSizeError(actual_vector_size, expected_vector_size, router_name):
            raise InconsistentModelVectorSizeHTTPException(actual_vector_size, expected_vector_size, router_name)
        case RouterNotFoundError(router_id):
            raise RouterNotFoundHTTPException(router_id)


@router.delete(
    path=ENDPOINT__ADMIN_PROVIDERS + "/{provider}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=204,
)
async def delete_provider(
    request: Request,
    provider: int = Path(description="The ID of the provider to delete."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> Response:
    await model_registry.delete_provider(provider_id=provider, postgres_session=postgres_session)

    return Response(status_code=204)


@router.patch(
    path=ENDPOINT__ADMIN_PROVIDERS + "/{provider}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=204,
)
async def update_provider(
    request: Request,
    provider: int = Path(description="The ID of the provider to update."),
    body: UpdateProvider = Body(description="The provider update request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> Response:
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


@router.get(
    path=ENDPOINT__ADMIN_PROVIDERS + "/{provider}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    response_model=Provider,
)
async def get_provider(
    request: Request,
    provider: int = Path(description="The ID of the provider to get."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> JSONResponse:
    providers = await model_registry.get_providers(router_id=None, provider_id=provider, postgres_session=postgres_session)
    provider = providers[0]

    return JSONResponse(status_code=200, content=provider.model_dump())


@router.get(
    path=ENDPOINT__ADMIN_PROVIDERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    response_model=Providers,
)
async def get_providers(
    request: Request,
    router: int | None = Query(default=None, description="Filter providers by router ID."),
    offset: int = Query(default=0, ge=0, description="The offset of the tokens to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the tokens to get."),
    order_by: Literal["id", "model_name", "created"] = Query(default="id", description="The field to order the tokens by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the tokens by."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> JSONResponse:
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
