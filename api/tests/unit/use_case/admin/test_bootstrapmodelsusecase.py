from unittest.mock import AsyncMock

import pytest

from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError, ModelNotFoundError
from api.domain.provider.entities import ProviderCapabilities
from api.domain.provider.errors import ProviderAlreadyExistsError, ProviderInvalidResponseError, ProviderNotReachableError
from api.domain.router.entities import RouterType
from api.domain.router.errors import RouterNameAlreadyExistsError
from api.tests.unit.use_case.factories import ProviderFactory, ProviderToCreateFactory, RouterFactory, RouterToCreateFactory
from api.use_cases.models import BootstrapModelsCommand, BootstrapModelsUseCase, BootstrapModelsUseCaseSkipped, BootstrapModelsUseCaseSuccess

BOOTSTRAP_ADMIN_USER_ID = 1


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def provider_capabilities_probe():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository, provider_repository, provider_capabilities_probe):
    return BootstrapModelsUseCase(
        router_repository=router_repository,
        provider_repository=provider_repository,
        provider_capabilities_probe=provider_capabilities_probe,
    )


class TestBootstrapModelsUseCase:
    @pytest.mark.asyncio
    async def test_skips_when_routers_already_exist(self, use_case, router_repository, provider_repository, provider_capabilities_probe):
        # Arrange
        existing_routers = [RouterFactory(id=1), RouterFactory(id=2)]
        router_repository.get_all_routers.return_value = existing_routers

        # Act
        result = await use_case.execute(
            BootstrapModelsCommand(routers_to_create=[RouterToCreateFactory()], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID)
        )

        # Assert
        assert result == BootstrapModelsUseCaseSkipped(number_of_routers=2)
        router_repository.create_router.assert_not_awaited()
        provider_capabilities_probe.get_capabilities.assert_not_awaited()
        provider_repository.create_provider.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_successfully_creates_router_with_single_provider(
        self, use_case, router_repository, provider_repository, provider_capabilities_probe
    ):
        # Arrange
        provider_to_create = ProviderToCreateFactory(qos_limit=8)
        router_to_create = RouterToCreateFactory(providers=[provider_to_create], qos_retries_before_reject=3)
        router = RouterFactory(id=10, name=router_to_create.name, type=RouterType.TEXT_GENERATION, max_context_length=4096, vector_size=None)
        provider = ProviderFactory(id=100, router_id=10, user_id=BOOTSTRAP_ADMIN_USER_ID)

        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_capabilities_probe.get_capabilities.return_value = ProviderCapabilities(max_context_length=4096, vector_size=None)
        provider_repository.create_provider.return_value = provider

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=[router_to_create], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert result == BootstrapModelsUseCaseSuccess(number_of_routers=1)

        router_repository.create_router.assert_awaited_once_with(
            name=router_to_create.name,
            router_type=router_to_create.type,
            load_balancing_strategy=router_to_create.load_balancing_strategy,
            qos_retries_before_reject=router_to_create.qos_retries_before_reject,
            cost_prompt_tokens=router_to_create.cost_prompt_tokens,
            cost_completion_tokens=router_to_create.cost_completion_tokens,
            user_id=BOOTSTRAP_ADMIN_USER_ID,
            aliases=router_to_create.aliases,
        )
        provider_capabilities_probe.get_capabilities.assert_awaited_once_with(
            router_type=router.type,
            provider_type=provider_to_create.type,
            url=provider_to_create.url,
            key=provider_to_create.key,
            timeout=provider_to_create.timeout,
            model_name=provider_to_create.model_name,
        )
        provider_repository.create_provider.assert_awaited_once_with(
            router_id=router.id,
            user_id=BOOTSTRAP_ADMIN_USER_ID,
            provider_type=provider_to_create.type,
            url=provider_to_create.url,
            key=provider_to_create.key,
            basic_auth=provider_to_create.basic_auth,
            timeout=provider_to_create.timeout,
            qos_limit=provider_to_create.qos_limit,
            model_name=provider_to_create.model_name,
            model_hosting_zone=provider_to_create.model_hosting_zone,
            model_total_params=provider_to_create.model_total_params,
            model_active_params=provider_to_create.model_active_params,
            max_context_length=4096,
            vector_size=None,
        )
        router_repository.delete_all_routers.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_successfully_creates_multiple_routers_with_multiple_providers(
        self, use_case, router_repository, provider_repository, provider_capabilities_probe
    ):
        # Arrange
        first_router_to_create = RouterToCreateFactory(
            name="text-gen",
            type=RouterType.TEXT_GENERATION,
            providers=[
                ProviderToCreateFactory(model_name="model-a", url="https://provider-a.com/"),
                ProviderToCreateFactory(model_name="model-b", url="https://provider-b.com/"),
            ],
        )
        second_router_to_create = RouterToCreateFactory(
            name="embeddings",
            type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            providers=[ProviderToCreateFactory(tei=True, model_name="embed-model", url="https://embed.com/")],
        )

        first_router = RouterFactory(id=1, name="text-gen", type=RouterType.TEXT_GENERATION)
        second_router = RouterFactory(id=2, name="embeddings", type=RouterType.TEXT_EMBEDDINGS_INFERENCE)

        router_repository.get_all_routers.return_value = []
        router_repository.create_router.side_effect = [first_router, second_router]
        provider_capabilities_probe.get_capabilities.side_effect = [
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
            BootstrapModelsCommand(
                routers_to_create=[first_router_to_create, second_router_to_create], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID
            )
        )

        # Assert
        assert result == BootstrapModelsUseCaseSuccess(number_of_routers=2)
        assert router_repository.create_router.await_count == 2
        assert provider_capabilities_probe.get_capabilities.await_count == 3
        assert provider_repository.create_provider.await_count == 3
        router_repository.delete_all_routers.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_router_name_already_exists_error_when_duplicate_name(
        self, use_case, router_repository, provider_repository, provider_capabilities_probe
    ):
        # Arrange
        routers_to_create = [
            RouterToCreateFactory(name="duplicate"),
            RouterToCreateFactory(name="duplicate"),
        ]
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=routers_to_create, bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert result == RouterNameAlreadyExistsError(name="duplicate")
        router_repository.create_router.assert_not_awaited()
        provider_capabilities_probe.get_capabilities.assert_not_awaited()
        provider_repository.create_provider.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_router_name_already_exists_error_when_duplicate_alias(self, use_case, router_repository):
        # Arrange
        routers_to_create = [
            RouterToCreateFactory(name="router-a", aliases=["shared-alias"]),
            RouterToCreateFactory(name="router-b", aliases=["shared-alias"]),
        ]
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=routers_to_create, bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert result == RouterNameAlreadyExistsError(name="shared-alias")
        router_repository.create_router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_router_name_already_exists_error_when_alias_clashes_with_name(self, use_case, router_repository):
        # Arrange
        routers_to_create = [
            RouterToCreateFactory(name="router-a"),
            RouterToCreateFactory(name="router-b", aliases=["router-a"]),
        ]
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=routers_to_create, bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert result == RouterNameAlreadyExistsError(name="router-a")
        router_repository.create_router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_provider_already_exists_error_when_duplicate_within_router(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_capabilities_probe,
    ):
        # Arrange
        router_to_create = RouterToCreateFactory(
            providers=[
                ProviderToCreateFactory(model_name="model-a", url="https://provider.com/"),
                ProviderToCreateFactory(model_name="model-a", url="https://provider.com/"),
            ],
        )
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=[router_to_create], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert isinstance(result, ProviderAlreadyExistsError)
        assert result.model_name == "model-a"
        assert result.url == "https://provider.com/"
        router_repository.create_router.assert_not_awaited()
        provider_capabilities_probe.get_capabilities.assert_not_awaited()
        provider_repository.create_provider.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_provider_not_reachable_error_and_rolls_back(
        self, use_case, router_repository, provider_repository, provider_capabilities_probe
    ):
        # Arrange
        router_to_create = RouterToCreateFactory()
        router = RouterFactory(id=1, name=router_to_create.name, type=RouterType.TEXT_GENERATION)
        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_capabilities_probe.get_capabilities.return_value = ProviderNotReachableError(
            model_name="my-model", status_code=500, detail="error_detail"
        )

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=[router_to_create], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert result == ProviderNotReachableError(model_name="my-model", status_code=500, detail="error_detail")
        provider_repository.create_provider.assert_not_awaited()
        router_repository.delete_all_routers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_provider_invalid_response_error_and_rolls_back(
        self, use_case, router_repository, provider_repository, provider_capabilities_probe
    ):
        # Arrange
        router_to_create = RouterToCreateFactory()
        router = RouterFactory(id=1, name=router_to_create.name, type=RouterType.TEXT_EMBEDDINGS_INFERENCE)
        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_capabilities_probe.get_capabilities.return_value = ProviderInvalidResponseError(
            model_name="my-model", detail="no embedding returned"
        )

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=[router_to_create], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert result == ProviderInvalidResponseError(model_name="my-model", detail="no embedding returned")
        provider_repository.create_provider.assert_not_awaited()
        router_repository.delete_all_routers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_model_not_found_error_and_rolls_back(self, use_case, router_repository, provider_repository, provider_capabilities_probe):
        # Arrange
        router_to_create = RouterToCreateFactory()
        router = RouterFactory(id=1, name=router_to_create.name, type=RouterType.TEXT_GENERATION)
        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_capabilities_probe.get_capabilities.return_value = ModelNotFoundError(name="my-model")

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=[router_to_create], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

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
        provider_capabilities_probe,
    ):
        # Arrange
        router_to_create = RouterToCreateFactory(
            providers=[
                ProviderToCreateFactory(model_name="model-a", url="https://provider-a.com/"),
                ProviderToCreateFactory(model_name="model-b", url="https://provider-b.com/"),
            ],
        )
        router = RouterFactory(id=1, name=router_to_create.name, type=RouterType.TEXT_GENERATION)
        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_capabilities_probe.get_capabilities.side_effect = [
            ProviderCapabilities(max_context_length=4096, vector_size=None),
            ProviderCapabilities(max_context_length=2048, vector_size=None),
        ]
        provider_repository.create_provider.return_value = ProviderFactory(id=10, router_id=1)

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=[router_to_create], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert result == InconsistentModelMaxContextLengthError(
            actual_max_context_length=2048, expected_max_context_length=4096, router_name=router.name
        )
        provider_repository.create_provider.assert_awaited_once()
        router_repository.delete_all_routers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_inconsistent_vector_size_error_and_rolls_back(
        self, use_case, router_repository, provider_repository, provider_capabilities_probe
    ):
        # Arrange
        router_to_create = RouterToCreateFactory(
            type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            providers=[
                ProviderToCreateFactory(tei=True, model_name="embed-a", url="https://provider-a.com/"),
                ProviderToCreateFactory(tei=True, model_name="embed-b", url="https://provider-b.com/"),
            ],
        )
        router = RouterFactory(id=1, name=router_to_create.name, type=RouterType.TEXT_EMBEDDINGS_INFERENCE)
        router_repository.get_all_routers.return_value = []
        router_repository.create_router.return_value = router
        provider_capabilities_probe.get_capabilities.side_effect = [
            ProviderCapabilities(max_context_length=512, vector_size=768),
            ProviderCapabilities(max_context_length=512, vector_size=384),
        ]
        provider_repository.create_provider.return_value = ProviderFactory(id=10, router_id=1)

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=[router_to_create], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert result == InconsistentModelVectorSizeError(
            actual_vector_size=384,
            expected_vector_size=768,
            router_name=router.name,
        )
        provider_repository.create_provider.assert_awaited_once()
        router_repository.delete_all_routers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_success_with_no_routers_to_create(self, use_case, router_repository, provider_repository, provider_capabilities_probe):
        # Arrange
        router_repository.get_all_routers.return_value = []

        # Act
        result = await use_case.execute(BootstrapModelsCommand(routers_to_create=[], bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID))

        # Assert
        assert result == BootstrapModelsUseCaseSuccess(number_of_routers=0)
        router_repository.create_router.assert_not_awaited()
        provider_capabilities_probe.get_capabilities.assert_not_awaited()
        provider_repository.create_provider.assert_not_awaited()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
