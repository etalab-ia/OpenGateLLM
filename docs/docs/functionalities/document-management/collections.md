import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Collections

Collections are the storage spaces for organizing your documents in the vector store. Each collection is associated with a specific embedding model and contains documents that are processed into searchable chunks.

## Collection Properties

- `name`: Collection name (required)
- `description`: Collection description (optional)
- `visibility`: Collection visibility - `private` or `public` (default: `private`)
  - **Private**: Only accessible by the owner
  - **Public**: Accessible by all users for reading

## Public Collections

Public collections allow you to share documents with all users in your OpenGateLLM instance. When a collection is marked as public:

- The owner can read, write, update, and delete the collection and its documents
- Other users can only read the collection and search within it
- Other users cannot modify or delete public collections they don't own

:::info
Creating public collections requires the `create_public_collection` permission. For more information about permissions, see [Roles and Permissions documentation](../iam/roles-permissions-rate-limitings.md).
:::

## Managing Collections

<Tabs>
  <TabItem value="Create collection" label="Create collection" default>
  Create a new collection, optionally with initial documents from a Parquet file.

  ```bash
  # Create empty collection
  curl -X POST http://localhost:8000/v1/collections \
    -H "Authorization: Bearer <api_key>" \
    -F "name=My Collection" \
    -F "visibility=private" \
    -F "description=A collection for my documents"
  ```

  ```bash
  # Create collection with Parquet file
  curl -X POST http://localhost:8000/v1/collections \
    -H "Authorization: Bearer <api_key>" \
    -F "name=My Collection" \
    -F "visibility=private" \
    -F "description=A collection for my documents" \
    -F "file=@documents.parquet"
  ```

  </TabItem>
  <TabItem value="Get collections" label="Get collections">
  List all collections with optional filters.

  ```bash
  curl -X GET "http://localhost:8000/v1/collections?offset=0&limit=10&visibility=private" \
    -H "Authorization: Bearer <api_key>"
  ```

  </TabItem>
  <TabItem value="Get collection by ID" label="Get collection by ID">
  Get details of a specific collection.

  ```bash
  curl -X GET http://localhost:8000/v1/collections/1 \
    -H "Authorization: Bearer <api_key>"
  ```

  </TabItem>
  <TabItem value="Update collection (PATCH)" label="Update collection (PATCH)">
  Update collection metadata and/or add/update documents. Existing documents with the same name will be compared and updated only if content has changed. Note that this endpoint doesn't delete any documents.

  ```bash
  # Update metadata only
  curl -X PATCH http://localhost:8000/v1/collections/1 \
    -H "Authorization: Bearer <api_key>" \
    -F "name=Updated Name" \
    -F "visibility=public"
  ```

  ```bash
  # Update documents only
  curl -X PATCH http://localhost:8000/v1/collections/1 \
    -H "Authorization: Bearer <api_key>" \
    -F "file=@updated_documents.parquet"
  ```

  ```bash
  # Update both metadata and documents
  curl -X PATCH http://localhost:8000/v1/collections/1 \
    -H "Authorization: Bearer <api_key>" \
    -F "name=Updated Name" \
    -F "description=New description" \
    -F "file=@updated_documents.parquet"
  ```

  </TabItem>
  <TabItem value="Force update collection (PUT)" label="Force update collection (PUT)">
  Replace all documents in the collection with new ones from a Parquet file. All existing documents will be deleted first.

  ```bash
  curl -X PUT http://localhost:8000/v1/collections/1 \
    -H "Authorization: Bearer <api_key>" \
    -F "file=@new_documents.parquet"
  ```

  :::warning
  This operation will **delete all existing documents** in the collection before uploading the new ones. Use `PATCH` for incremental updates.
  :::

  </TabItem>
  <TabItem value="Delete collection" label="Delete collection">
  Delete a collection and all its documents.

  ```bash
  curl -X DELETE http://localhost:8000/v1/collections/1 \
    -H "Authorization: Bearer <api_key>"
  ```

  </TabItem>
</Tabs>

## Parquet File Requirements

When uploading documents via Parquet files to collections, your files must meet these requirements:

### Required Columns

- **`document_name`** (string): Name of the document. All chunks belonging to the same document must have the same `document_name`.
- **`content`** (string): Text content of the chunk to be embedded.

### Optional Columns

- **`chunk_index`** (integer): Specifies the order of chunks within a document. If provided, must be sequential.
  - If absent, chunks will be assigned sequential IDs based on their order in the file starting from 1.
- **Custom metadata columns**: Any additional columns will be stored as metadata for each chunk (e.g., `page`, `section`, `author`).

### File Structure Rules

1. **Complete documents**: Each Parquet file must contain ALL chunks for each document. You cannot split a document's chunks across multiple files.
2. **Sequential chunk IDs**: If using `chunk_index`, values must be sequential ([1, 2, 3] or [2, 3, 4] ...) for each document with no gaps.
3. **Metadata handling**:
   - JSON strings in metadata columns (starting with `{` or `[`) will be automatically parsed as JSON objects or arrays.
   - Other values are stored as-is.

### Example Parquet Structure

```text
| document_name | chunk_index | content           | page | section |
|---------------|-------------|-------------------|------|---------|
| report.pdf    | 1           | Introduction...   | 1    | intro   |
| report.pdf    | 2           | Methodology...    | 2    | method  |
| report.pdf    | 3           | Results...        | 3    | results |
| manual.pdf    | 1           | Chapter 1...      | 1    | ch1     |
| manual.pdf    | 2           | Chapter 2...      | 5    | ch2     |
```

## Update Behavior

### PATCH (Incremental Update)

When using `PATCH /v1/collections/{collection}` with a Parquet file:

1. **Content comparison**: Each document in the Parquet file is compared with the collection's existing documents by name
2. **Smart updates**: Only documents with changed content or metadata are re-embedded and updated
3. **New documents**: Documents not present in the collection are added
4. **Preserved documents**: Existing documents not in the Parquet file remain unchanged
5. **Efficient**: Avoids unnecessary re-embedding of unchanged content

**Use case**: Regular updates, adding new documents, or updating specific documents while keeping others intact.

:::info
This endpoint doesn't delete any document. So obsolete documents must be deleted manually by using the `DELETE /v1/documents/{document}` endpoint.
:::

### PUT (Force Update)

When using `PUT /v1/collections/{collection}` with a Parquet file:

1. **Complete replacement**: All existing documents are deleted first
2. **Full re-embedding**: All documents in the Parquet file are processed and embedded
3. **No comparison**: Content hashing is skipped for faster processing

**Use case**: Complete collection refresh, starting from scratch, or when you want to ensure exact alignment with the Parquet file.

## Next Steps

- Learn how to import documents into collections: [Parsing and Chunking](./parsing-and-chunking.md)
- Learn how to search within collections: [RAG Search](./rag.md)