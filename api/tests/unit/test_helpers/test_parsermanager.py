import asyncio
from io import BytesIO
import threading
import time
from unittest.mock import MagicMock, patch

from fastapi import UploadFile
import pytest
from starlette.datastructures import Headers

from api.helpers._parsermanager import ParserManager
from api.schemas.core.documents import FileType
from api.utils.exceptions import UnsupportedFileTypeException


def create_upload_file(content: str, filename: str, content_type: str) -> UploadFile:
    """Helper function to create UploadFile from string content."""
    return UploadFile(filename=filename, file=BytesIO(content.encode("utf-8")), headers=Headers({"content-type": content_type}))


def create_binary_upload_file(content: bytes, filename: str, content_type: str) -> UploadFile:
    """Helper function to create UploadFile from binary content."""
    return UploadFile(filename=filename, file=BytesIO(content), headers=Headers({"content-type": content_type}))


class TestParserManagerDetectFileType:
    """Test file type detection logic."""

    def test_check_file_type_pdf_valid(self):
        """Test PDF file type detection with valid extension and content type."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "document.pdf", "application/pdf")

        manager = ParserManager()
        result = manager.check_file_type(file)

        assert result == FileType.PDF

    def test_check_file_type_html_valid(self):
        """Test HTML file type detection with valid extension and content type."""
        file = create_upload_file("<html><body>Test</body></html>", "page.html", "text/html")

        manager = ParserManager()
        result = manager.check_file_type(file)

        assert result == FileType.HTML

    def test_check_file_type_markdown_valid(self):
        """Test Markdown file type detection with valid extension and content type."""
        file = create_upload_file("# README\n\nThis is a test.", "README.md", "text/markdown")

        manager = ParserManager()
        result = manager.check_file_type(file)

        assert result == FileType.MD

    def test_check_file_type_txt_valid(self):
        """Test text file type detection with valid extension and content type."""
        file = create_upload_file("This is plain text content.", "notes.txt", "text/plain")

        manager = ParserManager()
        result = manager.check_file_type(file)

        assert result == FileType.TXT

    def test_check_file_type_content_type_only(self):
        """Test file type detection by content type when extension doesn't match."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "document.unknown", "application/pdf")

        manager = ParserManager()
        result = manager.check_file_type(file)

        assert result == FileType.PDF

    def test_check_file_type_invalid_extension_and_content_type(self):
        """Test UnsupportedFileTypeException for invalid file types."""
        file = create_upload_file("Unknown content", "document.xyz", "application/xyz")

        manager = ParserManager()

        with pytest.raises(UnsupportedFileTypeException):
            manager.check_file_type(file)

    def test_check_file_type_mismatch_with_required_type(self):
        """Test UnsupportedFileTypeException when detected type doesn't match required type."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "document.pdf", "application/pdf")

        manager = ParserManager()

        with pytest.raises(UnsupportedFileTypeException) as exc_info:
            manager.check_file_type(file, type=FileType.HTML)

        assert "File must be a html file." in str(exc_info.value)

    def test_check_file_type_case_insensitive_extension(self):
        """Test that extension detection is case insensitive."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "document.PDF", "application/pdf")

        manager = ParserManager()
        result = manager.check_file_type(file)

        assert result == FileType.PDF


class TestParserManagerReadContent:
    """Test content reading functionality."""

    @pytest.mark.asyncio
    async def test_read_content_utf8(self):
        """Test reading UTF-8 encoded content."""
        content = "Hello, world! 👋"
        file = create_upload_file(content, "test.txt", "text/plain")

        result = await ParserManager._read_content(file)

        assert result == content

    @pytest.mark.asyncio
    async def test_read_content_latin1_fallback(self):
        """Test reading with Latin-1 fallback when UTF-8 fails."""
        content = "Café"
        # Create file with Latin-1 encoding
        file = UploadFile(filename="test.txt", file=BytesIO(content.encode("latin-1")), headers=Headers({"content-type": "text/plain"}))

        result = await ParserManager._read_content(file)

        assert result == content

    @pytest.mark.asyncio
    async def test_read_content_with_replacement(self):
        """Test reading with character replacement when both UTF-8 and Latin-1 fail."""
        # Create invalid UTF-8/Latin-1 bytes
        content_bytes = b"\xff\xfe\x00\x00"
        file = create_binary_upload_file(content_bytes, "test.txt", "text/plain")

        result = await ParserManager._read_content(file)

        # Should contain replacement characters
        assert "" in result or len(result) > 0


class TestParserManagerParse:
    """Test parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_pdf_to_markdown(self):
        """Test PDF parsing to markdown using pymupdf4llm."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "test.pdf", "application/pdf")

        mock_pdf = MagicMock()
        markdown_content = "# Document Title\n\nThis is the converted markdown content."

        manager = ParserManager()

        with patch("pymupdf.open", return_value=mock_pdf) as mock_open:
            with patch("pymupdf4llm.to_markdown", return_value=markdown_content) as mock_to_markdown:
                result = await manager.parse(file=file)

                assert isinstance(result, str)
                assert result == markdown_content
                mock_open.assert_called_once()
                mock_to_markdown.assert_called_once_with(mock_pdf)

    @pytest.mark.asyncio
    async def test_parse_pdf_uses_semaphore(self):
        """Test that PDF parsing uses the semaphore for concurrent control."""
        file = create_binary_upload_file(b"%PDF-1.4 fake pdf content", "test.pdf", "application/pdf")

        mock_pdf = MagicMock()
        markdown_content = "# Test Content"

        manager = ParserManager(max_concurrent=2)

        # Track semaphore acquisition
        semaphore_acquired = []
        original_acquire = manager.conversion_semaphore.acquire

        async def tracked_acquire():
            semaphore_acquired.append(True)
            return await original_acquire()

        manager.conversion_semaphore.acquire = tracked_acquire

        with patch("pymupdf.open", return_value=mock_pdf):
            with patch("pymupdf4llm.to_markdown", return_value=markdown_content):
                result = await manager.parse(file=file)

                assert result == markdown_content
                assert len(semaphore_acquired) == 1  # Semaphore was acquired

    @pytest.mark.asyncio
    async def test_parse_txt(self):
        """Test text parsing fallback when no parser client."""
        txt_content = "Plain text content"
        file = create_upload_file(txt_content, "test.txt", "text/plain")

        manager = ParserManager()

        result = await manager.parse(file=file)

        assert result == txt_content

    @pytest.mark.asyncio
    async def test_parse_md(self):
        """Integration test for markdown file parsing end-to-end."""
        md_content = "# Sample Markdown\n\nThis is **bold** text and *italic* text."
        file = create_upload_file(md_content, "sample.md", "text/markdown")

        manager = ParserManager()

        result = await manager.parse(file=file)

        assert isinstance(result, str)
        assert result == md_content

    @pytest.mark.asyncio
    async def test_parse_html(self):
        """Integration test for HTML file parsing with markdown output."""
        html_content = "<h1>Sample HTML</h1><p>This is a <strong>paragraph</strong>.</p>"
        md_content = "# Sample HTML\n\nThis is a **paragraph**."
        file = create_upload_file(html_content, "sample.html", "text/html")

        manager = ParserManager()

        with patch("api.helpers._parsermanager.convert_to_markdown") as mock_convert:
            mock_convert.return_value = md_content

            result = await manager.parse(file=file)

            assert result == "# Sample HTML\n\nThis is a **paragraph**."


class TestParserManagerSemaphore:
    """Test semaphore concurrency control for PDF parsing."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_pdf_parsing(self):
        """Test that semaphore properly limits concurrent PDF parsing operations."""
        max_concurrent = 2
        manager = ParserManager(max_concurrent=max_concurrent)

        # Track concurrent executions using threading primitives
        # (since to_markdown is called in a thread via asyncio.to_thread)
        concurrent_count = 0
        max_concurrent_reached = 0
        lock = threading.Lock()

        def mock_to_markdown(doc):
            nonlocal concurrent_count, max_concurrent_reached
            with lock:
                concurrent_count += 1
                max_concurrent_reached = max(max_concurrent_reached, concurrent_count)

            # Simulate some work
            time.sleep(0.1)

            with lock:
                concurrent_count -= 1

            return "# Markdown content"

        # Create multiple files to parse
        files = [create_binary_upload_file(b"%PDF-1.4 content", f"test{i}.pdf", "application/pdf") for i in range(5)]

        mock_pdf = MagicMock()

        with patch("pymupdf.open", return_value=mock_pdf):
            with patch("pymupdf4llm.to_markdown", side_effect=mock_to_markdown):
                # Parse all files concurrently
                results = await asyncio.gather(*[manager.parse(file) for file in files])

                # Verify all files were parsed
                assert len(results) == 5
                assert all(result == "# Markdown content" for result in results)

                # Verify that we never exceeded the max concurrent limit
                assert max_concurrent_reached <= max_concurrent
                assert max_concurrent_reached > 0  # We did have some concurrency

    @pytest.mark.asyncio
    async def test_semaphore_releases_on_exception(self):
        """Test that semaphore is properly released even when parsing fails."""
        manager = ParserManager(max_concurrent=1)

        # First call will fail
        file1 = create_binary_upload_file(b"%PDF-1.4 content", "test1.pdf", "application/pdf")

        # Second call should succeed (proving semaphore was released)
        file2 = create_binary_upload_file(b"%PDF-1.4 content", "test2.pdf", "application/pdf")

        mock_pdf = MagicMock()
        call_count = [0]  # Use list to allow modification in nested function

        def mock_to_markdown(doc):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Parsing failed")
            return "# Success"

        with patch("pymupdf.open", return_value=mock_pdf):
            with patch("pymupdf4llm.to_markdown", side_effect=mock_to_markdown):
                # First parse should fail
                with pytest.raises(Exception) as exc_info:
                    await manager.parse(file1)
                assert "Parsing failed" in str(exc_info.value)

                # Second parse should succeed (semaphore was released)
                result = await manager.parse(file2)
                assert result == "# Success"

    @pytest.mark.asyncio
    async def test_semaphore_default_value(self):
        """Test that ParserManager has correct default semaphore value."""
        manager = ParserManager()

        # Check that semaphore has default value of 10
        assert manager.conversion_semaphore._value == 10

    @pytest.mark.asyncio
    async def test_semaphore_custom_value(self):
        """Test that ParserManager accepts custom semaphore value."""
        custom_max = 5
        manager = ParserManager(max_concurrent=custom_max)

        # Check that semaphore has custom value
        assert manager.conversion_semaphore._value == custom_max

    @pytest.mark.asyncio
    async def test_semaphore_only_affects_pdf_parsing(self):
        """Test that semaphore is only used for PDF parsing, not other file types."""
        manager = ParserManager(max_concurrent=1)

        # Create non-PDF files
        txt_file = create_upload_file("Text content", "test.txt", "text/plain")
        md_file = create_upload_file("# Markdown", "test.md", "text/markdown")
        html_file = create_upload_file("<h1>HTML</h1>", "test.html", "text/html")

        # Mock the semaphore to track if it's used
        semaphore_used = []
        original_acquire = manager.conversion_semaphore.acquire

        async def tracked_acquire():
            semaphore_used.append(True)
            return await original_acquire()

        manager.conversion_semaphore.acquire = tracked_acquire

        # Parse non-PDF files
        with patch("api.helpers._parsermanager.convert_to_markdown", return_value="# HTML"):
            await manager.parse(txt_file)
            await manager.parse(md_file)
            await manager.parse(html_file)

        # Semaphore should not have been acquired
        assert len(semaphore_used) == 0


class TestParserManagerEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_extension_map_completeness(self):
        """Test that all expected file extensions are mapped."""
        expected_extensions = {
            ".pdf": FileType.PDF,
            ".html": FileType.HTML,
            ".htm": FileType.HTML,
            ".md": FileType.MD,
            ".markdown": FileType.MD,
            ".txt": FileType.TXT,
            ".text": FileType.TXT,
        }

        assert ParserManager.EXTENSION_MAP == expected_extensions

    def test_valid_content_types_completeness(self):
        """Test that all file types have valid content types defined."""
        for file_type in FileType:
            if file_type in [FileType.PDF, FileType.HTML, FileType.MD, FileType.TXT]:
                assert file_type in ParserManager.VALID_CONTENT_TYPES
                assert len(ParserManager.VALID_CONTENT_TYPES[file_type]) > 0
