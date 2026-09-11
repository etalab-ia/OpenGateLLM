"""drop provider qos_metric and qos_limit

Revision ID: c8e1a04b7f12
Revises: a7f3c91b2e04
Create Date: 2026-09-11 13:40:00.000000

The old QoS policy (Redis INCR/DECR inflight check against provider qos_limit)
is removed. Columns and the unused PostgreSQL `metric` enum go with it.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8e1a04b7f12"
down_revision: Union[str, None] = "a7f3c91b2e04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

metric_enum = sa.Enum("ttft", "latency", "inflight", "performance", name="metric")


def upgrade() -> None:
    op.drop_column("provider", "qos_metric")
    op.drop_column("provider", "qos_limit")
    metric_enum.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    metric_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("provider", sa.Column("qos_limit", sa.Float(), nullable=True))
    op.add_column("provider", sa.Column("qos_metric", metric_enum, nullable=True))
