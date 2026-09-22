"""rename the modeltype enum to routertype

Revision ID: a9c2e7b41d35
Revises: b7e4c1a90f23
Create Date: 2026-09-22 15:39:00.000000

`ModelType` became `RouterType` in the domain, but the PostgreSQL enum kept the
old name, so `router.type` had to pin it explicitly. Renaming the type lets the
column map on the class name again. The members are untouched.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9c2e7b41d35"
down_revision: str | None = "b7e4c1a90f23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE modeltype RENAME TO routertype")


def downgrade() -> None:
    op.execute("ALTER TYPE routertype RENAME TO modeltype")
