from datetime import UTC, datetime, timedelta

import pytest

from api.domain.key.errors import KeyNotFoundError
from api.infrastructure.postgres import PostgresKeyRepository
from api.tests.integration.factories.sql import TokenSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresKeyRepository(postgres_session=db_session)


def _to_epoch(value: datetime) -> int:
    return int(value.replace(tzinfo=UTC).timestamp())


@pytest.mark.asyncio(loop_scope="session")
class TestGetKeyExpiration:
    async def test_get_key_expiration_should_return_expiration_epoch_when_token_has_expiration(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        expires_at = datetime(2030, 1, 1, 12, 0, 0)
        token = TokenSQLFactory(user=user, expires=expires_at)
        await db_session.flush()

        # Act
        result = await repository.get_key_expiration(user_id=user.id, key_id=token.id)

        # Assert
        assert result == _to_epoch(expires_at)

    async def test_get_key_expiration_should_return_none_when_token_never_expires(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        token = TokenSQLFactory(user=user, never_expires=True)
        await db_session.flush()

        # Act
        result = await repository.get_key_expiration(user_id=user.id, key_id=token.id)

        # Assert
        assert result is None

    async def test_get_key_expiration_should_return_past_epoch_when_token_is_expired(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        expires_at = (datetime.now() - timedelta(days=1)).replace(microsecond=0)
        token = TokenSQLFactory(user=user, expires=expires_at)
        await db_session.flush()

        # Act
        result = await repository.get_key_expiration(user_id=user.id, key_id=token.id)

        # Assert
        assert result == _to_epoch(expires_at)
        assert result < _to_epoch(datetime.now())

    async def test_get_key_expiration_should_return_key_not_found_when_token_does_not_exist(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_key_expiration(user_id=user.id, key_id=999999)

        # Assert
        assert isinstance(result, KeyNotFoundError)

    async def test_get_key_expiration_should_return_key_not_found_when_token_belongs_to_other_user(self, repository, db_session):
        # Arrange
        owner = UserSQLFactory()
        other_user = UserSQLFactory()
        token = TokenSQLFactory(user=owner)
        await db_session.flush()

        # Act
        result = await repository.get_key_expiration(user_id=other_user.id, key_id=token.id)

        # Assert
        assert isinstance(result, KeyNotFoundError)
