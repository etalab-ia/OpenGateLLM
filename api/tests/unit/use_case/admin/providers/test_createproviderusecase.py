from contextvars import ContextVar
import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider import ProviderCapabilities
from api.domain.provider.entities import HostingZone, ProviderType
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router.errors import RouterNotFoundError
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.infrastructure.fastapi.context import RequestContext
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory, UserWithRoleFactory
from api.use_cases.admin.providers import CreateProviderCommand, CreateProviderUseCase, CreateProviderUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def provider_gateway():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def admin_user():
    return UserWithRoleFactory(id=1, admin=True)


@pytest.fixture
def non_admin_user():
    return UserWithRoleFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def expired_user():
    return UserWithRoleFactory(id=1, expires=int((dt.datetime.now() - dt.timedelta(days=1)).timestamp()))


@pytest.fixture
def request_context() -> ContextVar:
    context = ContextVar("request_context")
    context.set(RequestContext(user_id=1))
    return context


@pytest.fixture
def use_case(router_repository, provider_repository, provider_gateway, user_with_role_query):
    return CreateProviderUseCase(
        router_repository=router_repository,
        provider_repository=provider_repository,
        provider_gateway=provider_gateway,
        user_with_role_query=user_with_role_query,
    )


@pytest.fixture
def sample_router():
    return RouterFactory(
        id=1,
        name="test-router",
        type=RouterType.TEXT_GENERATION,
        providers=0,
    )


@pytest.fixture
def sample_router_with_providers():
    return RouterFactory(
        id=1,
        name="test-router",
        type=RouterType.TEXT_GENERATION,
        providers=2,
        max_context_length=4096,
        vector_size=None,
    )


@pytest.fixture
def sample_embedding_router_with_providers():
    return RouterFactory(
        id=1,
        name="embedding-router",
        type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
        providers=1,
        max_context_length=512,
        vector_size=768,
    )


@pytest.fixture
def sample_provider():
    return ProviderFactory(
        id=1,
        router_id=1,
        user_id=1,
        type=ProviderType.VLLM,
        url="https://example.com/",
        model_name="my-model",
    )


@pytest.fixture
def default_command(request_context):
    return CreateProviderCommand(
        router_id=1,
        provider_type=ProviderType.VLLM,
        url="https://example.com/",
        key=None,
        timeout=30,
        model_name="my-model",
        model_hosting_zone=HostingZone.WOR,
        model_total_params=0,
        model_active_params=0,
        qos_metric=None,
        qos_limit=None,
        request_context=request_context,
    )


def with_provider_type(command: CreateProviderCommand, provider_type: ProviderType) -> CreateProviderCommand:
    return CreateProviderCommand(
        router_id=command.router_id,
        provider_type=provider_type,
        url=command.url,
        key=command.key,
        timeout=command.timeout,
        model_name=command.model_name,
        model_hosting_zone=command.model_hosting_zone,
        model_total_params=command.model_total_params,
        model_active_params=command.model_active_params,
        qos_metric=command.qos_metric,
        qos_limit=command.qos_limit,
        request_context=command.request_context,
    )


class TestCreateProviderUseCase:
    @pytest.mark.asyncio
    async def test_should_create_provider_when_router_exists_without_any_provider(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        sample_router,
        sample_provider,
        default_command,
        admin_user,
        request_context,
    ):
        # Arrange
        router_repository.get_router_by_id.return_value = sample_router
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
        provider_repository.create_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, CreateProviderUseCaseSuccess)
        assert result.provider == sample_provider
        router_repository.get_router_by_id.assert_called_once_with(router_id=1)
        provider_gateway.get_capabilities.assert_called_once_with(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.VLLM,
            url="https://example.com/",
            key=None,
            timeout=30,
            model_name="my-model",
            request_context=request_context,
        )
        provider_repository.create_provider.assert_called_once_with(
            router_id=1,
            user_id=1,
            provider_type=ProviderType.VLLM,
            url="https://example.com/",
            key=None,
            timeout=30,
            model_name="my-model",
            model_hosting_zone=HostingZone.WOR,
            model_total_params=0,
            model_active_params=0,
            qos_metric=None,
            qos_limit=None,
            max_context_length=4096,
            vector_size=None,
        )

    @pytest.mark.asyncio
    async def test_should_create_provider_when_router_has_a_different_provider(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        sample_router_with_providers,
        sample_provider,
        default_command,
        admin_user,
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_id.return_value = sample_router_with_providers
        provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
        provider_repository.create_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, CreateProviderUseCaseSuccess)
        assert result.provider == sample_provider
        provider_repository.create_provider.assert_called_once_with(
            router_id=1,
            user_id=1,
            provider_type=ProviderType.VLLM,
            url="https://example.com/",
            key=None,
            timeout=30,
            model_name="my-model",
            model_hosting_zone=HostingZone.WOR,
            model_total_params=0,
            model_active_params=0,
            qos_metric=None,
            qos_limit=None,
            max_context_length=4096,
            vector_size=None,
        )

    @pytest.mark.asyncio
    async def test_should_create_embedding_provider_when_vector_size_matches(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        sample_embedding_router_with_providers,
        sample_provider,
        default_command,
        admin_user,
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_id.return_value = sample_embedding_router_with_providers
        provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=512, vector_size=768)
        provider_repository.create_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(with_provider_type(default_command, ProviderType.TEI))

        # Assert
        assert isinstance(result, CreateProviderUseCaseSuccess)
        assert result.provider == sample_provider
        provider_repository.create_provider.assert_called_once_with(
            router_id=1,
            user_id=1,
            provider_type=ProviderType.TEI,
            url="https://example.com/",
            key=None,
            timeout=30,
            model_name="my-model",
            model_hosting_zone=HostingZone.WOR,
            model_total_params=0,
            model_active_params=0,
            qos_metric=None,
            qos_limit=None,
            max_context_length=512,
            vector_size=768,
        )

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(
        self, use_case, router_repository, provider_repository, provider_gateway, default_command, admin_user
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_id.return_value = None

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 1
        provider_gateway.get_capabilities.assert_not_called()
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_invalid_provider_type_error_when_type_not_compatible(
        self, use_case, router_repository, provider_repository, provider_gateway, default_command, admin_user
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_id.return_value = RouterFactory(id=1, name="tei-router", type=RouterType.TEXT_CLASSIFICATION)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, InvalidProviderTypeError)
        assert result.provider_type == ProviderType.VLLM.value
        assert result.router_type == RouterType.TEXT_CLASSIFICATION
        provider_gateway.get_capabilities.assert_not_called()
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_error_when_gateway_fails(
        self, use_case, router_repository, provider_repository, provider_gateway, sample_router, default_command, admin_user
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_id.return_value = sample_router
        provider_gateway.get_capabilities.return_value = ProviderNotReachableError(model_name="my-model", status_code=500, detail="error_detail")

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, ProviderNotReachableError)
        assert result.model_name == "my-model"
        assert result.status_code == 500
        assert result.detail == "error_detail"
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_inconsistent_max_context_length_error_when_mismatch(
        self, use_case, router_repository, provider_repository, provider_gateway, sample_router_with_providers, default_command, admin_user
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_id.return_value = sample_router_with_providers
        provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=2048, vector_size=None)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, InconsistentModelMaxContextLengthError)
        assert result.actual_max_context_length == 2048
        assert result.expected_max_context_length == 4096
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_inconsistent_vector_size_error_when_mismatch(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        sample_embedding_router_with_providers,
        default_command,
        admin_user,
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_id.return_value = sample_embedding_router_with_providers
        provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=512, vector_size=384)

        # Act
        result = await use_case.execute(with_provider_type(default_command, ProviderType.TEI))

        # Assert
        assert isinstance(result, InconsistentModelVectorSizeError)
        assert result.actual_vector_size == 384
        assert result.expected_vector_size == 768
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_provider_already_exists_error(
        self, use_case, router_repository, provider_repository, provider_gateway, sample_router, default_command, admin_user
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_id.return_value = sample_router
        provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
        provider_repository.create_provider.return_value = ProviderAlreadyExistsError(model_name="my-model", url="https://example.com/", router_id=1)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, ProviderAlreadyExistsError)
        assert result.model_name == "my-model"
        assert result.url == "https://example.com/"
        assert result.router_id == 1

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_not_admin(self, use_case, default_command, non_admin_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, use_case, default_command, expired_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, UserExpiredError)
