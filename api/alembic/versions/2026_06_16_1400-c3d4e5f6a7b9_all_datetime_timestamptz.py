"""all datetime columns timestamptz

Revision ID: c3d4e5f6a7b9
Revises: 0daf52aadaf0
Create Date: 2026-06-16 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b9"
down_revision: Union[str, None] = "0daf52aadaf0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        DECLARE
            column_record RECORD;
        BEGIN
            FOR column_record IN
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND data_type = 'timestamp without time zone'
            LOOP
                EXECUTE format(
                    'ALTER TABLE %I ALTER COLUMN %I TYPE TIMESTAMPTZ USING %I AT TIME ZONE ''UTC''',
                    column_record.table_name,
                    column_record.column_name,
                    column_record.column_name
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DO $$
        DECLARE
            column_record RECORD;
        BEGIN
            FOR column_record IN
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND data_type = 'timestamp with time zone'
            LOOP
                EXECUTE format(
                    'ALTER TABLE %I ALTER COLUMN %I TYPE TIMESTAMP WITHOUT TIME ZONE USING %I AT TIME ZONE ''UTC''',
                    column_record.table_name,
                    column_record.column_name,
                    column_record.column_name
                );
            END LOOP;
        END $$;
        """
    )
