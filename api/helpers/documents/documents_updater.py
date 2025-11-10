"""Collection update logic for document management."""

import logging
import time

import pyarrow as pa
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers.data.hasher import ChunkHasher
from api.helpers.files.parquet import ParquetDataExtractor
from api.schemas.chunks import Chunk
from api.sql.models import Document as DocumentTable
from api.utils.exceptions import CollectionNotFoundException, VectorizationFailedException

logger = logging.getLogger(__name__)


class DocumentsUpdater:
    """
    Handles document update logic for collections.

    Manages the comparison of existing vs new documents, creation of
    document records, and insertion of chunks into the vector store.
    """

    def __init__(self, vector_store, upsert_callback, delete_document_callback):
        """
        Initialize the updater with required dependencies.

        Args:
            vector_store: Vector store client for chunk operations
            upsert_callback: Async function to upsert chunks with embeddings
            delete_document_callback: Async function to delete documents
        """
        self.vector_store = vector_store
        self.upsert_callback = upsert_callback
        self.delete_document_callback = delete_document_callback

    async def process_document(
        self,
        session: AsyncSession,
        user_id: int,
        collection_id: int,
        document_name: str,
        document_table: pa.Table,
        available_columns: list[str],
        metadata_columns: list[str],
        has_chunk_index: bool,
        existing_docs_map: dict,
        force_update: bool,
        stats: dict,
    ) -> None:
        """
        Process a single document: check if update needed and create/update chunks.

        Args:
            session: Database session
            user_id: User ID performing the update
            collection_id: Collection ID
            document_name: Name of the document
            doc_table: PyArrow Table filtered for this document
            available_columns: All columns in the file
            metadata_columns: Columns that are metadata
            has_chunk_index: Whether chunk_index column exists
            existing_docs_map: Mapping of existing collection's document names to IDs
            force_update: Whether to force update without comparison
            stats: Statistics dictionary to update
        """
        # Extract document data
        doc_contents = document_table.column("content").to_pylist()
        doc_chunk_ids = ParquetDataExtractor.extract_chunk_ids(document_table, document_name, has_chunk_index)
        doc_metadata_dict = ParquetDataExtractor.extract_metadata_columns(document_table, metadata_columns)

        # Prepare chunks data
        new_chunks_data = self._prepare_chunks_data(
            doc_table=document_table,
            doc_contents=doc_contents,
            doc_chunk_ids=doc_chunk_ids,
            doc_metadata_dict=doc_metadata_dict,
            available_columns=available_columns,
            force_update=force_update,
        )

        # Check if update needed
        needs_update, is_new = await self._check_update_needed(
            collection_id=collection_id,
            document_name=document_name,
            existing_docs_map=existing_docs_map,
            new_chunks_data=new_chunks_data,
            force_update=force_update,
            has_chunk_index=has_chunk_index,
        )

        if not needs_update and not is_new:
            logger.debug(f"Document '{document_name}': no changes detected, skipping")
            return

        existing_doc_id = existing_docs_map.get(document_name) if not is_new else None
        try:
            # Create new document
            new_doc_id = await self._create_empty_document(session, document_name, collection_id)

            # Insert chunks with embeddings
            await self._insert_chunks(
                collection_id=collection_id,
                document_id=new_doc_id,
                document_name=document_name,
                chunks_data=new_chunks_data,
            )

            # Delete the old document (if updating)
            if existing_doc_id is not None:
                logger.debug(f"Document '{document_name}': deleting old version (id={existing_doc_id})")
                await self.delete_document_callback(session=session, user_id=user_id, document_id=existing_doc_id)

            # Update statistics
            if is_new:
                stats["added_documents"] += 1
                logger.debug(f"Document '{document_name}': new document added")
            else:
                stats["updated_documents"] += 1

            stats["total_chunks_processed"] += len(new_chunks_data)
            logger.debug(f"Document '{document_name}': processed {len(new_chunks_data)} chunks")
        except Exception as e:
            logger.error(f"Document '{document_name}': failed to process, rolling back (error: {e})")

            try:
                # Delete the new (failed) document if it was created
                if new_doc_id is not None:
                    logger.debug(f"Document '{document_name}': cleaning up failed document (id={new_doc_id})")
                    await self.delete_document_callback(session=session, user_id=user_id, document_id=new_doc_id)
            except Exception as cleanup_error:
                logger.exception(f"Document '{document_name}': cleanup failed: {cleanup_error}")

            raise e

    def _prepare_chunks_data(
        self,
        doc_table: pa.Table,
        doc_contents: list,
        doc_chunk_ids: list[int],
        doc_metadata_dict: dict,
        available_columns: list[str],
        force_update: bool,
    ) -> list[dict]:
        """
        Prepare chunk data with content, metadata, and optionally hashes.

        Args:
            doc_table: PyArrow Table filtered for this document
            doc_contents: List of chunk contents
            doc_chunk_ids: List of chunk IDs
            doc_metadata_dict: Dictionary of metadata columns
            available_columns: All columns in the Parquet file
            force_update: Whether to skip hash computation

        Returns:
            list: List of chunk data dictionaries
        """
        new_chunks_data = []

        for idx in range(len(doc_contents)):
            chunk_content = str(doc_contents[idx])

            # Build metadata for this chunk
            metadata = ParquetDataExtractor.build_chunk_metadata(doc_metadata_dict, idx)

            chunk_data = {
                "chunk_id": doc_chunk_ids[idx],
                "content": chunk_content,
                "metadata": metadata,
            }

            # Compute hash if not force updating (for comparison)
            if not force_update:
                chunk_dict = ParquetDataExtractor.get_row_values(doc_table, available_columns, idx)
                concatenated_values = ChunkHasher.concatenate_chunk_values(chunk=chunk_dict)
                chunk_data["hash"] = ChunkHasher.compute_chunk_hash(concatenated_values)

            new_chunks_data.append(chunk_data)

        return new_chunks_data

    async def _check_update_needed(
        self,
        collection_id: int,
        document_name: str,
        existing_docs_map: dict,
        new_chunks_data: list[dict],
        force_update: bool,
        has_chunk_index: bool,
    ) -> tuple[bool, bool]:
        """
        Check if document needs to be updated.

        Args:
            collection_id: Collection ID
            document_name: Document name
            existing_docs_map: Mapping of document names to IDs
            new_chunks_data: List of new chunk data
            force_update: Whether to force update
            has_chunk_index: Whether chunk_index column exists

        Returns:
            tuple: (needs_update, is_new_document)
        """
        if document_name not in existing_docs_map:
            return True, True  # New document

        if force_update:
            return True, False  # Force update existing

        # Check content changes
        existing_doc_id = existing_docs_map[document_name]
        existing_chunks = await self.vector_store.get_chunks(
            collection_id=collection_id,
            document_id=existing_doc_id,
            offset=0,
            limit=10000,
        )
        existing_chunks.sort(key=lambda c: c.id)

        # Compare chunk count
        if len(existing_chunks) != len(new_chunks_data):
            logger.info(f"Document '{document_name}': chunk count differs " f"({len(existing_chunks)} vs {len(new_chunks_data)})")
            return True, False

        # Compare hashes
        existing_hashes = [ChunkHasher.compute_existing_chunk_hash(chunk, has_chunk_index) for chunk in existing_chunks]
        new_hashes = [chunk["hash"] for chunk in new_chunks_data]

        if existing_hashes != new_hashes:
            # Log first difference
            for i, (old_h, new_h) in enumerate(zip(existing_hashes, new_hashes)):
                if old_h != new_h:
                    logger.info(f"Document '{document_name}': hash differs at chunk {i+1} " f"(old: {old_h} vs new: {new_h})")
                    break
            return True, False

        return False, False  # No changes

    async def _create_empty_document(self, session: AsyncSession, document_name: str, collection_id: int) -> int:
        """
        Create a new empty document record in the database.

        Args:
            session: Database session
            document_name: Document name
            collection_id: Collection ID

        Returns:
            int: New document ID

        Raises:
            CollectionNotFoundException: If collection no longer exists
        """
        try:
            result = await session.execute(
                statement=insert(table=DocumentTable).values(name=document_name, collection_id=collection_id).returning(DocumentTable.id)
            )
        except Exception as e:
            if "foreign key constraint" in str(e).lower() or "fkey" in str(e).lower():
                raise CollectionNotFoundException(detail=f"Collection {collection_id} no longer exists")
            raise

        document_id = result.scalar_one()
        await session.commit()
        return document_id

    async def _insert_chunks(
        self,
        collection_id: int,
        document_id: int,
        document_name: str,
        chunks_data: list[dict],
    ) -> None:
        """
        Insert chunks with embeddings into the vector store.

        Args:
            collection_id: Collection ID
            document_id: Document ID
            document_name: Document name
            chunks_data: List of chunk data dictionaries

        Raises:
            VectorizationFailedException: If embedding generation fails
        """
        current_time = round(time.time())
        chunks_to_insert = []

        # Prepare chunks with full metadata
        for chunk_data in chunks_data:
            chunk_metadata = chunk_data["metadata"].copy()
            chunk_metadata.update(
                {
                    "collection_id": collection_id,
                    "document_id": document_id,
                    "document_name": document_name,
                    "document_created_at": current_time,
                }
            )

            chunk = Chunk(
                id=chunk_data["chunk_id"],
                content=chunk_data["content"],
                metadata=chunk_metadata,
            )
            chunks_to_insert.append(chunk)

        # Upsert chunks with embeddings (batch operation)
        try:
            await self.upsert_callback(chunks=chunks_to_insert, collection_id=collection_id)
        except Exception as e:
            logger.exception(f"Error during vectorization for document '{document_name}': {e}")
            raise VectorizationFailedException(detail=f"Vectorization failed for document '{document_name}': {e}")
