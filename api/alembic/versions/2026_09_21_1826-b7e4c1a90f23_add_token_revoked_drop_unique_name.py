"""add token revoked drop unique name

Revision ID: b7e4c1a90f23
Revises: e7a1c4d8b902
Create Date: 2026-09-21 18:26:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision: str = "b7e4c1a90f23"
down_revision: str | None = "e7a1c4d8b902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("token", sa.Column("revoked", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.drop_constraint("unique_token_name_per_user", "token", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("unique_token_name_per_user", "token", ["user_id", "name"])
    op.drop_column("token", "revoked")
