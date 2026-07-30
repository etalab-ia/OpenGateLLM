from contextvars import ContextVar
import logging

from fastapi import Body, Depends, Path, Query, Security

from api.dependencies import (
    create_provider_use_case_factory,
    delete_provider_use_case_factory,
    get_one_provider_use_case_factory,
    get_providers_use_case_factory,
    get_request_context,
    update_provider_use_case_factory,
)
from api.domain import SortOrder
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError, ModelNotFoundError
from api.domain.provider.entities import ProviderSortField
from api.domain.provider.errors import (
    InvalidProviderTypeError,
    ProviderAlreadyExistsError,
    ProviderInvalidResponseError,
    ProviderNotFoundError,
    ProviderNotReachableError,
)
from api.domain.router.errors import RouterNotFoundError
from api.infrastructure.fastapi import AccessController
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InconsistentModelMaxContextLengthHTTPException,
    InconsistentModelVectorSizeHTTPException,
    InternalServerHTTPException,
    InvalidProviderTypeHTTPException,
    ModelNotFoundHTTPException,
    NotAdminUserHTTPException,
    ProviderAlreadyExistsHTTPException,
    ProviderInvalidResponseHTTPException,
    ProviderNotFoundHTTPException,
    ProviderNotReachableHTTPException,
    RouterNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.admin.providers import (
    CreateProviderBody,
    CreateProviderResponse,
    ProviderResponse,
    ProvidersResponse,
    UpdateProviderBody,
)
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
    UpdateProviderCommand,
    UpdateProviderUseCase,
    UpdateProviderUseCaseSuccess,
)
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.post(
    path=EndpointRoute.ADMIN_PROVIDERS,
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=201,
    responses=get_documentation_responses(
        exceptions=[
            InconsistentModelMaxContextLengthHTTPException,
            InconsistentModelVectorSizeHTTPException,
            InvalidProviderTypeHTTPException,
            ProviderNotReachableHTTPException,
            ProviderInvalidResponseHTTPException,
            ModelNotFoundHTTPException,
            ProviderAlreadyExistsHTTPException,
            RouterNotFoundHTTPException,
            NotAdminUserHTTPException,
        ]
    ),
)
async def create_provider(
    body: CreateProviderBody,
    create_provider_use_case: CreateProviderUseCase = Depends(create_provider_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> CreateProviderResponse:
    try:
        command = CreateProviderCommand(
            user_id=request_context.get().user.id,
            router_id=body.router_id,
            provider_type=body.type,
            url=body.url,
            key=body.key,
            basic_auth=body.basic_auth,
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
                "authenticated_user_id": request_context.get().user.id,
                "provider_router_id": body.router_id,
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

        case ProviderNotReachableError() as error:
            raise ProviderNotReachableHTTPException(name=error.model_name, status_code=error.status_code, detail=error.detail)

        case ModelNotFoundError(name=model_name):
            raise ModelNotFoundHTTPException(name=model_name)

        case ProviderInvalidResponseError(model_name=model_name, detail=detail):
            raise ProviderInvalidResponseHTTPException(name=model_name, detail=detail)

        case ProviderAlreadyExistsError(model_name=model_name, url=url, router_id=router_id):
            raise ProviderAlreadyExistsHTTPException(model_name=model_name, url=url, router_id=router_id)

        case RouterNotFoundError(id=router_id):
            raise RouterNotFoundHTTPException(router_id=router_id)


@router.delete(
    path=EndpointRoute.ADMIN_PROVIDERS + "/{provider_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses(exceptions=[ProviderNotFoundHTTPException, NotAdminUserHTTPException]),
)
async def delete_provider(
    provider_id: int = Path(description="The ID of the provider to delete."),
    delete_provider_use_case: DeleteProviderUseCase = Depends(delete_provider_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> ProviderResponse:
    command = DeleteProviderCommand(provider_id=provider_id)
    try:
        result = await delete_provider_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing delete_provider use case",
            extra={
                "authenticated_user_id": request_context.get().user.id,
                "provider_id": command.provider_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case DeleteProviderUseCaseSuccess(deleted_provider):
            return ProviderResponse.model_validate(deleted_provider, from_attributes=True)

        case ProviderNotFoundError(id=not_found_id):
            raise ProviderNotFoundHTTPException(provider_id=not_found_id)


@router.patch(
    path=EndpointRoute.ADMIN_PROVIDERS + "/{provider_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses(
        [
            InconsistentModelMaxContextLengthHTTPException,
            InconsistentModelVectorSizeHTTPException,
            InvalidProviderTypeHTTPException,
            ProviderAlreadyExistsHTTPException,
            RouterNotFoundHTTPException,
            ProviderNotFoundHTTPException,
            NotAdminUserHTTPException,
        ]
    ),
)
async def update_provider(
    provider_id: int = Path(description="The ID of the provider to update."),
    body: UpdateProviderBody = Body(description="The provider update request."),
    update_provider_use_case: UpdateProviderUseCase = Depends(update_provider_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> ProviderResponse:
    command = UpdateProviderCommand(
        provider_id=provider_id,
        router_id=body.router_id,
        timeout=body.timeout,
        model_hosting_zone=body.model_hosting_zone,
        model_total_params=body.model_total_params,
        model_active_params=body.model_active_params,
        qos_metric=body.qos_metric,
        qos_limit=body.qos_limit,
    )
    try:
        result = await update_provider_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing update_provider use case",
            extra={
                "authenticated_user_id": request_context.get().user.id,
                "provider_router_id": body.router_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case UpdateProviderUseCaseSuccess(updated_provider):
            return ProviderResponse.model_validate(updated_provider, from_attributes=True)

        case InconsistentModelMaxContextLengthError(expected_max_context_length=expected_max_context_length, actual_max_context_length=actual_max_context_length, router_name=router_name):  # fmt: off
            raise InconsistentModelMaxContextLengthHTTPException(input_max_context_length=actual_max_context_length, model_max_context_length=expected_max_context_length, model_name=router_name)  # fmt: off

        case InconsistentModelVectorSizeError(expected_vector_size=expected_vector_size, actual_vector_size=actual_vector_size, router_name=router_name):  # fmt: off
            raise InconsistentModelVectorSizeHTTPException(input_vector_size=actual_vector_size, model_vector_size=expected_vector_size, model_name=router_name)  # fmt: off

        case InvalidProviderTypeError(provider_type=provider_type, router_type=router_type):
            raise InvalidProviderTypeHTTPException(incorrect_provider_type=provider_type, router_type=router_type)

        case ProviderAlreadyExistsError(model_name=model_name, url=url, router_id=router_id):
            raise ProviderAlreadyExistsHTTPException(model_name=model_name, url=url, router_id=router_id)

        case RouterNotFoundError(id=router_id):
            raise RouterNotFoundHTTPException(router_id=router_id)

        case ProviderNotFoundError(id=provider_id):
            raise ProviderNotFoundHTTPException(provider_id=provider_id)


@router.get(
    path=EndpointRoute.ADMIN_PROVIDERS + "/{provider_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, ProviderNotFoundHTTPException]),
)
async def get_provider(
    provider_id: int = Path(description="The ID of the provider to get."),
    get_one_provider_use_case: GetOneProviderUseCase = Depends(get_one_provider_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> ProviderResponse:
    command = GetOneProviderCommand(provider_id=provider_id)
    try:
        result = await get_one_provider_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_one_provider use case",
            extra={
                "authenticated_user_id": request_context.get().user.id,
                "provider_id": command.provider_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case GetOneProviderUseCaseSuccess(provider):
            return ProviderResponse.model_validate(provider, from_attributes=True)

        case ProviderNotFoundError(id=not_found_id):
            raise ProviderNotFoundHTTPException(provider_id=not_found_id)


@router.get(
    path=EndpointRoute.ADMIN_PROVIDERS,
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    response_model=ProvidersResponse,
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
) -> ProvidersResponse:
    command = GetProvidersCommand(router_id=router_id, offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order)
    try:
        result = await get_providers_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_providers use case",
            extra={
                "authenticated_user_id": request_context.get().user.id,
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
            return ProvidersResponse(
                total=providers_page.total,
                offset=offset,
                limit=limit,
                data=[ProviderResponse.model_validate(provider, from_attributes=True) for provider in providers_page.data],
            )
