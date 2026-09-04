"""rename providercarbonfootprintzone enum type to hostingzone

Revision ID: a7f3c91b2e04
Revises: b2d58fce4b3c
Create Date: 2026-09-04 10:00:00.000000

The Python enum backing `provider.model_hosting_zone` moved from the legacy
`api.schemas.admin.providers.ProviderCarbonFootprintZone` to the domain
`api.domain.provider.entities.HostingZone`. Members are identical (250 ISO
3166-1 alpha-3 codes plus WOR), but SQLAlchemy derives the PostgreSQL type
name from the Python class name, so the type has to be renamed to match.

This is a catalog-only operation: `ALTER TYPE ... RENAME TO` does not rewrite
the table, and stored values are untouched.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7f3c91b2e04'
down_revision: Union[str, None] = 'b2d58fce4b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE providercarbonfootprintzone RENAME TO hostingzone")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE hostingzone RENAME TO providercarbonfootprintzone")
