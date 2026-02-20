from contextvars import ContextVar
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

from fastapi import UploadFile
import pytest
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from api.helpers._documentmanager import DocumentManager
from api.schemas.chunks import Chunk
from api.schemas.collections import CollectionVisibility
from api.schemas.core.context import RequestContext
from api.schemas.me.info import UserInfo
from api.schemas.usage import Usage
from api.utils.exceptions import (
    ChunkingFailedException,
    CollectionNotFoundException,
    DocumentNotFoundException,
    MasterNotAllowedException,
    ParsingDocumentFailedException,
    VectorizationFailedException,
)


def create_upload_file(content: str, filename: str, content_type: str) -> UploadFile:
    """Helper function to create UploadFile from string content."""
    return UploadFile(filename=filename, file=BytesIO(content.encode("utf-8")), headers=Headers({"content-type": content_type}))


@pytest.mark.asyncio
async def test_create_document_collection_no_longer_exists():
    """Test that CollectionNotFoundException is raised when document is created for a collection that does not exist."""

    # Mock dependencies
    mock_vector_store_model = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store_model=mock_vector_store_model, parser_manager=mock_parser)

    # Mock input parameters
    mock_collection_result = MagicMock()
    mock_collection_result.scalar_one.side_effect = NoResultFound()
    mock_session.execute.return_value = mock_collection_result
    mock_metadata = {"source_tags": ["test", "test2"], "source_title": "Test document"}
    mock_file = create_upload_file("#Test document content", "sample.md", "text/markdown")
    mock_redis_client = AsyncMock()
    mock_model_registry = AsyncMock()
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
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
            collection_id=123,
            file=mock_file,
            name=None,
            disable_chunking=False,
            chunk_size=1000,
            chunk_overlap=100,
            is_separator_regex=False,
            separators=["\n\n", "\n", " "],
            preset_separators="markdown",
            chunk_min_size=50,
            metadata=mock_metadata,
            elasticsearch_vector_store=mock_elasticsearch_vector_store,
            elasticsearch_client=mock_elasticsearch_client,
            postgres_session=mock_session,
            redis_client=mock_redis_client,
            model_registry=mock_model_registry,
            request_context=mock_request_context,
        )

        assert "Collection 123 no longer exists" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_collections_filter_by_visibility():
    """Test that get_collections correctly filters by visibility (private/public)."""

    # Mock dependencies
    mock_vector_store_model = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store_model=mock_vector_store_model, parser_manager=mock_parser)

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
    mock_vector_store_model = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    # Create DocumentManager instance
    document_manager = DocumentManager(vector_store_model=mock_vector_store_model, parser_manager=mock_parser)

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
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    mock_session.execute.return_value = mock_result

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

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
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one.side_effect = NoResultFound()
    mock_session.execute.return_value = mock_result

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    with pytest.raises(CollectionNotFoundException):
        await document_manager.delete_collection(
            postgres_session=mock_session,
            elasticsearch_vector_store=mock_elasticsearch_vector_store,
            elasticsearch_client=mock_elasticsearch_client,
            user_id=1,
            collection_id=99,
        )

    mock_elasticsearch_vector_store.delete_collection.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_collection_success():
    mock_vector_store = AsyncMock()
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_vector_store.delete_collection = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    select_result = MagicMock()
    select_result.scalar_one.return_value = MagicMock()
    delete_result = MagicMock()
    mock_session.execute.side_effect = [select_result, delete_result]

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    await document_manager.delete_collection(
        postgres_session=mock_session,
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
        user_id=1,
        collection_id=123,
    )

    assert mock_session.execute.await_count == 2
    mock_session.commit.assert_awaited_once()
    mock_elasticsearch_vector_store.delete_collection.assert_awaited_once_with(client=mock_elasticsearch_client, collection_id=123)


@pytest.mark.asyncio
async def test_create_document_success(monkeypatch):
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_parser.parse = AsyncMock(return_value="Test content for chunking")
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    check_collection = MagicMock()
    check_collection.scalar_one.return_value = MagicMock()
    insert_document = MagicMock()
    insert_document.scalar_one.return_value = 555
    mock_session.execute.side_effect = [check_collection, insert_document]

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    chunks = ["chunk-1", "chunk-2"]
    document_manager._split = MagicMock(return_value=chunks)
    document_manager._upsert_document_chunks = AsyncMock()

    mock_file = create_upload_file("Test content", "test.txt", "text/plain")
    mock_metadata = {"source_tags": ["test"]}
    mock_redis = AsyncMock()
    mock_model_registry = AsyncMock()
    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/documents",
        user_info=UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)

    document_id = await document_manager.create_document(
        postgres_session=mock_session,
        redis_client=mock_redis,
        model_registry=mock_model_registry,
        request_context=mock_request_context,
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
        collection_id=123,
        file=mock_file,
        metadata=mock_metadata,
        chunk_size=1000,
        chunk_overlap=100,
        chunk_min_size=50,
        name=None,
        disable_chunking=False,
        separators=[],
        preset_separators="markdown",
        is_separator_regex=False,
    )

    assert document_id == 555
    document_manager._split.assert_called_once()
    document_manager._upsert_document_chunks.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_documents_populates_chunk_count():
    mock_vector_store = AsyncMock()
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_vector_store.get_chunk_count = AsyncMock(side_effect=[3, 7])
    mock_elasticsearch_client = AsyncMock()
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

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    user = UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0)
    documents = await document_manager.get_documents(
        postgres_session=mock_session,
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
        user_id=user.id,
        collection_id=5,
    )

    assert len(documents) == 2
    assert documents[0].chunks == 3
    assert documents[1].chunks == 7
    assert mock_elasticsearch_vector_store.get_chunk_count.await_count == 2


@pytest.mark.asyncio
async def test_search_chunks_returns_empty_when_no_collections():
    mock_vector_store = AsyncMock()
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_vector_store.search = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

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
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
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
    mock_elasticsearch_vector_store.search.assert_not_called()
    mock_model_registry.get_model_provider.assert_not_called()


@pytest.mark.asyncio
async def test_update_collection_success():
    """Test successful collection update."""
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock the select result
    select_result = MagicMock()
    mock_collection = MagicMock()
    mock_collection.id = 123
    mock_collection.name = "Old Name"
    mock_collection.visibility = CollectionVisibility.PRIVATE
    mock_collection.description = "Old Description"
    select_result.scalar_one.return_value = mock_collection

    # Mock the update result
    update_result = MagicMock()
    mock_session.execute.side_effect = [select_result, update_result]

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    await document_manager.update_collection(
        postgres_session=mock_session,
        user_id=1,
        collection_id=123,
        name="New Name",
        visibility=CollectionVisibility.PUBLIC,
        description="New Description",
    )

    assert mock_session.execute.await_count == 2
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_collection_not_found():
    """Test updating non-existent collection raises CollectionNotFoundException."""
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock NoResultFound exception
    mock_result = MagicMock()
    mock_result.scalar_one.side_effect = NoResultFound()
    mock_session.execute.return_value = mock_result

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    with pytest.raises(CollectionNotFoundException):
        await document_manager.update_collection(postgres_session=mock_session, user_id=1, collection_id=999, name="New Name")

    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_document_success():
    """Test successful document deletion from both Postgres and Elasticsearch."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_vector_store.delete_document = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock the select result
    select_result = MagicMock()
    mock_document = MagicMock()
    mock_document.id = 456
    mock_document.collection_id = 123
    select_result.scalar_one.return_value = mock_document

    # Mock the delete result
    delete_result = MagicMock()
    mock_session.execute.side_effect = [select_result, delete_result]

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    await document_manager.delete_document(
        postgres_session=mock_session,
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
        user_id=1,
        document_id=456,
    )

    assert mock_session.execute.await_count == 2
    mock_session.commit.assert_awaited_once()
    mock_elasticsearch_vector_store.delete_document.assert_awaited_once_with(client=mock_elasticsearch_client, document_id=456)


@pytest.mark.asyncio
async def test_delete_document_not_found():
    """Test deleting non-existent document raises DocumentNotFoundException."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock NoResultFound exception
    mock_result = MagicMock()
    mock_result.scalar_one.side_effect = NoResultFound()
    mock_session.execute.return_value = mock_result

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    with pytest.raises(DocumentNotFoundException):
        await document_manager.delete_document(
            postgres_session=mock_session,
            elasticsearch_vector_store=mock_elasticsearch_vector_store,
            elasticsearch_client=mock_elasticsearch_client,
            user_id=1,
            document_id=999,
        )

    mock_elasticsearch_vector_store.delete_document.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_chunks_success():
    """Test retrieving chunks for a document."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()

    # Mock the select result
    select_result = MagicMock()
    mock_document = MagicMock()
    mock_document.id = 456
    mock_document.collection_id = 123
    select_result.scalar_one.return_value = mock_document
    mock_session.execute.return_value = select_result

    # Mock chunks returned from Elasticsearch
    mock_chunks = [
        Chunk(id=1, collection_id=123, document_id=456, metadata={"my_tags": ["tag1", "tag2"]}, content="chunk 1"),
        Chunk(id=2, collection_id=123, document_id=456, metadata={"my_tags": ["tag1", "tag2"]}, content="chunk 2"),
    ]
    mock_elasticsearch_vector_store.get_chunks = AsyncMock(return_value=mock_chunks)

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    chunks = await document_manager.get_document_chunks(
        postgres_session=mock_session,
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
        user_id=1,
        document_id=456,
        offset=0,
        limit=10,
    )

    assert len(chunks) == 2
    assert chunks[0].id == 1
    assert chunks[1].id == 2
    mock_elasticsearch_vector_store.get_chunks.assert_awaited_once_with(
        client=mock_elasticsearch_client, document_id=456, offset=0, limit=10, chunk_id=None
    )


@pytest.mark.asyncio
async def test_get_chunks_document_not_found():
    """Test getting chunks for non-existent document raises DocumentNotFoundException."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()

    # Mock NoResultFound exception
    mock_result = MagicMock()
    mock_result.scalar_one.side_effect = NoResultFound()
    mock_session.execute.return_value = mock_result

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    with pytest.raises(DocumentNotFoundException):
        await document_manager.get_document_chunks(
            postgres_session=mock_session,
            elasticsearch_vector_store=mock_elasticsearch_vector_store,
            elasticsearch_client=mock_elasticsearch_client,
            user_id=1,
            document_id=999,
        )

    mock_elasticsearch_vector_store.get_chunks.assert_not_called()


@pytest.mark.asyncio
async def test_search_chunks_with_similarity():
    """Test semantic search with vector embeddings."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_redis = AsyncMock()
    mock_model_registry = AsyncMock()

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    # Mock collection exists check
    collection_result = MagicMock()
    collection_result.scalar_one.return_value = MagicMock()
    mock_session.execute.return_value = collection_result

    # Mock model provider and embeddings
    mock_provider = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
    mock_provider.forward_request = AsyncMock(return_value=mock_response)
    mock_model_registry.get_model_provider = AsyncMock(return_value=mock_provider)

    # Mock search results
    mock_search_results = [MagicMock(id=1, content="result 1", score=0.95), MagicMock(id=2, content="result 2", score=0.85)]
    mock_elasticsearch_vector_store.search = AsyncMock(return_value=mock_search_results)

    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/search",
        user_info=UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)

    result = await document_manager.search_chunks(
        postgres_session=mock_session,
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
        redis_client=mock_redis,
        model_registry=mock_model_registry,
        request_context=mock_request_context,
        collection_ids=[123],
        prompt="test query",
        method="similarity",
        limit=10,
        offset=0,
        rff_k=50,
    )

    assert len(result) == 2
    mock_model_registry.get_model_provider.assert_awaited_once()
    mock_provider.forward_request.assert_awaited_once()
    mock_elasticsearch_vector_store.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_chunks_with_lexical():
    """Test lexical search (BM25) without embedding creation."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_redis = AsyncMock()
    mock_model_registry = AsyncMock()

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    # Mock collection exists check
    collection_result = MagicMock()
    collection_result.scalar_one.return_value = MagicMock()
    mock_session.execute.return_value = collection_result

    # Mock model provider (should not be called for lexical search)
    mock_provider = AsyncMock()
    mock_model_registry.get_model_provider = AsyncMock(return_value=mock_provider)

    # Mock search results
    mock_search_results = [MagicMock(id=1, content="result 1", score=5.2), MagicMock(id=2, content="result 2", score=4.1)]
    mock_elasticsearch_vector_store.search = AsyncMock(return_value=mock_search_results)

    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/search",
        user_info=UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)

    result = await document_manager.search_chunks(
        postgres_session=mock_session,
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
        redis_client=mock_redis,
        model_registry=mock_model_registry,
        request_context=mock_request_context,
        collection_ids=[123],
        prompt="test query",
        method="lexical",
        limit=10,
        offset=0,
        rff_k=50,
    )

    assert len(result) == 2
    mock_model_registry.get_model_provider.assert_awaited_once()
    # Verify no embedding creation for lexical search - provider.forward_request should not be called
    mock_provider.forward_request.assert_not_called()
    # Verify search was called with None for query_vector
    call_kwargs = mock_elasticsearch_vector_store.search.call_args.kwargs
    assert call_kwargs["query_vector"] is None
    mock_elasticsearch_vector_store.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_chunks_collection_not_found():
    """Test searching in non-existent collection raises CollectionNotFoundException."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_redis = AsyncMock()
    mock_model_registry = AsyncMock()

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    # Mock collection not found
    mock_result = MagicMock()
    mock_result.scalar_one.side_effect = NoResultFound()
    mock_session.execute.return_value = mock_result

    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/search",
        user_info=UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)

    with pytest.raises(CollectionNotFoundException):
        await document_manager.search_chunks(
            postgres_session=mock_session,
            elasticsearch_vector_store=mock_elasticsearch_vector_store,
            elasticsearch_client=mock_elasticsearch_client,
            redis_client=mock_redis,
            model_registry=mock_model_registry,
            request_context=mock_request_context,
            collection_ids=[999],
            prompt="test query",
            method="similarity",
            limit=10,
            offset=0,
            rff_k=50,
        )

    mock_elasticsearch_vector_store.search.assert_not_called()


@pytest.mark.asyncio
async def test_create_collection_master_user_forbidden():
    """Test that user_id=0 (master user) cannot create collections."""
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    with pytest.raises(MasterNotAllowedException) as exc_info:
        await document_manager.create_collection(
            postgres_session=mock_session,
            user_id=0,
            name="Test Collection",
            visibility=CollectionVisibility.PRIVATE,
            description="This should not work",
        )

    assert "Master user is not allowed" in str(exc_info.value.detail)
    mock_session.execute.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_document_parsing_fails():
    """Test ParsingDocumentFailedException when parser fails."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_parser.parse = AsyncMock(side_effect=Exception("Parse error"))
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_redis = AsyncMock()
    mock_model_registry = AsyncMock()

    # Mock collection exists
    collection_result = MagicMock()
    collection_result.scalar_one.return_value = MagicMock()
    mock_session.execute.return_value = collection_result

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    mock_file = create_upload_file("Test content", "test.txt", "text/plain")
    mock_metadata = {"source_tags": ["test"]}

    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/documents",
        user_info=UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)

    with pytest.raises(ParsingDocumentFailedException):
        await document_manager.create_document(
            postgres_session=mock_session,
            redis_client=mock_redis,
            model_registry=mock_model_registry,
            request_context=mock_request_context,
            elasticsearch_vector_store=mock_elasticsearch_vector_store,
            elasticsearch_client=mock_elasticsearch_client,
            collection_id=123,
            file=mock_file,
            metadata=mock_metadata,
            chunk_size=1000,
            chunk_overlap=100,
            chunk_min_size=50,
            name=None,
            disable_chunking=False,
            separators=[],
            preset_separators="markdown",
            is_separator_regex=False,
        )


@pytest.mark.asyncio
async def test_create_document_empty_chunks():
    """Test ChunkingFailedException when no chunks extracted."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_parser.parse = AsyncMock(return_value="Short content")
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_redis = AsyncMock()
    mock_model_registry = AsyncMock()

    # Mock collection exists
    collection_result = MagicMock()
    collection_result.scalar_one.return_value = MagicMock()
    mock_session.execute.return_value = collection_result

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    # Mock _split to return empty chunks
    document_manager._split = MagicMock(return_value=[])

    mock_file = create_upload_file("Test content", "test.txt", "text/plain")
    mock_metadata = {"source_tags": ["test"]}

    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/documents",
        user_info=UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)

    with pytest.raises(ChunkingFailedException) as exc_info:
        await document_manager.create_document(
            postgres_session=mock_session,
            redis_client=mock_redis,
            model_registry=mock_model_registry,
            request_context=mock_request_context,
            elasticsearch_vector_store=mock_elasticsearch_vector_store,
            elasticsearch_client=mock_elasticsearch_client,
            collection_id=123,
            file=mock_file,
            metadata=mock_metadata,
            chunk_size=1000,
            chunk_overlap=100,
            chunk_min_size=50,
            name=None,
            disable_chunking=False,
            separators=[],
            preset_separators="markdown",
            is_separator_regex=False,
        )

    assert "No chunks were extracted" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_document_vectorization_fails(monkeypatch):
    """Test cleanup when vectorization fails."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_parser.parse = AsyncMock(return_value="Test content for chunking")
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_redis = AsyncMock()
    mock_model_registry = AsyncMock()

    # Mock collection exists, insert document, and delete document
    collection_result = MagicMock()
    collection_result.scalar_one.return_value = MagicMock()
    insert_document = MagicMock()
    insert_document.scalar_one.return_value = 555
    # Additional selects for delete_document check
    select_for_delete = MagicMock()
    mock_doc = MagicMock()
    mock_doc.collection_id = 123
    select_for_delete.scalar_one.return_value = mock_doc
    delete_result = MagicMock()
    mock_session.execute.side_effect = [collection_result, insert_document, select_for_delete, delete_result]

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    # Mock _split to return chunks
    chunks = ["chunk-1", "chunk-2"]
    document_manager._split = MagicMock(return_value=chunks)

    # Mock chunk upsert to fail
    document_manager._upsert_document_chunks = AsyncMock(side_effect=Exception("Vectorization error"))

    mock_file = create_upload_file("Test content", "test.txt", "text/plain")
    mock_metadata = {"source_tags": ["test"]}

    mock_request_context_obj = RequestContext(
        id="123",
        client="test",
        method="POST",
        endpoint="/v1/documents",
        user_info=UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0),
        token_id=1,
        usage=Usage(),
    )
    mock_request_context = ContextVar("test_request_context", default=mock_request_context_obj)
    mock_request_context.set(mock_request_context_obj)

    with pytest.raises(VectorizationFailedException) as exc_info:
        await document_manager.create_document(
            postgres_session=mock_session,
            redis_client=mock_redis,
            model_registry=mock_model_registry,
            request_context=mock_request_context,
            elasticsearch_vector_store=mock_elasticsearch_vector_store,
            elasticsearch_client=mock_elasticsearch_client,
            collection_id=123,
            file=mock_file,
            metadata=mock_metadata,
            chunk_size=1000,
            chunk_overlap=100,
            chunk_min_size=50,
            name=None,
            disable_chunking=False,
            separators=[],
            preset_separators="markdown",
            is_separator_regex=False,
        )

    assert "Vectorization failed" in str(exc_info.value.detail)
    # Verify document was attempted to be deleted from Postgres
    assert mock_session.execute.await_count == 4  # collection check, insert, delete check, delete
    mock_elasticsearch_vector_store.delete_document.assert_awaited_once_with(client=mock_elasticsearch_client, document_id=555)


@pytest.mark.asyncio
async def test_get_documents_with_filters():
    """Test filtering documents by document_name and document_id."""
    mock_elasticsearch_vector_store = AsyncMock()
    mock_elasticsearch_vector_store.get_chunk_count = AsyncMock(return_value=5)
    mock_elasticsearch_client = AsyncMock()
    mock_parser = AsyncMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()

    row = MagicMock()
    row._asdict.return_value = {"id": 100, "name": "specific_doc.txt", "collection_id": 5, "created": 1697000000}
    mock_result = MagicMock()
    mock_result.all.return_value = [row]
    mock_session.execute.return_value = mock_result

    document_manager = DocumentManager(vector_store_model="test-model", parser_manager=mock_parser)

    # Test filtering by document_name
    documents = await document_manager.get_documents(
        postgres_session=mock_session,
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
        user_id=1,
        collection_id=5,
        document_name="specific_doc.txt",
    )

    assert len(documents) == 1
    assert documents[0].name == "specific_doc.txt"
    assert documents[0].chunks == 5

    # Test filtering by document_id
    mock_session.execute.return_value = mock_result
    documents = await document_manager.get_documents(
        postgres_session=mock_session,
        elasticsearch_vector_store=mock_elasticsearch_vector_store,
        elasticsearch_client=mock_elasticsearch_client,
        user_id=1,
        collection_id=5,
        document_id=100,
    )

    assert len(documents) == 1
    assert documents[0].id == 100
