from contextvars import ContextVar
import logging
from typing import Literal

from fastapi import Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import create_provider_use_case_factory, get_request_context
from api.domain.model import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider import InvalidProviderTypeError, ProviderNotReachableError
from api.domain.provider.errors import ProviderAlreadyExistsError
from api.domain.router.errors import RouterNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.helpers.models import ModelRegistry
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InconsistentModelMaxContextLengthHTTPException,
    InconsistentModelVectorSizeHTTPException,
    InternalServerHTTPException,
    InvalidProviderTypeHTTPException,
    NotAdminUserHTTPException,
    ProviderAlreadyExistsHTTPException,
    ProviderNotReachableHTTPException,
    RouterNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.providers import CreateProvider, CreateProviderResponse, Provider, Providers, UpdateProvider
from api.use_cases.admin.providers import CreateProviderCommand, CreateProviderUseCase, CreateProviderUseCaseSuccess
from api.utils.dependencies import get_model_registry, get_postgres_session
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.post(
    path=EndpointRoute.ADMIN_PROVIDERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=201,
    responses=get_documentation_responses(
        [
            InconsistentModelMaxContextLengthHTTPException,
            InconsistentModelVectorSizeHTTPException,
            InvalidProviderTypeHTTPException,
            ProviderNotReachableHTTPException,
            ProviderAlreadyExistsHTTPException,
            RouterNotFoundHTTPException,
            NotAdminUserHTTPException,
        ]
    ),
)
async def create_provider(
    request: Request,
    body: CreateProvider,
    create_provider_use_case: CreateProviderUseCase = Depends(create_provider_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> CreateProviderResponse:
    try:
        command = CreateProviderCommand(
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
        result = await create_provider_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing create_provider use case",
            extra={
                "user_id": request_context.get().user_id,
                "provider_router_id": body.router,
                "provider_url": body.url,
                "provider_model_name": body.model_name,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateProviderUseCaseSuccess(created_provider):
            return CreateProviderResponse.model_validate(created_provider, from_attributes=True)

        case InconsistentModelMaxContextLengthError(expected_max_context_length=expected_max_context_length, actual_max_context_length=actual_max_context_length, router_name=router_name):  # fmt: off
            raise InconsistentModelMaxContextLengthHTTPException(input_max_context_length=actual_max_context_length, model_max_context_length=expected_max_context_length, model_name=router_name)  # fmt: off
        case InconsistentModelVectorSizeError(expected_vector_size=expected_vector_size, actual_vector_size=actual_vector_size, router_name=router_name):  # fmt: off
            raise InconsistentModelVectorSizeHTTPException(input_vector_size=actual_vector_size, model_vector_size=expected_vector_size, model_name=router_name)  # fmt: off
        case InvalidProviderTypeError(provider_type=provider_type, router_type=router_type):
            raise InvalidProviderTypeHTTPException(incorrect_provider_type=provider_type, router_type=router_type)
        case ProviderNotReachableError(model_name=name):
            raise ProviderNotReachableHTTPException(name=name)
        case ProviderAlreadyExistsError(model_name=model_name, url=url, router_id=router_id):
            raise ProviderAlreadyExistsHTTPException(model_name=model_name, url=url, router_id=router_id)
        case RouterNotFoundError(router_id=router_id):
            raise RouterNotFoundHTTPException(router_id=router_id)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()


@router.delete(
    path=EndpointRoute.ADMIN_PROVIDERS + "/{provider}",
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
    path=EndpointRoute.ADMIN_PROVIDERS + "/{provider}",
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
    path=EndpointRoute.ADMIN_PROVIDERS + "/{provider}",
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
    path=EndpointRoute.ADMIN_PROVIDERS,
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
