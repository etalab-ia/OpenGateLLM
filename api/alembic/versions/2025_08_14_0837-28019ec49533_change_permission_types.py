"""change permission types

Revision ID: 28019ec49533
Revises: 564856827493
Create Date: 2025-08-14 08:37:57.174458

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "28019ec49533"
down_revision: Union[str, None] = "564856827493"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Keep the email index creation
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=False)

    # Update the permission enum to new values (admin, create_public_collection, read_metric)
    # 1) Convert enum column to text so we can change the underlying type safely
    op.execute("ALTER TABLE permission ALTER COLUMN permission TYPE text USING permission::text;")

    # 2) Drop the old enum type if present, then create the new enum type
    op.execute("DROP TYPE IF EXISTS permissiontype;")
    op.execute("CREATE TYPE permissiontype AS ENUM ('ADMIN', 'CREATE_PUBLIC_COLLECTION', 'READ_METRIC');")

    # 3) Delete all admin permissions except create_role
    op.execute(
        """
        DELETE FROM permission
        WHERE permission IN ('READ_ROLE','UPDATE_ROLE','DELETE_ROLE', 'CREATE_USER','READ_USER','UPDATE_USER','DELETE_USER');
        """
    )
    # 4) Replace create_role with admin
    op.execute(
        """
        UPDATE permission
        SET permission = 'ADMIN'
        WHERE permission IN ('CREATE_ROLE');
        """
    )

    # 5) Cast the column back to the new enum type
    op.execute("ALTER TABLE permission ALTER COLUMN permission TYPE permissiontype USING permission::permissiontype;")


def downgrade() -> None:
    """Downgrade schema."""
    # Revert the permission enum to the previous, fine-grained values
    op.execute("ALTER TABLE permission ALTER COLUMN permission TYPE text USING permission::text;")
    op.execute("DROP TYPE IF EXISTS permissiontype;")
    op.execute(
        """
        CREATE TYPE permissiontype AS ENUM (
            'CREATE_ROLE','READ_ROLE','UPDATE_ROLE','DELETE_ROLE',
            'CREATE_USER','READ_USER','UPDATE_USER','DELETE_USER',
            'CREATE_PUBLIC_COLLECTION','READ_METRIC'
        );
        """
    )
    # Best-effort back-mapping
    op.execute("UPDATE permission SET permission = 'CREATE_ROLE' WHERE permission = 'ADMIN';")
    op.execute("ALTER TABLE permission ALTER COLUMN permission TYPE permissiontype USING permission::permissiontype;")

    # Drop the email index added in this migration
    op.drop_index(op.f("ix_user_email"), table_name="user")
