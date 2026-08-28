from unittest.mock import AsyncMock

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider.entities import HostingZone, ProviderType, QoSMetric
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotFoundError
from api.domain.router.errors import RouterNotFoundError
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory
from api.use_cases.admin.providers._updateproviderusecase import UpdateProviderCommand, UpdateProviderUseCase, UpdateProviderUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def provider_repository():
    repository = AsyncMock()
    repository.get_all_providers_of_router.return_value = []
    return repository


@pytest.fixture
def use_case(router_repository, provider_repository):
    return UpdateProviderUseCase(
        router_repository=router_repository,
        provider_repository=provider_repository,
    )


@pytest.fixture
def sample_provider():
    return ProviderFactory(id=10, router_id=1, user_id=1, type=ProviderType.VLLM, timeout=30)


def full_command(provider, **overrides) -> UpdateProviderCommand:
    """Command replacing every persisted field with the current provider values, unless overridden."""
    command = UpdateProviderCommand(
        provider_id=provider.id,
        router_id=provider.router_id,
        timeout=provider.timeout,
        model_hosting_zone=provider.model_hosting_zone,
        model_total_params=provider.model_total_params,
        model_active_params=provider.model_active_params,
        qos_metric=provider.qos_metric,
        qos_limit=provider.qos_limit,
    )
    for field, value in overrides.items():
        setattr(command, field, value)
    return command


def provider_after_command(provider, command: UpdateProviderCommand):
    """Provider state the use case persists for a full-replacement command."""
    return (
        provider.with_router_id(command.router_id)
        .with_timeout(command.timeout)
        .with_model_hosting_zone(command.model_hosting_zone)
        .with_model_total_params(command.model_total_params)
        .with_model_active_params(command.model_active_params)
        .with_qos_metric(command.qos_metric)
        .with_qos_limit(command.qos_limit)
    )


@pytest.fixture
def unchanged_command(sample_provider):
    """Command replaying the current provider state: a full payload that changes nothing."""
    return full_command(sample_provider)


class TestUpdateProviderUseCase:
    @pytest.mark.asyncio
    async def test_should_return_provider_not_found_error_when_provider_does_not_exist(
        self,
        use_case,
        provider_repository,
        router_repository,
        unchanged_command,
    ):
        # Arrange
        provider_repository.get_one_provider.return_value = ProviderNotFoundError(id=10)

        # Act
        result = await use_case.execute(command=unchanged_command)

        # Assert
        assert isinstance(result, ProviderNotFoundError)
        assert result.id == 10
        router_repository.get_router_by_id.assert_not_called()
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_new_router_does_not_exist(
        self,
        use_case,
        provider_repository,
        router_repository,
        sample_provider,
    ):
        # Arrange
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = RouterNotFoundError(id=99)

        # Act
        result = await use_case.execute(command=full_command(sample_provider, router_id=99))

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 99
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_invalid_provider_type_error_when_type_not_compatible_with_new_router(
        self,
        use_case,
        provider_repository,
        router_repository,
    ):
        # Arrange
        provider = ProviderFactory(id=10, router_id=1, user_id=1, type=ProviderType.OPENAI, timeout=30)
        new_router = RouterFactory(id=2, type=RouterType.TEXT_CLASSIFICATION, providers=0)
        provider_repository.get_one_provider.return_value = provider
        router_repository.get_router_by_id.return_value = new_router

        # Act
        result = await use_case.execute(command=full_command(provider, router_id=2))

        # Assert
        assert isinstance(result, InvalidProviderTypeError)
        assert result.provider_type == ProviderType.OPENAI.value
        assert result.router_type == RouterType.TEXT_CLASSIFICATION.value
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_inconsistent_vector_size_error_when_new_router_provider_has_a_different_vector_size(
        self, use_case, provider_repository, router_repository
    ):
        # Arrange

        provider = ProviderFactory(id=10, router_id=1, user_id=1, type=ProviderType.TEI, vector_size=768)
        new_router = RouterFactory(id=2, name="other-router", type=RouterType.TEXT_EMBEDDINGS_INFERENCE, providers=1)
        provider_repository.get_one_provider.return_value = provider
        provider_repository.get_all_providers_of_router.return_value = [ProviderFactory(id=20, router_id=2, type=ProviderType.TEI, vector_size=384)]
        router_repository.get_router_by_id.return_value = new_router

        # Act
        result = await use_case.execute(command=full_command(provider, router_id=2))

        # Assert
        assert isinstance(result, InconsistentModelVectorSizeError)
        assert result.actual_vector_size == 768
        assert result.expected_vector_size == 384
        assert result.router_name == new_router.name
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_inconsistent_max_context_length_error_when_new_router_provider_has_a_different_max_context_length(
        self, use_case, provider_repository, router_repository
    ):
        # Arrange

        provider = ProviderFactory(id=10, router_id=1, user_id=1, type=ProviderType.VLLM, max_context_length=4096)
        new_router = RouterFactory(id=2, name="other-router", type=RouterType.TEXT_GENERATION, providers=1)
        provider_repository.get_one_provider.return_value = provider
        provider_repository.get_all_providers_of_router.return_value = [
            ProviderFactory(id=20, router_id=2, type=ProviderType.VLLM, max_context_length=8192)
        ]
        router_repository.get_router_by_id.return_value = new_router

        # Act
        result = await use_case.execute(command=full_command(provider, router_id=2))

        # Assert
        assert isinstance(result, InconsistentModelMaxContextLengthError)
        assert result.actual_max_context_length == 4096
        assert result.expected_max_context_length == 8192
        assert result.router_name == new_router.name
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_not_call_update_provider_when_no_fields_are_changed(
        self, use_case, provider_repository, sample_provider, unchanged_command
    ):
        # Arrange
        provider_repository.get_one_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(command=unchanged_command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == sample_provider
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_replace_every_persisted_field_with_the_command_values(
        self, use_case, provider_repository, router_repository, sample_provider
    ):
        # Arrange
        command = full_command(
            sample_provider,
            timeout=60,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )
        updated_provider = provider_after_command(sample_provider, command)

        provider_repository.get_one_provider.return_value = sample_provider
        provider_repository.update_provider.return_value = updated_provider

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(updated_provider)
        router_repository.get_router_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_router_is_changed_and_has_provider(
        self, use_case, provider_repository, router_repository, sample_provider
    ):
        # Arrange
        new_router = RouterFactory(id=2, type=RouterType.TEXT_GENERATION, providers=1)
        command = full_command(sample_provider, router_id=new_router.id)
        updated_provider = provider_after_command(sample_provider, command)

        provider_repository.get_one_provider.return_value = sample_provider
        provider_repository.get_all_providers_of_router.return_value = [
            ProviderFactory(
                id=20,
                router_id=2,
                type=ProviderType.VLLM,
                max_context_length=sample_provider.max_context_length,
                vector_size=sample_provider.vector_size,
            )
        ]
        router_repository.get_router_by_id.return_value = new_router
        provider_repository.update_provider.return_value = updated_provider

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(updated_provider)

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_router_is_changed_and_has_no_provider(
        self, use_case, provider_repository, router_repository, sample_provider
    ):
        # Arrange
        new_router = RouterFactory(id=2, type=RouterType.TEXT_GENERATION, providers=0)
        command = full_command(sample_provider, router_id=new_router.id)
        updated_provider = provider_after_command(sample_provider, command)

        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = new_router
        provider_repository.update_provider.return_value = updated_provider

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(updated_provider)

    @pytest.mark.asyncio
    async def test_should_propagate_provider_already_exists_error_from_repository(self, use_case, provider_repository, sample_provider):
        # Arrange
        provider_repository.get_one_provider.return_value = sample_provider
        provider_repository.update_provider.return_value = ProviderAlreadyExistsError(
            model_name=sample_provider.model_name, url=sample_provider.url, router_id=sample_provider.router_id
        )

        # Act
        result = await use_case.execute(command=full_command(sample_provider, timeout=60))

        # Assert
        assert isinstance(result, ProviderAlreadyExistsError)
        assert result.model_name == sample_provider.model_name
        assert result.url == sample_provider.url
        assert result.router_id == sample_provider.router_id

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_model_hosting_zone_is_changed(
        self, use_case, provider_repository, router_repository, sample_provider
    ):
        # Arrange
        new_zone = HostingZone.FRA
        command = full_command(sample_provider, model_hosting_zone=new_zone)
        updated_provider = provider_after_command(sample_provider, command)

        provider_repository.get_one_provider.return_value = sample_provider
        provider_repository.update_provider.return_value = updated_provider

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(updated_provider)
        router_repository.get_router_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_model_total_params_is_changed(
        self, use_case, provider_repository, router_repository, sample_provider
    ):
        # Arrange
        command = full_command(
            sample_provider,
            model_total_params=7,
            model_active_params=3,
            qos_metric=QoSMetric.TTFT,
            qos_limit=100.0,
        )
        updated_provider = provider_after_command(sample_provider, command)

        provider_repository.get_one_provider.return_value = sample_provider
        provider_repository.update_provider.return_value = updated_provider

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(updated_provider)
        router_repository.get_router_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_clear_qos_policy_when_qos_fields_are_none(self, use_case, provider_repository, router_repository):
        # Arrange
        provider = ProviderFactory(id=10, router_id=1, user_id=1, type=ProviderType.VLLM, qos_metric=QoSMetric.TTFT, qos_limit=100.0)
        command = full_command(provider, qos_metric=None, qos_limit=None)
        cleared_provider = provider_after_command(provider, command)

        provider_repository.get_one_provider.return_value = provider
        provider_repository.update_provider.return_value = cleared_provider

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == cleared_provider
        provider_repository.update_provider.assert_called_once_with(cleared_provider)

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_router_is_changed(self, use_case, provider_repository, router_repository, sample_provider):
        # Arrange
        new_router = RouterFactory(id=2, type=RouterType.TEXT_GENERATION, providers=1)
        command = full_command(sample_provider, router_id=new_router.id)
        updated_provider = provider_after_command(sample_provider, command)

        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = new_router
        provider_repository.update_provider.return_value = updated_provider

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(updated_provider)
        router_repository.get_router_by_id.assert_called_once_with(router_id=new_router.id)
