from unittest.mock import MagicMock

import pytest

from api.helpers.data.hasher.chunk_hasher import ChunkHasher


class TestChunkHasher:
    """Test suite for ChunkHasher class."""

    def _compute_hash(self, chunk_dict: dict) -> str:
        """Helper to compute hash from chunk dict."""
        concatenated = ChunkHasher.concatenate_chunk_values(chunk_dict)
        return ChunkHasher.compute_chunk_hash(concatenated)

    def test_compute_chunk_hash_deterministic(self):
        """Test that same chunk dict produces same hash."""
        chunk_dict = {"content": "Test content", "chunk_index": 5, "document_name": "test.txt"}

        hash1 = self._compute_hash(chunk_dict)
        hash2 = self._compute_hash(chunk_dict)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 16  # xxHash64 produces 16-char hex string

    @pytest.mark.parametrize(
        "chunk1,chunk2",
        [
            # Different content
            (
                {"content": "Content A", "chunk_index": 1, "document_name": "doc.txt"},
                {"content": "Content B", "chunk_index": 1, "document_name": "doc.txt"},
            ),
            # Different metadata
            (
                {"content": "Text", "chunk_index": 1, "document_name": "doc.txt", "page": 1},
                {"content": "Text", "chunk_index": 1, "document_name": "doc.txt", "page": 2},
            ),
        ],
        ids=["different_content", "different_metadata"],
    )
    def test_different_chunks_produce_different_hashes(self, chunk1, chunk2):
        """Test that any difference in chunk data produces different hashes."""
        hash1 = self._compute_hash(chunk1)
        hash2 = self._compute_hash(chunk2)
        assert hash1 != hash2

    def test_concatenate_chunk_values_deterministic(self):
        """Test that concatenate_chunk_values is deterministic and sorted."""
        chunk = {"content": "Test", "chunk_index": 1, "document_name": "doc"}

        concat1 = ChunkHasher.concatenate_chunk_values(chunk)
        concat2 = ChunkHasher.concatenate_chunk_values(chunk)

        assert concat1 == concat2
        assert isinstance(concat1, str)
        # Keys should be sorted alphabetically
        assert "chunk_index" in concat1
        assert "content" in concat1


class TestComputeExistingChunkHash:
    """Test suite for compute_existing_chunk_hash method - Essential tests only."""

    @pytest.fixture
    def base_chunk(self):
        """Factory to create mock chunks with common setup."""

        def _make_chunk(content: str, chunk_id: int, metadata: dict):
            mock = MagicMock()
            mock.content = content
            mock.id = chunk_id
            mock.metadata = metadata
            return mock

        return _make_chunk

    def test_excludes_auto_generated_fields(self, base_chunk):
        """Test that collection_id, document_id, document_created_at are excluded from hash."""
        # Two chunks with same content but different auto-generated fields
        chunk1 = base_chunk(
            content="Same content",
            chunk_id=0,
            metadata={
                "page": 1,
                "collection_id": 123,  # Should be excluded
                "document_id": 456,  # Should be excluded
                "document_created_at": "2025-11-12T10:00:00",  # Should be excluded
            },
        )

        chunk2 = base_chunk(
            content="Same content",
            chunk_id=0,
            metadata={
                "page": 1,
                "collection_id": 999,  # Different but excluded
                "document_id": 888,  # Different but excluded
                "document_created_at": "2025-11-12T11:00:00",  # Different but excluded
            },
        )

        # Hashes must be identical (auto-generated fields excluded)
        hash1 = ChunkHasher.compute_existing_chunk_hash(chunk1, has_chunk_index=False)
        hash2 = ChunkHasher.compute_existing_chunk_hash(chunk2, has_chunk_index=False)

        assert hash1 == hash2

    def test_includes_user_metadata(self, base_chunk):
        """Test that user-provided metadata IS included in hash."""
        chunk1 = base_chunk(content="Same content", chunk_id=0, metadata={"page": 1, "collection_id": 123})

        chunk2 = base_chunk(content="Same content", chunk_id=0, metadata={"page": 2, "collection_id": 123})

        # Hashes must differ (user metadata changed)
        hash1 = ChunkHasher.compute_existing_chunk_hash(chunk1, has_chunk_index=False)
        hash2 = ChunkHasher.compute_existing_chunk_hash(chunk2, has_chunk_index=False)

        assert hash1 != hash2

    @pytest.mark.parametrize(
        "has_chunk_index,should_differ",
        [
            (True, True),  # With has_chunk_index=True, different IDs → different hashes
            (False, False),  # With has_chunk_index=False, different IDs → same hashes
        ],
        ids=["chunk_index_included", "chunk_index_excluded"],
    )
    def test_chunk_index_behavior(self, base_chunk, has_chunk_index, should_differ):
        """Test that chunk.id inclusion depends on has_chunk_index parameter."""
        chunk1 = base_chunk(content="Same content", chunk_id=5, metadata={"page": 1})
        chunk2 = base_chunk(content="Same content", chunk_id=10, metadata={"page": 1})

        hash1 = ChunkHasher.compute_existing_chunk_hash(chunk1, has_chunk_index=has_chunk_index)
        hash2 = ChunkHasher.compute_existing_chunk_hash(chunk2, has_chunk_index=has_chunk_index)

        if should_differ:
            assert hash1 != hash2, "Hashes should differ when has_chunk_index=True"
        else:
            assert hash1 == hash2, "Hashes should be identical when has_chunk_index=False"
