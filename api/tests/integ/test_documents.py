import json
import os
from time import sleep
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from api.schemas.chunks import Chunks
from api.schemas.collections import CollectionVisibility
from api.schemas.documents import Document, Documents
from api.utils.variables import EndpointRoute


@pytest.fixture(scope="module")
def collection(client):
    response = client.post_without_permissions(
        url=f"/v1{EndpointRoute.COLLECTIONS}",
        json={"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE},
    )
    assert response.status_code == 201, response.text
    collection_id = response.json()["id"]

    yield collection_id


@pytest.fixture(scope="function")
def document(client: TestClient, collection: int):
    file_path = "api/tests/integ/assets/pdf.pdf"
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file, "application/pdf")}
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data={"collection": str(collection)}, files=files)
        file.close()
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]
    yield document_id

    response = client.delete_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
    assert response.status_code == 204, response.text


@pytest.mark.usefixtures("client", "collection")
class TestDocuments:
    def test_upload_file_with_metadata(self, client: TestClient, collection):
        file_path = "api/tests/integ/assets/pdf.pdf"

        data = {  # with metadata
            "collection": str(collection),
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
            "metadata": json.dumps({"source_title": "test", "source_tags": ["tag-1", "tag-2"]}),
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()
        assert response.status_code == 201, response.text

        sleep(1)

        document_id = response.json()["id"]
        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 200, response.text
        document = Document(**response.json())
        assert document.id == document_id
        assert document.chunks > 0
        nb_chunks = document.chunks
        assert document.name == file_path.split("/")[-1]

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks", params={"limit": nb_chunks})
        assert response.status_code == 200, response.text

        chunks = response.json()
        chunks = Chunks(**chunks)  # test output format
        assert len(chunks.data) == nb_chunks
        assert chunks.data[0].collection_id == collection
        assert chunks.data[0].document_id == document_id
        assert chunks.data[0].content != ""
        assert chunks.data[0].metadata == {"source_title": "test", "source_tags": ["tag-1", "tag-2"]}

    def test_upload_file_with_overwrite_name(self, client: TestClient, collection):
        file_path = "api/tests/integ/assets/pdf.pdf"

        data = {  # with metadata
            "collection": str(collection),
            "name": "test_document.pdf",
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
            "metadata": json.dumps({"source_title": "test", "source_tags": ["tag-1", "tag-2"]}),
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()
        assert response.status_code == 201, response.text

        sleep(1)

        document_id = response.json()["id"]
        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 200, response.text
        document = Document(**response.json())
        assert document.id == document_id
        assert document.name == "test_document.pdf"
        assert document.chunks > 0

    def test_upload_file_disable_chunking(self, client: TestClient, collection):
        file_path = "api/tests/integ/assets/pdf.pdf"
        data = {
            "collection": str(collection),
            "disable_chunking": "true",
            "chunk_size": "10",
            "metadata": json.dumps({"source_title": "test", "source_tags": ["tag-1", "tag-2"]}),
        }
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.seek(0)
            file.close()
        assert response.status_code == 201, response.text

        sleep(1)

        document_id = response.json()["id"]
        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 200, response.text
        document = Document(**response.json())
        assert document.id == document_id
        assert document.chunks == 1

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks")
        assert response.status_code == 200, response.text
        chunks = response.json()
        chunks = Chunks(**chunks)  # test output format
        assert len(chunks.data) == 1
        assert chunks.data[0].content != ""
        assert chunks.data[0].metadata == {"source_title": "test", "source_tags": ["tag-1", "tag-2"]}

    def test_create_document_without_file(self, client: TestClient, collection):
        data = {
            "collection": str(collection),
            "name": "test_document.pdf",
            "metadata": json.dumps({"source_title": "test", "source_tags": ["tag-1", "tag-2"]}),
        }
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data)
        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 200, response.text
        document = Document(**response.json())
        assert document.id == document_id
        assert document.name == "test_document.pdf"
        assert document.chunks == 0

    def test_create_document_without_name_and_file(self, client: TestClient, collection):
        data = {
            "collection": str(collection),
            "metadata": json.dumps({"source_title": "test", "source_tags": ["tag-1", "tag-2"]}),
        }
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data)
        assert response.status_code == 422, response.text

    def test_post_document_empty_metadata(self, client: TestClient, collection):
        file_path = "api/tests/integ/assets/pdf.pdf"

        data = {  # with metadata
            "collection": str(collection),
            "output_format": "markdown",
            "force_ocr": "false",
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "use_llm": "false",
            "paginate_output": "false",
            "chunker": "RecursiveCharacterTextSplitter",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

        data["metadata"] = ""

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

        data["metadata"] = None

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text

        data["metadata"] = "{}"

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 422, response.text

    def test_post_document_invalid_metadata_malformed(self, client: TestClient, collection):
        file_path = "api/tests/integ/assets/pdf.pdf"

        data = {  # with metadata
            "collection": str(collection),
            "output_format": "markdown",
            "force_ocr": "false",
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "use_llm": "false",
            "paginate_output": "false",
            "chunker": "RecursiveCharacterTextSplitter",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
            "metadata": "{test}",
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 422, response.text

    def test_post_document_invalid_metadata_str_too_long(self, client: TestClient, collection):
        file_path = "api/tests/integ/assets/pdf.pdf"

        data = {  # with metadata
            "collection": str(collection),
            "output_format": "markdown",
            "force_ocr": "false",
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "use_llm": "false",
            "paginate_output": "false",
            "chunker": "RecursiveCharacterTextSplitter",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
            "metadata": json.dumps({"source_title": "o" * 300}),
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 422, response.text

    def test_get_documents(self, client: TestClient, collection):
        # Create document
        file_path = "api/tests/integ/assets/pdf.pdf"

        data = {  # with empty metadata
            "collection": str(collection),
            "output_format": "markdown",
            "force_ocr": "false",
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "use_llm": "false",
            "paginate_output": "false",
            "chunker": "RecursiveCharacterTextSplitter",
            "length_function": "len",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}")
        assert response.status_code == 200, response.text

        documents = response.json()
        Documents(**documents)  # test output format

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", params={"collection": collection})
        assert response.status_code == 200, response.text

        documents = response.json()
        Documents(**documents)  # test output format

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 200, response.text

        document = response.json()
        Document(**document)  # test output format

    def test_delete_document(self, client: TestClient, collection):
        # Create document
        file_path = "api/tests/integ/assets/pdf.pdf"

        data = {  # without metadata
            "collection": str(collection),
            "output_format": "markdown",
            "force_ocr": "false",
            "chunk_size": "1000",
            "chunk_overlap": "200",
            "use_llm": "false",
            "paginate_output": "false",
            "chunker": "RecursiveCharacterTextSplitter",
            "length_function": "len",
            "chunk_min_size": "0",
            "is_separator_regex": "false",
        }

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()

        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        response = client.delete_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 204, response.text

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 404, response.text

    def test_create_chunks_into_empty_document(self, client: TestClient, collection):
        data = {
            "collection": str(collection),
            "name": "test_document.pdf",
            "metadata": json.dumps({"source_title": "test", "source_tags": ["tag-1", "tag-2"]}),
        }
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data)
        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        response = client.post_without_permissions(
            url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks",
            json={
                "chunks": [
                    {"content": "test_1", "metadata": {"source_title": "test_1", "source_tags": ["tag-1", "tag-2"]}},
                    {"content": "test_2", "metadata": {"source_title": "test_2", "source_tags": ["tag-1", "tag-2"]}},
                ]
            },
        )
        assert response.status_code == 201, response.text
        assert len(response.json()["ids"]) == 2
        assert response.json()["document_id"] == document_id
        assert response.json()["ids"][0] == 0
        assert response.json()["ids"][1] == 1

        sleep(1)

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 200, response.text
        document = Document(**response.json())
        assert document.id == document_id
        assert document.name == "test_document.pdf"
        assert document.chunks == 2

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks")
        assert response.status_code == 200, response.text
        chunks = response.json()
        chunks = Chunks(**chunks)  # test output format
        assert len(chunks.data) == 2
        assert chunks.data[0].collection_id == collection
        assert chunks.data[0].document_id == document_id
        assert chunks.data[0].content == "test_1"
        assert chunks.data[0].metadata == {"source_title": "test_1", "source_tags": ["tag-1", "tag-2"]}
        assert chunks.data[1].content == "test_2"
        assert chunks.data[1].metadata == {"source_title": "test_2", "source_tags": ["tag-1", "tag-2"]}

    def test_create_chunks_into_document_with_content(self, client: TestClient, collection):
        file_path = "api/tests/integ/assets/pdf.pdf"
        data = {
            "collection": str(collection),
            "name": "test_document.pdf",
        }
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/pdf")}
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
            file.close()
        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        sleep(1)

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 200, response.text
        document = Document(**response.json())
        assert document.id == document_id
        nb_chunks = document.chunks

        sleep(1)

        response = client.post_without_permissions(
            url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks",
            json={
                "chunks": [
                    {"content": "test_1", "metadata": {"source_title": "test_1", "source_tags": ["tag-1", "tag-2"]}},
                    {"content": "test_2", "metadata": {"source_title": "test_2", "source_tags": ["tag-1", "tag-2"]}},
                ]
            },
        )
        assert response.status_code == 201, response.text
        assert len(response.json()["ids"]) == 2
        assert response.json()["document_id"] == document_id

        sleep(1)

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
        assert response.status_code == 200, response.text
        document = Document(**response.json())
        assert document.id == document_id
        assert document.chunks == nb_chunks + 2

        response = client.get_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks", params={"limit": nb_chunks + 2})
        assert response.status_code == 200, response.text
        chunks = response.json()
        chunks = Chunks(**chunks)  # test output format
        assert len(chunks.data) == nb_chunks + 2
        assert chunks.data[-1].id == nb_chunks + 1
        assert chunks.data[-1].collection_id == collection
        assert chunks.data[-1].document_id == document_id

    def test_create_into_non_existent_document(self, client: TestClient, collection):
        response = client.post_without_permissions(
            url=f"/v1{EndpointRoute.DOCUMENTS}/1000/chunks",
            json={"chunks": [{"content": "test", "metadata": {"source_title": "test", "source_tags": ["tag-1", "tag-2"]}}]},
        )
        assert response.status_code == 404, response.text
