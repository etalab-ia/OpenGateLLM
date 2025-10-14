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
  ```bash
  curl -X POST http://localhost:8000/v1/collections \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "My Collection",
      "description": "A collection for my documents",
      "visibility": "private"
    }'
  ```
  </TabItem>
  <TabItem value="Get collections" label="Get collections">
  ```bash
  curl -X GET "http://localhost:8000/v1/collections?offset=0&limit=10" \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Get collection by ID" label="Get collection by ID">
  ```bash
  curl -X GET http://localhost:8000/v1/collections/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Update collection" label="Update collection">
  ```bash
  curl -X PATCH http://localhost:8000/v1/collections/1 \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Updated Collection Name",
      "visibility": "public"
    }'
  ```
  </TabItem>
  <TabItem value="Delete collection" label="Delete collection">
  ```bash
  curl -X DELETE http://localhost:8000/v1/collections/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
</Tabs>

## Next Steps

- Learn how to import documents into collections: [Parsing and Chunking](./parsing-and-chunking.md)
- Learn how to search within collections: [RAG Search](./rag.md)

