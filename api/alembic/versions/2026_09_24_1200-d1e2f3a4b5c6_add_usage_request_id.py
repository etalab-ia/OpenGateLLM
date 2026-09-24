"""add usage request_id

Revision ID: d1e2f3a4b5c6
Revises: c4f8e2d91a70
Create Date: 2026-09-24 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c4f8e2d91a70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usage", sa.Column("request_id", sa.String(), nullable=True))
    op.create_index(op.f("ix_usage_request_id"), "usage", ["request_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_request_id"), table_name="usage")
    op.drop_column("usage", "request_id")
