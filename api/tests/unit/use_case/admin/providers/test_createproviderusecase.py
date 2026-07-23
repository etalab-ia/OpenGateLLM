from unittest.mock import AsyncMock

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError, ModelNotFoundError
from api.domain.provider.entities import HostingZone, ProviderCapabilities, ProviderType
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router.errors import RouterNotFoundError
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory
from api.use_cases.admin.providers import CreateProviderCommand, CreateProviderUseCase, CreateProviderUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def provider_capabilities_repository():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository, provider_repository, provider_capabilities_repository):
    return CreateProviderUseCase(
        router_repository=router_repository,
        provider_repository=provider_repository,
        provider_capabilities_repository=provider_capabilities_repository,
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
def default_command():
    return CreateProviderCommand(
        router_id=1,
        user_id=1,
        provider_type=ProviderType.VLLM,
        url="https://example.com/",
        key=None,
        basic_auth=None,
        timeout=30,
        model_name="my-model",
        model_hosting_zone=HostingZone.WOR,
        model_total_params=0,
        model_active_params=0,
        qos_metric=None,
        qos_limit=None,
    )


COMPATIBLE_PROVIDER_ROUTER_PAIRS: list[tuple[RouterType, ProviderType]] = [
    (RouterType.AUTOMATIC_SPEECH_RECOGNITION, ProviderType.ALBERT),
    (RouterType.AUTOMATIC_SPEECH_RECOGNITION, ProviderType.MISTRAL),
    (RouterType.AUTOMATIC_SPEECH_RECOGNITION, ProviderType.OPENAI),
    (RouterType.AUTOMATIC_SPEECH_RECOGNITION, ProviderType.VLLM),
    (RouterType.IMAGE_TEXT_TO_TEXT, ProviderType.ALBERT),
    (RouterType.IMAGE_TEXT_TO_TEXT, ProviderType.MISTRAL),
    (RouterType.IMAGE_TEXT_TO_TEXT, ProviderType.OPENAI),
    (RouterType.IMAGE_TEXT_TO_TEXT, ProviderType.VLLM),
    (RouterType.TEXT_EMBEDDINGS_INFERENCE, ProviderType.ALBERT),
    (RouterType.TEXT_EMBEDDINGS_INFERENCE, ProviderType.OPENAI),
    (RouterType.TEXT_EMBEDDINGS_INFERENCE, ProviderType.MISTRAL),
    (RouterType.TEXT_EMBEDDINGS_INFERENCE, ProviderType.TEI),
    (RouterType.TEXT_EMBEDDINGS_INFERENCE, ProviderType.VLLM),
    (RouterType.TEXT_GENERATION, ProviderType.ALBERT),
    (RouterType.TEXT_GENERATION, ProviderType.MISTRAL),
    (RouterType.TEXT_GENERATION, ProviderType.OPENAI),
    (RouterType.TEXT_GENERATION, ProviderType.VLLM),
    (RouterType.TEXT_CLASSIFICATION, ProviderType.ALBERT),
    (RouterType.TEXT_CLASSIFICATION, ProviderType.TEI),
    (RouterType.TEXT_CLASSIFICATION, ProviderType.VLLM),
    (RouterType.IMAGE_TO_TEXT, ProviderType.MISTRAL),
]

INCOMPATIBLE_PROVIDER_ROUTER_PAIRS: list[tuple[RouterType, ProviderType]] = [
    (RouterType.AUTOMATIC_SPEECH_RECOGNITION, ProviderType.TEI),
    (RouterType.IMAGE_TEXT_TO_TEXT, ProviderType.TEI),
    (RouterType.TEXT_GENERATION, ProviderType.TEI),
    (RouterType.TEXT_CLASSIFICATION, ProviderType.OPENAI),
    (RouterType.TEXT_CLASSIFICATION, ProviderType.MISTRAL),
    (RouterType.IMAGE_TO_TEXT, ProviderType.ALBERT),
    (RouterType.IMAGE_TO_TEXT, ProviderType.OPENAI),
    (RouterType.IMAGE_TO_TEXT, ProviderType.TEI),
    (RouterType.IMAGE_TO_TEXT, ProviderType.VLLM),
]


def capabilities_for(router_type: RouterType) -> ProviderCapabilities:
    if router_type == RouterType.TEXT_EMBEDDINGS_INFERENCE:
        return ProviderCapabilities(max_context_length=512, vector_size=768)
    return ProviderCapabilities(max_context_length=4096, vector_size=None)


def with_provider_type(command: CreateProviderCommand, provider_type: ProviderType) -> CreateProviderCommand:
    return CreateProviderCommand(
        router_id=command.router_id,
        user_id=command.user_id,
        provider_type=provider_type,
        url=command.url,
        key=command.key,
        basic_auth=command.basic_auth,
        timeout=command.timeout,
        model_name=command.model_name,
        model_hosting_zone=command.model_hosting_zone,
        model_total_params=command.model_total_params,
        model_active_params=command.model_active_params,
        qos_metric=command.qos_metric,
        qos_limit=command.qos_limit,
    )


class TestCreateProviderUseCase:
    @pytest.mark.asyncio
    async def test_should_create_provider_when_router_has_a_different_provider(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_capabilities_repository,
        sample_router_with_providers,
        sample_provider,
        default_command,
    ):
        # Arrange

        router_repository.get_router_by_id.return_value = sample_router_with_providers
        provider_capabilities_repository.get_provider_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
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
            basic_auth=None,
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
        provider_capabilities_repository,
        sample_embedding_router_with_providers,
        sample_provider,
        default_command,
    ):
        # Arrange

        router_repository.get_router_by_id.return_value = sample_embedding_router_with_providers
        provider_capabilities_repository.get_provider_capabilities.return_value = ProviderCapabilities(max_context_length=512, vector_size=768)
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
            basic_auth=None,
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
        self, use_case, router_repository, provider_repository, provider_capabilities_repository, default_command
    ):
        # Arrange

        router_repository.get_router_by_id.return_value = None

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 1
        provider_capabilities_repository.get_provider_capabilities.assert_not_called()
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("router_type", "provider_type"),
        COMPATIBLE_PROVIDER_ROUTER_PAIRS,
        ids=[f"{router_type.value}-{provider_type.value}" for router_type, provider_type in COMPATIBLE_PROVIDER_ROUTER_PAIRS],
    )
    async def test_should_create_provider_when_provider_type_is_compatible(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_capabilities_repository,
        default_command,
        router_type,
        provider_type,
    ):
        # Arrange
        capabilities = capabilities_for(router_type)
        provider = ProviderFactory(id=1, router_id=1, user_id=1, type=provider_type, url="https://example.com/", model_name="my-model")
        router_repository.get_router_by_id.return_value = RouterFactory(id=1, name="test-router", type=router_type, providers=0)
        provider_capabilities_repository.get_provider_capabilities.return_value = capabilities
        provider_repository.create_provider.return_value = provider
        command = with_provider_type(default_command, provider_type)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, CreateProviderUseCaseSuccess)
        assert result.provider == provider
        provider_capabilities_repository.get_provider_capabilities.assert_called_once_with(
            router_type=router_type,
            provider_type=provider_type,
            url="https://example.com/",
            key=None,
            timeout=30,
            model_name="my-model",
        )
        provider_repository.create_provider.assert_called_once_with(
            router_id=1,
            user_id=1,
            provider_type=provider_type,
            url="https://example.com/",
            key=None,
            basic_auth=None,
            timeout=30,
            model_name="my-model",
            model_hosting_zone=HostingZone.WOR,
            model_total_params=0,
            model_active_params=0,
            qos_metric=None,
            qos_limit=None,
            max_context_length=capabilities.max_context_length,
            vector_size=capabilities.vector_size,
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("router_type", "provider_type"),
        INCOMPATIBLE_PROVIDER_ROUTER_PAIRS,
        ids=[f"{router_type.value}-{provider_type.value}" for router_type, provider_type in INCOMPATIBLE_PROVIDER_ROUTER_PAIRS],
    )
    async def test_should_return_invalid_provider_type_error_when_provider_type_is_not_compatible(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_capabilities_repository,
        default_command,
        router_type,
        provider_type,
    ):
        # Arrange
        router_repository.get_router_by_id.return_value = RouterFactory(id=1, name="test-router", type=router_type)
        command = with_provider_type(default_command, provider_type)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, InvalidProviderTypeError)
        assert result.provider_type == provider_type.value
        assert result.router_type == router_type.value
        provider_capabilities_repository.get_provider_capabilities.assert_not_called()
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_error_when_gateway_fails(
        self, use_case, router_repository, provider_repository, provider_capabilities_repository, sample_router, default_command
    ):
        # Arrange

        router_repository.get_router_by_id.return_value = sample_router
        provider_capabilities_repository.get_provider_capabilities.return_value = ProviderNotReachableError(
            model_name="my-model", status_code=500, detail="error_detail"
        )

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, ProviderNotReachableError)
        assert result.model_name == "my-model"
        assert result.status_code == 500
        assert result.detail == "error_detail"
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_error_when_model_is_missing(
        self, use_case, router_repository, provider_repository, provider_capabilities_repository, sample_router, default_command
    ):
        # Arrange

        router_repository.get_router_by_id.return_value = sample_router
        provider_capabilities_repository.get_provider_capabilities.return_value = ModelNotFoundError(name="my-model")

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, ModelNotFoundError)
        assert result.name == "my-model"
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_inconsistent_max_context_length_error_when_mismatch(
        self, use_case, router_repository, provider_repository, provider_capabilities_repository, sample_router_with_providers, default_command
    ):
        # Arrange

        router_repository.get_router_by_id.return_value = sample_router_with_providers
        provider_capabilities_repository.get_provider_capabilities.return_value = ProviderCapabilities(max_context_length=2048, vector_size=None)

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
        provider_capabilities_repository,
        sample_embedding_router_with_providers,
        default_command,
    ):
        # Arrange

        router_repository.get_router_by_id.return_value = sample_embedding_router_with_providers
        provider_capabilities_repository.get_provider_capabilities.return_value = ProviderCapabilities(max_context_length=512, vector_size=384)

        # Act
        result = await use_case.execute(with_provider_type(default_command, ProviderType.TEI))

        # Assert
        assert isinstance(result, InconsistentModelVectorSizeError)
        assert result.actual_vector_size == 384
        assert result.expected_vector_size == 768
        provider_repository.create_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_provider_already_exists_error(
        self, use_case, router_repository, provider_repository, provider_capabilities_repository, sample_router, default_command
    ):
        # Arrange

        router_repository.get_router_by_id.return_value = sample_router
        provider_capabilities_repository.get_provider_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
        provider_repository.create_provider.return_value = ProviderAlreadyExistsError(model_name="my-model", url="https://example.com/", router_id=1)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, ProviderAlreadyExistsError)
        assert result.model_name == "my-model"
        assert result.url == "https://example.com/"
        assert result.router_id == 1
