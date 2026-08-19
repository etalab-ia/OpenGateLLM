from unittest.mock import AsyncMock

from fastapi import Depends
from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import _key_encoder, _user_password_encoder, auth_login_use_case_factory, get_postgres_session
from api.domain.user import UserPasswordEncoder
from api.domain.user.errors import InvalidUserPasswordError, UserNotFoundError
from api.infrastructure.bcrypt import BcryptUserPasswordEncoder
from api.infrastructure.postgres import PostgresKeyRepository, PostgresUserRepository
from api.tests.integration.factories.sql import RoleSQLFactory
from api.use_cases.auth import AuthLoginUseCase
from api.utils.variables import SYSTEM_PLAYGROUND_KEY_NAME, EndpointRoute

URL = f"/v1{EndpointRoute.AUTH_LOGIN}"


def _valid_body(**overrides) -> dict:
    body = {
        "email": "login-user@test.com",
        "password": "s3cr3t",
    }
    body.update(overrides)
    return body


def _auth_login_use_case_factory(
    postgres_session=Depends(get_postgres_session),
    key_encoder=Depends(_key_encoder),
    password_encoder: UserPasswordEncoder = Depends(_user_password_encoder),
) -> AuthLoginUseCase:
    return AuthLoginUseCase(
        key_repository=PostgresKeyRepository(key_encoder=key_encoder, postgres_session=postgres_session),
        user_repository=PostgresUserRepository(postgres_session=postgres_session),
        user_password_encoder=password_encoder,
        auth_login_type="password",
    )


@pytest.mark.asyncio(loop_scope="session")
class TestAuthLogin:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, app):
        role = RoleSQLFactory()
        await db_session.flush()
        password_encoder = BcryptUserPasswordEncoder()
        repository = PostgresUserRepository(postgres_session=db_session)
        encoded_password = password_encoder.encode_password(password="s3cr3t")
        await repository.create_user(email="login-user@test.com", password=encoded_password, role_id=role.id)
        app.dependency_overrides[auth_login_use_case_factory] = _auth_login_use_case_factory

    async def test_happy_path(self, client: AsyncClient):
        response = await client.post(url=URL, json=_valid_body())

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "key"
        assert data["name"] == SYSTEM_PLAYGROUND_KEY_NAME
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
