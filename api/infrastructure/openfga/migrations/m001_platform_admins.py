import asyncpg

from ._openfgamigrationclient import OpenFgaMigrationClient

DESCRIPTION = "grant platform:api#admin@user:<id> to every user whose role holds the ADMIN permission"

# Frozen at the time of the migration, like an Alembic revision: not read from the authorization enums.
PLATFORM_OBJECT = "platform:api"
ADMIN_RELATION = "admin"

# SQLAlchemy persists enum *names*, not values, hence 'ADMIN' and not 'admin'.
_ADMIN_USER_IDS = """
    SELECT DISTINCT "user".id
    FROM "user"
    JOIN permission ON permission.role_id = "user".role_id
    WHERE permission.permission = 'ADMIN'
    ORDER BY 1
"""


async def run(connection: asyncpg.Connection, openfga: OpenFgaMigrationClient, dry_run: bool) -> dict[str, int]:
    rows = await connection.fetch(_ADMIN_USER_IDS)

    granted, already_granted = 0, 0
    for row in rows:
        subject = f"user:{row['id']}"

        if await openfga.check(subject=subject, relation=ADMIN_RELATION, object_=PLATFORM_OBJECT):
            already_granted += 1
            continue

        if not dry_run:
            await openfga.write(subject=subject, relation=ADMIN_RELATION, object_=PLATFORM_OBJECT)
        granted += 1

    return {"admins_found": len(rows), "granted": granted, "already_granted": already_granted}
