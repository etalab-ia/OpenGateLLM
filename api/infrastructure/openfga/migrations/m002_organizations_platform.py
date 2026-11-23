import asyncpg

from ._openfgamigrationclient import OpenFgaMigrationClient

DESCRIPTION = "attach every organization to the platform: organization:<id>#platform@platform:api"

# Frozen at the time of the migration, like an Alembic revision: not read from the authorization enums.
PLATFORM_SUBJECT = "platform:api"
PLATFORM_RELATION = "platform"

_ORGANIZATION_IDS = """
    SELECT id
    FROM organization
    ORDER BY 1
"""


async def run(connection: asyncpg.Connection, openfga: OpenFgaMigrationClient, dry_run: bool) -> dict[str, int]:
    rows = await connection.fetch(_ORGANIZATION_IDS)

    granted, already_granted = 0, 0
    for row in rows:
        organization_object = f"organization:{row['id']}"

        if await openfga.check(subject=PLATFORM_SUBJECT, relation=PLATFORM_RELATION, object_=organization_object):
            already_granted += 1
            continue

        if not dry_run:
            await openfga.write(subject=PLATFORM_SUBJECT, relation=PLATFORM_RELATION, object_=organization_object)
        granted += 1

    return {"organizations_found": len(rows), "granted": granted, "already_granted": already_granted}
