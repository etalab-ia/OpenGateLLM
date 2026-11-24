"""add_router_tokenizer

Revision ID: e3b7a5c9d104
Revises: 2b8e23234402
Create Date: 2026-11-24 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b7a5c9d104'
down_revision: Union[str, None] = '2b8e23234402'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Expand: a nullable column the previous release neither reads nor writes. A router without a tokenizer keeps
    using settings.usage_tokenizer.
    """
    op.add_column("router", sa.Column("tokenizer", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema.

    Loses the tokenizer chosen for each router: every router goes back to settings.usage_tokenizer.
    """
    op.drop_column("router", "tokenizer")
