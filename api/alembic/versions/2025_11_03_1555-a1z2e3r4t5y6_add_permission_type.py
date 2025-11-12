"""Add 'PROVIDE_MODELS' value to permissiontype enum

Revision ID: a1z2e3r4t5y6
Revises: ea462f747600
Create Date: 2025-11-03 15:55:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1z2e3r4t5y6'
down_revision: Union[str, None] = 'ea462f747600'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add the new enum value
    op.execute("ALTER TYPE permissiontype ADD VALUE IF NOT EXISTS 'PROVIDE_MODELS';")


def downgrade():
    # Workaround to remove a value from PostgreSQL enum:
    # 1. Create a new enum type without 'read_metrics'
    op.execute("CREATE TYPE permissiontype_new AS ENUM('ADMIN', 'CREATE_PUBLIC_COLLECTION', 'READ_METRIC');")

    # 2. Alter any columns using the old enum to use the new enum
    op.execute("""
        ALTER TABLE permission
        ALTER COLUMN permission TYPE permissiontype_new
        USING permission::text::permissiontype_new;
    """)

    # 3. Drop the old enum type
    op.execute("DROP TYPE permissiontype;")

    # 4. Rename the new enum type to the old name
    op.execute("ALTER TYPE permissiontype_new RENAME TO permissiontype;")
