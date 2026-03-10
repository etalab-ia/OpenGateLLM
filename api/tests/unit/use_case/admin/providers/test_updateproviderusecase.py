from unittest.mock import AsyncMock

import pytest

from api.domain.model import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.model import ModelType as RouterType
from api.domain.provider.entities import ProviderCarbonFootprintZone, ProviderType
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotFoundError
from api.domain.router.errors import RouterNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.schemas.core.models import Metric
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory, UserInfoFactory
from api.use_cases.admin.providers._updateproviderusecase import UpdateProviderCommand, UpdateProviderUseCase, UpdateProviderUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def user_info_repository():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository, provider_repository, user_info_repository):
    return UpdateProviderUseCase(
        router_repository=router_repository,
        provider_repository=provider_repository,
        user_info_repository=user_info_repository,
    )


@pytest.fixture
def admin_user_info():
    return UserInfoFactory(id=1, admin=True)


@pytest.fixture
def unauthorized_user_info():
    return UserInfoFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def sample_router():
    return RouterFactory(id=1, name="test-router", type=RouterType.TEXT_GENERATION, providers=0)


@pytest.fixture
def sample_provider():
    return ProviderFactory(id=10, router_id=1, user_id=1, type=ProviderType.VLLM, timeout=30)


@pytest.fixture
def default_command():
    return UpdateProviderCommand(
        provider_id=10,
        router_id=None,
        user_id=1,
        timeout=None,
        model_hosting_zone=None,
        model_total_params=None,
        model_active_params=None,
        qos_metric=None,
        qos_limit=None,
    )


class TestUpdateProviderUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(
        self, use_case, provider_repository, router_repository, user_info_repository, unauthorized_user_info, default_command
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = unauthorized_user_info

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        provider_repository.get_one_provider.assert_not_called()
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_provider_not_found_error_when_provider_does_not_exist(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, default_command
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = None

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, ProviderNotFoundError)
        assert result.provider_id == 10
        router_repository.get_router_by_id.assert_not_called()
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_current_router_does_not_exist(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, default_command
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = None

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.router_id == sample_provider.router_id
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_new_router_does_not_exist(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, sample_router
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.side_effect = [sample_router, None]

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=99,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.router_id == 99
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_invalid_provider_type_error_when_type_not_compatible_with_new_router(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        current_router = RouterFactory(id=1, type=RouterType.TEXT_GENERATION)
        # TEI provider is not compatible with TEXT_CLASSIFICATION for VLLM type
        new_router = RouterFactory(id=2, type=RouterType.TEXT_CLASSIFICATION, providers=0)
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.side_effect = [current_router, new_router]

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=2,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, InvalidProviderTypeError)
        assert result.provider_type == ProviderType.VLLM.value
        assert result.router_type == RouterType.TEXT_CLASSIFICATION.value
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_inconsistent_vector_size_error_when_new_router_has_different_vector_size(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        provider = ProviderFactory(id=10, router_id=1, user_id=1, type=ProviderType.TEI)
        current_router = RouterFactory(id=1, type=RouterType.TEXT_EMBEDDINGS_INFERENCE, vector_size=768, providers=1)
        new_router = RouterFactory(id=2, name="other-router", type=RouterType.TEXT_EMBEDDINGS_INFERENCE, vector_size=384, providers=1)
        provider_repository.get_one_provider.return_value = provider
        router_repository.get_router_by_id.side_effect = [current_router, new_router]

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=2,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, InconsistentModelVectorSizeError)
        assert result.actual_vector_size == 768
        assert result.expected_vector_size == 384
        assert result.router_name == new_router.name
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_inconsistent_max_context_length_error_when_new_router_has_different_max_context_length(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        provider = ProviderFactory(id=10, router_id=1, user_id=1, type=ProviderType.VLLM)
        current_router = RouterFactory(id=1, type=RouterType.TEXT_GENERATION, max_context_length=4096, vector_size=None, providers=1)
        new_router = RouterFactory(id=2, name="other-router", type=RouterType.TEXT_GENERATION, max_context_length=8192, vector_size=None, providers=1)
        provider_repository.get_one_provider.return_value = provider
        router_repository.get_router_by_id.side_effect = [current_router, new_router]

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=2,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, InconsistentModelMaxContextLengthError)
        assert result.actual_max_context_length == 4096
        assert result.expected_max_context_length == 8192
        assert result.router_name == new_router.name
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_not_call_update_provider_when_no_fields_are_changed(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, sample_router, default_command
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = sample_router

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == sample_provider
        provider_repository.update_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_timeout_is_changed(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, sample_router
    ):
        # Arrange
        updated_provider = sample_provider.with_timeout(60)
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = sample_router
        provider_repository.update_provider.return_value = updated_provider

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=None,
            user_id=1,
            timeout=60,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(sample_provider.with_timeout(60))

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_router_is_changed_and_has_provider(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider
    ):
        # Arrange
        current_router = RouterFactory(id=1, type=RouterType.TEXT_GENERATION, providers=0)
        new_router = RouterFactory(id=2, type=RouterType.TEXT_GENERATION, providers=1)
        updated_provider = sample_provider.with_router_id(new_router.id)
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.side_effect = [current_router, new_router]
        provider_repository.update_provider.return_value = updated_provider

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=2,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(sample_provider.with_router_id(new_router.id))

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_router_is_changed_and_has_no_provider(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider
    ):
        # Arrange
        current_router = RouterFactory(id=1, type=RouterType.TEXT_GENERATION, providers=0)
        new_router = RouterFactory(id=2, type=RouterType.TEXT_GENERATION, providers=0)
        updated_provider = sample_provider.with_router_id(new_router.id)
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.side_effect = [current_router, new_router]
        provider_repository.update_provider.return_value = updated_provider

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=2,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(sample_provider.with_router_id(new_router.id))

    @pytest.mark.asyncio
    async def test_should_propagate_provider_already_exists_error_from_repository(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, sample_router
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = sample_router
        provider_repository.update_provider.return_value = ProviderAlreadyExistsError(
            model_name=sample_provider.model_name, url=sample_provider.url, router_id=sample_provider.router_id
        )

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=None,
            user_id=1,
            timeout=60,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, ProviderAlreadyExistsError)
        assert result.model_name == sample_provider.model_name
        assert result.url == sample_provider.url
        assert result.router_id == sample_provider.router_id

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_model_hosting_zone_is_changed(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, sample_router
    ):
        # Arrange
        new_zone = ProviderCarbonFootprintZone.FRA
        updated_provider = sample_provider.with_model_hosting_zone(new_zone)
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = sample_router
        provider_repository.update_provider.return_value = updated_provider

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=None,
            user_id=1,
            timeout=None,
            model_hosting_zone=new_zone,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(sample_provider.with_model_hosting_zone(new_zone))

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_model_total_params_is_changed(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, sample_router
    ):
        # Arrange
        updated_provider = sample_provider.with_model_total_params(7)
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = sample_router
        provider_repository.update_provider.return_value = updated_provider

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=None,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=7,
            model_active_params=None,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(sample_provider.with_model_total_params(7))

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_model_active_params_is_changed(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, sample_router
    ):
        # Arrange
        updated_provider = sample_provider.with_model_active_params(3)
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = sample_router
        provider_repository.update_provider.return_value = updated_provider

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=None,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=3,
            qos_metric=None,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(sample_provider.with_model_active_params(3))

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_qos_metric_is_changed(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, sample_router
    ):
        # Arrange
        updated_provider = sample_provider.with_qos_metric(Metric.TTFT)
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = sample_router
        provider_repository.update_provider.return_value = updated_provider

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=None,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=Metric.TTFT,
            qos_limit=None,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(sample_provider.with_qos_metric(Metric.TTFT))

    @pytest.mark.asyncio
    async def test_should_return_updated_provider_when_qos_limit_is_changed(
        self, use_case, provider_repository, router_repository, user_info_repository, admin_user_info, sample_provider, sample_router
    ):
        # Arrange
        updated_provider = sample_provider.with_qos_limit(100.0)
        user_info_repository.get_user_info.return_value = admin_user_info
        provider_repository.get_one_provider.return_value = sample_provider
        router_repository.get_router_by_id.return_value = sample_router
        provider_repository.update_provider.return_value = updated_provider

        command = UpdateProviderCommand(
            provider_id=10,
            router_id=None,
            user_id=1,
            timeout=None,
            model_hosting_zone=None,
            model_total_params=None,
            model_active_params=None,
            qos_metric=None,
            qos_limit=100.0,
        )

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateProviderUseCaseSuccess)
        assert result.provider == updated_provider
        provider_repository.update_provider.assert_called_once_with(sample_provider.with_qos_limit(100.0))
