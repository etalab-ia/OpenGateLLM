from unittest.mock import create_autospec

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_my_organization_use_case_factory
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import create_key
from api.tests.integration.factories.sql import UserSQLFactory
from api.use_cases.organizations import GetMyOrganizationUseCase

URL = f"/v1{EndpointRoute.ORGANIZATIONS_ME}"


@pytest.mark.asyncio(loop_scope="session")
class TestRequestLog:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(regular_user=True)
        self.key = await create_key(db_session, name="user_key", user=self.user, never_expires=True)

    async def test_happy_path_returns_a_request_id(self, client: AsyncClient):
        response = await client.get(url=URL, headers={"Authorization": f"Bearer {self.key.token}"})

        assert response.status_code == 200, response.text
        assert len(response.headers["X-Request-ID"]) == 32

    async def test_unexpected_use_case_exception_answers_generic_500(self, client: AsyncClient, app):
        mock_use_case = create_autospec(GetMyOrganizationUseCase, instance=True, spec_set=True)
        mock_use_case.execute.side_effect = RuntimeError("database is gone")
        app.dependency_overrides[get_my_organization_use_case_factory] = lambda: mock_use_case

        response = await client.get(url=URL, headers={"Authorization": f"Bearer {self.key.token}"})

        assert response.status_code == 500
        assert response.json() == {"detail": "An unexpected error occurred"}
        assert "X-Request-ID" in response.headers
