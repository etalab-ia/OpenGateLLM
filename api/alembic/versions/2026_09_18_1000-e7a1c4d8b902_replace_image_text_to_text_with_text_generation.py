"""replace image-text-to-text router type with text-generation

Revision ID: e7a1c4d8b902
Revises: f4b7c2a91e30
Create Date: 2026-09-18 10:00:00.000000

Multimodal chat now uses `text-generation`. Existing `IMAGE_TEXT_TO_TEXT` rows
are rewritten, then the PostgreSQL `modeltype` enum drops that member.

The downgrade re-adds the enum value. Rows already rewritten stay
`TEXT_GENERATION`; there is no way to know which were multimodal.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e7a1c4d8b902"
down_revision: Union[str, None] = "f4b7c2a91e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MODELTYPE_WITHOUT_IMAGE_TEXT_TO_TEXT = (
    "AUTOMATIC_SPEECH_RECOGNITION",
    "IMAGE_TO_TEXT",
    "TEXT_CLASSIFICATION",
    "TEXT_EMBEDDINGS_INFERENCE",
    "TEXT_GENERATION",
)
_MODELTYPE_WITH_IMAGE_TEXT_TO_TEXT = (*_MODELTYPE_WITHOUT_IMAGE_TEXT_TO_TEXT, "IMAGE_TEXT_TO_TEXT")


def _replace_modeltype(values: tuple[str, ...]) -> None:
    quoted = ", ".join(f"'{value}'" for value in values)
    op.execute("ALTER TYPE modeltype RENAME TO modeltype_old")
    op.execute(f"CREATE TYPE modeltype AS ENUM ({quoted})")
    op.execute("ALTER TABLE router ALTER COLUMN type TYPE modeltype USING type::text::modeltype")
    op.execute("DROP TYPE modeltype_old")


def upgrade() -> None:
    op.execute("UPDATE router SET type = 'TEXT_GENERATION' WHERE type = 'IMAGE_TEXT_TO_TEXT'")
    _replace_modeltype(_MODELTYPE_WITHOUT_IMAGE_TEXT_TO_TEXT)


def downgrade() -> None:
    _replace_modeltype(_MODELTYPE_WITH_IMAGE_TEXT_TO_TEXT)
