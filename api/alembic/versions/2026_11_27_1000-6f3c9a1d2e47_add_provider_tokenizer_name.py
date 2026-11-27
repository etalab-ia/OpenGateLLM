"""add_provider_tokenizer_name

Revision ID: 6f3c9a1d2e47
Revises: 2b8e23234402
Create Date: 2026-11-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f3c9a1d2e47'
down_revision: Union[str, None] = '2b8e23234402'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Expand: both columns are nullable so the previous release can still insert providers. Existing providers get their
    model name as tokenizer, unvalidated: an admin fixes an unloadable one through PATCH, and sets an hf_token for a gated one.

    Breaking for API clients: PATCH /v1/admin/providers/{id} requires tokenizer_name and checks it on every update, so
    a provider whose model name is not a Hub repository (e.g. "gemma3:1b") cannot be updated until it gets a tokenizer.
    Creating or updating a provider, and bootstrapping the models section, needs the Hub unless the tokenizer is in the
    disk cache and HF_HUB_OFFLINE=1.
    """
    op.add_column("provider", sa.Column("tokenizer_name", sa.String(), nullable=True))
    op.add_column("provider", sa.Column("hf_token", sa.String(), nullable=True))
    op.execute("UPDATE provider SET tokenizer_name = model_name")


def downgrade() -> None:
    """Downgrade schema.

    Loses the tokenizer names and the Hugging Face tokens.
    """
    op.drop_column("provider", "hf_token")
    op.drop_column("provider", "tokenizer_name")
