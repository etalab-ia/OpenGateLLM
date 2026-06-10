import pytest

from api.domain.rerank.entities import CreateRerankBody


@pytest.fixture
def rerank_body() -> CreateRerankBody:
    return CreateRerankBody(query="query", documents=["document1"], model="openweight-rerank", top_n=None)


class TestCreateRerankBodyGetPrompts:
    def test_returns_query_followed_by_documents(self, rerank_body: CreateRerankBody):
        # Arrange
        rerank_body.query = "query"
        rerank_body.documents = ["document1", "document2 "]

        # Act
        result = rerank_body.get_prompts()

        # Assert
        assert result == ["query", "document1", "document2 "]

    def test_returns_query_only_when_documents_is_empty(self, rerank_body: CreateRerankBody):
        # Arrange
        rerank_body.query = "query"
        rerank_body.documents = []

        # Act
        result = rerank_body.get_prompts()

        # Assert
        assert result == ["query"]

    def test_preserves_whitespace_in_query_and_documents(self, rerank_body: CreateRerankBody):
        # Arrange
        rerank_body.query = "q "
        rerank_body.documents = ["d1  ", " d2"]

        # Act
        result = rerank_body.get_prompts()

        # Assert
        assert result == ["q ", "d1  ", " d2"]
