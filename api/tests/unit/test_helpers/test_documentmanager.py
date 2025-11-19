from contextvars import ContextVar
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._documentmanager import DocumentManager
from api.schemas.chunks import Chunk
from api.schemas.collections import CollectionVisibility
from api.schemas.core.context import RequestContext
from api.schemas.documents import Chunker
from api.schemas.me.info import UserInfo
from api.schemas.parse import ParsedDocument, ParsedDocumentMetadata, ParsedDocumentPage
from api.schemas.usage import Usage
from api.utils.exceptions import CollectionNotFoundException


@pytest.mark.asyncio
async def test_create_document_collection_no_longer_exists():
    """Test that CollectionNotFoundException is raised when document is created for a collection that does not exist."""

    # Mock dependencies
    mock_vectore_store = AsyncMock()
    mock_vector_store_model = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store=mock_vectore_store, vector_store_model=mock_vector_store_model, parser_manager=mock_parser)

    # Mock input parameters
    mock_collection_result = MagicMock()
    mock_collection_result.scalar_one.side_effect = NoResultFound()
    mock_session.execute.return_value = mock_collection_result
    mock_metadata = ParsedDocumentMetadata(document_name="test_doc.txt")
    mock_data = ParsedDocumentPage(content="Test document content", images={}, metadata=mock_metadata)
    mock_document = ParsedDocument(data=[mock_data])
    mock_redis_client = AsyncMock()
    mock_model_registry = AsyncMock()
    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/search",
        user_info=UserInfo(id=1, email="test@test.com", name="Test User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    # Use a real ContextVar instead of a mock
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)

    # Test that the exception is raised with the correct message
    with pytest.raises(CollectionNotFoundException) as exc_info:
        await document_manager.create_document(
            postgres_session=mock_session,
            redis_client=mock_redis_client,
            model_registry=mock_model_registry,
            request_context=mock_request_context,
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

        assert "Collection 123 no longer exists" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 404


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

    # Mock input parameters
    mock_private_result = MagicMock()
    mock_private_row = MagicMock()
    mock_private_row._asdict.return_value = {
        "id": 1,
        "name": "Private Collection",
        "owner": "test_user",
        "visibility": CollectionVisibility.PRIVATE,
        "description": "A private collection",
        "documents": 5,
        "created": 1697000000,
        "updated": 1697000000,
    }
    mock_private_result.all.return_value = [mock_private_row]
    mock_public_result = MagicMock()
    mock_public_row = MagicMock()
    mock_public_row._asdict.return_value = {
        "id": 2,
        "name": "Public Collection",
        "owner": "test_user",
        "visibility": CollectionVisibility.PUBLIC,
        "description": "A public collection",
        "documents": 10,
        "created": 1697000000,
        "updated": 1697000000,
    }
    mock_public_result.all.return_value = [mock_public_row]

    mock_session.execute.return_value = mock_private_result
    collections = await document_manager.get_collections(
        postgres_session=mock_session, user_id=1, visibility=CollectionVisibility.PRIVATE, offset=0, limit=10
    )

    assert len(collections) == 1, "Should return exactly one private collection"
    assert collections[0].visibility == CollectionVisibility.PRIVATE, "Collection should be private"
    assert collections[0].name == "Private Collection"
    assert collections[0].id == 1

    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    statement_str = str(call_args[1]["statement"])
    assert "visibility" in statement_str.lower()

    mock_session.execute.return_value = mock_public_result
    collections = await document_manager.get_collections(
        postgres_session=mock_session, user_id=1, visibility=CollectionVisibility.PUBLIC, offset=0, limit=10
    )

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

    # Mock input parameters
    mock_result_with_matches = MagicMock()
    mock_row1 = MagicMock()
    mock_row1._asdict.return_value = {
        "id": 1,
        "name": "test_collection_alpha",
        "owner": "test_user",
        "visibility": CollectionVisibility.PRIVATE,
        "description": "First test collection",
        "documents": 3,
        "created": 1697000000,
        "updated": 1697000000,
    }
    mock_row2 = MagicMock()
    mock_row2._asdict.return_value = {
        "id": 2,
        "name": "test_collection_beta",
        "owner": "test_user",
        "visibility": CollectionVisibility.PRIVATE,
        "description": "Second test collection",
        "documents": 7,
        "created": 1697000000,
        "updated": 1697000000,
    }
    mock_result_with_matches.all.return_value = [mock_row1, mock_row2]
    mock_result_empty = MagicMock()
    mock_result_empty.all.return_value = []
    mock_result_exact = MagicMock()
    mock_exact_row = MagicMock()
    mock_exact_row._asdict.return_value = {
        "id": 5,
        "name": "exact_match_collection",
        "owner": "test_user",
        "visibility": CollectionVisibility.PUBLIC,
        "description": "Exact match collection",
        "documents": 1,
        "created": 1697000000,
        "updated": 1697000000,
    }
    mock_result_exact.all.return_value = [mock_exact_row]

    mock_session.execute.return_value = mock_result_with_matches
    collections = await document_manager.get_collections(
        postgres_session=mock_session, user_id=1, collection_name="test_collection", offset=0, limit=10
    )

    assert len(collections) == 2, "Should return two matching collections"
    assert all("test_collection" in col.name for col in collections), "All collections should contain 'test_collection' in their name"
    assert collections[0].name == "test_collection_alpha"
    assert collections[1].name == "test_collection_beta"

    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    statement_str = str(call_args[1]["statement"])
    assert "name" in statement_str.lower()

    mock_session.execute.return_value = mock_result_empty
    collections = await document_manager.get_collections(
        postgres_session=mock_session, user_id=1, collection_name="nonexistent_collection_xyz", offset=0, limit=10
    )

    assert len(collections) == 0, "Should return empty list for non-existent collection name"

    mock_session.execute.return_value = mock_result_exact
    collections = await document_manager.get_collections(
        postgres_session=mock_session, user_id=1, collection_name="exact_match_collection", offset=0, limit=10
    )

    assert len(collections) == 1, "Should return exactly one collection for exact match"
    assert collections[0].name == "exact_match_collection"
    assert collections[0].id == 5


@pytest.mark.asyncio
async def test_create_collection_success():
    mock_vector_store = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    mock_session.execute.return_value = mock_result

    document_manager = DocumentManager(vector_store=mock_vector_store, vector_store_model="test-model", parser_manager=mock_parser)

    collection_id = await document_manager.create_collection(
        postgres_session=mock_session,
        user_id=1,
        name="My collection",
        visibility=CollectionVisibility.PRIVATE,
        description="desc",
    )

    assert collection_id == 42
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_collection_not_found():
    mock_vector_store = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one.side_effect = NoResultFound()
    mock_session.execute.return_value = mock_result

    document_manager = DocumentManager(vector_store=mock_vector_store, vector_store_model="test-model", parser_manager=mock_parser)

    with pytest.raises(CollectionNotFoundException):
        await document_manager.delete_collection(postgres_session=mock_session, user_id=1, collection_id=99)

    mock_vector_store.delete_collection.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_collection_success():
    mock_vector_store = AsyncMock()
    mock_vector_store.delete_collection = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    select_result = MagicMock()
    select_result.scalar_one.return_value = MagicMock()
    delete_result = MagicMock()
    mock_session.execute.side_effect = [select_result, delete_result]

    document_manager = DocumentManager(vector_store=mock_vector_store, vector_store_model="test-model", parser_manager=mock_parser)

    await document_manager.delete_collection(postgres_session=mock_session, user_id=1, collection_id=123)

    assert mock_session.execute.await_count == 2
    mock_session.commit.assert_awaited_once()
    mock_vector_store.delete_collection.assert_awaited_once_with(collection_id=123)


@pytest.mark.asyncio
async def test_create_document_success(monkeypatch):
    mock_vector_store = AsyncMock()
    mock_vector_store.create_collection = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    check_collection = MagicMock()
    check_collection.scalar_one.return_value = MagicMock()
    fetch_vector_size = MagicMock()
    fetch_vector_size.scalar_one.return_value = 1536
    insert_document = MagicMock()
    insert_document.scalar_one.return_value = 555
    mock_session.execute.side_effect = [check_collection, fetch_vector_size, insert_document]

    document_manager = DocumentManager(vector_store=mock_vector_store, vector_store_model="test-model", parser_manager=mock_parser)

    chunks = [Chunk(id=1, metadata={}, content="chunk-1")]
    document_manager._split = MagicMock(return_value=chunks)
    document_manager._upsert = AsyncMock()

    monkeypatch.setattr("api.helpers._documentmanager.time.time", lambda: 1700000000)

    mock_metadata = ParsedDocumentMetadata(document_name="test_doc.txt")
    mock_page = ParsedDocumentPage(content="Hello", images={}, metadata=mock_metadata)
    mock_document = ParsedDocument(data=[mock_page])
    mock_redis = AsyncMock()
    mock_model_registry = AsyncMock()
    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/search",
        user_info=UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    # Use a real ContextVar instead of a mock
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)
    document_id = await document_manager.create_document(
        postgres_session=mock_session,
        redis_client=mock_redis,
        model_registry=mock_model_registry,
        request_context=mock_request_context,
        collection_id=123,
        document=mock_document,
        chunker=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER,
        chunk_size=1000,
        chunk_overlap=50,
        length_function=len,
        chunk_min_size=20,
        is_separator_regex=False,
        separators=["\n"],
    )

    assert document_id == 555
    document_manager._split.assert_called_once()
    document_manager._upsert.assert_awaited_once()

    upsert_kwargs = document_manager._upsert.await_args.kwargs
    upsert_chunks = upsert_kwargs["chunks"]
    assert upsert_chunks[0].metadata["collection_id"] == 123
    assert upsert_chunks[0].metadata["document_id"] == 555
    assert upsert_chunks[0].metadata["document_created"] == 1700000000
    mock_vector_store.create_collection.assert_awaited_once_with(collection_id=123, vector_size=1536)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_documents_populates_chunk_count():
    mock_vector_store = AsyncMock()
    mock_vector_store.get_chunk_count = AsyncMock(side_effect=[3, 7])
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()

    row_one = MagicMock()
    row_one._asdict.return_value = {"id": 10, "name": "doc-a", "collection_id": 5, "created": 1697000000}
    row_two = MagicMock()
    row_two._asdict.return_value = {"id": 11, "name": "doc-b", "collection_id": 5, "created": 1697000001}
    mock_result = MagicMock()
    mock_result.all.return_value = [row_one, row_two]
    mock_session.execute.return_value = mock_result

    document_manager = DocumentManager(vector_store=mock_vector_store, vector_store_model="test-model", parser_manager=mock_parser)

    user = UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0)
    documents = await document_manager.get_documents(postgres_session=mock_session, user_id=user.id, collection_id=5)

    assert len(documents) == 2
    assert documents[0].chunks == 3
    assert documents[1].chunks == 7
    assert mock_vector_store.get_chunk_count.await_count == 2


@pytest.mark.asyncio
async def test_search_chunks_returns_empty_when_no_collections():
    mock_vector_store = AsyncMock()
    mock_vector_store.search = AsyncMock()
    mock_parser = AsyncMock()
    document_manager = DocumentManager(vector_store=mock_vector_store, vector_store_model="test-model", parser_manager=mock_parser)

    mock_session = AsyncMock(spec=AsyncSession)
    mock_redis = AsyncMock()
    mock_model_registry = AsyncMock()
    mock_model_registry.get_model_provider = AsyncMock()

    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/search",
        user_info=UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    # Use a real ContextVar instead of a mock
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)

    result = await document_manager.search_chunks(
        postgres_session=mock_session,
        redis_client=mock_redis,
        model_registry=mock_model_registry,
        request_context=mock_request_context,
        collection_ids=[],
        prompt="hello",
        method="similarity",
        limit=5,
        offset=0,
        rff_k=10,
    )

    assert result == []
    mock_vector_store.search.assert_not_called()
    mock_model_registry.get_model_provider.assert_not_called()
