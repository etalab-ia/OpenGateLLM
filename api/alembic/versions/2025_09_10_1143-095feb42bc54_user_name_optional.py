"""User name optional

Revision ID: 095feb42bc54
Revises: 479aeeae940b
Create Date: 2025-09-10 11:43:13.810362

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "095feb42bc54"
down_revision: Union[str, None] = "479aeeae940b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("user", "name", existing_type=sa.VARCHAR(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("user", "name", existing_type=sa.VARCHAR(), nullable=False)
