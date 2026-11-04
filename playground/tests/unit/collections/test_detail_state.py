import io
import json
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
        "upload_advanced_open": False,
        "upload_chunk_size": "",
        "upload_chunk_overlap": "",
        "upload_chunk_min_size": "",
        "upload_preset_separators": "markdown",
        "upload_metadata": [],
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
    state._reset_upload_settings = CollectionDetailState._reset_upload_settings.__get__(state)
    state._parse_upload_setting = CollectionDetailState._parse_upload_setting.__get__(state)
    state._validate_upload_settings = CollectionDetailState._validate_upload_settings.__get__(state)
    state._validate_upload_metadata = CollectionDetailState._validate_upload_metadata.__get__(state)
    state._build_upload_data = CollectionDetailState._build_upload_data.__get__(state)
    state._build_upload_metadata = CollectionDetailState._build_upload_metadata.__get__(state)
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
async def test_should_upload_multipart_with_custom_chunking_and_metadata():
    # Arrange
    state = make_detail_state(
        upload_chunk_size="512",
        upload_chunk_overlap="64",
        upload_chunk_min_size="10",
        upload_preset_separators="html",
        upload_metadata=[
            {"key": "source", "value": "intranet", "type": "text"},
            {"key": "year", "value": "2026", "type": "number"},
            {"key": "rating", "value": "4.5", "type": "number"},
            {"key": "verified", "value": "true", "type": "boolean"},
        ],
    )
    state.load_collection_detail = noop_reload
    state._request = AsyncMock(return_value=response({"id": 101}, status_code=201))

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file()]))

    # Assert
    data = state._request.await_args.kwargs["data"]
    assert data["collection_id"] == "42"
    assert data["chunk_size"] == "512"
    assert data["chunk_overlap"] == "64"
    assert data["chunk_min_size"] == "10"
    assert data["preset_separators"] == "html"
    assert json.loads(data["metadata"]) == {"source": "intranet", "year": 2026, "rating": 4.5, "verified": True}
    assert state.upload_error == ""
    assert state.is_upload_dialog_open is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"upload_chunk_size": "0"}, "Chunk size must be 1 or more."),
        ({"upload_chunk_size": "abc"}, "Chunk size must be a whole number."),
        ({"upload_chunk_size": "-5"}, "Chunk size must be 1 or more."),
        ({"upload_chunk_overlap": "-5"}, "Chunk overlap must be 0 or more."),
        ({"upload_chunk_overlap": "4096"}, "Chunk overlap must not exceed the chunk size (2048)."),
        ({"upload_chunk_size": "50", "upload_chunk_overlap": "100"}, "Chunk overlap must not exceed the chunk size (50)."),
        ({"upload_chunk_min_size": "1.5"}, "Minimum chunk size must be a whole number."),
        ({"upload_preset_separators": "cobol"}, "Separator preset must be one of: markdown, html, rst, latex."),
    ],
)
async def test_should_reject_invalid_ingestion_settings_before_requesting_api(overrides, message):
    # Arrange
    state = make_detail_state(**overrides)
    state._request = AsyncMock()

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file()]))

    # Assert
    state._request.assert_not_awaited()
    assert message in state.upload_error
    assert state.is_upload_dialog_open is True
    assert state.upload_loading is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([{"key": "page_number", "value": "3", "type": "text"}], "Metadata key 'page_number' is reserved for the document parser."),
        ([{"key": "source", "value": "a", "type": "text"}, {"key": "source", "value": "b", "type": "text"}], "Duplicate metadata key 'source'."),
        ([{"key": "  ", "value": "a", "type": "text"}], "Metadata keys cannot be empty."),
        ([{"key": "source", "value": "", "type": "text"}], "Metadata value for 'source' cannot be empty."),
        ([{"key": "source", "value": "x" * 256, "type": "text"}], "Metadata value for 'source' is limited to 255 characters."),
        ([{"key": "k" * 256, "value": "a", "type": "text"}], "is limited to 255 characters."),
        ([{"key": "year", "value": "abc", "type": "number"}], "Metadata value for 'year' must be a number."),
        ([{"key": "year", "value": "1e30", "type": "number"}], "Metadata value for 'year' is too large."),
        ([{"key": "flag", "value": "maybe", "type": "boolean"}], "Metadata value for 'flag' must be true or false."),
    ],
)
async def test_should_reject_invalid_metadata_before_requesting_api(rows, message):
    # Arrange
    state = make_detail_state(upload_metadata=rows)
    state._request = AsyncMock()

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file()]))

    # Assert
    state._request.assert_not_awaited()
    assert message in state.upload_error
    assert state.is_upload_dialog_open is True


@pytest.mark.asyncio
async def test_should_reject_more_than_ten_metadata_entries_before_requesting_api():
    # Arrange
    state = make_detail_state(upload_metadata=[{"key": f"key{i}", "value": "v", "type": "text"} for i in range(11)])
    state._request = AsyncMock()

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file()]))

    # Assert
    state._request.assert_not_awaited()
    assert "Metadata is limited to 10 entries." in state.upload_error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("sheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("slides.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("memo.odt", "application/vnd.oasis.opendocument.text"),
        ("data.ods", "application/vnd.oasis.opendocument.spreadsheet"),
        ("deck.odp", "application/vnd.oasis.opendocument.presentation"),
        ("table.csv", "text/csv"),
        ("book.epub", "application/epub+zip"),
    ],
)
async def test_should_upload_each_newly_supported_format(filename, content_type):
    # Arrange
    state = make_detail_state()
    state.load_collection_detail = noop_reload
    state._request = AsyncMock(return_value=response({"id": 101}, status_code=201))

    # Act
    await drive(CollectionDetailState.upload_documents.fn(state, [upload_file(filename=filename, content=b"content", content_type=content_type)]))

    # Assert
    state._request.assert_awaited_once()
    assert state._request.await_args.kwargs["files"]["file"][0] == filename
    assert state._request.await_args.kwargs["files"]["file"][2] == content_type
    assert state.upload_error == ""
    assert state.is_upload_dialog_open is False


@pytest.mark.asyncio
async def test_should_reject_unsupported_file_before_requesting_api():
    # Arrange
    state = make_detail_state()
    state._request = AsyncMock()

    # Act
    await drive(
        CollectionDetailState.upload_documents.fn(state, [upload_file(filename="archive.zip", content=b"PK\x03\x04", content_type="application/zip")])
    )

    # Assert
    state._request.assert_not_awaited()
    assert "supported formats are PDF, DOCX, XLSX, PPTX, ODT, ODS, ODP, CSV, EPUB, HTML, Markdown and TXT" in state.upload_error
    assert state.is_upload_dialog_open is True


def test_should_add_update_and_remove_metadata_rows():
    # Arrange
    state = make_detail_state()

    # Act & assert
    CollectionDetailState.add_upload_metadata_row.fn(state)
    CollectionDetailState.add_upload_metadata_row.fn(state)
    assert state.upload_metadata == [{"key": "", "value": "", "type": "text"}, {"key": "", "value": "", "type": "text"}]

    CollectionDetailState.set_upload_metadata_key.fn(state, 0, "source")
    CollectionDetailState.set_upload_metadata_value.fn(state, 0, "intranet")
    CollectionDetailState.set_upload_metadata_type.fn(state, 1, "boolean")
    assert state.upload_metadata[0] == {"key": "source", "value": "intranet", "type": "text"}
    assert state.upload_metadata[1] == {"key": "", "value": "true", "type": "boolean"}

    CollectionDetailState.remove_upload_metadata_row.fn(state, 0)
    assert state.upload_metadata == [{"key": "", "value": "true", "type": "boolean"}]


def test_should_ignore_metadata_row_updates_out_of_range():
    # Arrange
    state = make_detail_state(upload_metadata=[{"key": "a", "value": "1", "type": "text"}])

    # Act
    CollectionDetailState.set_upload_metadata_key.fn(state, 5, "x")
    CollectionDetailState.set_upload_metadata_value.fn(state, -1, "x")
    CollectionDetailState.set_upload_metadata_type.fn(state, 0, "cobol")
    CollectionDetailState.remove_upload_metadata_row.fn(state, 9)

    # Assert
    assert state.upload_metadata == [{"key": "a", "value": "1", "type": "text"}]


def test_should_cap_metadata_rows_at_ten():
    # Arrange
    state = make_detail_state(upload_metadata=[{"key": f"k{i}", "value": "v", "type": "text"} for i in range(10)])

    # Act
    CollectionDetailState.add_upload_metadata_row.fn(state)

    # Assert
    assert len(state.upload_metadata) == 10


def test_should_reset_upload_settings_when_reopening_the_dialog():
    # Arrange
    state = make_detail_state(
        upload_advanced_open=True,
        upload_chunk_size="512",
        upload_chunk_overlap="64",
        upload_preset_separators="html",
        upload_metadata=[{"key": "a", "value": "1", "type": "text"}],
    )

    # Act
    CollectionDetailState.open_upload_dialog.fn(state)

    # Assert
    assert state.upload_advanced_open is False
    assert state.upload_chunk_size == ""
    assert state.upload_chunk_overlap == ""
    assert state.upload_preset_separators == "markdown"
    assert state.upload_metadata == []


def test_should_reset_upload_settings_when_the_dialog_closes():
    # Arrange
    state = make_detail_state(
        upload_chunk_size="512",
        upload_metadata=[{"key": "a", "value": "1", "type": "text"}],
    )

    # Act
    CollectionDetailState.handle_upload_dialog_change.fn(state, False)

    # Assert
    assert state.upload_chunk_size == ""
    assert state.upload_metadata == []


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
