from unittest.mock import AsyncMock, create_autospec

import pytest

from api.domain.model import ModelTokenizer, ModelTokenizerLoader
from api.domain.model.errors import ModelTokenizerNotLoadableError
from api.domain.router.entities import RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import CreateRouterCommand, CreateRouterUseCase


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def mock_model_tokenizer_loader():
    loader = create_autospec(ModelTokenizerLoader, instance=True, spec_set=True)
    loader.load.return_value = create_autospec(ModelTokenizer, instance=True, spec_set=True)
    return loader


@pytest.fixture
def use_case(router_repository, mock_model_tokenizer_loader):
    return CreateRouterUseCase(router_repository=router_repository, model_tokenizer_loader=mock_model_tokenizer_loader)


@pytest.fixture
def sample_router_with_aliases():
    return RouterFactory(
        id=1,
        name="test-model",
        type=RouterType.TEXT_GENERATION,
        aliases=["alias1", "alias2"],
        user_id=1,
        qos_retries_before_reject=3,
        cost_prompt_tokens=0.01,
        cost_completion_tokens=0.02,
        providers=0,
    )


class TestCreateRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_create_router_with_aliases_when_aliases_are_given(self, use_case, router_repository, sample_router_with_aliases):
        # Arrange
        router_repository.create_router.return_value = sample_router_with_aliases

        # Act
        result = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=["alias1", "alias2"],
                cost_prompt_tokens=0.01,
                cost_completion_tokens=0.02,
                qos_retries_before_reject=3,
            )
        )

        # Assert
        assert result.router == sample_router_with_aliases

        router_repository.create_router.assert_called_once_with(
            name="test-model",
            router_type=RouterType.TEXT_GENERATION,
            qos_retries_before_reject=3,
            cost_prompt_tokens=0.01,
            cost_completion_tokens=0.02,
            user_id=1,
            aliases=["alias1", "alias2"],
            tokenizer=None,
        )

    @pytest.mark.asyncio
    async def test_should_create_router_without_aliases_if_no_alias_is_given(self, use_case, router_repository):
        # Arrange
        router_without_aliases = RouterFactory(
            id=2,
            name="model-no-alias",
            type=RouterType.TEXT_GENERATION,
            aliases=[],
            user_id=1,
        )

        router_repository.create_router.return_value = router_without_aliases

        # Act
        result = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="model-no-alias",
                router_type=RouterType.TEXT_GENERATION,
                aliases=[],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
            )
        )

        # Assert
        assert result.router == router_without_aliases
        router_repository.create_router.assert_called_once_with(
            name="model-no-alias",
            router_type=RouterType.TEXT_GENERATION,
            qos_retries_before_reject=None,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=1,
            aliases=[],
            tokenizer=None,
        )

    @pytest.mark.asyncio
    async def test_should_return_router_alias_already_exists_when_alias_already_exists(self, use_case, router_repository):
        # Arrange
        router_repository.create_router.return_value = RouterAliasAlreadyExistsError(aliases=["alias1"])

        # Act
        error = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=["alias1", "alias2"],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
            )
        )

        # Assert
        assert isinstance(error, RouterAliasAlreadyExistsError)
        router_repository.create_router.assert_called_once_with(
            aliases=["alias1", "alias2"],
            cost_completion_tokens=0.0,
            cost_prompt_tokens=0.0,
            qos_retries_before_reject=None,
            name="test-model",
            router_type=RouterType.TEXT_GENERATION,
            user_id=1,
            tokenizer=None,
        )

    @pytest.mark.asyncio
    async def test_should_return_router_name_already_exists_when_name_already_exists(self, use_case, router_repository):
        # Arrange
        router_repository.create_router.return_value = RouterNameAlreadyExistsError(name="existing-router")

        # Act
        error = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=["alias1", "alias2"],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
            )
        )

        # Assert
        assert isinstance(error, RouterNameAlreadyExistsError)
        router_repository.create_router.assert_called_once_with(
            user_id=1,
            name="test-model",
            router_type=RouterType.TEXT_GENERATION,
            qos_retries_before_reject=None,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            aliases=["alias1", "alias2"],
            tokenizer=None,
        )

    @pytest.mark.asyncio
    async def test_should_persist_the_tokenizer_when_it_can_be_loaded(self, use_case, router_repository, mock_model_tokenizer_loader):
        # Arrange
        router = RouterFactory(id=3, tokenizer="tiktoken_o200k_base")
        router_repository.create_router.return_value = router

        # Act
        result = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=[],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
                tokenizer="tiktoken_o200k_base",
            )
        )

        # Assert
        assert result.router == router
        mock_model_tokenizer_loader.load.assert_awaited_once_with("tiktoken_o200k_base")
        assert router_repository.create_router.call_args.kwargs["tokenizer"] == "tiktoken_o200k_base"

    @pytest.mark.asyncio
    async def test_should_not_load_a_tokenizer_when_none_is_given(self, use_case, router_repository, mock_model_tokenizer_loader):
        # Arrange
        router_repository.create_router.return_value = RouterFactory(id=3)

        # Act
        await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=[],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
            )
        )

        # Assert
        mock_model_tokenizer_loader.load.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_the_error_without_creating_the_router_when_the_tokenizer_cannot_be_loaded(
        self, use_case, router_repository, mock_model_tokenizer_loader
    ):
        # Arrange
        error = ModelTokenizerNotLoadableError(tokenizer="unknown/model", detail="not found")
        mock_model_tokenizer_loader.load.return_value = error

        # Act
        result = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=[],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
                tokenizer="unknown/model",
            )
        )

        # Assert
        assert result is error
        router_repository.create_router.assert_not_called()
