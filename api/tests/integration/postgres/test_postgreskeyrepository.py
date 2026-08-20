from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from api.domain import EntitiesPage, SortField, SortOrder
from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.infrastructure.jwt import JwtKeyEncoder
from api.infrastructure.postgres import PostgresKeyRepository
from api.sql.models import Token as KeyTable
from api.tests.integration.factories.sql import KeySQLFactory, UserSQLFactory


@pytest.fixture
def secret_key():
    return "MY_SECRET_KEY"


@pytest.fixture
def key_encoder(secret_key):
    return JwtKeyEncoder(secret_key=secret_key)


@pytest.fixture
def repository(db_session, key_encoder):
    return PostgresKeyRepository(key_encoder=key_encoder, postgres_session=db_session)


async def _assert_stored_token_is_masked(db_session, key: Key) -> None:
    stored = await db_session.scalar(select(KeyTable).where(KeyTable.id == key.id))
    registered_value = f"{key.value[:8]}...{key.value[-8:]}"
    assert stored.token == registered_value
    assert stored.token != key.value


def _assert_jwt_claims(key: Key, *, key_encoder: JwtKeyEncoder, user_id: int, expires: datetime | None) -> None:
    claims = key_encoder.decode(key_value=key.value)
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
class TestGetKeysPage:
    async def test_returns_correct_page_with_limit_and_offset(self, repository, db_session):
        user = UserSQLFactory()
        KeySQLFactory(user=user, name="key_a", never_expires=True)
        KeySQLFactory(user=user, name="key_b", never_expires=True)
        KeySQLFactory(user=user, name="key_c", never_expires=True)
        await db_session.flush()

        result = await repository.get_keys_page(user_id=user.id, limit=2, offset=0, sort_by=SortField.NAME, sort_order=SortOrder.ASC)

        assert isinstance(result, EntitiesPage)
        assert all(isinstance(k, Key) for k in result.data)
        returned_names = [k.name for k in result.data]
        assert returned_names == ["key_a", "key_b"]

    async def test_filters_by_user_id(self, repository, db_session):
        user = UserSQLFactory()
        other_user = UserSQLFactory()
        KeySQLFactory(user=user, name="user-key", never_expires=True)
        KeySQLFactory(user=other_user, name="other-key", never_expires=True)
        await db_session.flush()

        result = await repository.get_keys_page(user_id=user.id)

        assert result.total == 1
        assert result.data[0].name == "user-key"

    async def test_excludes_expired_keys(self, repository, db_session):
        user = UserSQLFactory()
        KeySQLFactory(user=user, name="active-key", never_expires=True)
        KeySQLFactory(user=user, name="expired-key", expired=True)
        await db_session.flush()

        result = await repository.get_keys_page(user_id=user.id)

        assert result.total == 1
        assert result.data[0].name == "active-key"

    async def test_returns_empty_page_when_offset_exceeds_total(self, repository, db_session):
        # the windowed count rides on the rows, an empty page must still report the real total
        user = UserSQLFactory()
        KeySQLFactory(user=user, name="key_a", never_expires=True)
        await db_session.flush()

        result = await repository.get_keys_page(user_id=user.id, limit=10, offset=100)

        assert result.data == []
        assert result.total == 1

    async def test_sort_by_name_desc(self, repository, db_session):
        user = UserSQLFactory()
        KeySQLFactory(user=user, name="key_a", never_expires=True)
        KeySQLFactory(user=user, name="key_c", never_expires=True)
        KeySQLFactory(user=user, name="key_b", never_expires=True)
        await db_session.flush()

        result = await repository.get_keys_page(user_id=user.id, sort_by=SortField.NAME, sort_order=SortOrder.DESC)

        assert [k.name for k in result.data] == ["key_c", "key_b", "key_a"]


@pytest.mark.asyncio(loop_scope="session")
class TestCreateKey:
    async def test_create_key_should_return_key_when_user_exists(self, repository, db_session, key_encoder):
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
        _assert_jwt_claims(result, key_encoder=key_encoder, user_id=user.id, expires=None)
        await _assert_stored_token_is_masked(db_session, result)

    async def test_create_key_should_return_key_with_expiration(self, repository, db_session, key_encoder):
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
        _assert_jwt_claims(result, key_encoder=key_encoder, user_id=user.id, expires=expires_at)
        await _assert_stored_token_is_masked(db_session, result)

    async def test_create_key_should_return_user_not_found_error_when_user_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.create_key(user_id=999999, name="orphan-key", expire=None)

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 999999


@pytest.mark.asyncio(loop_scope="session")
class TestUpsertKey:
    async def test_upsert_key_should_create_key_when_it_does_not_exist(self, repository, db_session, key_encoder):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.upsert_key(user_id=user.id, name="playground", expire=None)

        # Assert
        assert isinstance(result, Key)
        assert result.name == "playground"
        assert result.user_id == user.id
        assert result.value.startswith("sk-")
        _assert_jwt_claims(result, key_encoder=key_encoder, user_id=user.id, expires=None)
        await _assert_stored_token_is_masked(db_session, result)

    async def test_upsert_key_should_update_existing_key(self, repository, db_session, key_encoder):
        # Arrange
        user = UserSQLFactory()
        expires_at = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
        await db_session.flush()
        created = await repository.upsert_key(user_id=user.id, name="playground", expire=None)

        # Act
        result = await repository.upsert_key(user_id=user.id, name="playground", expire=expires_at)

        # Assert
        assert isinstance(result, Key)
        assert result.id == created.id
        assert result.expires == expires_at
        _assert_jwt_claims(result, key_encoder=key_encoder, user_id=user.id, expires=expires_at)
        await _assert_stored_token_is_masked(db_session, result)

    async def test_upsert_key_should_return_user_not_found_error_when_user_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.upsert_key(user_id=999999, name="playground", expire=None)

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 999999
