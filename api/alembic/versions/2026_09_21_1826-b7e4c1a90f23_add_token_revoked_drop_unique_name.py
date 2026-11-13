"""add token revoked drop unique name

Revision ID: b7e4c1a90f23
Revises: e7a1c4d8b902
Create Date: 2026-09-21 18:26:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision: str = "b7e4c1a90f23"
down_revision: str | None = "e7a1c4d8b902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("token", sa.Column("revoked", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.drop_constraint("unique_token_name_per_user", "token", type_="unique")


def downgrade() -> None:
    """Restore the 0.8.0 key semantics before its schema.

    - Revoked keys are deleted: before this revision, revoking a key deleted its row,
      and dropping the revoked column would make them valid again.
    - Keys sharing a name with an older key of the same user get a suffix with the key id,
      so that unique_token_name_per_user can be recreated. Their value does not change.
    """
    op.execute("DELETE FROM token WHERE revoked")
    op.execute("""
        UPDATE token SET name = name || ' (duplicate ' || id || ')'
        WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (PARTITION BY user_id, name ORDER BY id) AS rank
                FROM token WHERE name IS NOT NULL
            ) ranked WHERE rank > 1
        )
    """)
    op.create_unique_constraint("unique_token_name_per_user", "token", ["user_id", "name"])
    op.drop_column("token", "revoked")
