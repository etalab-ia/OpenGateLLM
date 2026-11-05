from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import Engine, create_engine, func, make_url, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from api.domain.role.entities import PermissionType
from api.infrastructure.postgres.models import Base
from api.tests.integration.factories.sql import (
    KeySQLFactory,
    LimitSQLFactory,
    PermissionSQLFactory,
    ProviderSQLFactory,
    RouterAliasSQLFactory,
    RouterSQLFactory,
    UsageSQLFactory,
    UserSQLFactory,
)
from api.tests.integration.postgresfixtures import TEST_POSTGRES_URL, bind_sql_factories

REPOSITORY_ROOT = Path(__file__).parents[4]


@pytest.fixture
def alembic_config() -> Config:
    # Without a file: alembic.ini configures the logging, which would disable the loggers of the tests that run next.
    config = Config()
    config.set_main_option("script_location", str(REPOSITORY_ROOT / "api" / "alembic"))
    return config


@pytest.fixture
def empty_database(test_configuration, monkeypatch) -> Iterator[Engine]:
    test_url = make_url(TEST_POSTGRES_URL)
    database_url = test_url.set(database=f"{test_url.database}_migrations")
    maintenance_engine = create_engine(
        test_url.set(drivername="postgresql+psycopg2", database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    with maintenance_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{database_url.database}"'))
        connection.execute(text(f'CREATE DATABASE "{database_url.database}"'))

    # env.py reads the database URL from the configuration, and two migrations read it too.
    postgres = SimpleNamespace(url=database_url.render_as_string(hide_password=False))
    configuration = test_configuration.model_copy(update={"dependencies": SimpleNamespace(postgres=postgres)})
    monkeypatch.setattr("api.infrastructure.configuration.get_configuration", lambda: configuration)

    yield create_engine(database_url.set(drivername="postgresql+psycopg2"), poolclass=NullPool)

    with maintenance_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE "{database_url.database}"'))


def test_should_have_a_single_head(alembic_config):
    heads = ScriptDirectory.from_config(alembic_config).get_heads()

    assert len(heads) == 1, f"Two migrations share a parent, `alembic upgrade head` would fail: {heads}"


def test_should_match_the_models_and_downgrade_with_rows(alembic_config, empty_database):
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)

    _insert_a_row_in_every_table(empty_database)

    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)


def _insert_a_row_in_every_table(engine: Engine) -> None:
    with Session(engine) as session, bind_sql_factories(session):
        user = UserSQLFactory()
        key = KeySQLFactory(user=user)
        router = RouterSQLFactory(user=user)
        provider = ProviderSQLFactory(router=router)
        RouterAliasSQLFactory(router=router)
        for permission in PermissionType:
            PermissionSQLFactory(role=user.role, permission=permission)
        LimitSQLFactory(role=user.role, router=router)
        UsageSQLFactory(user=user, token_id=key.id, router_id=router.id, provider_id=provider.id)
        session.commit()

        empty_tables = [table.name for table in Base.metadata.sorted_tables if session.scalar(select(func.count()).select_from(table)) == 0]

    assert not empty_tables, f"Add a row to these tables, their migrations meet no data here: {empty_tables}"
