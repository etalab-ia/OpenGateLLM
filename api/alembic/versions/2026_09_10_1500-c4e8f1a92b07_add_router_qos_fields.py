"""add router qos fields

Revision ID: c4e8f1a92b07
Revises: a7f3c91b2e04
Create Date: 2026-09-10 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c4e8f1a92b07"
down_revision: Union[str, None] = "a7f3c91b2e04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

routerqosmode = postgresql.ENUM("off", "wait", name="routerqosmode", create_type=False)
routerqosmetric = postgresql.ENUM("inflight", name="routerqosmetric", create_type=False)


def upgrade() -> None:
    routerqosmode.create(op.get_bind(), checkfirst=True)
    routerqosmetric.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "router",
        sa.Column("qos_mode", routerqosmode, server_default="wait", nullable=False),
    )
    op.add_column(
        "router",
        sa.Column("qos_retry", sa.Integer(), server_default="10", nullable=False),
    )
    op.add_column(
        "router",
        sa.Column("qos_metric", routerqosmetric, server_default="inflight", nullable=False),
    )
    op.add_column(
        "router",
        sa.Column(
            "qos_health_thresholds",
            postgresql.ARRAY(sa.Float()),
            server_default="{0.9,1.1}",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("router", "qos_health_thresholds")
    op.drop_column("router", "qos_metric")
    op.drop_column("router", "qos_retry")
    op.drop_column("router", "qos_mode")
    routerqosmetric.drop(op.get_bind(), checkfirst=True)
    routerqosmode.drop(op.get_bind(), checkfirst=True)
