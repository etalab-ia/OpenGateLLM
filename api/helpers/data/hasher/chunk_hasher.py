"""Hash computation for chunk content comparison."""

import json

import xxhash

from api.schemas.chunks import Chunk


class ChunkHasher:
    """
    Handles hash computation for chunk content to detect changes.

    Uses xxHash64 for fast, non-cryptographic hashing optimized for
    performance in production environments.
    """

    @staticmethod
    def concatenate_chunk_values(chunk: dict) -> str:
        """
        Concatenate all chunk values into a single string for hashing.

        The keys are sorted alphabetically to ensure consistent ordering,
        which guarantees identical hashes for identical content regardless
        of insertion order.

        Args:
            chunk: Dictionary containing chunk data (content, metadata, etc.)

        Returns:
            str: Concatenated string representation of all chunk values

        Example:
            >>> chunk = {"content": "text", "page": 1}
            >>> ChunkHasher.concatenate_chunk_values(chunk)
            "content:textpage:1"
        """
        parts = []
        for key in sorted(chunk.keys()):
            value = chunk.get(key, None)
            if isinstance(value, (dict | list)):
                # Serialize complex types to JSON for consistent representation
                parts.append(f"{key}:{json.dumps(value, ensure_ascii=False)}")
            else:
                parts.append(f"{key}:{value}")
        return "".join(parts)

    @staticmethod
    def compute_chunk_hash(text_content: str) -> str:
        """
        Compute xxHash64 hash of text content.

        xxHash is extremely fast (~10GB/s) and provides good distribution
        for hash-based comparisons. Perfect for detecting content changes.

        Args:
            text_content: String content to hash

        Returns:
            str: Hexadecimal hash string (16 characters)

        Example:
            >>> ChunkHasher.compute_chunk_hash("test content")
            "d4f3c6e2a1b5c7d8"
        """
        return xxhash.xxh64(text_content.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_existing_chunk_hash(chunk: Chunk, has_chunk_index: bool = False) -> str:
        """
        Compute hash for an existing chunk from the vector store.

        Excludes auto-generated metadata fields that shouldn't be compared:
        - collection_id: Internal identifier
        - document_id: Internal identifier
        - document_created_at: Timestamp that changes on updates

        Args:
            chunk: Chunk object from vector store with .metadata, .content, .id
            has_chunk_index: Whether to include chunk_index in the hash

        Returns:
            str: Hash of the chunk content and relevant metadata
        """
        metadatas_to_exclude = {"collection_id", "document_id", "document_created_at"}

        # Extract only relevant metadata
        existing_chunk = {key: value for key, value in chunk.metadata.items() if key not in metadatas_to_exclude}

        # Add content
        existing_chunk["content"] = chunk.content

        # Add chunk_index if present (for consistent comparison with parquet data)
        if has_chunk_index:
            existing_chunk["chunk_index"] = chunk.id

        # Compute hash
        concatenated = ChunkHasher.concatenate_chunk_values(chunk=existing_chunk)
        return ChunkHasher.compute_chunk_hash(text_content=concatenated)
