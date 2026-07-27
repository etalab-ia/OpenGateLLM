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

    def test_returns_messages_content_when_input_is_none(self, embeddings_body: CreateEmbeddingsBody):
        # Arrange
        embeddings_body = CreateEmbeddingsBody(
            model=embeddings_body.model,
            input=None,
            messages=[
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user prompt"},
            ],
        )

        # Act
        result = embeddings_body.get_prompts()

        # Assert
        assert result == ["system prompt", "user prompt"]

    def test_returns_only_text_parts_from_multimodal_messages_when_input_is_none(self, embeddings_body: CreateEmbeddingsBody):
        # Arrange
        embeddings_body = CreateEmbeddingsBody(
            model=embeddings_body.model,
            input=None,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
                        {"type": "text", "text": "Describe this image"},
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Image description"},
                    ],
                },
            ],
        )

        # Act
        result = embeddings_body.get_prompts()

        # Assert
        assert result == ["Describe this image", "Image description"]

    def test_returns_empty_list_when_input_and_messages_are_missing(self, embeddings_body: CreateEmbeddingsBody):
        # Arrange
        embeddings_body = CreateEmbeddingsBody(model=embeddings_body.model, input=None, messages=None)

        # Act
        result = embeddings_body.get_prompts()

        # Assert
        assert result == []
