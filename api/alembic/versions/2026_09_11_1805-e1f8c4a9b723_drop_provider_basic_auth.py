"""drop provider basic_auth

Revision ID: e1f8c4a9b723
Revises: d4f2a6b8c910
Create Date: 2026-09-11 18:05:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e1f8c4a9b723"
down_revision: str | None = "d4f2a6b8c910"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("provider", "basic_auth")


def downgrade() -> None:
    op.add_column("provider", sa.Column("basic_auth", sa.JSON(), nullable=True))
