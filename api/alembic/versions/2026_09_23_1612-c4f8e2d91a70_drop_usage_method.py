"""drop unused usage.method column

Revision ID: c4f8e2d91a70
Revises: a9c2e7b41d35
Create Date: 2026-09-23 16:12:00.000000

Model-forward usage is always POST. The recorder no longer writes the column,
so it and the leftover `httpmethod` enum go.
"""

from alembic import op
import sqlalchemy as sa

revision: str = "c4f8e2d91a70"
down_revision: str | None = "a9c2e7b41d35"
branch_labels = None
depends_on = None

httpmethod_enum = sa.Enum(
    "CONNECT",
    "DELETE",
    "GET",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
    "TRACE",
    name="httpmethod",
)


def upgrade() -> None:
    op.drop_column("usage", "method")
    httpmethod_enum.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    httpmethod_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("usage", sa.Column("method", httpmethod_enum, nullable=True))
