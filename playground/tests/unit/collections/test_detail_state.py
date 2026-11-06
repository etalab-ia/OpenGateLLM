import io
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
import reflex as rx
from starlette.datastructures import Headers

from app.features.collections.detail_state import MAX_DOCUMENT_SIZE, CollectionDetailState
from app.features.collections.models import Collection, Document

from tests.unit.collections.test_state import drive, make_state, response


def owned_collection(**overrides):
    values = {
        "id": 42,
        "name": "Guides",
        "description": "Administrative guides",
        "owner": 7,
        "visibility": "private",
        "documents": 1,
        "size": 100,
        "created": "2026-01-01 00:00",
        "updated": "2026-01-01 00:00",
        "is_owner": True,
    }
    values.update(overrides)
    return Collection(**values)


def document_model(**overrides):
    values = {"id": 101, "name": "guide.pdf", "collection_id": 42, "created": "2026-01-01 00:00", "chunks": 2, "size": 100}
    values.update(overrides)
    return Document(**values)


def raw_collection(**overrides):
    values = {
        "id": 42,
        "name": "Guides",
        "description": "Administrative guides",
        "owner": 7,
        "visibility": "private",
        "documents": 1,
        "size": 100,
        "created": 1767225600,
        "updated": 1767225600,
    }
    values.update(overrides)
    return values


def raw_document(**overrides):
    values = {"id": 101, "name": "guide.pdf", "collection_id": 42, "created": 1767225600, "chunks": 2, "size": 100}
    values.update(overrides)
    return values


def raw_chunk(**overrides):
    values = {
        "id": 0,
        "collection_id": 42,
        "document_id": 101,
        "content": "First page text",
        "metadata": {"page_number": 2, "source": "guide.pdf"},
        "created": 1767225600,
    }
    values.update(overrides)
    return values


def make_detail_state(**overrides):
    values = {
        "collection_id": "42",
        "detail_collection": owned_collection(),
        "detail_loading": False,
        "detail_error": "",
        "documents": [],
        "documents_loading": False,
        "documents_error": "",
        "document_page": 1,
        "documents_per_page": 10,
        "documents_has_next_page": False,
        "is_upload_dialog_open": True,
        "upload_loading": False,
        "upload_error": "",
        "upload_status": "",
        "document_to_delete": Document(),
        "selected_document": Document(),
        "chunks": [],
        "chunks_loading": False,
        "chunks_error": "",
        "chunk_page": 1,
        "chunks_per_page": 5,
        "chunks_has_next_page": False,
    }
    values.update(overrides)
    state = make_state(**values)
    state._format_document = CollectionDetailState._format_document.__get__(state)
    state._format_chunk = CollectionDetailState._format_chunk.__get__(state)
    state._can_manage_collection = CollectionDetailState._can_manage_collection.__get__(state)
    state._detail_error_message = CollectionDetailState._detail_error_message.__get__(state)
    state._upload_error_message = CollectionDetailState._upload_error_message.__get__(state)
    state.load_documents = lambda: CollectionDetailState.load_documents.fn(state)
    state.load_collection_detail = lambda reset_page=True: CollectionDetailState.load_collection_detail.fn(state, reset_page=reset_page)
    state.load_chunks = lambda: CollectionDetailState.load_chunks.fn(state)
    return state


async def noop_reload(reset_page=True):
    if False:
        yield None


def upload_file(filename="guide.pdf", content=b"%PDF-1.4", size=None, content_type="application/pdf"):
    return rx.UploadFile(
        file=io.BytesIO(content),
        path=Path(filename),
        size=len(content) if size is None else size,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.asyncio
async def test_should_load_collection_and_documents_with_page_size_plus_one():
    # Arrange
    state = make_detail_state(document_page=2)
    state._request = AsyncMock(side_effect=[response(raw_collection()), response({"data": [raw_document()] * 11})])

    # Act
    await drive(CollectionDetailState.load_collection_detail.fn(state, reset_page=False))

    # Assert
    assert state._request.await_args_list[0].args == ("GET", "/v1/collections/42")
    assert state._request.await_args_list[1].args == ("GET", "/v1/documents")
    assert state._request.await_args_list[1].kwargs["params"] == {
        "collection_id": 42,
        "offset": 10,
        "limit": 11,
        "order_by": "created",
        "order_direction": "desc",
    }
    assert len(state.documents) == 10
    assert state.documents_has_next_page is True
    assert state.detail_collection.is_owner is True
    assert state.detail_loading is False
    assert state.documents_loading is False


@pytest.mark.asyncio
async def test_should_reject_invalid_collection_route_without_requesting_api():
    # Arrange
    state = make_detail_state(collection_id="not-an-integer")
    state._request = AsyncMock()

    # Act
    await drive(CollectionDetailState.load_collection_detail.fn(state))

    # Assert
    state._request.assert_not_awaited()
    assert state.detail_error == "This collection link is invalid."
    assert state.detail_collection.id is None


@pytest.mark.asyncio
async def test_should_clear_stale_documents_when_loading_fails():
    # Arrange
    state = make_detail_state(documents=[document_model()], documents_has_next_page=True)
    state._request = AsyncMock(return_value=response({"detail": "Insufficient rights."}, status_code=403))

    # Act
    await drive(CollectionDetailState.load_documents.fn(state))

    # Assert
    assert state.documents == []
    assert state.documents_has_next_page is False
    assert state.documents_error == "Insufficient rights."
    assert state.documents_loading is False


@pytest.mark.asyncio
async def test_should_upload_multipart_with_api_default_chunking():
    # Arrange
    state = make_detail_state()
    state.load_collection_detail = noop_reload
    state._request = AsyncMock(return_value=response({"id": 101}, status_code=201))

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file()]))

    # Assert
    state._request.assert_awaited_once()
    method, path = state._request.await_args.args
    assert (method, path) == ("POST", "/v1/documents")
    assert state._request.await_args.kwargs["data"] == {"collection_id": "42"}
    filename, content, content_type = state._request.await_args.kwargs["files"]["file"]
    assert filename == "guide.pdf"
    assert content == b"%PDF-1.4"
    assert content_type == "application/pdf"
    assert "chunk_size" not in state._request.await_args.kwargs["data"]
    assert "json" not in state._request.await_args.kwargs
    assert state.is_upload_dialog_open is False
    assert state.upload_error == ""
    assert state.upload_loading is False


@pytest.mark.asyncio
async def test_should_reject_unsupported_file_before_requesting_api():
    # Arrange
    state = make_detail_state()
    state._request = AsyncMock()

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file(filename="guide.docx")]))

    # Assert
    state._request.assert_not_awaited()
    assert "supported formats are PDF, HTML, Markdown and TXT" in state.upload_error
    assert state.is_upload_dialog_open is True


@pytest.mark.asyncio
async def test_should_enforce_twenty_megabyte_limit_before_reading_file():
    # Arrange
    state = make_detail_state()
    state._request = AsyncMock()

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file(size=MAX_DOCUMENT_SIZE + 1)]))

    # Assert
    state._request.assert_not_awaited()
    assert "file size limit exceeded" in state.upload_error


@pytest.mark.asyncio
async def test_should_keep_indexing_failure_visible_without_success_message():
    # Arrange
    state = make_detail_state()
    state.load_collection_detail = noop_reload
    state._request = AsyncMock(return_value=response({"detail": "Vectorization failed: unavailable"}, status_code=500))

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file()]))

    # Assert
    assert "Vectorization failed: unavailable" in state.upload_error
    assert state.is_upload_dialog_open is True
    assert state.upload_loading is False
    assert state.upload_status == ""


@pytest.mark.asyncio
async def test_should_report_each_file_in_mixed_upload_results():
    # Arrange
    state = make_detail_state()
    state.load_collection_detail = noop_reload
    state._request = AsyncMock(
        side_effect=[
            response({"id": 101}, status_code=201),
            response({"detail": "Parsing document failed."}, status_code=500),
        ]
    )
    files = [upload_file(), upload_file(filename="notes.txt", content=b"notes", content_type="text/plain")]

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, files))

    # Assert
    assert state._request.await_count == 2
    assert "notes.txt: Parsing document failed." in state.upload_error
    assert state.is_upload_dialog_open is True


@pytest.mark.asyncio
async def test_should_not_upload_or_delete_for_read_only_public_collection():
    # Arrange
    public_collection = owned_collection(owner=99, visibility="public", is_owner=False)
    state = make_detail_state(detail_collection=public_collection, is_upload_dialog_open=False)
    state._request = AsyncMock()

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file()]))
    CollectionDetailState.set_document_to_delete.fn(state, document_model())
    await drive(CollectionDetailState.delete_document.fn(state))

    # Assert
    state._request.assert_not_awaited()
    assert state.document_to_delete.id is None
    CollectionDetailState.open_upload_dialog.fn(state)
    assert state.is_upload_dialog_open is False


@pytest.mark.asyncio
async def test_should_delete_document_without_parsing_204_response():
    # Arrange
    document = document_model()
    state = make_detail_state(document_to_delete=document, documents=[document], document_page=2)
    state.load_collection_detail = noop_reload
    no_content = httpx.Response(204, request=httpx.Request("DELETE", "http://rag:8000/v1/documents/101"))
    state._request = AsyncMock(return_value=no_content)

    # Act
    await drive(CollectionDetailState.delete_document.fn(state))

    # Assert
    state._request.assert_awaited_once_with("DELETE", "/v1/documents/101")
    assert state.document_to_delete.id is None
    assert state.document_page == 1
    assert state.delete_entity_loading is False


@pytest.mark.asyncio
async def test_should_load_chunks_with_page_provenance_and_pagination():
    # Arrange
    state = make_detail_state(selected_document=document_model(), chunk_page=2)
    state._request = AsyncMock(return_value=response({"data": [raw_chunk()] * 6}))

    # Act
    await drive(CollectionDetailState.load_chunks.fn(state))

    # Assert
    state._request.assert_awaited_once_with("GET", "/v1/documents/101/chunks", params={"offset": 5, "limit": 6})
    assert len(state.chunks) == 5
    assert state.chunks_has_next_page is True
    assert state.chunks[0].page_number == 2
    assert state.chunks[0].content == "First page text"
    assert '"source": "guide.pdf"' in state.chunks[0].metadata_json
    assert state.chunks[0].created is not None


@pytest.mark.parametrize("page_number", [None, "2", 2.0, True, 0, -1])
def test_should_not_invent_page_number_for_non_standard_metadata(page_number):
    # Arrange
    state = make_detail_state()
    metadata = {"source": "guide.txt"}
    if page_number is not None:
        metadata["page_number"] = page_number

    # Act
    chunk = CollectionDetailState._format_chunk(state, raw_chunk(metadata=metadata))

    # Assert
    assert chunk.page_number is None
    assert chunk.metadata["source"] == "guide.txt"


@pytest.mark.asyncio
async def test_should_clear_stale_chunks_when_loading_fails():
    # Arrange
    state = make_detail_state(selected_document=document_model(), chunks=[], chunks_has_next_page=True)
    state.chunks = [CollectionDetailState._format_chunk(state, raw_chunk())]
    state._request = AsyncMock(return_value=response({"detail": "Document not found."}, status_code=404))

    # Act
    await drive(CollectionDetailState.load_chunks.fn(state))

    # Assert
    assert state.chunks == []
    assert state.chunks_has_next_page is False
    assert state.chunks_error == "Document not found."
    assert state.chunks_loading is False
