from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.infrastructure.postgres import AutocommitSession, TransactionRequiredError
from api.sql.models import User as UserTable


class TestAutocommitSession:
    @pytest.mark.asyncio
    async def test_should_commit_after_the_statement_so_the_connection_returns_to_the_pool(self):
        # Arrange
        session = AutocommitSession()
        recorder = MagicMock()
        with (
            patch.object(AsyncSession, "execute", new=AsyncMock(return_value="result")) as parent_execute,
            patch.object(AutocommitSession, "commit", new=AsyncMock()) as commit,
        ):
            recorder.attach_mock(parent_execute, "execute")
            recorder.attach_mock(commit, "commit")

            # Act
            result = await session.execute(select(UserTable))

        # Assert
        assert result == "result"
        assert [name for name, _, _ in recorder.mock_calls] == ["execute", "commit"]

    @pytest.mark.asyncio
    async def test_should_commit_once_per_statement(self):
        # Arrange
        session = AutocommitSession()
        with (
            patch.object(AsyncSession, "execute", new=AsyncMock(return_value="result")),
            patch.object(AutocommitSession, "commit", new=AsyncMock()) as commit,
        ):
            # Act
            await session.execute(select(UserTable))
            await session.execute(select(UserTable))

        # Assert
        assert commit.await_count == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entry_point", ["scalar", "get"])
    async def test_should_commit_after_the_other_reading_entry_points_that_bypass_execute(self, entry_point):
        # Arrange: scalar() and get() do not route through execute(), they would pin a connection unnoticed
        session = AutocommitSession()
        with (
            patch.object(AsyncSession, entry_point, new=AsyncMock(return_value="result")),
            patch.object(AutocommitSession, "commit", new=AsyncMock()) as commit,
        ):
            # Act
            result = await getattr(session, entry_point)(select(UserTable))

        # Assert
        assert result == "result"
        commit.assert_awaited_once()

    def test_should_refuse_begin_nested_because_a_savepoint_needs_a_transaction(self):
        # Arrange
        session = AutocommitSession()

        # Act / Assert
        with pytest.raises(TransactionRequiredError):
            session.begin_nested()

    def test_should_refuse_begin_because_it_spans_several_statements(self):
        # Arrange
        session = AutocommitSession()

        # Act / Assert
        with pytest.raises(TransactionRequiredError):
            session.begin()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entry_point", ["stream", "stream_scalars", "connection"])
    async def test_should_refuse_the_entry_points_that_inherently_hold_the_connection(self, entry_point):
        # Arrange
        session = AutocommitSession()

        # Act / Assert
        with pytest.raises(TransactionRequiredError):
            await getattr(session, entry_point)()
