from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.clients.model import BaseModelProvider
from api.domain.key import KeyRepository
from api.infrastructure.postgres import PostgresKeyRepository, PostgresRouterRepository, PostgresUserInfoRepository
from api.schemas.core.context import RequestContext
from api.use_cases.admin import CreateRouterUseCase
from api.use_cases.models import GetModelsUseCase
from api.utils.configuration import configuration
from api.utils.context import global_context, request_context


async def get_postgres_session() -> AsyncGenerator[Any, Any]:
    """
    Get a PostgreSQL postgres_session from the global context.

    Returns:
        AsyncSession: A PostgreSQL postgres_session instance.
    """

    session_factory = global_context.postgres_session_factory
    async with session_factory() as postgres_session:
        try:
            yield postgres_session
            if postgres_session.in_transaction():
                await postgres_session.commit()
        except Exception:
            if postgres_session.in_transaction():
                await postgres_session.rollback()
            raise


def get_request_context() -> ContextVar[RequestContext]:
    """
    Get the RequestContext ContextVar from the global context.

    Returns:
        ContextVar[RequestContext]: The RequestContext ContextVar instance.
    """

    return request_context


def get_models_use_case(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: RequestContext = Depends(get_request_context),
) -> GetModelsUseCase:
    return GetModelsUseCase(
        router_repository=PostgresRouterRepository(postgres_session=postgres_session, app_title=configuration.settings.app_title),
        user_id=request_context.get().user_id,
        user_info_repository=PostgresUserInfoRepository(postgres_session=postgres_session),
    )


def create_router_use_case(postgres_session: AsyncSession = Depends(get_postgres_session)) -> CreateRouterUseCase:
    return CreateRouterUseCase(
        router_repository=PostgresRouterRepository(postgres_session=postgres_session, app_title=configuration.settings.app_title),
        user_info_repository=PostgresUserInfoRepository(postgres_session=postgres_session),
    )


def get_key_repository(postgres_session: AsyncSession = Depends(get_postgres_session)) -> KeyRepository:
    return PostgresKeyRepository(postgres_session=postgres_session)


def get_master_key() -> str:
    return configuration.settings.auth_master_key


def get_model_provider_factory():
    """
    Get the ModelProviderClientFactory instance.

    This is a singleton factory used to create model provider clients.

    Returns:
        ModelProviderClientFactory: The factory instance.

    Example:
        >>> from api.clients.model import BaseModelProvider
        >>> from api.schemas.admin.providers import ProviderType
        >>>
        >>> @app.get("/test")
        >>> async def test(factory = Depends(get_model_provider_factory)):
        ...     provider = factory.create(
        ...         provider_type=ProviderType.OPENAI,
        ...         url="https://api.openai.com",
        ...         key="sk-...",
        ...         timeout=30,
        ...         model_name="gpt-4",
        ...     )
        ...     return {"provider": provider.name}
    """
    from api.clients.model import ModelProviderClientFactory

    return ModelProviderClientFactory


def create_model_provider(
    provider_type: str,
    url: str,
    key: str | None,
    timeout: int,
    model_name: str,
    model_carbon_footprint_zone: str | None = None,
    model_carbon_footprint_total_params: int | None = None,
    model_carbon_footprint_active_params: int | None = None,
) -> BaseModelProvider:
    """
    Dependency injection helper to create a model provider client.

    This function wraps ModelProviderClientFactory.create() and can be used
    directly in FastAPI dependency injection.

    Args:
        provider_type: Type of provider (e.g., "openai", "mistral")
        url: Base URL of the provider API
        key: API key (optional)
        timeout: Request timeout in seconds
        model_name: Name of the model
        model_carbon_footprint_zone: Zone for carbon calculation
        model_carbon_footprint_total_params: Total params
        model_carbon_footprint_active_params: Active params

    Returns:
        A model provider client instance

    Example:
        This can be used in endpoints that need a provider client:

        >>> @app.post("/forward")
        >>> async def forward_request(
        ...     request: RequestBody,
        ...     provider = Depends(create_model_provider),
        ... ):
        ...     response = await provider.forward_request(...)
        ...     return response
    """
    from api.clients.model import ModelProviderClientFactory
    from api.schemas.admin.providers import ProviderType

    if isinstance(provider_type, str):
        provider_type = ProviderType(provider_type)

    return ModelProviderClientFactory.create(
        provider_type=provider_type,
        url=url,
        key=key,
        timeout=timeout,
        model_name=model_name,
        model_carbon_footprint_zone=model_carbon_footprint_zone,
        model_carbon_footprint_total_params=model_carbon_footprint_total_params,
        model_carbon_footprint_active_params=model_carbon_footprint_active_params,
    )
