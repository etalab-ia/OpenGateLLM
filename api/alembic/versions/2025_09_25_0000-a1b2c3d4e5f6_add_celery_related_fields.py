"""Add user priority

Revision ID: a1b2c3d4e5f6
Revises: 17be379f45ac
Create Date: 2025-09-25 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "17be379f45ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
    # Remove server_default after setting existing rows if desired (kept simple here)
    op.add_column("model_client", sa.Column("qos_policy", sa.String(), nullable=False))
    op.add_column("model_client", sa.Column("performance_threshold", sa.Float(), nullable=True))
    op.add_column("model_client", sa.Column("max_parallel_requests", sa.Integer(), nullable=True))
    op.add_column("model", sa.Column("cycle_offset", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "priority")
    op.drop_column("model_client", "max_parallel_requests")
    op.drop_column("model_client", "performance_threshold")
    op.drop_column("model_client", "qos_policy")
    op.drop_column("model", "cycle_offset")
