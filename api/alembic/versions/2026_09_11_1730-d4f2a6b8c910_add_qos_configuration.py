"""add qos configuration

Revision ID: d4f2a6b8c910
Revises: c8e1a04b7f12
Create Date: 2026-09-11 17:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d4f2a6b8c910"
down_revision: str | None = "c8e1a04b7f12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("provider", sa.Column("qos_limit", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "provider_qos_limit_non_negative",
        "provider",
        "qos_limit >= 0",
    )
    op.add_column(
        "router",
        sa.Column("qos_retries_before_reject", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "router_qos_retries_before_reject_non_negative",
        "router",
        "qos_retries_before_reject >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "router_qos_retries_before_reject_non_negative",
        "router",
        type_="check",
    )
    op.drop_column("router", "qos_retries_before_reject")
    op.drop_constraint(
        "provider_qos_limit_non_negative",
        "provider",
        type_="check",
    )
    op.drop_column("provider", "qos_limit")
