from datetime import UTC, datetime

from jose import jwt
import pytest
from sqlalchemy import select

from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.infrastructure.postgres import PostgresKeyRepository
from api.sql.models import Token as KeyTable
from api.tests.integration.factories.sql import KeySQLFactory, UserSQLFactory


@pytest.fixture
def secret_key():
    return "MY_SECRET_KEY"


@pytest.fixture
def repository(db_session, secret_key):
    return PostgresKeyRepository(postgres_session=db_session, secret_key=secret_key)


async def _assert_stored_token_is_masked(db_session, key: Key) -> None:
    stored = await db_session.scalar(select(KeyTable).where(KeyTable.id == key.id))
    registered_value = f"{key.value[:8]}...{key.value[-8:]}"
    assert stored.token == registered_value
    assert stored.token != key.value


def _assert_jwt_claims(key: Key, *, secret_key: str, user_id: int, expires: datetime | None) -> None:
    claims = jwt.decode(key.value.removeprefix("sk-"), key=secret_key, algorithms=["HS256"])
    assert claims["user_id"] == user_id
    assert claims["token_id"] == key.id
    assert claims.get("expires") == (int(expires.timestamp()) if expires is not None else None)


@pytest.mark.asyncio(loop_scope="session")
class TestGetKeyById:
    async def test_get_key_by_id_should_return_key_when_token_exists(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        expires_at = datetime(2030, 1, 1, 12, 0, 0)
        token = KeySQLFactory(user=user, expires=expires_at, name="my-key")
        await db_session.flush()

        # Act
        result = await repository.get_key_by_id(key_id=token.id)

        # Assert
        assert isinstance(result, Key)
        assert result.id == token.id
        assert result.name == "my-key"
        assert result.user_id == user.id

    async def test_get_key_by_id_should_return_key_with_none_expires_when_token_never_expires(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        token = KeySQLFactory(user=user, never_expires=True)
        await db_session.flush()

        # Act
        result = await repository.get_key_by_id(key_id=token.id)

        # Assert
        assert isinstance(result, Key)
        assert result.id == token.id
        assert result.user_id == user.id
        assert result.expires is None

    async def test_get_key_by_id_should_return_key_not_found_when_token_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.get_key_by_id(key_id=999999)

        # Assert
        assert isinstance(result, KeyNotFoundError)
        assert result.id == 999999


@pytest.mark.asyncio(loop_scope="session")
class TestCreateKey:
    async def test_create_key_should_return_key_when_user_exists(self, repository, db_session, secret_key):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_key(user_id=user.id, name="new-key", expire=None)

        # Assert
        assert isinstance(result, Key)
        assert result.name == "new-key"
        assert result.user_id == user.id
        assert result.value.startswith("sk-")
        assert result.expires is None
        assert isinstance(result.id, int)
        _assert_jwt_claims(result, secret_key=secret_key, user_id=user.id, expires=None)
        await _assert_stored_token_is_masked(db_session, result)

    async def test_create_key_should_return_key_with_expiration(self, repository, db_session, secret_key):
        # Arrange
        user = UserSQLFactory()
        expires_at = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
        await db_session.flush()

        # Act
        result = await repository.create_key(user_id=user.id, name="expiring-key", expire=expires_at)

        # Assert
        assert isinstance(result, Key)
        assert result.name == "expiring-key"
        assert result.expires == expires_at
        _assert_jwt_claims(result, secret_key=secret_key, user_id=user.id, expires=expires_at)
        await _assert_stored_token_is_masked(db_session, result)

    async def test_create_key_should_return_user_not_found_error_when_user_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.create_key(user_id=999999, name="orphan-key", expire=None)

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 999999
