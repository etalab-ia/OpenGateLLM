"""merge heads

Revision ID: e09ebf3b90a4
Revises: 479aeeae940b, c1e54102255e
Create Date: 2025-08-17 19:34:30.430580

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = 'e09ebf3b90a4'
down_revision: Union[str, None] = ('479aeeae940b', 'c1e54102255e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
