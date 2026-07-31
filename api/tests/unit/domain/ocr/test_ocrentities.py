from api.domain.ocr.entities import OCR, CreateOCRBody, OCRDocumentURLChunk, OCRImageURL, OCRImageURLChunk, OCRPageObject


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


class TestOCRGetCompletions:
    def test_returns_markdown_from_pages(self):
        # Arrange
        ocr = OCR(
            pages=[
                OCRPageObject(index=0, images=[], markdown="# Page 1"),
                OCRPageObject(index=1, images=[], markdown="# Page 2"),
            ],
        )

        # Act
        result = ocr.get_completions()

        # Assert
        assert result == ["# Page 1", "# Page 2"]

    def test_skips_pages_without_markdown(self):
        # Arrange
        ocr = OCR(
            pages=[
                OCRPageObject(index=0, images=[], markdown="# Page 1"),
                OCRPageObject(index=1, images=[], markdown=None),
                OCRPageObject(index=2, images=[], markdown=""),
            ],
        )

        # Act
        result = ocr.get_completions()

        # Assert
        assert result == ["# Page 1"]

    def test_appends_document_annotation(self):
        # Arrange
        ocr = OCR(
            document_annotation='{"invoice_number": "42"}',
            pages=[OCRPageObject(index=0, images=[], markdown="# Document")],
        )

        # Act
        result = ocr.get_completions()

        # Assert
        assert result == ["# Document", '{"invoice_number": "42"}']

    def test_returns_only_document_annotation_when_pages_have_no_markdown(self):
        # Arrange
        ocr = OCR(
            document_annotation='{"invoice_number": "42"}',
            pages=[OCRPageObject(index=0, images=[], markdown=None)],
        )

        # Act
        result = ocr.get_completions()

        # Assert
        assert result == ['{"invoice_number": "42"}']

    def test_returns_empty_list_when_no_markdown_and_no_annotation(self):
        # Arrange
        ocr = OCR(pages=[OCRPageObject(index=0, images=[], markdown=None)])

        # Act
        result = ocr.get_completions()

        # Assert
        assert result == []
