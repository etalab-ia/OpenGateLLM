from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import auth_login_use_case_factory
from api.domain.user.errors import InvalidUserPasswordError, UserNotFoundError
from api.infrastructure.bcrypt import BcryptUserPasswordEncoder
from api.infrastructure.postgres import PostgresUserRepository
from api.tests.integration.factories.sql import RoleSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.AUTH_LOGIN}"


def _valid_body(**overrides) -> dict:
    body = {
        "email": "login-user@test.com",
        "password": "s3cr3t",
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestAuthLogin:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        role = RoleSQLFactory()
        await db_session.flush()
        password_encoder = BcryptUserPasswordEncoder()
        repository = PostgresUserRepository(postgres_session=db_session)
        encoded_password = password_encoder.encode_password(password="s3cr3t")
        await repository.create_user(email="login-user@test.com", password=encoded_password, role_id=role.id)

    async def test_happy_path(self, client: AsyncClient):
        response = await client.post(url=URL, json=_valid_body())

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "key"
        assert data["name"] == "playground"
        assert isinstance(data["id"], int)
        assert data["value"].startswith("sk-")
        assert isinstance(data["expires"], int)
        assert isinstance(data["created"], int)

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                UserNotFoundError(email="missing@test.com"),
                401,
                "Invalid email or password.",
            ),
            (
                InvalidUserPasswordError(),
                401,
                "Invalid email or password.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[auth_login_use_case_factory] = lambda: mock_use_case

        response = await client.post(url=URL, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
