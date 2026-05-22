from contextvars import ContextVar
from unittest.mock import AsyncMock

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError, ModelNotFoundError
from api.domain.provider import ProviderCapabilities
from api.domain.provider.errors import ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router.errors import RouterNameAlreadyExistsError
from api.infrastructure.fastapi.context import RequestContext
from api.tests.unit.use_case.factories import (
    ModelConfigurationFactory,
    ModelProviderConfigurationFactory,
    ProviderFactory,
    RouterFactory,
)
from api.use_cases.models import BootstrapModelsUseCase, BootstrapModelsUseCaseSkipped, BootstrapModelsUseCaseSuccess

BOOTSTRAP_ADMIN_USER_ID = 1


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
def request_context() -> ContextVar:
    context = ContextVar("request_context")
    context.set(RequestContext(user_id=1))
    return context


@pytest.fixture
def use_case(router_repository, provider_repository, provider_gateway):
    return BootstrapModelsUseCase(
        router_repository=router_repository,
        provider_repository=provider_repository,
        provider_gateway=provider_gateway,
    )


class TestBootstrapModelsUseCase:
    @pytest.mark.asyncio
    async def test_skips_when_routers_already_exist(self, use_case, router_repository, provider_repository, provider_gateway, request_context):
        # Arrange
        existing_routers = [RouterFactory(id=1), RouterFactory(id=2)]
        router_repository.get_all_routers.return_value = existing_routers

        # Act
        result = await use_case.execute(
            routers_to_create=[ModelConfigurationFactory()],
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == BootstrapModelsUseCaseSkipped(number_of_routers=2)
        router_repository.create_router.assert_not_awaited()
        provider_gateway.get_capabilities.assert_not_awaited()
        provider_repository.create_provider.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_successfully_creates_router_with_single_provider(
        self, use_case, router_repository, provider_repository, provider_gateway, request_context
    ):
        # Arrange
        model_provider = ModelProviderConfigurationFactory()
        model_configuration = ModelConfigurationFactory(providers=[model_provider])
        router = RouterFactory(id=10, name=model_configuration.name, type=RouterType.TEXT_GENERATION, max_context_length=4096, vector_size=None)
        provider = ProviderFactory(id=100, router_id=10, user_id=BOOTSTRAP_ADMIN_USER_ID)

        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
        provider_repository.create_provider.return_value = provider

        # Act
        result = await use_case.execute(
            routers_to_create=[model_configuration],
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == BootstrapModelsUseCaseSuccess(number_of_routers=1)

        router_repository.create_router.assert_awaited_once_with(
            name=model_configuration.name,
            router_type=model_configuration.type,
            load_balancing_strategy=model_configuration.load_balancing_strategy,
            cost_prompt_tokens=model_configuration.cost_prompt_tokens,
            cost_completion_tokens=model_configuration.cost_completion_tokens,
            user_id=BOOTSTRAP_ADMIN_USER_ID,
            aliases=model_configuration.aliases,
        )
        provider_gateway.get_capabilities.assert_awaited_once_with(
            router_type=router.type,
            provider_type=model_provider.type,
            url=model_provider.url,
            key=model_provider.key,
            timeout=model_provider.timeout,
            model_name=model_provider.model_name,
            request_context=request_context,
        )
        provider_repository.create_provider.assert_awaited_once_with(
            router_id=router.id,
            user_id=BOOTSTRAP_ADMIN_USER_ID,
            provider_type=model_provider.type,
            url=model_provider.url,
            key=model_provider.key,
            timeout=model_provider.timeout,
            model_name=model_provider.model_name,
            model_hosting_zone=model_provider.model_hosting_zone,
            model_total_params=model_provider.model_total_params,
            model_active_params=model_provider.model_active_params,
            qos_metric=model_provider.qos_metric,
            qos_limit=model_provider.qos_limit,
            max_context_length=4096,
            vector_size=None,
        )
        router_repository.delete_all_routers.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_successfully_creates_multiple_routers_with_multiple_providers(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        request_context,
    ):
        # Arrange
        first_model = ModelConfigurationFactory(
            name="text-gen",
            type=RouterType.TEXT_GENERATION,
            providers=[
                ModelProviderConfigurationFactory(model_name="model-a", url="https://provider-a.com/"),
                ModelProviderConfigurationFactory(model_name="model-b", url="https://provider-b.com/"),
            ],
        )
        second_model = ModelConfigurationFactory(
            name="embeddings",
            type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            providers=[ModelProviderConfigurationFactory(tei=True, model_name="embed-model", url="https://embed.com/")],
        )

        first_router = RouterFactory(id=1, name="text-gen", type=RouterType.TEXT_GENERATION, max_context_length=4096, vector_size=None)
        second_router = RouterFactory(id=2, name="embeddings", type=RouterType.TEXT_EMBEDDINGS_INFERENCE, max_context_length=512, vector_size=768)

        router_repository.get_all_routers.return_value = []
        router_repository.create_router.side_effect = [first_router, second_router]
        provider_gateway.get_capabilities.side_effect = [
            ProviderCapabilities(max_context_length=4096, vector_size=None),
            ProviderCapabilities(max_context_length=4096, vector_size=None),
            ProviderCapabilities(max_context_length=512, vector_size=768),
        ]
        provider_repository.create_provider.side_effect = [
            ProviderFactory(id=10, router_id=1),
            ProviderFactory(id=11, router_id=1),
            ProviderFactory(id=20, router_id=2),
        ]

        # Act
        result = await use_case.execute(
            routers_to_create=[first_model, second_model],
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == BootstrapModelsUseCaseSuccess(number_of_routers=2)
        assert router_repository.create_router.await_count == 2
        assert provider_gateway.get_capabilities.await_count == 3
        assert provider_repository.create_provider.await_count == 3
        router_repository.delete_all_routers.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_router_name_already_exists_error_when_duplicate_name(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        request_context,
    ):
        # Arrange
        routers_to_create = [
            ModelConfigurationFactory(name="duplicate"),
            ModelConfigurationFactory(name="duplicate"),
        ]
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(
            routers_to_create=routers_to_create,
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == RouterNameAlreadyExistsError(name="duplicate")
        router_repository.create_router.assert_not_awaited()
        provider_gateway.get_capabilities.assert_not_awaited()
        provider_repository.create_provider.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_router_name_already_exists_error_when_duplicate_alias(self, use_case, router_repository, request_context):
        # Arrange
        routers_to_create = [
            ModelConfigurationFactory(name="router-a", aliases=["shared-alias"]),
            ModelConfigurationFactory(name="router-b", aliases=["shared-alias"]),
        ]
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(
            routers_to_create=routers_to_create,
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == RouterNameAlreadyExistsError(name="shared-alias")
        router_repository.create_router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_router_name_already_exists_error_when_alias_clashes_with_name(self, use_case, router_repository, request_context):
        # Arrange
        routers_to_create = [
            ModelConfigurationFactory(name="router-a"),
            ModelConfigurationFactory(name="router-b", aliases=["router-a"]),
        ]
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(
            routers_to_create=routers_to_create,
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == RouterNameAlreadyExistsError(name="router-a")
        router_repository.create_router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_provider_already_exists_error_when_duplicate_within_router(
        self, use_case, router_repository, provider_repository, provider_gateway, request_context
    ):
        # Arrange
        model_configuration = ModelConfigurationFactory(
            providers=[
                ModelProviderConfigurationFactory(model_name="model-a", url="https://provider.com/"),
                ModelProviderConfigurationFactory(model_name="model-a", url="https://provider.com/"),
            ],
        )
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(
            routers_to_create=[model_configuration],
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert isinstance(result, ProviderAlreadyExistsError)
        assert result.model_name == "model-a"
        assert result.url == "https://provider.com/"
        router_repository.create_router.assert_not_awaited()
        provider_gateway.get_capabilities.assert_not_awaited()
        provider_repository.create_provider.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_provider_not_reachable_error_and_rolls_back(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        request_context,
    ):
        # Arrange
        model_configuration = ModelConfigurationFactory()
        router = RouterFactory(id=1, name=model_configuration.name, type=RouterType.TEXT_GENERATION)
        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_gateway.get_capabilities.return_value = ProviderNotReachableError(model_name="my-model", status_code=500, detail="error_detail")

        # Act
        result = await use_case.execute(
            routers_to_create=[model_configuration],
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == ProviderNotReachableError(model_name="my-model", status_code=500, detail="error_detail")
        provider_repository.create_provider.assert_not_awaited()
        router_repository.delete_all_routers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_model_not_found_error_and_rolls_back(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        request_context,
    ):
        # Arrange
        model_configuration = ModelConfigurationFactory()
        router = RouterFactory(id=1, name=model_configuration.name, type=RouterType.TEXT_GENERATION)
        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_gateway.get_capabilities.return_value = ModelNotFoundError(name="my-model")

        # Act
        result = await use_case.execute(
            routers_to_create=[model_configuration],
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == ModelNotFoundError(name="my-model")
        provider_repository.create_provider.assert_not_awaited()
        router_repository.delete_all_routers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_inconsistent_max_context_length_error_and_rolls_back(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        request_context,
    ):
        # Arrange
        model_configuration = ModelConfigurationFactory(
            providers=[
                ModelProviderConfigurationFactory(model_name="model-a", url="https://provider-a.com/"),
                ModelProviderConfigurationFactory(model_name="model-b", url="https://provider-b.com/"),
            ],
        )
        router = RouterFactory(id=1, name=model_configuration.name, type=RouterType.TEXT_GENERATION, max_context_length=4096, vector_size=None)
        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_gateway.get_capabilities.side_effect = [
            ProviderCapabilities(max_context_length=4096, vector_size=None),
            ProviderCapabilities(max_context_length=2048, vector_size=None),
        ]
        provider_repository.create_provider.return_value = ProviderFactory(id=10, router_id=1)

        # Act
        result = await use_case.execute(
            routers_to_create=[model_configuration],
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == InconsistentModelMaxContextLengthError(
            actual_max_context_length=2048,
            expected_max_context_length=4096,
            router_name=router.name,
        )
        provider_repository.create_provider.assert_awaited_once()
        router_repository.delete_all_routers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_inconsistent_vector_size_error_and_rolls_back(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        request_context,
    ):
        # Arrange
        model_configuration = ModelConfigurationFactory(
            type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            providers=[
                ModelProviderConfigurationFactory(tei=True, model_name="embed-a", url="https://provider-a.com/"),
                ModelProviderConfigurationFactory(tei=True, model_name="embed-b", url="https://provider-b.com/"),
            ],
        )
        router = RouterFactory(
            id=1,
            name=model_configuration.name,
            type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            max_context_length=512,
            vector_size=768,
        )
        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_gateway.get_capabilities.side_effect = [
            ProviderCapabilities(max_context_length=512, vector_size=768),
            ProviderCapabilities(max_context_length=512, vector_size=384),
        ]
        provider_repository.create_provider.return_value = ProviderFactory(id=10, router_id=1)

        # Act
        result = await use_case.execute(
            routers_to_create=[model_configuration],
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == InconsistentModelVectorSizeError(
            actual_vector_size=384,
            expected_vector_size=768,
            router_name=router.name,
        )
        provider_repository.create_provider.assert_awaited_once()
        router_repository.delete_all_routers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_success_with_no_routers_to_create(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_gateway,
        request_context,
    ):
        # Arrange
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(
            routers_to_create=[],
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            request_context=request_context,
        )

        # Assert
        assert result == BootstrapModelsUseCaseSuccess(number_of_routers=0)
        router_repository.create_router.assert_not_awaited()
        provider_gateway.get_capabilities.assert_not_awaited()
        provider_repository.create_provider.assert_not_awaited()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
