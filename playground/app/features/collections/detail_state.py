import json
from pathlib import Path

import httpx
import reflex as rx

from app.features.collections.models import Chunk, Collection, Document
from app.features.collections.state import CollectionsState
from app.shared.components.toasts import httpx_error_toast
from app.shared.utils.timestamps import format_datetime

COLLECTION_UPLOAD_ID = "collection-document-upload"
MAX_DOCUMENT_SIZE = 20_000_000
SUPPORTED_UPLOAD_TYPES = {
    "application/pdf": [".pdf"],
    "text/html": [".html", ".htm"],
    "text/markdown": [".md", ".markdown"],
    "text/plain": [".txt"],
}
SUPPORTED_UPLOAD_EXTENSIONS = {extension for extensions in SUPPORTED_UPLOAD_TYPES.values() for extension in extensions}


class CollectionDetailState(CollectionsState):
    """Manage documents and inspect chunks for one collection."""

    detail_collection: Collection = Collection()
    detail_loading: bool = False
    detail_error: str = ""

    documents: list[Document] = []
    documents_loading: bool = False
    documents_error: str = ""
    document_page: int = 1
    documents_per_page: int = 10
    documents_has_next_page: bool = False

    is_upload_dialog_open: bool = False
    upload_loading: bool = False
    upload_error: str = ""
    upload_status: str = ""

    document_to_delete: Document = Document()

    selected_document: Document = Document()
    chunks: list[Chunk] = []
    chunks_loading: bool = False
    chunks_error: str = ""
    chunk_page: int = 1
    chunks_per_page: int = 5
    chunks_has_next_page: bool = False

    @rx.var
    def is_delete_document_dialog_open(self) -> bool:
        return self.document_to_delete.id is not None

    @rx.var
    def is_chunk_dialog_open(self) -> bool:
        return self.selected_document.id is not None

    def _can_manage_collection(self) -> bool:
        return self.detail_collection.id is not None and self.detail_collection.is_owner and self.detail_collection.owner == self.user_id

    def _detail_error_message(self, response: httpx.Response | None, resource: str) -> str:
        if response is None:
            return f"{resource} could not be loaded. Check your connection and try again."
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if detail:
            return str(detail)
        return f"{resource} could not be loaded (HTTP {response.status_code}). Try again."

    def _upload_error_message(self, response: httpx.Response | None) -> str:
        if response is None:
            return "The document could not be uploaded or indexed. Check your connection and try again."
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if detail:
            return str(detail)
        return f"The document could not be uploaded or indexed (HTTP {response.status_code})."

    def _format_document(self, document: dict) -> Document:
        return Document(
            id=document["id"],
            name=document["name"],
            collection_id=document["collection_id"],
            created=format_datetime(document["created"]),
            chunks=document.get("chunks", 0),
            size=document.get("size", 0),
        )

    def _format_chunk(self, chunk: dict) -> Chunk:
        metadata = chunk.get("metadata") or {}
        page_number = metadata.get("page_number")
        if type(page_number) is not int or page_number < 1:
            page_number = None
        return Chunk(
            id=chunk["id"],
            collection_id=chunk["collection_id"],
            document_id=chunk["document_id"],
            content=chunk["content"],
            metadata=metadata,
            metadata_json=json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
            page_number=page_number,
            created=format_datetime(chunk["created"]),
        )

    @rx.event
    async def load_collection_detail(self, reset_page: bool = True):
        if not self.is_authenticated or not self.api_key:
            return
        try:
            collection_id = int(self.collection_id)
            if collection_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            self.detail_collection = Collection()
            self.documents = []
            self.detail_error = "This collection link is invalid."
            self.detail_loading = False
            return

        if reset_page:
            self.document_page = 1
            self.detail_collection = Collection()
            self.documents = []
            self.selected_document = Document()
            self.chunks = []
            self.is_upload_dialog_open = False
        self.detail_error = ""
        self.documents_error = ""
        self.detail_loading = True
        yield

        collection_loaded = False
        response = None
        try:
            response = await self._request("GET", f"/v1/collections/{collection_id}")
            response.raise_for_status()
            self.detail_collection = self._format_collection(response.json())
            collection_loaded = True
        except Exception as e:
            self.detail_collection = Collection()
            self.documents = []
            self.documents_has_next_page = False
            self.detail_error = self._detail_error_message(response, "Collection")
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.detail_loading = False
            yield

        if collection_loaded:
            async for event in self.load_documents():
                yield event

    @rx.event
    async def refresh_collection_detail(self):
        async for event in self.load_collection_detail(reset_page=False):
            yield event

    @rx.event
    async def load_documents(self):
        if not self.is_authenticated or not self.api_key or self.detail_collection.id is None:
            return

        self.documents_loading = True
        self.documents_error = ""
        yield

        response = None
        try:
            response = await self._request(
                "GET",
                "/v1/documents",
                params={
                    "collection_id": self.detail_collection.id,
                    "offset": (self.document_page - 1) * self.documents_per_page,
                    "limit": self.documents_per_page + 1,
                    "order_by": "created",
                    "order_direction": "desc",
                },
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            self.documents_has_next_page = len(data) > self.documents_per_page
            self.documents = [self._format_document(item) for item in data[: self.documents_per_page]]
        except Exception as e:
            self.documents = []
            self.documents_has_next_page = False
            self.documents_error = self._detail_error_message(response, "Documents")
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.documents_loading = False
            yield

    @rx.event
    async def previous_documents_page(self):
        if self.document_page > 1:
            self.document_page -= 1
            async for event in self.load_documents():
                yield event

    @rx.event
    async def next_documents_page(self):
        if self.documents_has_next_page:
            self.document_page += 1
            async for event in self.load_documents():
                yield event

    @rx.event
    def open_upload_dialog(self):
        if not self._can_manage_collection():
            return rx.toast.error("Only the collection owner can upload documents", position="bottom-right")
        self.upload_error = ""
        self.upload_status = ""
        self.is_upload_dialog_open = True
        return rx.clear_selected_files(COLLECTION_UPLOAD_ID)

    @rx.event
    def handle_upload_dialog_change(self, is_open: bool):
        if self.upload_loading:
            return None
        self.is_upload_dialog_open = is_open
        if not is_open:
            self.upload_error = ""
            return rx.clear_selected_files(COLLECTION_UPLOAD_ID)
        return None

    @rx.event
    async def upload_documents(self, files: list[rx.UploadFile]):
        if not self._can_manage_collection():
            yield rx.toast.error("Only the collection owner can upload documents", position="bottom-right")
            return
        if not files:
            yield rx.toast.warning("Select at least one file", position="bottom-right")
            return

        self.upload_loading = True
        self.upload_error = ""
        yield

        uploaded_count = 0
        errors = []
        for index, file in enumerate(files, start=1):
            filename = file.filename or "unnamed file"
            self.upload_status = f"Uploading and indexing {filename} ({index}/{len(files)})"
            yield

            if Path(filename).suffix.lower() not in SUPPORTED_UPLOAD_EXTENSIONS:
                errors.append(f"{filename}: supported formats are PDF, HTML, Markdown and TXT.")
                continue
            if file.size is not None and file.size > MAX_DOCUMENT_SIZE:
                errors.append(f"{filename}: file size limit exceeded (max: {MAX_DOCUMENT_SIZE} bytes).")
                continue

            response = None
            try:
                content = await file.read()
                if len(content) > MAX_DOCUMENT_SIZE:
                    errors.append(f"{filename}: file size limit exceeded (max: {MAX_DOCUMENT_SIZE} bytes).")
                    continue
                if not content:
                    errors.append(f"{filename}: the file is empty.")
                    continue

                response = await self._request(
                    "POST",
                    "/v1/documents",
                    data={"collection_id": str(self.detail_collection.id)},
                    files={"file": (filename, content, file.headers.get("content-type") or "application/octet-stream")},
                )
                response.raise_for_status()
                uploaded_count += 1
            except Exception:
                errors.append(f"{filename}: {self._upload_error_message(response)}")

        if errors:
            self.upload_error = "\n".join(errors)
            if uploaded_count:
                yield rx.toast.warning(f"{uploaded_count} document(s) uploaded and indexed; {len(errors)} failed", position="bottom-right")
            else:
                yield rx.toast.error("No documents were uploaded and indexed", position="bottom-right")
        else:
            self.is_upload_dialog_open = False
            yield rx.toast.success(f"{uploaded_count} document(s) uploaded and indexed", position="bottom-right")

        yield rx.clear_selected_files(COLLECTION_UPLOAD_ID)
        if uploaded_count:
            async for event in self.load_collection_detail(reset_page=False):
                yield event
        self.upload_loading = False
        self.upload_status = ""
        yield

    @rx.event
    def set_document_to_delete(self, document: Document):
        if self._can_manage_collection() and document.collection_id == self.detail_collection.id:
            self.document_to_delete = document

    @rx.event
    def handle_delete_document_dialog_change(self, is_open: bool):
        if not is_open and not self.delete_entity_loading:
            self.document_to_delete = Document()

    @rx.event
    async def delete_document(self):
        if not self._can_manage_collection() or self.document_to_delete.collection_id != self.detail_collection.id:
            yield rx.toast.error("Only the collection owner can delete documents", position="bottom-right")
            return

        self.delete_entity_loading = True
        yield

        response = None
        try:
            response = await self._request("DELETE", f"/v1/documents/{self.document_to_delete.id}")
            response.raise_for_status()
            self.document_to_delete = Document()
            if len(self.documents) == 1 and self.document_page > 1:
                self.document_page -= 1
            yield rx.toast.success("Document deleted", position="bottom-right")
            async for event in self.load_collection_detail(reset_page=False):
                yield event
        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.delete_entity_loading = False
            yield

    @rx.event
    async def open_chunk_inspector(self, document: Document):
        if document.collection_id != self.detail_collection.id:
            return
        self.selected_document = document
        self.chunks = []
        self.chunks_error = ""
        self.chunk_page = 1
        async for event in self.load_chunks():
            yield event

    @rx.event
    def handle_chunk_dialog_change(self, is_open: bool):
        if not is_open and not self.chunks_loading:
            self.selected_document = Document()
            self.chunks = []
            self.chunks_error = ""

    @rx.event
    async def load_chunks(self):
        if not self.is_authenticated or not self.api_key or self.selected_document.id is None:
            return

        self.chunks_loading = True
        self.chunks_error = ""
        yield

        response = None
        try:
            response = await self._request(
                "GET",
                f"/v1/documents/{self.selected_document.id}/chunks",
                params={
                    "offset": (self.chunk_page - 1) * self.chunks_per_page,
                    "limit": self.chunks_per_page + 1,
                },
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            self.chunks_has_next_page = len(data) > self.chunks_per_page
            self.chunks = [self._format_chunk(item) for item in data[: self.chunks_per_page]]
        except Exception as e:
            self.chunks = []
            self.chunks_has_next_page = False
            self.chunks_error = self._detail_error_message(response, "Chunks")
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.chunks_loading = False
            yield

    @rx.event
    async def previous_chunks_page(self):
        if self.chunk_page > 1:
            self.chunk_page -= 1
            async for event in self.load_chunks():
                yield event

    @rx.event
    async def next_chunks_page(self):
        if self.chunks_has_next_page:
            self.chunk_page += 1
            async for event in self.load_chunks():
                yield event
