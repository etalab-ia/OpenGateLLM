from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import UsageSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.USAGE}"
DEPRECATED_URL = f"/v1{EndpointRoute.ME_USAGE}"
DAY = datetime(2026, 8, 1, tzinfo=UTC)
NEXT_DAY = datetime(2026, 8, 2, tzinfo=UTC)


def _unix(moment: datetime) -> int:
    return int(moment.timestamp())


@pytest.mark.asyncio(loop_scope="session")
class TestGetUsages:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(regular_user=True)
        self.key = await create_key(db_session, name="user_key", user=self.user, never_expires=True)

    @pytest.mark.parametrize("url", [URL, DEPRECATED_URL])
    async def test_happy_path(self, client: AsyncClient, db_session, url: str):
        UsageSQLFactory(
            user=self.user,
            router_name="model-a",
            token_id=self.key.id,
            endpoint="/v1/chat/completions",
            created=DAY.replace(hour=10),
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cost=0.1,
            kwh=0.01,
            kgco2eq=0.02,
        )
        UsageSQLFactory(
            user=self.user,
            router_name="model-a",
            token_id=self.key.id,
            endpoint="/v1/chat/completions",
            created=DAY.replace(hour=18),
            prompt_tokens=5,
            completion_tokens=5,
            total_tokens=10,
            cost=0.05,
            kwh=0.005,
            kgco2eq=0.01,
        )
        UsageSQLFactory(
            user=self.user,
            router_name="model-b",
            created=NEXT_DAY.replace(hour=8),
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            cost=0.01,
            kwh=0.001,
            kgco2eq=0.002,
        )
        other_user = UserSQLFactory()
        UsageSQLFactory(user=other_user, router_name="other-model", created=DAY.replace(hour=12))
        UsageSQLFactory(user=self.user, router_name="failed-model", created=DAY.replace(hour=11), failed=True)
        await db_session.flush()

        response = await client.get(
            url=url,
            headers={"Authorization": f"Bearer {self.key.token}"},
            params={"start_time": _unix(DAY), "end_time": _unix(NEXT_DAY + timedelta(days=1)), "limit": 10},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert data["total"] == 2
        assert data["offset"] == 0
        assert data["limit"] == 10
        assert len(data["data"]) == 2

        newest, oldest = data["data"]
        assert newest["object"] == "usage.bucket"
        assert newest["start_time"] == _unix(NEXT_DAY)
        assert newest["end_time"] == _unix(NEXT_DAY + timedelta(days=1))
        assert newest["prompt_tokens"] == 1
        assert newest["completion_tokens"] == 1
        assert newest["total_tokens"] == 2
        assert newest["cost"] == pytest.approx(0.01)
        assert newest["impacts"]["kWh"] == pytest.approx(0.001)
        assert newest["impacts"]["kgCO2eq"] == pytest.approx(0.002)

        assert oldest["object"] == "usage.bucket"
        assert oldest["start_time"] == _unix(DAY)
        assert oldest["end_time"] == _unix(NEXT_DAY)
        assert oldest["prompt_tokens"] == 15
        assert oldest["completion_tokens"] == 25
        assert oldest["total_tokens"] == 40
        assert oldest["cost"] == pytest.approx(0.15)
        assert oldest["impacts"]["kWh"] == pytest.approx(0.015)
        assert oldest["impacts"]["kgCO2eq"] == pytest.approx(0.03)

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.get(
            url=URL,
            headers=headers,
            params={"start_time": _unix(DAY), "end_time": _unix(NEXT_DAY)},
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
