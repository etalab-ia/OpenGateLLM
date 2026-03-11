"""add master to permissiontype enum

Revision ID: b1c2d3e4f5a6
Revises: f02a2525b97c
Create Date: 2026-03-10 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "c206a2bfefe9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# This migration adds 'MASTER' to the 'permissiontype' enum. Since PostgreSQL does not support removing values from an enum type directly, the downgrade function recreates the enum without these values and updates the existing data accordingly.
# Alembic's autogenerate does not detect changes to enum types, so we need to manually add the new values in the upgrade function and handle the downgrade by recreating the enum type without the new values.
# Alembic: https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect
# PostgreSQL: https://www.postgresql.org/docs/current/datatype-enum.html#DATATYPE-ENUM-IMPLEMENTATION-DETAILS


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE permissiontype ADD VALUE IF NOT EXISTS 'MASTER';")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL does not support removing values from an enum directly (no DROP VALUE).
    # The only way to remove a value is to recreate the enum type from scratch.
    # This requires three steps: detach the column, drop the type, recreate it, reattach.

    # Step 1: cast the column to text so the enum type has no dependents and can be dropped.
    # USING permission::text tells PostgreSQL to convert each enum value to text (identity cast).
    op.execute("ALTER TABLE permission ALTER COLUMN permission TYPE text USING permission::text;")

    # Step 2: drop the existing enum type now that nothing depends on it.
    op.execute("DROP TYPE IF EXISTS permissiontype;")

    # Step 3: recreate the enum without MASTER.
    op.execute("CREATE TYPE permissiontype AS ENUM ('ADMIN', 'CREATE_PUBLIC_COLLECTION', 'READ_METRIC', 'PROVIDE_MODELS');")

    # Step 4: delete rows that used MASTER before recasting, since 'MASTER' no longer exists in the enum and the cast in the next step would fail on those rows.
    op.execute("DELETE FROM permission WHERE permission = 'MASTER';")

    # Step 5: cast the column back from text to the recreated enum type.
    # USING permission::permissiontype does a direct string match against the enum labels.
    op.execute("ALTER TABLE permission ALTER COLUMN permission TYPE permissiontype USING permission::permissiontype;")
