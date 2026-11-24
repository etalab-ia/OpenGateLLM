from unittest.mock import AsyncMock, create_autospec

import pytest

from api.domain.model import ModelTokenizer, ModelTokenizerLoader
from api.domain.model.errors import ModelTokenizerNotLoadableError
from api.domain.router.entities import RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import UpdateRouterCommand, UpdateRouterUseCase, UpdateRouterUseCaseSuccess


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
    return UpdateRouterUseCase(router_repository=router_repository, model_tokenizer_loader=mock_model_tokenizer_loader)


@pytest.fixture
def sample_router():
    return RouterFactory(id=42, user_id=1, name="original-name", aliases=[])


def full_command(router, **overrides) -> UpdateRouterCommand:
    """Command replacing every persisted field with the current router values, unless overridden."""
    command = UpdateRouterCommand(
        router_id=router.id,
        name=router.name,
        router_type=router.type,
        aliases=router.aliases,
        cost_prompt_tokens=router.cost_prompt_tokens,
        cost_completion_tokens=router.cost_completion_tokens,
        qos_retries_before_reject=router.qos_retries_before_reject,
        tokenizer=router.tokenizer,
    )
    for field, value in overrides.items():
        setattr(command, field, value)
    return command


class TestUpdateRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_return_updated_router_when_user_is_admin_and_router_exists(self, use_case, router_repository, sample_router):
        # Arrange
        updated_router = (
            sample_router.with_name("new-name")
            .with_type(RouterType.TEXT_EMBEDDINGS_INFERENCE)
            .with_cost_prompt_tokens(0.005)
            .with_cost_completion_tokens(0.010)
            .with_qos_retries_before_reject(2)
            .with_aliases(["alias-a", "alias-b"])
        )

        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.router_repository.get_aliases.return_value = []
        use_case.router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(
            command=full_command(
                sample_router,
                name="new-name",
                router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
                cost_prompt_tokens=0.005,
                cost_completion_tokens=0.010,
                qos_retries_before_reject=2,
                aliases=["alias-a", "alias-b"],
            )
        )

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        assert result.router == updated_router

        router_repository.get_router_by_id.assert_called_once_with(router_id=42)
        router_repository.update_router.assert_called_once_with(router=updated_router)

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, use_case, router_repository):
        # Arrange

        use_case.router_repository.get_router_by_id.return_value = RouterNotFoundError(id=99)

        # Act
        result = await use_case.execute(command=full_command(RouterFactory(id=99, user_id=1)))

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 99
        router_repository.update_router.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_alias_already_exists_error_when_alias_belongs_to_another_router(self, use_case, router_repository, sample_router):
        # Arrange

        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.router_repository.get_aliases.return_value = ["conflicting-alias"]

        # Act
        result = await use_case.execute(command=full_command(sample_router, aliases=["conflicting-alias"]))

        # Assert
        assert isinstance(result, RouterAliasAlreadyExistsError)
        assert result.aliases == ["conflicting-alias"]
        router_repository.update_router.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_not_flag_conflict_when_alias_already_belongs_to_the_same_router(self, use_case, router_repository):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=["own-alias"])
        updated_router = router.with_aliases(["own-alias", "new-alias"])

        use_case.router_repository.get_router_by_id.return_value = router
        use_case.router_repository.get_aliases.return_value = ["own-alias"]
        use_case.router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(command=full_command(router, aliases=["own-alias", "new-alias"]))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        router_repository.update_router.assert_called_once_with(router=router.with_aliases(["own-alias", "new-alias"]))

    @pytest.mark.asyncio
    async def test_should_clear_aliases_when_command_aliases_is_empty(self, use_case, router_repository):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=["own-alias"])
        cleared_router = router.with_aliases([])

        use_case.router_repository.get_router_by_id.return_value = router
        use_case.router_repository.update_router.return_value = cleared_router

        # Act
        result = await use_case.execute(command=full_command(router, aliases=[]))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        assert result.router == cleared_router
        router_repository.get_aliases.assert_not_called()
        router_repository.update_router.assert_called_once_with(router=cleared_router)

    @pytest.mark.asyncio
    async def test_should_propagate_router_name_already_exists_error_from_repository(self, use_case, router_repository, sample_router):
        # Arrange

        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.router_repository.update_router.return_value = RouterNameAlreadyExistsError(name="taken-name")

        # Act
        result = await use_case.execute(command=full_command(sample_router, name="taken-name"))

        # Assert
        assert isinstance(result, RouterNameAlreadyExistsError)
        assert result.name == "taken-name"

    @pytest.mark.asyncio
    async def test_should_add_aliases_when_router_has_no_aliases_and_command_updates_aliases(self, use_case, router_repository):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=[])
        updated_router = router.with_aliases(["new-alias"])

        use_case.router_repository.get_router_by_id.return_value = router
        use_case.router_repository.get_aliases.return_value = []
        use_case.router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(command=full_command(router, aliases=["new-alias"]))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        router_repository.update_router.assert_called_once_with(router=router.with_aliases(["new-alias"]))

    @pytest.mark.asyncio
    async def test_should_not_call_update_router_when_router_should_not_be_updated(self, use_case, router_repository, sample_router):
        # Arrange

        use_case.router_repository.get_router_by_id.return_value = sample_router

        # Act
        result = await use_case.execute(command=full_command(sample_router))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        router_repository.update_router.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_load_and_persist_the_tokenizer_when_it_changes(
        self, use_case, router_repository, mock_model_tokenizer_loader, sample_router
    ):
        # Arrange
        updated_router = sample_router.with_tokenizer("tiktoken_o200k_base")
        router_repository.get_router_by_id.return_value = sample_router
        router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(command=full_command(sample_router, tokenizer="tiktoken_o200k_base"))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        mock_model_tokenizer_loader.load.assert_awaited_once_with("tiktoken_o200k_base")
        router_repository.update_router.assert_called_once_with(router=updated_router)

    @pytest.mark.asyncio
    async def test_should_not_load_the_tokenizer_when_it_is_unchanged(self, use_case, router_repository, mock_model_tokenizer_loader):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=[], tokenizer="mistralai/Mistral-7B-Instruct-v0.3")
        router_repository.get_router_by_id.return_value = router

        # Act
        result = await use_case.execute(command=full_command(router))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        mock_model_tokenizer_loader.load.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_clear_the_tokenizer_without_loading_when_the_command_tokenizer_is_none(
        self, use_case, router_repository, mock_model_tokenizer_loader
    ):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=[], tokenizer="tiktoken_o200k_base")
        cleared_router = router.with_tokenizer(None)
        router_repository.get_router_by_id.return_value = router
        router_repository.update_router.return_value = cleared_router

        # Act
        result = await use_case.execute(command=full_command(router, tokenizer=None))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        mock_model_tokenizer_loader.load.assert_not_awaited()
        router_repository.update_router.assert_called_once_with(router=cleared_router)

    @pytest.mark.asyncio
    async def test_should_return_the_error_without_updating_when_the_new_tokenizer_cannot_be_loaded(
        self, use_case, router_repository, mock_model_tokenizer_loader, sample_router
    ):
        # Arrange
        error = ModelTokenizerNotLoadableError(tokenizer="unknown/model", detail="not found")
        router_repository.get_router_by_id.return_value = sample_router
        mock_model_tokenizer_loader.load.return_value = error

        # Act
        result = await use_case.execute(command=full_command(sample_router, tokenizer="unknown/model"))

        # Assert
        assert result is error
        router_repository.update_router.assert_not_called()
