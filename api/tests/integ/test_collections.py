import os
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from api.schemas.collections import Collection, Collections, CollectionVisibility
from api.utils.variables import ENDPOINT__COLLECTIONS

# Path to test assets
current_path = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(current_path, "assets")


@pytest.mark.usefixtures("client")
class TestCollections:
    def test_create_private_collection(self, client: TestClient):
        data = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        assert response.status_code == 200, response.text

        collections = response.json()
        Collections(**collections)  # test output format

        collections = [collection for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 1

        collection = collections[0]
        assert collection["name"] == data["name"]
        assert collection["visibility"] == CollectionVisibility.PRIVATE

    def test_get_one_collection(self, client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["name"] == collection_name

    def test_patch_collection_name(self, client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]
        new_collection_name = f"test_collection_{str(uuid4())}"
        data = {"name": new_collection_name}
        response = client.patch_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}", data=data)
        assert response.status_code == 200, response.text

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["name"] == new_collection_name

    def test_format_collection(self, client: TestClient):
        data = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text
        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        assert response.status_code == 200, response.text

        collections = response.json()
        Collections(**collections)  # test output format

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        Collection(**collection)  # test output format

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        Collection(**collection)  # test output format

    def test_create_public_collection_without_permissions(self, client: TestClient):
        data = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PUBLIC.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 403, response.text

    def test_patch_public_collection_without_permissions(self, client: TestClient):
        data = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PUBLIC.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 403, response.text

    def test_create_public_collection_with_permissions(self, client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC.value}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        assert response.status_code == 200, response.text

        collections = response.json()
        collections = [collection for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 1

        collection = collections[0]
        assert collection["name"] == collection_name
        assert collection["visibility"] == CollectionVisibility.PUBLIC

    def test_patch_public_collection_with_permissions(self, client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        data = {"visibility": CollectionVisibility.PUBLIC.value}
        response = client.patch_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}", data=data)
        assert response.status_code == 200, response.text

    def test_view_collection_of_other_user(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 404, response.text

    def test_view_public_collection_of_other_user(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC.value}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

    def test_delete_private_collection_without_permissions(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.delete_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 204

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        collections = response.json()
        assert response.status_code == 200, response.text

        collections = [collection for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 0

    def test_delete_public_collection_without_permissions(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC.value}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        collections = response.json()
        assert response.status_code == 200, response.text

        response = client.delete_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 404, response.text

    def test_delete_public_collection_with_permissions(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC.value}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.delete_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 204, response.text

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        collections = response.json()
        assert response.status_code == 200, response.text

        collections = [collection["id"] for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 0

    def test_create_collection_with_empty_name(self, client: TestClient):
        collection_name = " "
        data = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 422, response.text

    def test_create_collection_with_description(self, client: TestClient):
        data = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE.value, "description": "test-description"}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()

        assert collection["description"] == data["description"]

    def test_update_collection_updated_at(self, client: TestClient):
        data = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["updated_at"] is not None
        updated_at = collection["updated_at"]

        time.sleep(1)

        response = client.patch_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}", data={"description": "test-description"})
        assert response.status_code == 200, response.text

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["updated_at"] is not None
        assert collection["updated_at"] > updated_at

    def test_create_collection_with_parquet_file(self, client: TestClient):
        """Test creating a collection with an initial Parquet file upload, including metadata columns."""
        file_path = os.path.join(current_path, "assets/parquet.parquet")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/octet-stream")}
            collection_name = f"test_collection_{str(uuid4())}"
            response = client.post_without_permissions(
                url=f"/v1{ENDPOINT__COLLECTIONS}",
                data={"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value},
                files=files,
            )

        assert response.status_code == 201, response.text
        data = response.json()
        assert "id" in data
        assert "details" in data

    def test_put_collection_with_parquet_file(self, client: TestClient):
        """Test force updating a collection with PUT endpoint."""
        # Create collection first
        collection_name = f"test_collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text
        collection_id = response.json()["id"]

        # Upload parquet file
        file_path = os.path.join(current_path, "assets/parquet.parquet")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/octet-stream")}
            response = client.put_without_permissions(
                url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}",
                data={},
                files=files,
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert "updated" in data
        assert "details" in data

    def test_patch_collection_metadata_and_file(self, client: TestClient):
        """Test updating both metadata and documents with different file scenarios."""
        # Create collection
        collection_name = f"test_collection_{str(uuid4())}"
        data = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", data=data)
        assert response.status_code == 201, response.text
        collection_id = response.json()["id"]

        # First upload: valid parquet file with metadata update
        file_path = os.path.join(current_path, "assets/parquet.parquet")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/octet-stream")}
            new_name = f"test_collection_{str(uuid4())}"
            response = client.patch_without_permissions(
                url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}",
                data={"name": new_name, "description": "Updated description"},
                files=files,
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert "updated" in data
        assert "documents" in data["updated"]

        # Verify metadata was updated
        get_response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert get_response.status_code == 200
        collection = get_response.json()
        assert collection["name"] == new_name
        assert collection["description"] == "Updated description"

        # Second upload: same file again (should detect no changes)
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/octet-stream")}
            response = client.patch_without_permissions(
                url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}",
                data={},
                files=files,
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert "updated" in data
        assert "documents" in data["updated"]
        assert "details" in data

        # Verify no changes occurred (identical file)
        details = data["details"]
        assert details["added_documents"] == 0, f"Expected 0 added documents, got {details['added_documents']}"
        assert details["updated_documents"] == 0, f"Expected 0 updated documents, got {details['updated_documents']}"
        assert details["deleted_documents"] == 0, f"Expected 0 deleted documents, got {details['deleted_documents']}"
        assert details["total_chunks_processed"] == 0, f"Expected 0 chunks processed, got {details['total_chunks_processed']}"

        # Third upload: updated version of the parquet file
        updated_file_path = os.path.join(current_path, "assets/updated_parquet.parquet")
        with open(updated_file_path, "rb") as file:
            files = {"file": (os.path.basename(updated_file_path), file, "application/octet-stream")}
            response = client.patch_without_permissions(
                url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}",
                data={},  # No metadata changes this time
                files=files,
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert "updated" in data
        assert "documents" in data["updated"]
        assert "details" in data

        # Verify the expected changes
        details = data["details"]
        assert details["added_documents"] == 1, f"Expected 1 added document, got {details['added_documents']}"
        assert details["updated_documents"] == 1, f"Expected 1 updated document, got {details['updated_documents']}"
        assert details["deleted_documents"] == 0, f"Expected 0 deleted documents, got {details['deleted_documents']}"
        assert details["total_chunks_processed"] == 3, f"Expected 3 chunks processed, got {details['total_chunks_processed']}"

    def test_parquet_missing_required_columns(self, client: TestClient):
        """Test that parquet files missing required columns are rejected."""
        file_path = os.path.join(current_path, "assets/parquet_wrong_format.parquet")
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "application/octet-stream")}
            collection_name = f"test_collection_{str(uuid4())}"
            response = client.post_without_permissions(
                url=f"/v1{ENDPOINT__COLLECTIONS}",
                data={"name": collection_name, "visibility": CollectionVisibility.PRIVATE.value},
                files=files,
            )

        assert response.status_code == 422, response.text
