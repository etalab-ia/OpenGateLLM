"""
Backfill the OpenFGA relations that rows already in Postgres must hold.

Runs every mNNN_*.py module of this package, in order. Each one reads Postgres and writes the tuples OpenFGA lacks,
checking each one first, so a second run writes nothing. Reads only the postgres and openfga dependencies of the
configuration file given by CONFIG_FILE, like Alembic, so it needs none of the other variables that file interpolates.

    python -m api.infrastructure.openfga.migrations [--dry-run] [--only m001_platform_admins]
"""

import argparse
import asyncio
import importlib
import pkgutil
import re
import sys

import aiohttp
import asyncpg
from openfga_sdk.exceptions import OpenApiException

from api.infrastructure.configuration import get_openfga_dependency, get_postgres_dependency

from ._openfgamigrationclient import OpenFgaMigrationClient, OpenFgaMigrationError

_OPENFGA_ERRORS = (OpenFgaMigrationError, OpenApiException, aiohttp.ClientError)
_MIGRATION_ERRORS = (*_OPENFGA_ERRORS, asyncpg.PostgresError)
_MIGRATION_NAME = re.compile(r"m\d{3}_")


def _get_migrations(only: str | None) -> list[str]:
    available = sorted(name for _, name, _ in pkgutil.iter_modules(sys.modules[__package__].__path__) if _MIGRATION_NAME.match(name))

    if only is None:
        return available

    wanted = only.removesuffix(".py")
    if wanted not in available:
        sys.exit(f"no migration named {only!r}, available: {', '.join(available)}")

    return [wanted]


def _get_asyncpg_url(sqlalchemy_url: str) -> str:
    return sqlalchemy_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _display_header(store_name: str, store_id: str, authorization_model_id: str, dry_run: bool) -> None:
    print(f"store:               {store_name} ({store_id})")
    print(f"authorization model: {authorization_model_id}")
    if dry_run:
        print("dry run:             enabled - nothing will be written")
    else:
        print("dry run:             disabled - changes will be applied to OpenFGA")
    print()


async def _run_migrations(migration_names: list[str], postgres_url: str, openfga: OpenFgaMigrationClient, dry_run: bool) -> int:
    connection = await asyncpg.connect(dsn=postgres_url)
    failures = 0
    try:
        for migration in migration_names:
            print(migration)
            module = importlib.import_module(f"{__package__}.{migration}")
            print(f"  description: {module.DESCRIPTION}")
            try:
                report = await module.run(connection=connection, openfga=openfga, dry_run=dry_run)
                print(f"  result:      {', '.join(f'{key}={value}' for key, value in report.items())}")
            except _MIGRATION_ERRORS as error:
                failures += 1
                print(f"  FAILED:      {error}", file=sys.stderr)
            finally:
                print()

        return failures
    finally:
        await connection.close()


async def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m api.infrastructure.openfga.migrations", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dry-run", action="store_true", help="report what would be written without writing it")
    parser.add_argument("--only", metavar="MODULE", help="run a single migration, by module name (m001_platform_admins)")
    arguments = parser.parse_args()

    selected_migrations = _get_migrations(arguments.only)
    postgres_configuration = get_postgres_dependency()
    openfga_configuration = get_openfga_dependency()

    openfga = OpenFgaMigrationClient(
        url=openfga_configuration.url, api_token=openfga_configuration.api_token, store_name=openfga_configuration.store_name
    )
    try:
        store_id, authorization_model_id = await openfga.connect()
    except _OPENFGA_ERRORS as error:
        await openfga.aclose()
        sys.exit(str(error))

    _display_header(store_name=openfga.store_name, store_id=store_id, authorization_model_id=authorization_model_id, dry_run=arguments.dry_run)

    try:
        failures = await _run_migrations(
            migration_names=selected_migrations,
            postgres_url=_get_asyncpg_url(postgres_configuration.url),
            openfga=openfga,
            dry_run=arguments.dry_run,
        )
    finally:
        await openfga.aclose()

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
