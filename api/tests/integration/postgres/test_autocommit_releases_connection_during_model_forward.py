import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from unittest.mock import MagicMock
from urllib.parse import urljoin

import asyncpg
import httpx
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
import redis.asyncio as redis
import respx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.app import create_app
from api.dependencies import get_autocommit_postgres_session, get_postgres_session, get_redis_client
from api.domain.provider.entities import HostingZone, ProviderType
from api.schemas.models import ModelType
from api.sql.models import Base
from api.tests.helpers import create_key
from api.tests.integration.conftest import TEST_POSTGRES_URL, bind_sql_factories, override_global_context
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL
from api.tests.integration.factories import sql as sql_factories
from api.tests.integration.factories.mistral import MistralOcrResponseFactory
from api.tests.integration.factories.tei import TeiEmbeddingsResponseFactory, TeiRerankResponseFactory
from api.utils.dependencies import get_model_registry
from api.utils.dependencies import get_postgres_session as get_postgres_session_utils
from api.utils.dependencies import get_redis_client as get_redis_client_utils
from api.utils.lifespan import create_autocommit_postgres_session_factory
from api.utils.variables import EndpointRoute

APP_NAME = "ogllm_idle_in_transaction_probe"
PROBE_DSN = TEST_POSTGRES_URL.replace("+asyncpg", "")
ROUTER_NAME = "forward-idle-probe"
RERANK_DOCUMENTS = ["The weather is nice.", "The news is grim.", "The match was close."]


@dataclass
class ForwardScenario:
    name: str
    url: str
    router_type: ModelType
    provider_type: ProviderType
    provider_path: str
    build_response: Callable[[], httpx.Response]
    request_body: dict
    provider_kwargs: dict = field(default_factory=dict)


FORWARD_SCENARIOS = [
    ForwardScenario(
        name="ocr",
        url=f"/v1{EndpointRoute.OCR}",
        router_type=ModelType.IMAGE_TO_TEXT,
        provider_type=ProviderType.MISTRAL,
        provider_path="/v1/ocr",
        build_response=lambda: httpx.Response(MistralOcrResponseFactory._status_code, json=MistralOcrResponseFactory(page_count=2)),
        request_body={"model": ROUTER_NAME, "document": {"type": "document_url", "document_url": "https://example.com/document.pdf"}},
        provider_kwargs={"model_hosting_zone": HostingZone.FRA},
    ),
    ForwardScenario(
        name="embeddings",
        url=f"/v1{EndpointRoute.EMBEDDINGS}",
        router_type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
        provider_type=ProviderType.TEI,
        provider_path="/v1/embeddings",
        build_response=lambda: httpx.Response(TeiEmbeddingsResponseFactory._status_code, json=TeiEmbeddingsResponseFactory()),
        request_body={"model": ROUTER_NAME, "input": "The sun is shining."},
    ),
    ForwardScenario(
        name="rerank",
        url=f"/v1{EndpointRoute.RERANK}",
        router_type=ModelType.TEXT_CLASSIFICATION,
        provider_type=ProviderType.TEI,
        provider_path="/rerank",
        build_response=lambda: httpx.Response(TeiRerankResponseFactory._status_code, json=TeiRerankResponseFactory(count=len(RERANK_DOCUMENTS))),
        request_body={"model": ROUTER_NAME, "query": "The sun is shining.", "documents": RERANK_DOCUMENTS},
    ),
]


async def _count_idle_in_transaction() -> int:
    conn = await asyncpg.connect(PROBE_DSN)
    try:
        return await conn.fetchval(
            "SELECT count(*) FROM pg_stat_activity WHERE application_name = $1 AND state = 'idle in transaction'",
            APP_NAME,
        )
    finally:
        await conn.close()


@pytest.fixture(params=FORWARD_SCENARIOS, ids=lambda scenario: scenario.name)
def scenario(request) -> ForwardScenario:
    return request.param


@pytest_asyncio.fixture
async def probe_engine(test_postgres_engine):
    engine = create_async_engine(
        url=TEST_POSTGRES_URL,
        pool_size=5,
        max_overflow=5,
        connect_args={"server_settings": {"application_name": APP_NAME}},
    )
    try:
        yield engine
    finally:
        table_list = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        async with engine.begin() as connection:
            await connection.execute(text(f"TRUNCATE {table_list} RESTART IDENTITY CASCADE"))
        await engine.dispose()


@pytest_asyncio.fixture
async def seed_forward_auth(probe_engine, scenario):
    seed_factory = async_sessionmaker(probe_engine, class_=AsyncSession, expire_on_commit=False)
    async with seed_factory() as seed_session:
        with bind_sql_factories(seed_session):
            admin = sql_factories.UserSQLFactory(admin_user=True)
            key = await create_key(seed_session, user=admin, name="forward_probe_key")
            sql_factories.RouterSQLFactory(
                user=admin,
                name=ROUTER_NAME,
                type=scenario.router_type,
                free=True,
                providers=1,
                providers__type=scenario.provider_type,
                providers__url=DEFAULT_PROVIDER_URL,
                **{f"providers__{key_}": value for key_, value in scenario.provider_kwargs.items()},
            )
            token = key.token
            await seed_session.commit()
    return token


@pytest.mark.asyncio(loop_scope="session")
class TestModelForwardReleasesConnection:
    def _build_app(self, probe_engine, autocommit_session_factory, test_configuration, test_redis_pool, model_registry):
        app = create_app(test_configuration, skip_lifespan=True)
        transactional_factory = async_sessionmaker(probe_engine, class_=AsyncSession, expire_on_commit=False)

        async def override_get_postgres_session():
            async with transactional_factory() as session:
                try:
                    yield session
                    if session.in_transaction():
                        await session.commit()
                except Exception:
                    if session.in_transaction():
                        await session.rollback()
                    raise

        async def override_get_autocommit_postgres_session():
            async with autocommit_session_factory() as session:
                yield session

        async def override_get_redis_client():
            client = redis.Redis(connection_pool=test_redis_pool)
            try:
                yield client
            finally:
                await client.aclose()

        app.dependency_overrides[get_postgres_session] = override_get_postgres_session
        app.dependency_overrides[get_postgres_session_utils] = override_get_postgres_session
        app.dependency_overrides[get_autocommit_postgres_session] = override_get_autocommit_postgres_session
        app.dependency_overrides[get_redis_client] = override_get_redis_client
        app.dependency_overrides[get_redis_client_utils] = override_get_redis_client
        app.dependency_overrides[get_model_registry] = lambda: model_registry
        return app

    @pytest.fixture(autouse=True)
    def _stub_global_context(self, probe_engine, test_redis_pool):
        tokenizer = MagicMock()
        tokenizer.encode.side_effect = lambda text: [0] * 10 if text else []
        with override_global_context(
            redis_pool=test_redis_pool,
            postgres_session_factory=async_sessionmaker(probe_engine, class_=AsyncSession, expire_on_commit=False),
            _tokenizer=tokenizer,
        ):
            yield

    async def _post_and_probe_during_forward(self, app, probe_engine, token, scenario) -> tuple[httpx.Response, dict]:
        captured: dict = {}

        async def probe_during_forward(request: httpx.Request) -> httpx.Response:
            captured["checked_out"] = probe_engine.pool.checkedout()
            captured["idle_in_transaction"] = await _count_idle_in_transaction()
            return scenario.build_response()

        respx.post(url=urljoin(DEFAULT_PROVIDER_URL, scenario.provider_path)).mock(side_effect=probe_during_forward)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(url=scenario.url, headers={"Authorization": f"Bearer {token}"}, json=scenario.request_body)

            hooks_tasks = [task for task in asyncio.all_tasks() if task.get_name().startswith("hooks-")]
            if hooks_tasks:
                await asyncio.gather(*hooks_tasks, return_exceptions=True)

        return response, captured

    @respx.mock
    async def test_autocommit_wiring_releases_the_connection_during_the_forward(
        self, scenario, probe_engine, seed_forward_auth, test_configuration, test_redis_pool, model_registry
    ):
        app = self._build_app(
            probe_engine,
            create_autocommit_postgres_session_factory(engine=probe_engine),
            test_configuration,
            test_redis_pool,
            model_registry,
        )

        response, captured = await self._post_and_probe_during_forward(app, probe_engine, seed_forward_auth, scenario)

        assert response.status_code == 200, response.text
        assert captured["checked_out"] == 0, captured
        assert captured["idle_in_transaction"] == 0, captured

    @respx.mock
    async def test_transactional_wiring_pins_an_idle_in_transaction_connection(
        self, scenario, probe_engine, seed_forward_auth, test_configuration, test_redis_pool, model_registry
    ):
        app = self._build_app(
            probe_engine,
            async_sessionmaker(probe_engine, class_=AsyncSession, expire_on_commit=False),
            test_configuration,
            test_redis_pool,
            model_registry,
        )

        response, captured = await self._post_and_probe_during_forward(app, probe_engine, seed_forward_auth, scenario)

        assert response.status_code == 200, response.text
        assert captured["checked_out"] == 1, captured
        assert captured["idle_in_transaction"] == 1, captured
