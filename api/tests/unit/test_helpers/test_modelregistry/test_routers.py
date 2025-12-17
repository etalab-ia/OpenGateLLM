from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers.models._modelregistry import ModelRegistry
from api.schemas.admin.routers import Router, RouterLoadBalancingStrategy
from api.schemas.models import ModelType
from api.utils.exceptions import (
    RouterAliasAlreadyExistsException,
    RouterAlreadyExistsException,
    RouterNotFoundException,
)


class _Result:
    def __init__(self, scalar_one=None, all_rows=None, iterate_rows=None, mappings=None, scalars_rows=None):
        self._scalar_one = scalar_one
        self._all_rows = all_rows
        self._iterate_rows = iterate_rows
        self._mappings = mappings
        self._scalars_rows = scalars_rows

    def scalar_one(self):
        if isinstance(self._scalar_one, Exception):
            raise self._scalar_one
        return self._scalar_one

    def scalar_one_or_none(self):
        if isinstance(self._scalar_one, Exception):
            raise self._scalar_one
        return self._scalar_one

    def all(self):
        return self._all_rows or []

    def mappings(self):
        return self._mappings or []

    def scalars(self):
        return self  # For scalars().all()

    def __iter__(self):
        return iter(self._iterate_rows or [])


@pytest.fixture
def postgres_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def model_registry():
    return ModelRegistry(
        app_title="TestApp",
        queuing_enabled=False,
        max_priority=10,
        max_retries=3,
        retry_countdown=60,
    )


@pytest.mark.asyncio
async def test_create_router_success(postgres_session: AsyncSession, model_registry: ModelRegistry):
    # Router insert returns id, aliases check returns empty, aliases insert succeeds (one per alias)
    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(scalar_one=123),  # insert router, returning id
            _Result(all_rows=[]),  # check aliases integrity
            None,  # insert alias1
            None,  # insert alias2
        ]
    )

    router_id = await model_registry.create_router(
        name="test-router",
        type=ModelType.TEXT_GENERATION,
        aliases=["alias1", "alias2"],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        cost_prompt_tokens=1.0,
        cost_completion_tokens=2.0,
        user_id=1,
        postgres_session=postgres_session,
    )

    assert router_id == 123
    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_router_master_user(postgres_session: AsyncSession, model_registry: ModelRegistry):
    # Master user (user_id=0) should be converted to None
    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(scalar_one=456),  # insert router
            _Result(all_rows=[]),  # check aliases
            None,  # insert aliases
        ]
    )

    router_id = await model_registry.create_router(
        name="master-router",
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        user_id=0,  # master user
        postgres_session=postgres_session,
    )

    assert router_id == 456
    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_router_already_exists(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(side_effect=IntegrityError("", "", None))

    with pytest.raises(RouterAlreadyExistsException):
        await model_registry.create_router(
            name="existing-router",
            type=ModelType.TEXT_GENERATION,
            aliases=[],
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=1,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_create_router_alias_already_exists(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(scalar_one=789),  # insert router succeeds
            _Result(all_rows=[("existing-alias",)]),  # alias already exists
        ]
    )

    with pytest.raises(RouterAliasAlreadyExistsException):
        await model_registry.create_router(
            name="new-router",
            type=ModelType.TEXT_GENERATION,
            aliases=["existing-alias"],
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=1,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_delete_router_not_found(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(RouterNotFoundException):
        await model_registry.delete_router(router_id=999, postgres_session=postgres_session)


@pytest.mark.asyncio
async def test_delete_router_success(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(side_effect=[_Result(scalar_one=MagicMock(id=1)), None])

    await model_registry.delete_router(router_id=1, postgres_session=postgres_session)
    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_router_not_found(postgres_session: AsyncSession, model_registry: ModelRegistry):
    # get_routers is called internally and returns empty list when router_id is provided
    # Mock postgres_session.execute to return empty results for get_routers query
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=[]))

    with pytest.raises(RouterNotFoundException):
        await model_registry.update_router(
            router_id=999,
            name="new-name",
            type=None,
            aliases=None,
            load_balancing_strategy=None,
            cost_prompt_tokens=None,
            cost_completion_tokens=None,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_update_router_success_all_fields(postgres_session: AsyncSession, model_registry: ModelRegistry):
    # Mock get_routers to return a router
    router = Router(
        id=1,
        name="old-name",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=["old-alias"],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=1.0,
        cost_completion_tokens=2.0,
        providers=0,
        created=100,
        updated=200,
    )

    model_registry.get_routers = AsyncMock(return_value=[router])
    # check aliases (scalars().all() returns empty), update router, delete old aliases, insert new aliases
    alias_result = _Result(scalars_rows=[])
    alias_result.scalars = lambda: alias_result
    alias_result.all = lambda: []
    postgres_session.execute = AsyncMock(side_effect=[alias_result, None, None, None])

    await model_registry.update_router(
        router_id=1,
        name="new-name",
        type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
        aliases=["new-alias1", "new-alias2"],
        load_balancing_strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
        cost_prompt_tokens=3.0,
        cost_completion_tokens=4.0,
        postgres_session=postgres_session,
    )

    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_router_alias_conflict(postgres_session: AsyncSession, model_registry: ModelRegistry):
    router = Router(
        id=1,
        name="router",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=0,
        created=100,
        updated=200,
    )

    model_registry.get_routers = AsyncMock(return_value=[router])
    # Check aliases returns conflicting router_id (scalars().all() returns [2])
    alias_result = _Result()
    alias_result.scalars = lambda: alias_result
    alias_result.all = lambda: [2]  # alias belongs to router 2
    postgres_session.execute = AsyncMock(return_value=alias_result)

    with pytest.raises(RouterAliasAlreadyExistsException):
        await model_registry.update_router(
            router_id=1,
            name=None,
            type=None,
            aliases=["conflicting-alias"],
            load_balancing_strategy=None,
            cost_prompt_tokens=None,
            cost_completion_tokens=None,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_update_router_noop(postgres_session: AsyncSession, model_registry: ModelRegistry):
    router = Router(
        id=1,
        name="router",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=0,
        created=100,
        updated=200,
    )

    model_registry.get_routers = AsyncMock(return_value=[router])
    postgres_session.execute = AsyncMock()

    await model_registry.update_router(
        router_id=1,
        name=None,
        type=None,
        aliases=None,
        load_balancing_strategy=None,
        cost_prompt_tokens=None,
        cost_completion_tokens=None,
        postgres_session=postgres_session,
    )

    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_get_routers_by_id_success(postgres_session: AsyncSession, model_registry: ModelRegistry):
    # Mock router result with provider count
    router_row = MagicMock(
        _asdict=lambda: {
            "id": 1,
            "name": "test-router",
            "user_id": 1,
            "type": ModelType.TEXT_GENERATION.value,
            "load_balancing_strategy": RouterLoadBalancingStrategy.SHUFFLE.value,
            "cost_prompt_tokens": 1.0,
            "cost_completion_tokens": 2.0,
            "max_context_length": 4096,
            "vector_size": None,
            "providers": 2,
            "created": 100,
            "updated": 200,
        }
    )

    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[router_row]),  # router query
            _Result(all_rows=[]),  # aliases query
        ]
    )

    routers = await model_registry.get_routers(router_id=1, name=None, postgres_session=postgres_session)

    assert len(routers) == 1
    assert routers[0].id == 1
    assert routers[0].name == "test-router"
    assert routers[0].type == ModelType.TEXT_GENERATION


@pytest.mark.asyncio
async def test_get_routers_by_id_not_found(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=[]))

    with pytest.raises(RouterNotFoundException):
        await model_registry.get_routers(router_id=999, name=None, postgres_session=postgres_session)


@pytest.mark.asyncio
async def test_get_routers_by_name_success(postgres_session: AsyncSession, model_registry: ModelRegistry):
    router_row = MagicMock(
        _asdict=lambda: {
            "id": 1,
            "name": "test-router",
            "user_id": 1,
            "type": ModelType.TEXT_GENERATION.value,
            "load_balancing_strategy": RouterLoadBalancingStrategy.SHUFFLE.value,
            "cost_prompt_tokens": 0.0,
            "cost_completion_tokens": 0.0,
            "max_context_length": 4096,
            "vector_size": None,
            "providers": 1,
            "created": 100,
            "updated": 200,
        }
    )

    alias_row = MagicMock(router_id=1, value="alias1")

    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[router_row]),  # router query
            _Result(all_rows=[alias_row]),  # aliases query
        ]
    )

    routers = await model_registry.get_routers(router_id=None, name="test-router", postgres_session=postgres_session)

    assert len(routers) == 1
    assert routers[0].name == "test-router"


@pytest.mark.asyncio
async def test_get_routers_by_alias_success(postgres_session: AsyncSession, model_registry: ModelRegistry):
    router_row = MagicMock(
        _asdict=lambda: {
            "id": 1,
            "name": "test-router",
            "user_id": 1,
            "type": ModelType.TEXT_GENERATION.value,
            "load_balancing_strategy": RouterLoadBalancingStrategy.SHUFFLE.value,
            "cost_prompt_tokens": 0.0,
            "cost_completion_tokens": 0.0,
            "max_context_length": 4096,
            "vector_size": None,
            "providers": 1,
            "created": 100,
            "updated": 200,
        }
    )

    alias_row = MagicMock(router_id=1, value="my-alias")

    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[router_row]),  # router query
            _Result(all_rows=[alias_row]),  # aliases query
        ]
    )

    routers = await model_registry.get_routers(router_id=None, name="my-alias", postgres_session=postgres_session)

    assert len(routers) == 1
    assert "my-alias" in routers[0].aliases


@pytest.mark.asyncio
async def test_get_routers_by_name_not_found(postgres_session: AsyncSession, model_registry: ModelRegistry):
    router_row = MagicMock(
        _asdict=lambda: {
            "id": 1,
            "name": "other-router",
            "user_id": 1,
            "type": ModelType.TEXT_GENERATION.value,
            "load_balancing_strategy": RouterLoadBalancingStrategy.SHUFFLE.value,
            "cost_prompt_tokens": 0.0,
            "cost_completion_tokens": 0.0,
            "max_context_length": 4096,
            "vector_size": None,
            "providers": 1,
            "created": 100,
            "updated": 200,
        }
    )

    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[router_row]),  # router query
            _Result(all_rows=[]),  # aliases query
        ]
    )

    with pytest.raises(RouterNotFoundException):
        await model_registry.get_routers(router_id=None, name="nonexistent", postgres_session=postgres_session)


@pytest.mark.asyncio
async def test_get_routers_pagination_and_ordering(postgres_session: AsyncSession, model_registry: ModelRegistry):
    router_row1 = MagicMock(
        _asdict=lambda: {
            "id": 1,
            "name": "router-a",
            "user_id": 1,
            "type": ModelType.TEXT_GENERATION.value,
            "load_balancing_strategy": RouterLoadBalancingStrategy.SHUFFLE.value,
            "cost_prompt_tokens": 0.0,
            "cost_completion_tokens": 0.0,
            "max_context_length": 4096,
            "vector_size": None,
            "providers": 1,
            "created": 100,
            "updated": 200,
        }
    )

    router_row2 = MagicMock(
        _asdict=lambda: {
            "id": 2,
            "name": "router-b",
            "user_id": 1,
            "type": ModelType.TEXT_EMBEDDINGS_INFERENCE.value,
            "load_balancing_strategy": RouterLoadBalancingStrategy.LEAST_BUSY.value,
            "cost_prompt_tokens": 0.0,
            "cost_completion_tokens": 0.0,
            "max_context_length": 2048,
            "vector_size": 768,
            "providers": 2,
            "created": 200,
            "updated": 300,
        }
    )

    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[router_row1, router_row2]),  # router query
            _Result(all_rows=[]),  # aliases query
        ]
    )

    routers = await model_registry.get_routers(
        router_id=None,
        name=None,
        postgres_session=postgres_session,
        offset=0,
        limit=10,
        order_by="name",
        order_direction="asc",
    )

    assert len(routers) == 2


@pytest.mark.asyncio
async def test_get_routers_master_user(postgres_session: AsyncSession, model_registry: ModelRegistry):
    # Router with user_id=None should be converted to user_id=0
    router_row = MagicMock(
        _asdict=lambda: {
            "id": 1,
            "name": "master-router",
            "user_id": None,  # master user
            "type": ModelType.TEXT_GENERATION.value,
            "load_balancing_strategy": RouterLoadBalancingStrategy.SHUFFLE.value,
            "cost_prompt_tokens": 0.0,
            "cost_completion_tokens": 0.0,
            "max_context_length": 4096,
            "vector_size": None,
            "providers": 0,
            "created": 100,
            "updated": 200,
        }
    )

    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[router_row]),
            _Result(all_rows=[]),
        ]
    )

    routers = await model_registry.get_routers(router_id=1, name=None, postgres_session=postgres_session)

    assert routers[0].user_id == 0


@pytest.mark.asyncio
async def test_get_router_id_from_model_name_by_name(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=42))

    router_id = await model_registry.get_router_id_from_model_name("test-model", postgres_session)

    assert router_id == 42


@pytest.mark.asyncio
async def test_get_router_id_from_model_name_by_alias(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=99))

    router_id = await model_registry.get_router_id_from_model_name("alias-name", postgres_session)

    assert router_id == 99


@pytest.mark.asyncio
async def test_get_router_id_from_model_name_not_found(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=None))

    router_id = await model_registry.get_router_id_from_model_name("nonexistent", postgres_session)

    assert router_id is None
