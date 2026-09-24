from unittest.mock import AsyncMock

import pytest

from api.infrastructure.postgres import AutocommitSession, TransactionRequiredError
from api.infrastructure.postgres.decorators import with_lock


class _Repository:
    def __init__(self, postgres_session):
        self.postgres_session = postgres_session

    @with_lock(namespace="user", key="user_id")
    async def update_something(self, user_id: int) -> str:
        return "done"


class TestWithLock:
    @pytest.mark.asyncio
    async def test_should_acquire_the_advisory_lock_on_a_transactional_session(self):
        # Arrange
        repository = _Repository(postgres_session=AsyncMock())

        # Act
        result = await repository.update_something(user_id=42)

        # Assert
        assert result == "done"
        statement, parameters = repository.postgres_session.execute.await_args.args
        assert "pg_advisory_xact_lock" in str(statement)
        assert parameters == {"key": "user:42"}

    @pytest.mark.asyncio
    async def test_should_refuse_an_autocommit_session_instead_of_silently_dropping_the_lock(self):
        # Arrange: an autocommit session would commit right after the lock statement, releasing it at once
        repository = _Repository(postgres_session=AutocommitSession())

        # Act / Assert
        with pytest.raises(TransactionRequiredError, match="update_something"):
            await repository.update_something(user_id=42)
