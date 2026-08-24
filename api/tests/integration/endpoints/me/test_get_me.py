from datetime import datetime, timedelta

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.domain.role.entities import LimitType, PermissionType
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import LimitSQLFactory, PermissionSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ME}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetMe:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(regular_user=True, name="Alice", email="alice@example.com", budget=42.5, priority=3)
        PermissionSQLFactory(role=self.user.role, permission=PermissionType.READ_METRIC)
        self.router = RouterSQLFactory()
        LimitSQLFactory(role=self.user.role, router=self.router, type=LimitType.TPM, value=100)
        LimitSQLFactory(role=self.user.role, router=self.router, type=LimitType.RPM, value=0)
        self.key = await create_key(db_session, name="user_key", user=self.user, never_expires=True)

    async def test_happy_path(self, client: AsyncClient):
        response = await client.get(url=URL, headers={"Authorization": f"Bearer {self.key.token}"})

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "userInfo"
        assert data["id"] == self.user.id
        assert data["email"] == "alice@example.com"
        assert data["name"] == "Alice"
        assert data["organization_id"] == self.user.organization_id
        assert data["budget"] == 42.5
        assert data["permissions"] == [PermissionType.READ_METRIC]
        assert data["expires"] is None
        assert {"router_id": self.router.id, "type": LimitType.TPM, "value": 100} in data["limits"]
        assert "organization" not in data
        assert "priority" not in data
        assert "created" not in data
        assert "updated" not in data

    async def test_allows_expired_user(self, client: AsyncClient, db_session):
        expired_user = UserSQLFactory(role=self.user.role, expires=datetime.now() - timedelta(days=1))
        key = await create_key(db_session, name="expired_user_key", user=expired_user, never_expires=True)

        response = await client.get(url=URL, headers={"Authorization": f"Bearer {key.token}"})

        assert response.status_code == 200, response.text
        assert response.json()["id"] == expired_user.id
        assert response.json()["object"] == "userInfo"

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
