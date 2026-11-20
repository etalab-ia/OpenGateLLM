"""default_router_load_balancing_strategy

Revision ID: 2b8e23234402
Revises: c8fef686d652
Create Date: 2026-11-19 09:52:54.533794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b8e23234402'
down_revision: Union[str, None] = 'c8fef686d652'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Expand: the API no longer writes router.load_balancing_strategy, so a new router takes this default, which the
    previous release still reads during a rolling deployment.
    """
    op.alter_column("router", "load_balancing_strategy", server_default="SHUFFLE")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("router", "load_balancing_strategy", server_default=None)
