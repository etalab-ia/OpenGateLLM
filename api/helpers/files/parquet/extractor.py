"""Parquet data extraction utilities."""

import json
import logging

from fastapi import HTTPException
import pyarrow as pa
import pyarrow.compute as pc

logger = logging.getLogger(__name__)


class ParquetDataExtractor:
    """
    Extracts and processes data from PyArrow tables.

    Provides methods to extract document data, validate chunk IDs,
    and prepare metadata from Parquet files.
    """

    @staticmethod
    def get_unique_document_names(table: pa.Table) -> list[str]:
        """
        Extract unique document names from table using PyArrow compute.

        Uses vectorized operations for performance with large datasets.

        Args:
            table: PyArrow Table containing document_name column

        Returns:
            list: Unique document names
        """
        doc_names_array = table.column("document_name")
        return pc.unique(doc_names_array).to_pylist()

    @staticmethod
    def filter_document_table(table: pa.Table, document_name: str) -> pa.Table:
        """
        Filter table to get rows for a specific document.

        Args:
            table: PyArrow Table to filter
            document_name: Document name to filter by

        Returns:
            PyArrow Table: Filtered table containing only rows for doc_name
        """
        doc_names_array = table.column("document_name")
        mask = pc.equal(doc_names_array, document_name)
        return table.filter(mask)

    @staticmethod
    def extract_chunk_ids(doc_table: pa.Table, document_name: str, has_chunk_index: bool) -> list[int]:
        """
        Extract or assign chunk IDs for a document.

        If chunk_index column exists, extracts and validates sequential IDs.
        Otherwise, assigns sequential IDs starting from 1.

        Args:
            doc_table: PyArrow Table filtered for a specific document
            document_name: Document name (for error messages)
            has_chunk_index: Whether chunk_index column is present

        Returns:
            list: Chunk IDs (sequential integers)

        Raises:
            HTTPException: If chunk IDs are not sequential
        """
        if has_chunk_index:
            chunk_ids = doc_table.column("chunk_index").to_pylist()
            ParquetDataExtractor._validate_chunk_ids_sequential(chunk_ids=chunk_ids, document_name=document_name)
            return chunk_ids
        else:
            # Assign sequential IDs starting from 1
            num_chunks = len(doc_table)
            if num_chunks > 1:
                logger.info(f"Document '{document_name}': No chunk_index column, " f"assigning sequential IDs (1-{num_chunks})")
            return list(range(1, num_chunks + 1))

    @staticmethod
    def _validate_chunk_ids_sequential(chunk_ids: list[int], document_name: str) -> None:
        """
        Validate that chunk IDs are sequential.

        Args:
            chunk_ids: List of chunk IDs
            document_name: Document name for error messages

        Raises:
            HTTPException: If chunk IDs are not sequential
        """
        if not chunk_ids:
            return

        min_id = min(chunk_ids)
        expected_ids = list(range(min_id, min_id + len(chunk_ids)))

        if chunk_ids != expected_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Document '{document_name}' has non-sequential chunk IDs: {chunk_ids}. "
                f"Expected: {expected_ids}. All chunks must have sequential IDs.",
            )

    @staticmethod
    def extract_metadata_columns(doc_table: pa.Table, metadata_columns: list[str]) -> dict:
        """
        Extract metadata columns from a document table.

        Args:
            doc_table: PyArrow Table filtered for a specific document
            metadata_columns: List of metadata column names

        Returns:
            dict: Mapping of column name to list of values
        """
        return {col: doc_table.column(col).to_pylist() for col in metadata_columns}

    @staticmethod
    def build_chunk_metadata(metadata_dict: dict, idx: int) -> dict:
        """
        Build metadata dictionary for a single chunk.

        Handles JSON string parsing and null values appropriately.

        Args:
            metadata_dict: Dictionary of metadata columns with lists of values
            idx: Index of the chunk within the document

        Returns:
            dict: Metadata for the specific chunk
        """
        metadata = {}

        for meta_col, values in metadata_dict.items():
            value = values[idx]

            if value is None:
                metadata[meta_col] = None
            elif isinstance(value, str):
                stripped = value.strip()

                # Try to parse as JSON if it looks like a JSON object or array
                if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
                    try:
                        parsed = json.loads(stripped)
                        if isinstance(parsed, (dict | list)):
                            metadata[meta_col] = parsed
                        else:
                            metadata[meta_col] = value
                    except json.JSONDecodeError:
                        metadata[meta_col] = value
                    except Exception as e:
                        logger.warning(f"Unexpected error parsing JSON metadata for column '{meta_col}': {e}")
                        metadata[meta_col] = value
                else:
                    metadata[meta_col] = value
            else:
                metadata[meta_col] = value

        return metadata

    @staticmethod
    def get_row_values(doc_table: pa.Table, available_columns: list[str], idx: int) -> dict:
        """
        Extract all column values for a specific row.

        Args:
            doc_table: PyArrow Table filtered for a specific document
            available_columns: List of all column names
            idx: Index of the row within the table

        Returns:
            dict: Dictionary with all column values for the row
        """
        return {col: doc_table.column(col).to_pylist()[idx] for col in available_columns}
