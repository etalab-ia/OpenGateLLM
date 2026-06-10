import pytest

from api.domain.embeddings.entities import CreateEmbeddingsBody


@pytest.fixture
def embeddings_body() -> CreateEmbeddingsBody:
    return CreateEmbeddingsBody(model="openweight-embeddings", input="hello")


class TestCreateEmbeddingsBodyGetPrompts:
    def test_returns_single_element_list_when_input_is_a_string(self, embeddings_body: CreateEmbeddingsBody):
        # Arrange
        embeddings_body.input = "q  d1 "

        # Act
        result = embeddings_body.get_prompts()

        # Assert
        assert result == ["q  d1 "]

    def test_returns_string_items_when_input_is_a_list_of_strings(self, embeddings_body: CreateEmbeddingsBody):
        # Arrange
        embeddings_body.input = ["q ", "d1  "]

        # Act
        result = embeddings_body.get_prompts()

        # Assert
        assert result == ["q ", "d1  "]

    def test_returns_string_items_when_input_is_a_list_of_integers(self, embeddings_body: CreateEmbeddingsBody):
        # Arrange
        embeddings_body.input = [1, 2, 3, 4, 5]

        # Act
        result = embeddings_body.get_prompts()

        # Assert
        assert result == ["1", "2", "3", "4", "5"]

    def test_returns_flattened_string_items_when_input_is_a_list_of_lists_of_integers(self, embeddings_body: CreateEmbeddingsBody):
        # Arrange
        embeddings_body.input = [[1, 2, 3], [4, 5, 6]]

        # Act
        result = embeddings_body.get_prompts()

        # Assert
        assert result == ["1", "2", "3", "4", "5", "6"]
