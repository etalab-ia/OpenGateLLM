import asyncio
from collections.abc import Generator
from functools import partial
import logging
import time

from elasticsearch import AsyncElasticsearch
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from api.main import app
from api.schemas.admin.roles import LimitType, PermissionType
from api.sql.models import Base
from api.utils.configuration import configuration
from api.utils.variables import ENDPOINT__ADMIN_ROLES, ENDPOINT__ADMIN_ROUTERS, ENDPOINT__ADMIN_TOKENS, ENDPOINT__ADMIN_USERS


@pytest.fixture(scope="session")
def setup_database() -> None:
    """Create database tables before running tests."""
    url = configuration.dependencies.postgres.model_dump().get("url").replace("+asyncpg", "")
    engine = create_engine(url=url)
    Base.metadata.drop_all(engine)  # Clean state
    Base.metadata.create_all(engine)
    engine.dispose()


@pytest.fixture(scope="session")
def setup_elasticsearch_index() -> None:
    """Delete Elasticsearch index before running integration tests."""
    if configuration.dependencies.elasticsearch is None:
        return

    async def _delete_index() -> None:
        kwargs = configuration.dependencies.elasticsearch.model_dump()
        index_name = kwargs.pop("index_name")
        kwargs.pop("index_language")
        kwargs.pop("number_of_shards")
        kwargs.pop("number_of_replicas")
        client = AsyncElasticsearch(**kwargs)
        try:
            if await client.indices.exists(index=index_name):
                await client.indices.delete(index=index_name)
        finally:
            await client.close()

    asyncio.run(_delete_index())


@pytest.fixture(scope="session")
def test_client(setup_database, setup_elasticsearch_index) -> Generator[TestClient, None, None]:
    """Create test client with database already set up."""
    with TestClient(app=app) as client:
        client.headers = {"Authorization": f"Bearer {configuration.settings.auth_master_key}"}
        yield client


@pytest.fixture(scope="session")
def roles(test_client: TestClient) -> tuple[dict, dict]:
    """Create roles for tests, one with permissions and one without permissions."""

    # Use master key for authentication
    response = test_client.get(url=f"/v1{ENDPOINT__ADMIN_ROUTERS}")

    logging.debug(msg=f"get models: {response.text}")
    response.raise_for_status()
    routers = response.json()["data"]

    limits = []
    for router in routers:
        limits.append({"router": router["id"], "type": LimitType.RPM.value, "value": None})
        limits.append({"router": router["id"], "type": LimitType.RPD.value, "value": None})
        limits.append({"router": router["id"], "type": LimitType.TPM.value, "value": None})
        limits.append({"router": router["id"], "type": LimitType.TPD.value, "value": None})

    # create role admin
    response = test_client.post(
        url=f"/v1{ENDPOINT__ADMIN_ROLES}",
        json={"name": "test-role-admin", "default": False, "permissions": [permission.value for permission in PermissionType], "limits": limits},
    )
    logging.debug(msg=f"create role test-role-admin: {response.text}")
    response.raise_for_status()

    role_id_with_permissions = response.json()["id"]

    # create role user
    response = test_client.post(
        url=f"/v1{ENDPOINT__ADMIN_ROLES}",
        json={"name": "test-role-user", "default": False, "permissions": [], "limits": limits},
    )
    logging.debug(msg=f"create role test-role-user: {response.text}")
    response.raise_for_status()
    role_id_without_permissions = response.json()["id"]

    response = test_client.get(url=f"/v1{ENDPOINT__ADMIN_ROLES}/{role_id_with_permissions}")
    logging.debug(msg=f"get role test-role-with-permissions: {response.text}")
    response.raise_for_status()
    role_with_permissions = response.json()

    response = test_client.get(url=f"/v1{ENDPOINT__ADMIN_ROLES}/{role_id_without_permissions}")
    logging.debug(msg=f"get role test-role-without-permissions: {response.text}")
    response.raise_for_status()
    role_without_permissions = response.json()

    return role_with_permissions, role_without_permissions


@pytest.fixture(scope="session")
def users(test_client: TestClient, roles: tuple[dict, dict]) -> tuple[dict, dict]:
    """Create users for tests, one with admin role and one with user role."""

    # Use master key for authentication
    headers = {"Authorization": f"Bearer {configuration.settings.auth_master_key}"}

    role_with_permissions, role_without_permissions = roles

    # create user admin
    response = test_client.post(
        url=f"/v1{ENDPOINT__ADMIN_USERS}",
        json={"email": "test-user-admin@example.com", "name": "test-user-admin", "password": "test-password", "role": role_with_permissions["id"]},
        headers=headers,
    )
    response.raise_for_status()
    user_id_with_permissions = response.json()["id"]

    response = test_client.get(url=f"/v1{ENDPOINT__ADMIN_USERS}/{user_id_with_permissions}", headers=headers)
    logging.debug(msg=f"get user test-user-with-permissions: {response.text}")
    response.raise_for_status()
    user_with_permissions = response.json()

    # create user user
    response = test_client.post(
        url=f"/v1{ENDPOINT__ADMIN_USERS}",
        json={"email": "test-user-user@example.com", "name": "test-user-user", "password": "test-password", "role": role_without_permissions["id"]},
        headers=headers,
    )
    response.raise_for_status()
    user_id_user = response.json()["id"]

    response = test_client.get(url=f"/v1{ENDPOINT__ADMIN_USERS}/{user_id_user}", headers=headers)
    logging.debug(msg=f"get user test-user-without-permissions: {response.text}")
    response.raise_for_status()
    user_without_permissions = response.json()

    return user_with_permissions, user_without_permissions


@pytest.fixture(scope="session")
def tokens(test_client: TestClient, users: tuple[dict, dict]) -> tuple[dict, dict]:
    """Create tokens for test users."""

    # Use master key for authentication
    headers = {"Authorization": f"Bearer {configuration.settings.auth_master_key}"}

    user_with_permissions, user_without_permissions = users

    # create token admin
    response = test_client.post(
        url=f"/v1{ENDPOINT__ADMIN_TOKENS}",
        json={"user": user_with_permissions["id"], "name": "test-token-admin", "expires": int(time.time()) + 300},
        headers=headers,
    )
    response.raise_for_status()
    token_with_permissions = response.json()

    # create token user
    response = test_client.post(
        url=f"/v1{ENDPOINT__ADMIN_TOKENS}",
        json={"user": user_without_permissions["id"], "name": "test-token-user", "expires": int(time.time()) + 300},
        headers=headers,
    )
    response.raise_for_status()
    token_without_permissions = response.json()

    return token_with_permissions, token_without_permissions


@pytest.fixture(scope="session")
def client(test_client: TestClient, tokens: tuple[dict, dict]) -> Generator[TestClient, None, None]:
    token_with_permissions, token_without_permissions = tokens

    client = test_client

    # user
    client.get_without_permissions = partial(client.get, headers={"Authorization": f"Bearer {token_without_permissions["token"]}"})
    client.post_without_permissions = partial(client.post, headers={"Authorization": f"Bearer {token_without_permissions["token"]}"})
    client.delete_without_permissions = partial(client.delete, headers={"Authorization": f"Bearer {token_without_permissions["token"]}"})
    client.patch_without_permissions = partial(client.patch, headers={"Authorization": f"Bearer {token_without_permissions["token"]}"})

    # admin
    client.get_with_permissions = partial(client.get, headers={"Authorization": f"Bearer {token_with_permissions["token"]}"})
    client.post_with_permissions = partial(client.post, headers={"Authorization": f"Bearer {token_with_permissions["token"]}"})
    client.delete_with_permissions = partial(client.delete, headers={"Authorization": f"Bearer {token_with_permissions["token"]}"})
    client.patch_with_permissions = partial(client.patch, headers={"Authorization": f"Bearer {token_with_permissions["token"]}"})

    # root
    client.get_master = partial(client.get, headers={"Authorization": f"Bearer {configuration.settings.auth_master_key}"})
    client.post_master = partial(client.post, headers={"Authorization": f"Bearer {configuration.settings.auth_master_key}"})
    client.delete_master = partial(client.delete, headers={"Authorization": f"Bearer {configuration.settings.auth_master_key}"})
    client.patch_master = partial(client.patch, headers={"Authorization": f"Bearer {configuration.settings.auth_master_key}"})

    yield client
