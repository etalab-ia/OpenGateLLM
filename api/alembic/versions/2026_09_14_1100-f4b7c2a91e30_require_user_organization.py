"""require user organization

Revision ID: f4b7c2a91e30
Revises: c8e1a04b7f12
Create Date: 2026-09-14 11:00:00.000000

Organization membership becomes mandatory. Users that have none are moved to the
`default` organization, created here when the deployment does not already have it.

The downgrade only relaxes the NOT NULL: the `default` organization and the
memberships backfilled here are operator data and are kept.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f4b7c2a91e30"
down_revision: Union[str, None] = "c8e1a04b7f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# inlined on purpose: a migration must keep replaying the value that was current when it was written
_DEFAULT_ORGANIZATION_NAME = "default"


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("INSERT INTO organization (name, created, updated) VALUES (:name, now(), now()) ON CONFLICT (name) DO NOTHING"),
        {"name": _DEFAULT_ORGANIZATION_NAME},
    )
    connection.execute(
        sa.text('UPDATE "user" SET organization_id = (SELECT id FROM organization WHERE name = :name) WHERE organization_id IS NULL'),
        {"name": _DEFAULT_ORGANIZATION_NAME},
    )
    op.alter_column("user", "organization_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column("user", "organization_id", existing_type=sa.Integer(), nullable=True)
