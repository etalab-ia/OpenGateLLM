"""Parquet file reader with validation."""

import io
import logging

from fastapi import HTTPException, UploadFile
import pyarrow as pa
import pyarrow.parquet as pq

from api.schemas.core.documents import FileType
from api.utils.context import global_context
from api.utils.exceptions import (
    FileSizeLimitExceededException,
    InvalidPARQUETFormatException,
)

logger = logging.getLogger(__name__)


class ParquetReader:
    """
    Handles reading and validation of Parquet files.

    Uses PyArrow for efficient columnar data processing with zero-copy
    operations where possible.
    """

    REQUIRED_COLUMNS = {"document_name", "content"}
    CHUNK_INDEX_COLUMN = "chunk_index"

    @classmethod
    async def read_and_validate(cls, parquet_file: UploadFile) -> tuple[pa.Table, list[str], bool]:
        """
        Read and validate a Parquet file.

        Args:
            parquet_file: Uploaded Parquet file

        Returns:
            tuple: (pyarrow.Table, available_columns, has_chunk_index)
                - pyarrow.Table: The parsed Parquet table
                - available_columns: List of column names in the file
                - has_chunk_index: Whether chunk_index column is present

        Raises:
            FileSizeLimitExceededException: If file size exceeds maximum allowed
            InvalidPARQUETFormatException: If file is missing required columns
            HTTPException: If file cannot be read or parsed
        """
        # Validate file size
        parquet_file.file.seek(0, 2)
        file_size = parquet_file.file.tell()

        if file_size > FileSizeLimitExceededException.MAX_PARQUET_CONTENT_SIZE:
            raise FileSizeLimitExceededException(
                detail=f"File size exceeds maximum allowed size of {FileSizeLimitExceededException.MAX_PARQUET_CONTENT_SIZE / (1024 * 1024)} MB"
            )
        parquet_file.file.seek(0)  # reset file pointer to the beginning of the file

        # Validate file type
        global_context.document_manager.parser_manager._detect_file_type(file=parquet_file, type=FileType.PARQUET)

        # Read file content
        try:
            content = await parquet_file.read()
            pf = pq.ParquetFile(io.BytesIO(content))
        except Exception as e:
            logger.exception(f"Error reading parquet file: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid parquet file: {e}")

        # Get and validate columns
        available_columns = sorted(list(pf.schema.names))
        cls._validate_required_columns(available_columns)

        # Check for chunk_index column
        has_chunk_index = cls.CHUNK_INDEX_COLUMN in available_columns
        if not has_chunk_index:
            logger.info(f"Column '{cls.CHUNK_INDEX_COLUMN}' not found in parquet file. " "Sequential IDs will be assigned automatically.")

        # Read full table
        table = pf.read()

        return table, available_columns, has_chunk_index

    @classmethod
    def _validate_required_columns(cls, available_columns: list[str]) -> None:
        """
        Validate that all required columns are present.

        Args:
            available_columns: List of column names in the Parquet file

        Raises:
            HTTPException: If required columns are missing
        """
        if not cls.REQUIRED_COLUMNS.issubset(available_columns):
            missing = cls.REQUIRED_COLUMNS - set(available_columns)
            raise InvalidPARQUETFormatException(detail=f"Parquet file missing required columns: {missing}. " f"Available: {available_columns}")

    @staticmethod
    def sort_table(table: pa.Table, has_chunk_index: bool) -> pa.Table:
        """
        Sort table by document_name and optionally by chunk_index.

        Sorting ensures that chunks belonging to the same document are
        grouped together and in the correct order.

        Args:
            table: PyArrow Table to sort
            has_chunk_index: Whether to sort by chunk_index as secondary key

        Returns:
            PyArrow Table: Sorted table
        """
        sort_keys = [("document_name", "ascending")]
        if has_chunk_index:
            sort_keys.append(("chunk_index", "ascending"))
        return table.sort_by(sort_keys)

    @classmethod
    def identify_metadata_columns(cls, available_columns: list[str], has_chunk_index: bool) -> list[str]:
        """
        Identify which columns should be treated as metadata.

        Excludes the required columns (document_name, content) and optionally
        chunk_index from metadata.

        Args:
            available_columns: All columns in the Parquet file
            has_chunk_index: Whether chunk_index column is present

        Returns:
            list: Column names that are metadata
        """
        excluded_columns = cls.REQUIRED_COLUMNS.copy()
        if has_chunk_index:
            excluded_columns.add(cls.CHUNK_INDEX_COLUMN)

        return [col for col in available_columns if col not in excluded_columns]
