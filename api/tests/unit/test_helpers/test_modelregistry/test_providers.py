from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

import api.helpers.models._modelregistry as modelregistry_module
from api.helpers.models._modelregistry import ModelRegistry
from api.schemas.admin.providers import Provider, ProviderCarbonFootprintZone, ProviderType
from api.schemas.admin.routers import Router, RouterLoadBalancingStrategy
from api.schemas.core.metrics import Metric
from api.schemas.models import ModelType
from api.utils.exceptions import (
    InconsistentModelMaxContextLengthException,
    InconsistentModelVectorSizeException,
    InvalidProviderTypeException,
    ProviderAlreadyExistsException,
    ProviderNotFoundException,
    ProviderNotReachableException,
)


class _MappingsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Result:
    def __init__(self, scalar_one=None, all_rows=None, iterate_rows=None, mappings=None):
        self._scalar_one = scalar_one
        self._all_rows = all_rows
        self._iterate_rows = iterate_rows
        self._mappings = mappings

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
        return _MappingsResult(self._mappings or [])

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


@pytest.fixture
def mock_router():
    return Router(
        id=1,
        name="test-router",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=1.0,
        cost_completion_tokens=2.0,
        providers=0,
        created=100,
        updated=200,
    )


@pytest.fixture
def mock_provider_class():
    """Mock BaseModelProvider class"""
    provider_instance = AsyncMock()
    provider_instance.get_max_context_length = AsyncMock(return_value=4096)
    provider_instance.get_vector_size = AsyncMock(return_value=None)
    provider_instance.name = "test-model"

    provider_class = MagicMock(return_value=provider_instance)
    return provider_class, provider_instance


@pytest.mark.asyncio
async def test_create_provider_success(
    postgres_session: AsyncSession,
    model_registry: ModelRegistry,
    mock_router: Router,
    mock_provider_class,
):
    provider_class, provider_instance = mock_provider_class

    model_registry.get_routers = AsyncMock(return_value=[mock_router])
    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(scalar_one=123),  # insert provider, returning id
        ]
    )

    with patch.object(modelregistry_module.ModelProvider, "import_module", return_value=provider_class):
        provider_id = await model_registry.create_provider(
            router_id=1,
            user_id=1,
            type=ProviderType.OPENAI,
            url="https://api.openai.com/",
            key="sk-test",
            timeout=30,
            model_name="gpt-4",
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
            postgres_session=postgres_session,
        )

    assert provider_id == 123
    postgres_session.commit.assert_awaited()
    provider_instance.get_max_context_length.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_provider_with_vector_size(
    postgres_session: AsyncSession,
    model_registry: ModelRegistry,
    mock_provider_class,
):
    provider_class, provider_instance = mock_provider_class
    provider_instance.get_max_context_length = AsyncMock(return_value=2048)
    provider_instance.get_vector_size = AsyncMock(return_value=768)

    router = Router(
        id=1,
        name="embedding-router",
        user_id=1,
        type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=2048,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=0,
        created=100,
        updated=200,
    )

    model_registry.get_routers = AsyncMock(return_value=[router])
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=456))

    with patch.object(modelregistry_module.ModelProvider, "import_module", return_value=provider_class):
        provider_id = await model_registry.create_provider(
            router_id=1,
            user_id=1,
            type=ProviderType.TEI,
            url="https://tei.example.com/",
            key=None,
            timeout=30,
            model_name="embedding-model",
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
            postgres_session=postgres_session,
        )

    assert provider_id == 456
    provider_instance.get_max_context_length.assert_awaited_once()
    provider_instance.get_vector_size.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_provider_invalid_type(
    postgres_session: AsyncSession,
    model_registry: ModelRegistry,
    mock_router: Router,
):
    model_registry.get_routers = AsyncMock(return_value=[mock_router])

    with pytest.raises(InvalidProviderTypeException):
        await model_registry.create_provider(
            router_id=1,
            user_id=1,
            type=ProviderType.TEI,  # TEI not compatible with TEXT_GENERATION
            url="https://tei.example.com/",
            key=None,
            timeout=30,
            model_name="test-model",
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_create_provider_not_reachable(
    postgres_session: AsyncSession,
    model_registry: ModelRegistry,
    mock_router: Router,
    mock_provider_class,
):
    provider_class, provider_instance = mock_provider_class
    provider_instance.get_max_context_length = AsyncMock(side_effect=AssertionError("Connection failed"))

    model_registry.get_routers = AsyncMock(return_value=[mock_router])

    with patch.object(modelregistry_module.ModelProvider, "import_module", return_value=provider_class):
        with pytest.raises(ProviderNotReachableException):
            await model_registry.create_provider(
                router_id=1,
                user_id=1,
                type=ProviderType.OPENAI,
                url="https://invalid-url.com/",
                key="sk-test",
                timeout=30,
                model_name="gpt-4",
                model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
                model_carbon_footprint_total_params=0,
                model_carbon_footprint_active_params=0,
                qos_metric=None,
                qos_limit=None,
                postgres_session=postgres_session,
            )


@pytest.mark.asyncio
async def test_create_provider_inconsistent_vector_size(
    postgres_session: AsyncSession,
    model_registry: ModelRegistry,
    mock_provider_class,
):
    provider_class, provider_instance = mock_provider_class
    provider_instance.get_max_context_length = AsyncMock(return_value=2048)
    provider_instance.get_vector_size = AsyncMock(return_value=512)

    router = Router(
        id=1,
        name="embedding-router",
        user_id=1,
        type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=768,  # Different from provider
        max_context_length=2048,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,  # Has existing providers
        created=100,
        updated=200,
    )

    model_registry.get_routers = AsyncMock(return_value=[router])

    with patch.object(modelregistry_module.ModelProvider, "import_module", return_value=provider_class):
        with pytest.raises(InconsistentModelVectorSizeException):
            await model_registry.create_provider(
                router_id=1,
                user_id=1,
                type=ProviderType.TEI,
                url="https://tei.example.com/",
                key=None,
                timeout=30,
                model_name="embedding-model",
                model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
                model_carbon_footprint_total_params=0,
                model_carbon_footprint_active_params=0,
                qos_metric=None,
                qos_limit=None,
                postgres_session=postgres_session,
            )


@pytest.mark.asyncio
async def test_create_provider_inconsistent_max_context_length(
    postgres_session: AsyncSession,
    model_registry: ModelRegistry,
    mock_router: Router,
    mock_provider_class,
):
    provider_class, provider_instance = mock_provider_class
    provider_instance.get_max_context_length = AsyncMock(return_value=2048)  # Different from router

    router_with_providers = Router(
        id=1,
        name="test-router",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,  # Different from provider
        cost_prompt_tokens=1.0,
        cost_completion_tokens=2.0,
        providers=1,  # Has existing providers
        created=100,
        updated=200,
    )

    model_registry.get_routers = AsyncMock(return_value=[router_with_providers])

    with patch.object(modelregistry_module.ModelProvider, "import_module", return_value=provider_class):
        with pytest.raises(InconsistentModelMaxContextLengthException):
            await model_registry.create_provider(
                router_id=1,
                user_id=1,
                type=ProviderType.OPENAI,
                url="https://api.openai.com/",
                key="sk-test",
                timeout=30,
                model_name="gpt-4",
                model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
                model_carbon_footprint_total_params=0,
                model_carbon_footprint_active_params=0,
                qos_metric=None,
                qos_limit=None,
                postgres_session=postgres_session,
            )


@pytest.mark.asyncio
async def test_create_provider_already_exists(
    postgres_session: AsyncSession,
    model_registry: ModelRegistry,
    mock_router: Router,
    mock_provider_class,
):
    provider_class, provider_instance = mock_provider_class

    model_registry.get_routers = AsyncMock(return_value=[mock_router])
    postgres_session.execute = AsyncMock(side_effect=IntegrityError("", "", None))

    with patch.object(modelregistry_module.ModelProvider, "import_module", return_value=provider_class):
        with pytest.raises(ProviderAlreadyExistsException):
            await model_registry.create_provider(
                router_id=1,
                user_id=1,
                type=ProviderType.OPENAI,
                url="https://api.openai.com/",
                key="sk-test",
                timeout=30,
                model_name="gpt-4",
                model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
                model_carbon_footprint_total_params=0,
                model_carbon_footprint_active_params=0,
                qos_metric=None,
                qos_limit=None,
                postgres_session=postgres_session,
            )


@pytest.mark.asyncio
async def test_create_provider_master_user(
    postgres_session: AsyncSession,
    model_registry: ModelRegistry,
    mock_router: Router,
    mock_provider_class,
):
    provider_class, provider_instance = mock_provider_class

    model_registry.get_routers = AsyncMock(return_value=[mock_router])
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=789))

    with patch.object(modelregistry_module.ModelProvider, "import_module", return_value=provider_class):
        provider_id = await model_registry.create_provider(
            router_id=1,
            user_id=0,  # master user
            type=ProviderType.OPENAI,
            url="https://api.openai.com/",
            key="sk-test",
            timeout=30,
            model_name="gpt-4",
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
            postgres_session=postgres_session,
        )

    assert provider_id == 789


@pytest.mark.asyncio
async def test_create_provider_with_qos(
    postgres_session: AsyncSession,
    model_registry: ModelRegistry,
    mock_router: Router,
    mock_provider_class,
):
    provider_class, provider_instance = mock_provider_class

    model_registry.get_routers = AsyncMock(return_value=[mock_router])
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=999))

    with patch.object(modelregistry_module.ModelProvider, "import_module", return_value=provider_class):
        provider_id = await model_registry.create_provider(
            router_id=1,
            user_id=1,
            type=ProviderType.OPENAI,
            url="https://api.openai.com/",
            key="sk-test",
            timeout=30,
            model_name="gpt-4",
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=Metric.TTFT,
            qos_limit=0.5,
            postgres_session=postgres_session,
        )

    assert provider_id == 999


@pytest.mark.asyncio
async def test_delete_provider_not_found(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(ProviderNotFoundException):
        await model_registry.delete_provider(provider_id=999, postgres_session=postgres_session)


@pytest.mark.asyncio
async def test_delete_provider_success(postgres_session: AsyncSession, model_registry: ModelRegistry):
    postgres_session.execute = AsyncMock(side_effect=[_Result(scalar_one=MagicMock(id=1)), None])

    await model_registry.delete_provider(provider_id=1, postgres_session=postgres_session)
    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_get_providers_by_router_id(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider_rows = [
        {
            "id": 1,
            "router_id": 1,
            "user_id": 1,
            "type": ProviderType.OPENAI.value,
            "url": "https://api.openai.com/",
            "key": "sk-test",
            "timeout": 30,
            "model_name": "gpt-4",
            "model_carbon_footprint_zone": ProviderCarbonFootprintZone.WOR.value,
            "model_carbon_footprint_total_params": 0,
            "model_carbon_footprint_active_params": 0,
            "qos_metric": None,
            "qos_limit": None,
            "created": 100,
            "updated": 200,
        },
        {
            "id": 2,
            "router_id": 1,
            "user_id": 1,
            "type": ProviderType.VLLM.value,
            "url": "https://vllm.example.com/",
            "key": None,
            "timeout": 60,
            "model_name": "llama-2",
            "model_carbon_footprint_zone": ProviderCarbonFootprintZone.WOR.value,
            "model_carbon_footprint_total_params": 0,
            "model_carbon_footprint_active_params": 0,
            "qos_metric": Metric.TTFT.value,
            "qos_limit": 0.5,
            "created": 200,
            "updated": 300,
        },
    ]

    result = _Result()
    result.mappings = lambda: _MappingsResult(provider_rows)
    postgres_session.execute = AsyncMock(return_value=result)

    providers = await model_registry.get_providers(
        router_id=1,
        provider_id=None,
        postgres_session=postgres_session,
    )

    assert len(providers) == 2
    assert providers[0].id == 1
    assert providers[0].type == ProviderType.OPENAI.value
    assert providers[1].id == 2
    assert providers[1].qos_metric == Metric.TTFT


@pytest.mark.asyncio
async def test_get_providers_by_provider_id(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider_row = {
        "id": 42,
        "router_id": 1,
        "user_id": 1,
        "type": ProviderType.OPENAI.value,
        "url": "https://api.openai.com/",
        "key": "sk-test",
        "timeout": 30,
        "model_name": "gpt-4",
        "model_carbon_footprint_zone": ProviderCarbonFootprintZone.WOR.value,
        "model_carbon_footprint_total_params": 0,
        "model_carbon_footprint_active_params": 0,
        "qos_metric": None,
        "qos_limit": None,
        "created": 100,
        "updated": 200,
    }

    result = _Result()
    result.mappings = lambda: _MappingsResult([provider_row])
    postgres_session.execute = AsyncMock(return_value=result)

    providers = await model_registry.get_providers(
        router_id=None,
        provider_id=42,
        postgres_session=postgres_session,
    )

    assert len(providers) == 1
    assert providers[0].id == 42


@pytest.mark.asyncio
async def test_get_providers_not_found(postgres_session: AsyncSession, model_registry: ModelRegistry):
    result = _Result()
    result.mappings = lambda: _MappingsResult([])
    postgres_session.execute = AsyncMock(return_value=result)

    with pytest.raises(ProviderNotFoundException):
        await model_registry.get_providers(
            router_id=None,
            provider_id=999,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_get_providers_master_user(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider_row = {
        "id": 1,
        "router_id": 1,
        "user_id": None,  # master user
        "type": ProviderType.OPENAI.value,
        "url": "https://api.openai.com/",
        "key": "sk-test",
        "timeout": 30,
        "model_name": "gpt-4",
        "model_carbon_footprint_zone": ProviderCarbonFootprintZone.WOR.value,
        "model_carbon_footprint_total_params": 0,
        "model_carbon_footprint_active_params": 0,
        "qos_metric": None,
        "qos_limit": None,
        "created": 100,
        "updated": 200,
    }

    result = _Result()
    result.mappings = lambda: _MappingsResult([provider_row])
    postgres_session.execute = AsyncMock(return_value=result)

    providers = await model_registry.get_providers(
        router_id=1,
        provider_id=None,
        postgres_session=postgres_session,
    )

    assert providers[0].user_id == 0


@pytest.mark.asyncio
async def test_get_providers_pagination_and_ordering(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider_rows = [
        {
            "id": 1,
            "router_id": 1,
            "user_id": 1,
            "type": ProviderType.OPENAI.value,
            "url": "https://api.openai.com/",
            "key": "sk-test",
            "timeout": 30,
            "model_name": "gpt-4",
            "model_carbon_footprint_zone": ProviderCarbonFootprintZone.WOR.value,
            "model_carbon_footprint_total_params": 0,
            "model_carbon_footprint_active_params": 0,
            "qos_metric": None,
            "qos_limit": None,
            "created": 100,
            "updated": 200,
        },
        {
            "id": 2,
            "router_id": 1,
            "user_id": 1,
            "type": ProviderType.VLLM.value,
            "url": "https://vllm.example.com/",
            "key": None,
            "timeout": 60,
            "model_name": "llama-2",
            "model_carbon_footprint_zone": ProviderCarbonFootprintZone.WOR.value,
            "model_carbon_footprint_total_params": 0,
            "model_carbon_footprint_active_params": 0,
            "qos_metric": None,
            "qos_limit": None,
            "created": 200,
            "updated": 300,
        },
    ]

    result = _Result()
    result.mappings = lambda: _MappingsResult(provider_rows)
    postgres_session.execute = AsyncMock(return_value=result)

    providers = await model_registry.get_providers(
        router_id=1,
        provider_id=None,
        postgres_session=postgres_session,
        offset=0,
        limit=10,
        order_by="created",
        order_direction="desc",
    )

    assert len(providers) == 2


@pytest.mark.asyncio
async def test_update_provider_not_found(postgres_session: AsyncSession, model_registry: ModelRegistry):
    # get_providers with provider_id raises ProviderNotFoundException when empty
    result = _Result()
    result.mappings = lambda: _MappingsResult([])
    postgres_session.execute = AsyncMock(return_value=result)

    with pytest.raises(ProviderNotFoundException):
        await model_registry.update_provider(
            provider_id=999,
            router_id=None,
            timeout=None,
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_update_provider_timeout(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider = Provider(
        id=1,
        router_id=1,
        user_id=1,
        type=ProviderType.OPENAI.value,
        url="https://api.openai.com/",
        key="sk-test",
        timeout=30,
        model_name="gpt-4",
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=None,
        qos_limit=None,
        created=100,
        updated=200,
    )

    router = Router(
        id=1,
        name="test-router",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,
        created=100,
        updated=200,
    )

    model_registry.get_providers = AsyncMock(return_value=[provider])
    model_registry.get_routers = AsyncMock(return_value=[router])
    postgres_session.execute = AsyncMock()

    await model_registry.update_provider(
        provider_id=1,
        router_id=None,
        timeout=60,
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=None,
        qos_limit=None,
        postgres_session=postgres_session,
    )

    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_provider_change_router_invalid_type(postgres_session: AsyncSession, model_registry: ModelRegistry):
    current_router = Router(
        id=1,
        name="text-gen-router",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,
        created=100,
        updated=200,
    )

    new_router = Router(
        id=2,
        name="classification-router",
        user_id=1,
        type=ModelType.TEXT_CLASSIFICATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=0,
        created=200,
        updated=300,
    )

    # Mock get_providers to return provider (will be called with router_id=None, provider_id=1)
    # Note: get_providers creates Provider with type from DB (string), which Pydantic converts to enum
    provider_result = _Result()
    provider_result.mappings = lambda: _MappingsResult(
        [
            {
                "id": 1,
                "router_id": 1,
                "user_id": 1,
                "type": ProviderType.MISTRAL.value,  # MISTRAL is not compatible with TEXT_CLASSIFICATION
                "url": "https://mistral.example.com/",
                "key": "sk-test",
                "timeout": 30,
                "model_name": "mistral-model",
                "model_carbon_footprint_zone": ProviderCarbonFootprintZone.WOR.value,
                "model_carbon_footprint_total_params": 0,
                "model_carbon_footprint_active_params": 0,
                "qos_metric": None,
                "qos_limit": None,
                "created": 100,
                "updated": 200,
            }
        ]
    )
    postgres_session.execute = AsyncMock(return_value=provider_result)
    model_registry.get_routers = AsyncMock(side_effect=[[current_router], [new_router]])

    with pytest.raises(InvalidProviderTypeException):
        await model_registry.update_provider(
            provider_id=1,
            router_id=2,
            timeout=None,
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_update_provider_change_router_success(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider = Provider(
        id=1,
        router_id=1,
        user_id=1,
        type=ProviderType.OPENAI.value,
        url="https://api.openai.com/",
        key="sk-test",
        timeout=30,
        model_name="gpt-4o-mini",
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=None,
        qos_limit=None,
        created=100,
        updated=200,
    )

    current_router = Router(
        id=1,
        name="router-1",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,
        created=100,
        updated=200,
    )

    new_router = Router(
        id=2,
        name="router-2",
        user_id=1,
        type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=768,
        max_context_length=2048,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=0,  # skip consistency checks
        created=200,
        updated=300,
    )

    model_registry.get_providers = AsyncMock(return_value=[provider])
    model_registry.get_routers = AsyncMock(side_effect=[[current_router], [new_router]])
    postgres_session.execute = AsyncMock()

    await model_registry.update_provider(
        provider_id=1,
        router_id=2,
        timeout=None,
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=None,
        qos_limit=None,
        postgres_session=postgres_session,
    )

    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_provider_change_router_inconsistent_vector_size(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider = Provider(
        id=1,
        router_id=1,
        user_id=1,
        type=ProviderType.TEI.value,
        url="https://tei.example.com/",
        key=None,
        timeout=30,
        model_name="embedding-model",
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=None,
        qos_limit=None,
        created=100,
        updated=200,
    )

    current_router = Router(
        id=1,
        name="embedding-router-1",
        user_id=1,
        type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=512,
        max_context_length=2048,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,
        created=100,
        updated=200,
    )

    new_router = Router(
        id=2,
        name="embedding-router-2",
        user_id=1,
        type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=768,  # Different vector size
        max_context_length=2048,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,  # Has existing providers
        created=200,
        updated=300,
    )

    model_registry.get_providers = AsyncMock(return_value=[provider])
    model_registry.get_routers = AsyncMock(side_effect=[[current_router], [new_router]])

    with pytest.raises(InconsistentModelVectorSizeException):
        await model_registry.update_provider(
            provider_id=1,
            router_id=2,
            timeout=None,
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_update_provider_change_router_inconsistent_max_context_length(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider = Provider(
        id=1,
        router_id=1,
        user_id=1,
        type=ProviderType.OPENAI.value,
        url="https://api.openai.com/",
        key="sk-test",
        timeout=30,
        model_name="gpt-4",
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=None,
        qos_limit=None,
        created=100,
        updated=200,
    )

    current_router = Router(
        id=1,
        name="router-1",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,
        created=100,
        updated=200,
    )

    new_router = Router(
        id=2,
        name="router-2",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=2048,  # Different max context length
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,  # Has existing providers
        created=200,
        updated=300,
    )

    model_registry.get_providers = AsyncMock(return_value=[provider])
    model_registry.get_routers = AsyncMock(side_effect=[[current_router], [new_router]])

    with pytest.raises(InconsistentModelMaxContextLengthException):
        await model_registry.update_provider(
            provider_id=1,
            router_id=2,
            timeout=None,
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_update_provider_change_router_already_exists(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider = Provider(
        id=1,
        router_id=1,
        user_id=1,
        type=ProviderType.OPENAI.value,
        url="https://api.openai.com/",
        key="sk-test",
        timeout=30,
        model_name="gpt-4",
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=None,
        qos_limit=None,
        created=100,
        updated=200,
    )

    router = Router(
        id=1,
        name="test-router",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,
        created=100,
        updated=200,
    )

    model_registry.get_providers = AsyncMock(return_value=[provider])
    model_registry.get_routers = AsyncMock(return_value=[router])
    postgres_session.execute = AsyncMock(side_effect=IntegrityError("", "", None))

    with pytest.raises(ProviderAlreadyExistsException):
        await model_registry.update_provider(
            provider_id=1,
            router_id=2,
            timeout=None,
            model_carbon_footprint_zone=None,
            model_carbon_footprint_total_params=None,
            model_carbon_footprint_active_params=None,
            qos_metric=None,
            qos_limit=None,
            postgres_session=postgres_session,
        )


@pytest.mark.asyncio
async def test_update_provider_qos_metric(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider = Provider(
        id=1,
        router_id=1,
        user_id=1,
        type=ProviderType.OPENAI.value,
        url="https://api.openai.com/",
        key="sk-test",
        timeout=30,
        model_name="gpt-4",
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=None,
        qos_limit=None,
        created=100,
        updated=200,
    )

    router = Router(
        id=1,
        name="test-router",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,
        created=100,
        updated=200,
    )

    model_registry.get_providers = AsyncMock(return_value=[provider])
    model_registry.get_routers = AsyncMock(return_value=[router])
    postgres_session.execute = AsyncMock()

    await model_registry.update_provider(
        provider_id=1,
        router_id=None,
        timeout=None,
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=Metric.TTFT,
        qos_limit=0.5,
        postgres_session=postgres_session,
    )

    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_provider_noop(postgres_session: AsyncSession, model_registry: ModelRegistry):
    provider = Provider(
        id=1,
        router_id=1,
        user_id=1,
        type=ProviderType.OPENAI.value,
        url="https://api.openai.com/",
        key="sk-test",
        timeout=30,
        model_name="gpt-4",
        model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR.value,
        model_carbon_footprint_total_params=0,
        model_carbon_footprint_active_params=0,
        qos_metric=None,
        qos_limit=None,
        created=100,
        updated=200,
    )

    router = Router(
        id=1,
        name="test-router",
        user_id=1,
        type=ModelType.TEXT_GENERATION,
        aliases=[],
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        vector_size=None,
        max_context_length=4096,
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
        providers=1,
        created=100,
        updated=200,
    )

    result = _Result()
    result.mappings = lambda: _MappingsResult(
        [
            {
                "id": 1,
                "router_id": 1,
                "user_id": 1,
                "type": ProviderType.OPENAI.value,
                "url": "https://api.openai.com/",
                "key": "sk-test",
                "timeout": 30,
                "model_name": "gpt-4",
                "model_carbon_footprint_zone": ProviderCarbonFootprintZone.WOR.value,
                "model_carbon_footprint_total_params": 0,
                "model_carbon_footprint_active_params": 0,
                "qos_metric": None,
                "qos_limit": None,
                "created": 100,
                "updated": 200,
            }
        ]
    )
    postgres_session.execute = AsyncMock(return_value=result)
    model_registry.get_routers = AsyncMock(return_value=[router])

    await model_registry.update_provider(
        provider_id=1,
        router_id=None,
        timeout=None,
        model_carbon_footprint_zone=None,
        model_carbon_footprint_total_params=None,
        model_carbon_footprint_active_params=None,
        qos_metric=None,
        qos_limit=None,
        postgres_session=postgres_session,
    )

    # Should NOT commit if no updates (update_value is empty)
    postgres_session.commit.assert_not_awaited()
