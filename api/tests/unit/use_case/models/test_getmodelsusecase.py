from unittest.mock import AsyncMock, Mock

import pytest

from api.domain.role.entities import Limit, LimitType, PermissionType
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ModelViewFactory
from api.use_cases.models import GetModelsCommand, GetModelsUseCase, GetModelsUseCaseSucess


@pytest.fixture
def mock_model_query():
    query = Mock()
    query.get_models = AsyncMock()
    return query


@pytest.fixture
def use_case(mock_model_query):
    return GetModelsUseCase(model_query=mock_model_query)


@pytest.fixture
def sample_models():
    return [
        ModelViewFactory(router_id=1, id="gpt-4"),
        ModelViewFactory(router_id=2, id="claude-3"),
    ]


@pytest.fixture
def default_command():
    return GetModelsCommand(
        authenticated_user=AuthenticatedUserFactory(
            id=1,
            limits=[Limit(router_id=1, value=100, type=LimitType.RPM), Limit(router_id=2, value=None, type=LimitType.RPM)],
            permissions=[],
        )
    )


class TestGetModelsUseCase:
    @pytest.mark.asyncio
    async def test_should_return_the_models_the_user_has_a_limit_on(self, mock_model_query, sample_models, use_case, default_command):
        # Arrange
        mock_model_query.get_models.return_value = sample_models

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelsUseCaseSucess)
        assert [model.id for model in result.models] == ["gpt-4", "claude-3"]
        mock_model_query.get_models.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_should_return_all_models_when_the_user_is_admin(self, mock_model_query, sample_models, use_case, default_command):
        # Arrange
        default_command.authenticated_user = AuthenticatedUserFactory(id=1, limits=[], permissions=[PermissionType.ADMIN])
        mock_model_query.get_models.return_value = sample_models

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelsUseCaseSucess)
        assert len(result.models) == 2

    @pytest.mark.asyncio
    async def test_should_return_an_empty_list_when_the_user_has_no_limit_and_no_admin_permission(
        self, mock_model_query, sample_models, use_case, default_command
    ):
        # Arrange
        default_command.authenticated_user = AuthenticatedUserFactory(id=1, limits=[], permissions=[])
        mock_model_query.get_models.return_value = sample_models

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelsUseCaseSucess)
        assert result.models == []

    @pytest.mark.asyncio
    async def test_should_not_return_the_models_whose_limit_is_zero(self, mock_model_query, sample_models, use_case, default_command):
        # Arrange
        default_command.authenticated_user = AuthenticatedUserFactory(
            id=1,
            limits=[Limit(router_id=1, value=0, type=LimitType.RPM), Limit(router_id=2, value=10, type=LimitType.RPM)],
            permissions=[],
        )
        mock_model_query.get_models.return_value = sample_models

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelsUseCaseSucess)
        assert [model.id for model in result.models] == ["claude-3"]
