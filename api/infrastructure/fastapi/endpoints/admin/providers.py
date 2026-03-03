from contextvars import ContextVar
import logging

from fastapi import Body, Depends, Path, Query, Request, Security
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    create_provider_use_case_factory,
    delete_provider_use_case_factory,
    get_one_provider_use_case_factory,
    get_providers_use_case_factory,
    get_request_context,
)
from api.domain import SortOrder
from api.domain.model import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider import InvalidProviderTypeError, ProviderNotReachableError
from api.domain.provider.entities import ProviderSortField
from api.domain.provider.errors import ProviderAlreadyExistsError, ProviderNotFoundError
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
    ProviderNotFoundHTTPException,
    ProviderNotReachableHTTPException,
    RouterNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.providers import CreateProvider, CreateProviderResponse, Provider, Providers, UpdateProvider
from api.use_cases.admin.providers import (
    CreateProviderCommand,
    CreateProviderUseCase,
    CreateProviderUseCaseSuccess,
    DeleteProviderCommand,
    DeleteProviderUseCase,
    DeleteProviderUseCaseSuccess,
    GetOneProviderCommand,
    GetOneProviderUseCase,
    GetOneProviderUseCaseSuccess,
    GetProvidersCommand,
    GetProvidersUseCase,
    GetProvidersUseCaseSuccess,
)
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

        case InconsistentModelMaxContextLengthError(expected_max_context_length=expected_max_context_length,
                                                    actual_max_context_length=actual_max_context_length,
                                                    router_name=router_name):  # fmt: off
            raise InconsistentModelMaxContextLengthHTTPException(input_max_context_length=actual_max_context_length,
                                                                 model_max_context_length=expected_max_context_length,
                                                                 model_name=router_name)  # fmt: off
        case InconsistentModelVectorSizeError(expected_vector_size=expected_vector_size,
                                              actual_vector_size=actual_vector_size,
                                              router_name=router_name):  # fmt: off
            raise InconsistentModelVectorSizeHTTPException(input_vector_size=actual_vector_size,
                                                           model_vector_size=expected_vector_size,
                                                           model_name=router_name)  # fmt: off
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
    path=EndpointRoute.ADMIN_PROVIDERS + "/{provider_id}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, ProviderNotFoundHTTPException]),
)
async def delete_provider(
    provider_id: int = Path(description="The ID of the provider to delete."),
    delete_provider_use_case: DeleteProviderUseCase = Depends(delete_provider_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> Provider:
    command = DeleteProviderCommand(
        user_id=request_context.get().user_id,
        provider_id=provider_id,
    )
    try:
        result = await delete_provider_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing delete_provider use case",
            extra={
                "user_id": command.user_id,
                "provider_id": command.provider_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case DeleteProviderUseCaseSuccess(deleted_provider):
            return Provider.model_validate(deleted_provider, from_attributes=True)
        case ProviderNotFoundError(provider_id=not_found_id):
            raise ProviderNotFoundHTTPException(not_found_id)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()


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
    path=EndpointRoute.ADMIN_PROVIDERS + "/{provider_id}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, ProviderNotFoundHTTPException]),
)
async def get_provider(
    provider_id: int = Path(description="The ID of the provider to get."),
    get_one_provider_use_case: GetOneProviderUseCase = Depends(get_one_provider_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> Provider:
    command = GetOneProviderCommand(user_id=request_context.get().user_id, provider_id=provider_id)
    try:
        result = await get_one_provider_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_one_provider use case",
            extra={
                "user_id": command.user_id,
                "provider_id": command.provider_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case GetOneProviderUseCaseSuccess(provider):
            return Provider.model_validate(provider, from_attributes=True)
        case ProviderNotFoundError(provider_id=not_found_id):
            raise ProviderNotFoundHTTPException(not_found_id)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()


@router.get(
    path=EndpointRoute.ADMIN_PROVIDERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    response_model=Providers,
    responses=get_documentation_responses([NotAdminUserHTTPException]),
)
async def get_providers(
    router_id: int | None = Query(default=None, description="Filter providers by router ID."),
    offset: int = Query(default=0, ge=0, description="Number of providers to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of providers to return."),
    sort_by: ProviderSortField = Query(default=ProviderSortField.ID, description="Field to sort by."),
    sort_order: SortOrder = Query(default=SortOrder.ASC, description="Sort order."),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
    get_providers_use_case: GetProvidersUseCase = Depends(get_providers_use_case_factory),
) -> Providers:
    command = GetProvidersCommand(
        router_id=router_id,
        user_id=request_context.get().user_id,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    try:
        result = await get_providers_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_providers use case",
            extra={
                "user_id": command.user_id,
                "router_id": router_id,
                "offset": command.offset,
                "limit": command.limit,
                "sort_by": command.sort_by,
                "sort_order": command.sort_order,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case GetProvidersUseCaseSuccess(page=providers_page):
            return Providers(
                total=providers_page.total,
                offset=offset,
                limit=limit,
                data=[Provider.model_validate(provider, from_attributes=True) for provider in providers_page.data],
            )
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
