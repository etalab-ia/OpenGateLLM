from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError, ModelNotFoundError
from api.domain.provider.errors import ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router.errors import RouterNameAlreadyExistsError
from api.schemas.core.configuration import Configuration, Dependencies, Settings
from api.use_cases.models import BootstrapModelsUseCaseSkipped, BootstrapModelsUseCaseSuccess
from api.utils.context import global_context
from api.utils.lifespan import bootstrap_models

BOOTSTRAP_ADMIN_USER_ID = 1


@pytest.fixture
def bootstrap_configuration() -> Configuration:
    return Configuration.model_construct(
        settings=Settings.model_construct(app_title="test"),
        dependencies=Dependencies.model_construct(sentry=None),
        models=[],
    )


@pytest.fixture
def postgres_session():
    return AsyncMock()


@pytest.fixture(autouse=True)
def _set_global_redis_pool():
    previous = global_context.redis_pool
    global_context.redis_pool = MagicMock()
    try:
        yield
    finally:
        global_context.redis_pool = previous


class TestBootstrapModels:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "use_case_result,expected_count",
        [
            (BootstrapModelsUseCaseSuccess(number_of_routers=2), 2),
            (BootstrapModelsUseCaseSkipped(number_of_routers=1), 1),
            (BootstrapModelsUseCaseSuccess(number_of_routers=0), 0),
        ],
    )
    async def test_happy_path(self, bootstrap_configuration, postgres_session, use_case_result, expected_count):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result

        with patch("api.utils.lifespan.BootstrapModelsUseCase", return_value=mock_use_case):
            result = await bootstrap_models(
                configuration=bootstrap_configuration,
                postgres_session=postgres_session,
                bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
            )

        assert result == expected_count
        mock_use_case.execute.assert_awaited_once_with(
            routers_to_create=bootstrap_configuration.models,
            bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "use_case_result,expected_message",
        [
            (
                RouterNameAlreadyExistsError(name="duplicate"),
                "Router name or alias is already taken (duplicate) by another router.",
            ),
            (
                ModelNotFoundError(name="my-model"),
                "Provider my-model are not found.",
            ),
            (
                ProviderAlreadyExistsError(model_name="model-a", url="https://provider.com/", router_id=0),
                "Provider model-a already exists (https://provider.com/) for the same router (0).",
            ),
            (
                ProviderNotReachableError(model_name="my-model", status_code=500, detail="error_detail"),
                "Provider my-model not reachable (500): error_detail",
            ),
            (
                InconsistentModelVectorSizeError(actual_vector_size=384, expected_vector_size=768, router_name="my-router"),
                "Inconsistent model vector size (my-router).",
            ),
            (
                InconsistentModelMaxContextLengthError(
                    actual_max_context_length=2048,
                    expected_max_context_length=4096,
                    router_name="my-router",
                ),
                "Inconsistent model max context length (my-router).",
            ),
        ],
    )
    async def test_error_maps_to_runtime_error(self, bootstrap_configuration, postgres_session, use_case_result, expected_message):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result

        with patch("api.utils.lifespan.BootstrapModelsUseCase", return_value=mock_use_case):
            with pytest.raises(RuntimeError) as exc_info:
                await bootstrap_models(
                    configuration=bootstrap_configuration,
                    postgres_session=postgres_session,
                    bootstrap_admin_user_id=BOOTSTRAP_ADMIN_USER_ID,
                )

        assert str(exc_info.value) == expected_message
