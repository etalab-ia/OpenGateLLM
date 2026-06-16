from datetime import datetime

import pytest

from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.infrastructure.postgres import PostgresKeyRepository
from api.tests.integration.factories.sql import TokenSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresKeyRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetKeyById:
    async def test_get_key_by_id_should_return_key_when_token_exists(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        expires_at = datetime(2030, 1, 1, 12, 0, 0)
        token = TokenSQLFactory(user=user, expires=expires_at, name="my-key")
        await db_session.flush()

        # Act
        result = await repository.get_key_by_id(key_id=token.id)

        # Assert
        assert isinstance(result, Key)
        assert result.id == token.id
        assert result.name == "my-key"
        assert result.user_id == user.id
        assert result.expires == PostgresKeyRepository._to_utc(expires_at)
        assert result.created == PostgresKeyRepository._to_utc(token.created)

    async def test_get_key_by_id_should_return_key_with_none_expires_when_token_never_expires(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        token = TokenSQLFactory(user=user, never_expires=True)
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
