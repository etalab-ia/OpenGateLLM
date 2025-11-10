"""Unit tests for DocumentsUpdater."""

from unittest.mock import AsyncMock, MagicMock, patch

import pyarrow as pa
import pytest

from api.helpers.documents.documents_updater import DocumentsUpdater
from api.utils.exceptions import VectorizationFailedException


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    return MagicMock()


@pytest.fixture
def mock_upsert_callback():
    """Mock upsert callback."""
    return AsyncMock()


@pytest.fixture
def mock_delete_callback():
    """Mock delete document callback."""
    return AsyncMock()


@pytest.fixture
def updater(mock_vector_store, mock_upsert_callback, mock_delete_callback):
    """Create DocumentsUpdater instance."""
    return DocumentsUpdater(
        vector_store=mock_vector_store,
        upsert_callback=mock_upsert_callback,
        delete_document_callback=mock_delete_callback,
    )


class TestPrepareChunksData:
    """Tests for _prepare_chunks_data method."""

    def test_prepare_chunks_basic(self, updater):
        """Test basic chunk preparation without metadata."""
        # Create test data
        doc_table = pa.table(
            {
                "content": ["chunk1", "chunk2", "chunk3"],
            }
        )
        doc_contents = ["chunk1", "chunk2", "chunk3"]
        doc_chunk_ids = [0, 1, 2]
        doc_metadata_dict = {}
        available_columns = ["content"]

        # Prepare chunks
        chunks_data = updater._prepare_chunks_data(
            doc_table=doc_table,
            doc_contents=doc_contents,
            doc_chunk_ids=doc_chunk_ids,
            doc_metadata_dict=doc_metadata_dict,
            available_columns=available_columns,
            force_update=False,
        )

        # Verify
        assert len(chunks_data) == 3
        assert chunks_data[0]["content"] == "chunk1"
        assert chunks_data[0]["chunk_id"] == 0
        assert chunks_data[0]["metadata"] == {}
        assert "hash" in chunks_data[0]

    def test_prepare_chunks_with_metadata(self, updater):
        """Test chunk preparation with metadata columns."""
        # Create test data
        doc_table = pa.table(
            {
                "content": ["chunk1", "chunk2"],
                "page": [1, 2],
                "section": ["intro", "body"],
            }
        )
        doc_contents = ["chunk1", "chunk2"]
        doc_chunk_ids = [0, 1]
        doc_metadata_dict = {
            "page": [1, 2],
            "section": ["intro", "body"],
        }
        available_columns = ["content", "page", "section"]

        # Prepare chunks
        chunks_data = updater._prepare_chunks_data(
            doc_table=doc_table,
            doc_contents=doc_contents,
            doc_chunk_ids=doc_chunk_ids,
            doc_metadata_dict=doc_metadata_dict,
            available_columns=available_columns,
            force_update=False,
        )

        # Verify
        assert len(chunks_data) == 2
        assert chunks_data[0]["metadata"]["page"] == 1
        assert chunks_data[0]["metadata"]["section"] == "intro"
        assert chunks_data[1]["metadata"]["page"] == 2
        assert chunks_data[1]["metadata"]["section"] == "body"

    def test_prepare_chunks_force_update_no_hash(self, updater):
        """Test that force_update skips hash computation."""
        doc_table = pa.table({"content": ["chunk1"]})
        doc_contents = ["chunk1"]
        doc_chunk_ids = [0]
        doc_metadata_dict = {}
        available_columns = ["content"]

        # With force_update=True, hash key should not be present
        chunks_data = updater._prepare_chunks_data(
            doc_table=doc_table,
            doc_contents=doc_contents,
            doc_chunk_ids=doc_chunk_ids,
            doc_metadata_dict=doc_metadata_dict,
            available_columns=available_columns,
            force_update=True,
        )

        assert "hash" not in chunks_data[0]

    def test_prepare_chunks_empty_content(self, updater):
        """Test handling of empty content."""
        doc_table = pa.table({"content": [""]})
        doc_contents = [""]
        doc_chunk_ids = [0]
        doc_metadata_dict = {}
        available_columns = ["content"]

        chunks_data = updater._prepare_chunks_data(
            doc_table=doc_table,
            doc_contents=doc_contents,
            doc_chunk_ids=doc_chunk_ids,
            doc_metadata_dict=doc_metadata_dict,
            available_columns=available_columns,
            force_update=False,
        )

        # Empty content should still be processed
        assert len(chunks_data) == 1
        assert chunks_data[0]["content"] == ""


class TestCheckUpdateNeeded:
    """Tests for _check_update_needed method."""

    @pytest.mark.asyncio
    async def test_new_document(self, updater):
        """Test detection of new document."""
        existing_docs_map = {"doc1": 1, "doc2": 2}
        new_chunks_data = [{"chunk_id": 1, "hash": "abc123"}]

        needs_update, is_new = await updater._check_update_needed(
            collection_id=1,
            document_name="doc3",  # Not in existing_docs_map
            existing_docs_map=existing_docs_map,
            new_chunks_data=new_chunks_data,
            force_update=False,
            has_chunk_index=False,
        )

        assert is_new is True
        assert needs_update is True

    @pytest.mark.asyncio
    async def test_force_update(self, updater):
        """Test force update always returns needs_update=True."""
        existing_docs_map = {"doc1": 1}
        new_chunks_data = [{"chunk_id": 1, "hash": "abc123"}]

        needs_update, is_new = await updater._check_update_needed(
            collection_id=1,
            document_name="doc1",
            existing_docs_map=existing_docs_map,
            new_chunks_data=new_chunks_data,
            force_update=True,
            has_chunk_index=False,
        )

        assert needs_update is True
        assert is_new is False

    @pytest.mark.asyncio
    async def test_no_update_needed_same_hashes(self, updater):
        """Test no update when hashes match."""
        existing_docs_map = {"doc1": 1}
        new_chunks_data = [
            {"chunk_id": 0, "hash": "hash0"},
            {"chunk_id": 1, "hash": "hash1"},
        ]

        # Mock vector store to return matching hashes
        updater.vector_store.get_chunks = AsyncMock(
            return_value=[
                MagicMock(id=0, chunk_id=0, hash="hash0"),
                MagicMock(id=1, chunk_id=1, hash="hash1"),
            ]
        )

        # Mock ChunkHasher to return same hashes
        with patch("api.helpers.documents.documents_updater.ChunkHasher.compute_existing_chunk_hash") as mock_hash:
            mock_hash.side_effect = lambda chunk, has_index: chunk.hash

            needs_update, is_new = await updater._check_update_needed(
                collection_id=1,
                document_name="doc1",
                existing_docs_map=existing_docs_map,
                new_chunks_data=new_chunks_data,
                force_update=False,
                has_chunk_index=True,
            )

        assert needs_update is False
        assert is_new is False

    @pytest.mark.asyncio
    async def test_update_needed_different_hashes(self, updater):
        """Test update when hashes differ."""
        existing_docs_map = {"doc1": 1}
        new_chunks_data = [
            {"chunk_id": 0, "hash": "new_hash0"},
            {"chunk_id": 1, "hash": "new_hash1"},
        ]

        # Mock vector store to return different hashes
        updater.vector_store.get_chunks = AsyncMock(
            return_value=[
                MagicMock(id=0, chunk_id=0, hash="old_hash0"),
                MagicMock(id=1, chunk_id=1, hash="old_hash1"),
            ]
        )

        # Mock ChunkHasher to return old hashes (different from new)
        with patch("api.helpers.documents.documents_updater.ChunkHasher.compute_existing_chunk_hash") as mock_hash:
            mock_hash.side_effect = lambda chunk, has_index: chunk.hash

            needs_update, is_new = await updater._check_update_needed(
                collection_id=1,
                document_name="doc1",
                existing_docs_map=existing_docs_map,
                new_chunks_data=new_chunks_data,
                force_update=False,
                has_chunk_index=True,
            )

        assert needs_update is True
        assert is_new is False

    @pytest.mark.asyncio
    async def test_update_needed_different_chunk_count(self, updater):
        """Test update when chunk count differs."""
        existing_docs_map = {"doc1": 1}
        new_chunks_data = [
            {"chunk_id": 0, "hash": "hash0"},
            {"chunk_id": 1, "hash": "hash1"},
            {"chunk_id": 2, "hash": "hash2"},  # Extra chunk
        ]

        # Mock vector store to return fewer chunks
        updater.vector_store.get_chunks = AsyncMock(
            return_value=[
                MagicMock(id=0, chunk_id=0, hash="hash0"),
                MagicMock(id=1, chunk_id=1, hash="hash1"),
            ]
        )

        # Note: ChunkHasher mock not needed here because the count check happens first
        # (short-circuit before hash comparison)

        needs_update, is_new = await updater._check_update_needed(
            collection_id=1,
            document_name="doc1",
            existing_docs_map=existing_docs_map,
            new_chunks_data=new_chunks_data,
            force_update=False,
            has_chunk_index=True,
        )

        assert needs_update is True
        assert is_new is False


class TestProcessDocument:
    """Tests for process_document method."""

    @pytest.mark.asyncio
    async def test_process_new_document(self, updater, mock_upsert_callback):
        """Test processing a new document."""
        # Mock data
        doc_table = pa.table(
            {
                "content": ["chunk1", "chunk2"],
                "chunk_index": [0, 1],
            }
        )
        existing_docs_map = {}
        stats = {
            "added_documents": 0,
            "updated_documents": 0,
            "total_chunks_processed": 0,
        }

        # Mock methods
        with patch.object(updater, "_create_empty_document", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = 123  # New document ID

            with patch.object(updater, "_insert_chunks", new_callable=AsyncMock) as mock_insert:
                await updater.process_document(
                    session=MagicMock(),
                    user_id=1,
                    collection_id=10,
                    document_name="test_doc",
                    document_table=doc_table,
                    available_columns=["content", "chunk_index"],
                    metadata_columns=[],
                    has_chunk_index=True,
                    existing_docs_map=existing_docs_map,
                    force_update=False,
                    stats=stats,
                )

        # Verify document created and chunks inserted
        mock_create.assert_awaited_once()
        mock_insert.assert_awaited_once()

        # Verify stats updated
        assert stats["added_documents"] == 1
        assert stats["updated_documents"] == 0
        assert stats["total_chunks_processed"] == 2

    @pytest.mark.asyncio
    async def test_process_document_rollback_on_failure(self, updater, mock_delete_callback):
        """Test rollback when chunk insertion fails."""
        doc_table = pa.table({"content": ["chunk1"]})
        existing_docs_map = {}
        stats = {"added_documents": 0, "updated_documents": 0, "total_chunks_processed": 0}

        # Mock create succeeds but insert fails
        with patch.object(updater, "_create_empty_document", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = 123

            with patch.object(updater, "_insert_chunks", new_callable=AsyncMock) as mock_insert:
                mock_insert.side_effect = VectorizationFailedException("Embedding failed")

                # Should raise and rollback
                with pytest.raises(VectorizationFailedException):
                    await updater.process_document(
                        session=MagicMock(),
                        user_id=1,
                        collection_id=10,
                        document_name="test_doc",
                        document_table=doc_table,
                        available_columns=["content"],
                        metadata_columns=[],
                        has_chunk_index=False,
                        existing_docs_map=existing_docs_map,
                        force_update=False,
                        stats=stats,
                    )

        # Verify rollback: new document deleted
        mock_delete_callback.assert_awaited_once()
        assert mock_delete_callback.await_args[1]["document_id"] == 123

        # Stats should not be updated
        assert stats["added_documents"] == 0

    @pytest.mark.asyncio
    async def test_process_document_update_existing(self, updater, mock_delete_callback):
        """Test updating an existing document."""
        doc_table = pa.table({"content": ["new_chunk"]})
        existing_docs_map = {"test_doc": 456}
        stats = {"added_documents": 0, "updated_documents": 0, "total_chunks_processed": 0}

        # Mock vector store to return different hash (needs update)
        updater.vector_store.get_chunks = AsyncMock(return_value=[MagicMock(id=0, chunk_id=0, hash="old_hash")])

        # Mock ChunkHasher to return old hash (different from new)
        with patch("api.helpers.documents.documents_updater.ChunkHasher.compute_existing_chunk_hash") as mock_hash:
            mock_hash.return_value = "old_hash"

            with patch.object(updater, "_create_empty_document", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = 789  # New document ID

                with patch.object(updater, "_insert_chunks", new_callable=AsyncMock):
                    await updater.process_document(
                        session=MagicMock(),
                        user_id=1,
                        collection_id=10,
                        document_name="test_doc",
                        document_table=doc_table,
                        available_columns=["content"],
                        metadata_columns=[],
                        has_chunk_index=False,
                        existing_docs_map=existing_docs_map,
                        force_update=False,
                        stats=stats,
                    )

        # Verify old document deleted after successful update
        mock_delete_callback.assert_awaited_once()
        assert mock_delete_callback.await_args[1]["document_id"] == 456

        # Verify stats
        assert stats["updated_documents"] == 1
        assert stats["added_documents"] == 0

    @pytest.mark.asyncio
    async def test_process_document_no_update_needed(self, updater):
        """Test skipping when no update needed."""
        doc_table = pa.table({"content": ["same_chunk"]})
        existing_docs_map = {"test_doc": 456}
        stats = {"added_documents": 0, "updated_documents": 0, "total_chunks_processed": 0}

        # Mock vector store to return same hash
        updater.vector_store.get_chunks = AsyncMock(return_value=[MagicMock(id=0, chunk_id=0, hash="same_hash")])

        with patch.object(updater, "_prepare_chunks_data") as mock_prepare:
            mock_prepare.return_value = [{"chunk_id": 0, "hash": "same_hash", "metadata": {}}]

            with patch("api.helpers.documents.documents_updater.ChunkHasher.compute_existing_chunk_hash") as mock_hash:
                mock_hash.return_value = "same_hash"

                with patch.object(updater, "_create_empty_document", new_callable=AsyncMock) as mock_create:
                    await updater.process_document(
                        session=MagicMock(),
                        user_id=1,
                        collection_id=10,
                        document_name="test_doc",
                        document_table=doc_table,
                        available_columns=["content"],
                        metadata_columns=[],
                        has_chunk_index=False,
                        existing_docs_map=existing_docs_map,
                        force_update=False,
                        stats=stats,
                    )

        # Verify no document creation
        mock_create.assert_not_awaited()

        # Stats should not change
        assert stats["added_documents"] == 0
        assert stats["updated_documents"] == 0
