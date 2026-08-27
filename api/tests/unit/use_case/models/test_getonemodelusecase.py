from unittest.mock import AsyncMock, Mock

import pytest

from api.domain.model.errors import ModelNotFoundError
from api.domain.role.entities import Limit, LimitType
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ModelViewFactory
from api.use_cases.models import GetOneModelCommand, GetOneModelUseCase, GetOneModelUseCaseSuccess


@pytest.fixture
def mock_model_query():
    query = Mock()
    query.get_model_by_name_or_alias = AsyncMock()
    return query


@pytest.fixture
def use_case(mock_model_query):
    return GetOneModelUseCase(model_query=mock_model_query)


@pytest.fixture
def model():
    return ModelViewFactory(router_id=1, id="gpt-4", aliases=["gpt-4-turbo"])


@pytest.fixture
def default_command():
    return GetOneModelCommand(
        authenticated_user=AuthenticatedUserFactory(id=1, limits=[Limit(router_id=1, value=100, type=LimitType.RPM)], permissions=[]),
        name="gpt-4",
    )


class TestGetOneModelUseCase:
    @pytest.mark.asyncio
    async def test_should_return_the_model_when_the_user_has_access_to_it(self, mock_model_query, model, use_case, default_command):
        # Arrange
        mock_model_query.get_model_by_name_or_alias.return_value = model

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetOneModelUseCaseSuccess)
        assert result.model.id == "gpt-4"
        mock_model_query.get_model_by_name_or_alias.assert_awaited_once_with(name="gpt-4")

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_the_query_finds_no_model(self, mock_model_query, use_case, default_command):
        # Arrange
        default_command.name = "non-existent-model"
        mock_model_query.get_model_by_name_or_alias.return_value = ModelNotFoundError(name="non-existent-model")

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert result == ModelNotFoundError(name="non-existent-model")

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_the_user_has_no_limit_and_no_admin_permission(
        self, mock_model_query, model, use_case, default_command
    ):
        # Arrange
        default_command.authenticated_user = AuthenticatedUserFactory(id=2, limits=[], permissions=[])
        mock_model_query.get_model_by_name_or_alias.return_value = model

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert result == ModelNotFoundError(name="gpt-4")
