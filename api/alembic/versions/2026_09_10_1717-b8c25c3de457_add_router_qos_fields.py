"""add_router_qos_fields

Revision ID: b8c25c3de457
Revises: a7f3c91b2e04
Create Date: 2026-09-10 17:17:12.123984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b8c25c3de457'
down_revision: Union[str, None] = 'a7f3c91b2e04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

routerqosmetric = postgresql.ENUM('INFLIGHT', name='routerqosmetric', create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE TYPE routerqosmetric AS ENUM ('INFLIGHT')")
    op.add_column('router', sa.Column('qos_enable', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('router', sa.Column('qos_retry', sa.Integer(), server_default='10', nullable=False))
    op.add_column('router', sa.Column('qos_metric', routerqosmetric, server_default='INFLIGHT', nullable=False))
    op.add_column('router', sa.Column('qos_health_thresholds', postgresql.ARRAY(sa.Float()), server_default='{0.9,1.1}', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('router', 'qos_health_thresholds')
    op.drop_column('router', 'qos_metric')
    op.drop_column('router', 'qos_retry')
    op.drop_column('router', 'qos_enable')
    op.execute('DROP TYPE routerqosmetric')
