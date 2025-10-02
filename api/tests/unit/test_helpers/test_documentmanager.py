from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._documentmanager import DocumentManager
from api.schemas.collections import CollectionVisibility
from api.schemas.documents import Chunker
from api.schemas.parse import ParsedDocument, ParsedDocumentMetadata, ParsedDocumentPage
from api.utils.exceptions import CollectionNotFoundException


@pytest.mark.asyncio
async def test_create_document_collection_no_longer_exists():
    """Test that CollectionNotFoundException is raised when collection is deleted during document creation."""

    # Mock dependencies
    mock_vectore_store = AsyncMock()
    mock_vector_store_model = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store=mock_vectore_store, vector_store_model=mock_vector_store_model, parser_manager=mock_parser)

    # Mock the collection existence check to pass initially
    mock_collection_result = MagicMock()
    mock_collection_result.scalar_one.return_value = MagicMock()  # Collection exists
    mock_session.execute.return_value = mock_collection_result

    # Create a mock parsed document
    mock_metadata = ParsedDocumentMetadata(document_name="test_doc.txt")
    mock_data = ParsedDocumentPage(content="Test document content", images={}, metadata=mock_metadata)
    mock_document = ParsedDocument(data=[mock_data])

    # Mock the _split method to return some chunks
    mock_chunks = [MagicMock()]
    with patch.object(document_manager, "_split", return_value=mock_chunks):
        # Configure the session.execute to:
        # 1. First call: return collection exists (for the initial check)
        # 2. Second call: raise IntegrityError with foreign key constraint message
        def side_effect(*args, **kwargs):
            statement_str = str(kwargs["statement"])
            if "INSERT INTO document" in statement_str or "document" in statement_str.lower():
                # This is the insert statement that should fail
                raise IntegrityError(statement="INSERT INTO document", params={}, orig=Exception("foreign key constraint fails"))
            else:
                # This is the collection check that should pass
                return mock_collection_result

        mock_session.execute.side_effect = side_effect

        # Test that the exception is raised with the correct message
        with pytest.raises(CollectionNotFoundException) as exc_info:
            await document_manager.create_document(
                session=mock_session,
                user_id=1,
                collection_id=123,
                document=mock_document,
                chunker=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER,
                chunk_size=1000,
                chunk_overlap=100,
                length_function=len,
                is_separator_regex=False,
                separators=["\n\n", "\n", " "],
                chunk_min_size=50,
            )

        # Verify the exception message contains the collection ID
        assert "Collection 123 no longer exists" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_document_collection_no_longer_exists_with_fkey_error():
    """Test that CollectionNotFoundException is raised when fkey constraint fails."""

    # Mock dependencies
    mock_vectore_store = AsyncMock()
    mock_vector_store_model = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store=mock_vectore_store, vector_store_model=mock_vector_store_model, parser_manager=mock_parser)

    # Mock the collection existence check to pass initially
    mock_collection_result = MagicMock()
    mock_collection_result.scalar_one.return_value = MagicMock()  # Collection exists
    mock_session.execute.return_value = mock_collection_result

    # Create a mock parsed document
    mock_metadata = ParsedDocumentMetadata(document_name="test_doc.txt")
    mock_data = ParsedDocumentPage(content="Test document content", images={}, metadata=mock_metadata)
    mock_document = ParsedDocument(data=[mock_data])

    # Mock the _split method to return some chunks
    mock_chunks = [MagicMock()]
    with patch.object(document_manager, "_split", return_value=mock_chunks):
        # Configure the session.execute to raise IntegrityError with fkey message
        def side_effect(*args, **kwargs):
            statement_str = str(kwargs["statement"])
            if "INSERT INTO document" in statement_str or "document" in statement_str.lower():
                # This is the insert statement that should fail with fkey error
                raise IntegrityError(statement="INSERT INTO document", params={}, orig=Exception("fkey constraint violation"))
            else:
                # This is the collection check that should pass
                return mock_collection_result

        mock_session.execute.side_effect = side_effect

        # Test that the exception is raised with the correct message
        with pytest.raises(CollectionNotFoundException) as exc_info:
            await document_manager.create_document(
                session=mock_session,
                user_id=1,
                collection_id=456,
                document=mock_document,
                chunker=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER,
                chunk_size=1000,
                chunk_overlap=100,
                length_function=len,
                is_separator_regex=False,
                separators=["\n\n", "\n", " "],
                chunk_min_size=50,
            )

        # Verify the exception message contains the collection ID
        assert "Collection 456 no longer exists" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_document_other_integrity_error_not_collection_related():
    """Test that other IntegrityErrors are not caught and converted to CollectionNotFoundException."""

    # Mock dependencies
    mock_vectore_store = AsyncMock()
    mock_parser = AsyncMock()
    mock_vector_store_model = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store=mock_vectore_store, vector_store_model=mock_vector_store_model, parser_manager=mock_parser)

    # Mock the collection existence check to pass initially
    mock_collection_result = MagicMock()
    mock_collection_result.scalar_one.return_value = MagicMock()  # Collection exists
    mock_session.execute.return_value = mock_collection_result

    # Create a mock parsed document
    mock_metadata = ParsedDocumentMetadata(document_name="test_doc.txt")
    mock_data = ParsedDocumentPage(content="Test document content", images={}, metadata=mock_metadata)
    mock_document = ParsedDocument(data=[mock_data])

    # Mock the _split method to return some chunks
    mock_chunks = [MagicMock()]
    with patch.object(document_manager, "_split", return_value=mock_chunks):
        # Configure the session.execute to raise IntegrityError without foreign key message
        def side_effect(*args, **kwargs):
            statement_str = str(kwargs["statement"])
            if "INSERT INTO document" in statement_str or "document" in statement_str.lower():
                # This is the insert statement that should fail with non-fkey error
                raise IntegrityError(statement="INSERT INTO document", params={}, orig=Exception("unique constraint violation"))
            else:
                # This is the collection check that should pass
                return mock_collection_result

        mock_session.execute.side_effect = side_effect

        # Test that the original IntegrityError is raised, not CollectionNotFoundException
        with pytest.raises(IntegrityError):
            await document_manager.create_document(
                session=mock_session,
                user_id=1,
                collection_id=789,
                document=mock_document,
                chunker=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER,
                chunk_size=1000,
                chunk_overlap=100,
                length_function=len,
                is_separator_regex=False,
                separators=["\n\n", "\n", " "],
                chunk_min_size=50,
            )


@pytest.mark.asyncio
async def test_get_collections_filter_by_visibility():
    """Test that get_collections correctly filters by visibility (private/public)."""

    # Mock dependencies
    mock_vector_store = AsyncMock()
    mock_vector_store_model = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store=mock_vector_store, vector_store_model=mock_vector_store_model, parser_manager=mock_parser)

    # Mock database result for PRIVATE visibility filter
    mock_private_result = MagicMock()
    mock_private_row = MagicMock()
    mock_private_row._asdict.return_value = {
        "id": 1,
        "name": "Private Collection",
        "owner": "test_user",
        "visibility": CollectionVisibility.PRIVATE,
        "description": "A private collection",
        "documents": 5,
        "created_at": 1697000000,
        "updated_at": 1697000000,
    }
    mock_private_result.all.return_value = [mock_private_row]

    # Mock database result for PUBLIC visibility filter
    mock_public_result = MagicMock()
    mock_public_row = MagicMock()
    mock_public_row._asdict.return_value = {
        "id": 2,
        "name": "Public Collection",
        "owner": "test_user",
        "visibility": CollectionVisibility.PUBLIC,
        "description": "A public collection",
        "documents": 10,
        "created_at": 1697000000,
        "updated_at": 1697000000,
    }
    mock_public_result.all.return_value = [mock_public_row]

    # Test filtering by PRIVATE visibility
    mock_session.execute.return_value = mock_private_result

    collections = await document_manager.get_collections(session=mock_session, user_id=1, visibility=CollectionVisibility.PRIVATE, offset=0, limit=10)

    assert len(collections) == 1, "Should return exactly one private collection"
    assert collections[0].visibility == CollectionVisibility.PRIVATE, "Collection should be private"
    assert collections[0].name == "Private Collection"
    assert collections[0].id == 1

    # Verify the SQL query was called with the correct filter
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    statement_str = str(call_args[1]["statement"])
    # The visibility filter should be applied in the WHERE clause
    assert "visibility" in statement_str.lower()

    # Test filtering by PUBLIC visibility
    mock_session.execute.return_value = mock_public_result

    collections = await document_manager.get_collections(session=mock_session, user_id=1, visibility=CollectionVisibility.PUBLIC, offset=0, limit=10)

    assert len(collections) == 1, "Should return exactly one public collection"
    assert collections[0].visibility == CollectionVisibility.PUBLIC, "Collection should be public"
    assert collections[0].name == "Public Collection"
    assert collections[0].id == 2


@pytest.mark.asyncio
async def test_get_collections_filter_by_collection_name():
    """Test that get_collections correctly filters by collection name."""

    # Mock dependencies
    mock_vector_store = AsyncMock()
    mock_vector_store_model = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store=mock_vector_store, vector_store_model=mock_vector_store_model, parser_manager=mock_parser)

    # Mock database result for name filter matching
    mock_result_with_matches = MagicMock()
    mock_row1 = MagicMock()
    mock_row1._asdict.return_value = {
        "id": 1,
        "name": "test_collection_alpha",
        "owner": "test_user",
        "visibility": CollectionVisibility.PRIVATE,
        "description": "First test collection",
        "documents": 3,
        "created_at": 1697000000,
        "updated_at": 1697000000,
    }
    mock_row2 = MagicMock()
    mock_row2._asdict.return_value = {
        "id": 2,
        "name": "test_collection_beta",
        "owner": "test_user",
        "visibility": CollectionVisibility.PRIVATE,
        "description": "Second test collection",
        "documents": 7,
        "created_at": 1697000000,
        "updated_at": 1697000000,
    }
    mock_result_with_matches.all.return_value = [mock_row1, mock_row2]

    # Test filtering by partial name match
    mock_session.execute.return_value = mock_result_with_matches

    collections = await document_manager.get_collections(session=mock_session, user_id=1, collection_name="test_collection", offset=0, limit=10)

    assert len(collections) == 2, "Should return two matching collections"
    assert all("test_collection" in col.name for col in collections), "All collections should contain 'test_collection' in their name"
    assert collections[0].name == "test_collection_alpha"
    assert collections[1].name == "test_collection_beta"

    # Verify the SQL query was called with the name filter
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    statement_str = str(call_args[1]["statement"])
    # The name filter should be applied (typically with LIKE/ILIKE)
    assert "name" in statement_str.lower()

    # Mock database result for no matches
    mock_result_empty = MagicMock()
    mock_result_empty.all.return_value = []
    mock_session.execute.return_value = mock_result_empty

    # Test filtering by non-existent name
    collections = await document_manager.get_collections(
        session=mock_session, user_id=1, collection_name="nonexistent_collection_xyz", offset=0, limit=10
    )

    assert len(collections) == 0, "Should return empty list for non-existent collection name"

    # Mock database result for exact match
    mock_result_exact = MagicMock()
    mock_exact_row = MagicMock()
    mock_exact_row._asdict.return_value = {
        "id": 5,
        "name": "exact_match_collection",
        "owner": "test_user",
        "visibility": CollectionVisibility.PUBLIC,
        "description": "Exact match collection",
        "documents": 1,
        "created_at": 1697000000,
        "updated_at": 1697000000,
    }
    mock_result_exact.all.return_value = [mock_exact_row]
    mock_session.execute.return_value = mock_result_exact

    # Test filtering by exact name
    collections = await document_manager.get_collections(
        session=mock_session, user_id=1, collection_name="exact_match_collection", offset=0, limit=10
    )

    assert len(collections) == 1, "Should return exactly one collection for exact match"
    assert collections[0].name == "exact_match_collection"
    assert collections[0].id == 5
