import json
import logging
import os
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from api.schemas.search import Searches
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def setup(client: TestClient):
    # Create a collection
    response = client.post_without_permissions(url=f"/v1{EndpointRoute.COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
    assert response.status_code == 201, response.text
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    data = {
        "collection": str(COLLECTION_ID),
        "output_format": "markdown",
        "force_ocr": "false",
        "chunk_size": "1000",
        "chunk_overlap": "200",
        "use_llm": "false",
        "paginate_output": "false",
        "chunker": "RecursiveCharacterTextSplitter",
        "chunk_min_size": "0",
        "is_separator_regex": "false",
        "metadata": json.dumps({"source_title": "test", "source_tags": ["tag-1", "tag-2"]}),
    }

    file_path = "api/tests/integ/assets/pdf.pdf"
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file, "application/pdf")}
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
        file.close()

    assert response.status_code == 201, response.text
    DOCUMENT_ID = response.json()["id"]

    time.sleep(1)

    yield COLLECTION_ID, DOCUMENT_ID


@pytest.mark.usefixtures("client", "setup")
class TestSearch:
    def test_search(self, client: TestClient, setup):
        """Test the POST /search response status code."""
        COLLECTION_ID, DOCUMENT_ID = setup

        data = {"prompt": "Qui est Albert ?", "collections": [COLLECTION_ID], "k": 3}
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text

        searches = Searches(**response.json())  # test output format

        search = searches.data[0]
        assert search.chunk.document_id == DOCUMENT_ID

    def test_search_with_score_threshold(self, client: TestClient, setup):
        """Test search with a score threshold."""
        COLLECTION_ID, DOCUMENT_ID = setup
        data = {"prompt": "Erasmus", "collections": [COLLECTION_ID], "k": 3, "score_threshold": 0.5}
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text

    def test_search_invalid_collection(self, client: TestClient, setup):
        """Test search with an invalid collection."""
        COLLECTION_ID, DOCUMENT_ID = setup
        data = {"prompt": "Erasmus", "collections": [100], "k": 3}
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 404, response.text

    def test_search_empty_prompt(self, client: TestClient, setup):
        """Test search with an empty prompt."""
        COLLECTION_ID, DOCUMENT_ID = setup
        data = {"prompt": "", "collections": [COLLECTION_ID], "k": 3}
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 422, response.text

    def test_search_access_other_user_collection(self, client: TestClient, setup):
        """Test search with the web search."""

        # create a private collection with a different user
        response = client.post_with_permissions(url=f"/v1{EndpointRoute.COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
        assert response.status_code == 201, response.text
        COLLECTION_ID = response.json()["id"]

        data = {"prompt": "What is the largest planet in our solar system?", "collections": [COLLECTION_ID], "k": 3}
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 404, response.text
