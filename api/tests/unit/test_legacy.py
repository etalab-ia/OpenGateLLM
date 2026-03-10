from datetime import datetime

from api.schemas.chunks import Chunk


def test_pydantic_chunck_model_support_legacy_metadata():
    """Test that the Chunk model supports legacy metadata, None type and list. None are ignored, list are converted to a string by joining the strings with a comma."""
    # Given
    content = {
        "id": 1,
        "collection_id": 1,
        "document_id": 1,
        "content": "test",
        "created": datetime.now(),
        "metadata": {"list_metadata": ["tag1", "tag2"], "none_metadata": None},
    }
    # When
    result = Chunk(**content)
    # Then
    assert result.metadata == {"list_metadata": "tag1,tag2"}
