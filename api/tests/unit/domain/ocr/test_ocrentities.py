from api.domain.ocr.entities import CreateOCRBody, OCRDocumentURLChunk, OCRImageURL, OCRImageURLChunk


class TestCreateOCRBodyGetPrompts:
    def test_returns_empty_list_for_document_url(self):
        # Arrange
        body = CreateOCRBody(
            document=OCRDocumentURLChunk(document_url="https://example.com/document.pdf"),
            model="ocr-router",
        )

        # Act
        result = body.get_prompts()

        # Assert
        assert result == []

    def test_returns_empty_list_even_when_document_annotation_prompt_is_set(self):
        # Arrange
        body = CreateOCRBody(
            document=OCRImageURLChunk(image_url=OCRImageURL(url="https://example.com/image.png")),
            model="ocr-router",
            document_annotation_prompt="Extract the invoice number.",
        )

        # Act
        result = body.get_prompts()

        # Assert
        assert result == ["Extract the invoice number."]
