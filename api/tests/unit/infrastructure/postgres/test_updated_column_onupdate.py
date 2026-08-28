"""`updated` must be bumped by every Core UPDATE.

The columns rely on `onupdate=func.now()` (`api/sql/models.py`) rather than on each
repository spelling `updated=func.now()` in its `.values()`. That works — SQLAlchemy
injects the column default into the SET clause of any `update()` construct — but
nothing pinned it, so removing `onupdate`, or issuing a raw `text()` UPDATE, would
silently leave `updated` equal to `created`.

These tests assert on the compiled statement rather than on a round trip: Postgres
`now()` is transaction-scoped, so a create and an update executed inside a single
transaction — which is what the integration harness does, see
`adr/2026-03-17-integration-test-isolation.md` — always share the same timestamp.
A round-trip assertion would fail for that reason alone, whatever the code does.
"""

import pytest
from sqlalchemy import update
from sqlalchemy.dialects import postgresql

from api.sql.models import Organization, Provider, Role, Router, User


def _set_clause(statement) -> str:
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    return compiled.split("SET", 1)[1].split("WHERE", 1)[0]


class TestUpdatedColumnIsBumpedByCoreUpdate:
    @pytest.mark.parametrize(
        "table,values",
        [
            (Role, {"name": "x"}),
            (User, {"email": "x@y.z"}),
            (Router, {"name": "x"}),
            (Provider, {"timeout": 60}),
            (Organization, {"name": "x"}),
        ],
        ids=["role", "user", "router", "provider", "organization"],
    )
    def test_should_set_updated_on_every_core_update(self, table, values):
        # Act
        clause = _set_clause(update(table).values(**values))

        # Assert
        assert "updated=now()" in clause.replace(" ", ""), f"UPDATE {table.__tablename__} does not bump `updated`: SET{clause}"

    @pytest.mark.parametrize(
        "table",
        [Role, User, Router, Provider, Organization],
        ids=["role", "user", "router", "provider", "organization"],
    )
    def test_should_declare_onupdate_on_the_updated_column(self, table):
        # Act
        column = table.__table__.c["updated"]

        # Assert
        assert column.onupdate is not None, f"{table.__tablename__}.updated lost its onupdate default"

    def test_should_not_touch_updated_when_the_statement_sets_it_explicitly(self):
        # Arrange — the budget deduction in the request hooks sets `updated` itself
        from sqlalchemy import func

        # Act
        clause = _set_clause(update(User).values(budget=1.0, updated=func.now()))

        # Assert — a single assignment, not a duplicated one
        assert clause.count("updated=") == 1
