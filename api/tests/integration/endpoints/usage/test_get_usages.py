from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import UsageSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.USAGE}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetUsages:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(regular_user=True)
        self.key = await create_key(db_session, name="user_key", user=self.user, never_expires=True)

    async def test_happy_path(self, client: AsyncClient, db_session):
        own_usage = UsageSQLFactory(user=self.user, router_name="model-a", token_name="own-key", endpoint="/v1/chat/completions")
        other_user = UserSQLFactory()
        UsageSQLFactory(user=other_user, router_name="other-model")
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert data["total"] == 1
        assert data["offset"] == 0
        assert data["limit"] == 10
        assert len(data["data"]) == 1
        item = data["data"][0]
        assert item["object"] == "usage"
        assert item["model"] == "model-a"
        assert item["key"] == "own-key"
        assert item["endpoint"] == "/v1/chat/completions"
        assert item["usage"]["prompt_tokens"] == own_usage.prompt_tokens
        assert item["usage"]["completion_tokens"] == own_usage.completion_tokens
        assert item["usage"]["total_tokens"] == own_usage.total_tokens
        assert item["usage"]["metrics"]["latency"] == own_usage.latency
        assert item["usage"]["metrics"]["ttft"] == own_usage.ttft

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.get(url=URL, headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
