import asyncpg

from ._openfgamigrationclient import OpenFgaMigrationClient

DESCRIPTION = "write user:<id>#member@organization:<organization_id> for every user"

# Frozen at the time of the migration, like an Alembic revision: not read from the authorization enums.
MEMBER_RELATION = "member"

_USER_ORGANIZATIONS = """
    SELECT id, organization_id
    FROM "user"
    ORDER BY 1
"""


async def run(connection: asyncpg.Connection, openfga: OpenFgaMigrationClient, dry_run: bool) -> dict[str, int]:
    rows = await connection.fetch(_USER_ORGANIZATIONS)

    granted, already_granted = 0, 0
    for row in rows:
        subject = f"user:{row['id']}"
        organization_object = f"organization:{row['organization_id']}"

        if await openfga.check(subject=subject, relation=MEMBER_RELATION, object_=organization_object):
            already_granted += 1
            continue

        if not dry_run:
            await openfga.write(subject=subject, relation=MEMBER_RELATION, object_=organization_object)
        granted += 1

    return {"users_found": len(rows), "granted": granted, "already_granted": already_granted}
