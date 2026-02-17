from unittest.mock import AsyncMock

import pytest

from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider import ProviderCapabilities
from api.domain.provider.entities import ProviderCarbonFootprintZone, ProviderType
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router.entities import ModelType
from api.domain.router.errors import RouterNotFoundError
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory
from api.use_cases.admin.providers import CreateProviderUseCase, CreateProviderUseCaseSuccess


@pytest.fixture
def use_case():
    return CreateProviderUseCase(
        router_repository=AsyncMock(),
        provider_repository=AsyncMock(),
        user_info_repository=AsyncMock(),
        provider_gateway=AsyncMock(),
    )


@pytest.fixture
def sample_router():
    return RouterFactory(
        id=1,
        name="test-router",
        type=ModelType.TEXT_GENERATION,
        providers=0,
    )


@pytest.fixture
def sample_router_with_providers():
    return RouterFactory(
        id=1,
        name="test-router",
        type=ModelType.TEXT_GENERATION,
        providers=2,
        max_context_length=4096,
        vector_size=None,
    )


@pytest.fixture
def sample_embedding_router_with_providers():
    return RouterFactory(
        id=1,
        name="embedding-router",
        type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
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
def default_execute_params():
    return dict(
        router_id=1,
        user_id=1,
        provider_type=ProviderType.VLLM,
        url="https://example.com/",
        key=None,
        timeout=30,
        model_name="my-model",
        model_hosting_zone=ProviderCarbonFootprintZone.WOR,
        model_total_params=0,
        model_active_params=0,
        qos_metric=None,
        qos_limit=None,
    )


class TestCreateProviderUseCase:
    @pytest.mark.asyncio
    async def test_should_create_provider_when_router_exists_without_any_provider(
        self, use_case, sample_router, sample_provider, default_execute_params
    ):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
        use_case.provider_repository.create_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(**default_execute_params)

        # Assert
        assert isinstance(result, CreateProviderUseCaseSuccess)
        assert result.provider == sample_provider
        use_case.router_repository.get_router_by_id.assert_called_once_with(router_id=1)
        use_case.provider_gateway.get_capabilities.assert_called_once_with(
            provider_type=ProviderType.VLLM, url="https://example.com/", key=None, timeout=30, model_name="my-model"
        )
        use_case.provider_repository.create_provider.assert_called_once_with(
            router_id=1,
            user_id=1,
            provider_type=ProviderType.VLLM,
            url="https://example.com/",
            key=None,
            timeout=30,
            model_name="my-model",
            model_hosting_zone=ProviderCarbonFootprintZone.WOR,
            model_total_params=0,
            model_active_params=0,
            qos_metric=None,
            qos_limit=None,
            max_context_length=4096,
            vector_size=None,
        )

    @pytest.mark.asyncio
    async def test_should_create_provider_when_router_has_a_different_provider(
        self, use_case, sample_router_with_providers, sample_provider, default_execute_params
    ):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = sample_router_with_providers
        use_case.provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
        use_case.provider_repository.create_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(**default_execute_params)

        # Assert
        assert isinstance(result, CreateProviderUseCaseSuccess)
        assert result.provider == sample_provider
        use_case.provider_repository.create_provider.assert_called_once_with(
            router_id=1,
            user_id=1,
            provider_type=ProviderType.VLLM,
            url="https://example.com/",
            key=None,
            timeout=30,
            model_name="my-model",
            model_hosting_zone=ProviderCarbonFootprintZone.WOR,
            model_total_params=0,
            model_active_params=0,
            qos_metric=None,
            qos_limit=None,
            max_context_length=4096,
            vector_size=None,
        )

    @pytest.mark.asyncio
    async def test_should_create_embedding_provider_when_vector_size_matches(
        self, use_case, sample_embedding_router_with_providers, sample_provider, default_execute_params
    ):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = sample_embedding_router_with_providers
        use_case.provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=512, vector_size=768)
        use_case.provider_repository.create_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(**{**default_execute_params, "provider_type": ProviderType.TEI})

        # Assert
        assert isinstance(result, CreateProviderUseCaseSuccess)
        assert result.provider == sample_provider
        use_case.provider_repository.create_provider.assert_called_once_with(
            router_id=1,
            user_id=1,
            provider_type=ProviderType.TEI,
            url="https://example.com/",
            key=None,
            timeout=30,
            model_name="my-model",
            model_hosting_zone=ProviderCarbonFootprintZone.WOR,
            model_total_params=0,
            model_active_params=0,
            qos_metric=None,
            qos_limit=None,
            max_context_length=512,
            vector_size=768,
        )

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, use_case, default_execute_params):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = None

        # Act
        result = await use_case.execute(**default_execute_params)

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.router_id == 1
        use_case.provider_gateway.get_capabilities.assert_not_called()
        use_case.provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_invalid_provider_type_error_when_type_not_compatible(self, use_case, default_execute_params):
        # Arrange
        router = RouterFactory(id=1, name="tei-router", type=ModelType.TEXT_CLASSIFICATION)
        use_case.router_repository.get_router_by_id.return_value = router

        # Act
        result = await use_case.execute(**default_execute_params)

        # Assert
        assert isinstance(result, InvalidProviderTypeError)
        assert result.provider_type == ProviderType.VLLM.value
        assert result.router_type == ModelType.TEXT_CLASSIFICATION
        use_case.provider_gateway.get_capabilities.assert_not_called()
        use_case.provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_error_when_gateway_fails(self, use_case, sample_router, default_execute_params):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.provider_gateway.get_capabilities.return_value = ProviderNotReachableError(model_name="my-model")

        # Act
        result = await use_case.execute(**default_execute_params)

        # Assert
        assert isinstance(result, ProviderNotReachableError)
        assert result.model_name == "my-model"
        use_case.provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_inconsistent_max_context_length_error_when_mismatch(
        self, use_case, sample_router_with_providers, default_execute_params
    ):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = sample_router_with_providers
        use_case.provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=2048, vector_size=None)

        # Act
        result = await use_case.execute(**default_execute_params)

        # Assert
        assert isinstance(result, InconsistentModelMaxContextLengthError)
        assert result.actual_max_context_length == 2048
        assert result.expected_max_context_length == 4096
        use_case.provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_inconsistent_vector_size_error_when_mismatch(
        self, use_case, sample_embedding_router_with_providers, default_execute_params
    ):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = sample_embedding_router_with_providers
        use_case.provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=512, vector_size=384)

        # Act
        result = await use_case.execute(**{**default_execute_params, "provider_type": ProviderType.TEI})

        # Assert
        assert isinstance(result, InconsistentModelVectorSizeError)
        assert result.actual_vector_size == 384
        assert result.expected_vector_size == 768
        use_case.provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_provider_already_exists_error(self, use_case, sample_router, default_execute_params):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.provider_gateway.get_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
        use_case.provider_repository.create_provider.return_value = ProviderAlreadyExistsError(
            model_name="my-model", url="https://example.com/", router_id=1
        )

        # Act
        result = await use_case.execute(**default_execute_params)

        # Assert
        assert isinstance(result, ProviderAlreadyExistsError)
        assert result.model_name == "my-model"
        assert result.url == "https://example.com/"
        assert result.router_id == 1
