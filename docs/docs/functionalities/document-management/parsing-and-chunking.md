import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Parsing and Chunking

This section covers the data ingestion process: importing files, parsing them into documents, and chunking them for vectorization and storage in the vector store.

## Document Management

Documents represent files that have been imported and processed into the vector store. Each document belongs to a [collection](./collections.md) and is broken down into searchable chunks.

## Importing Files

The API accepts multiple file types: **JSON**, **PDF**, **Markdown**, and **HTML**.

### Standard File Import

<Tabs>
  <TabItem value="Import document" label="Import document" default>
  ```bash
  curl -X POST http://localhost:8000/v1/documents \
    -H "Authorization: Bearer <api_key>" \
    -F "file=@/path/to/document.pdf" \
    -F "collection=1" \
    -F "chunker=RecursiveCharacterTextSplitter" \
    -F "chunk_size=2048" \
    -F "chunk_overlap=0"
  ```
  </TabItem>
  <TabItem value="Get documents" label="Get documents">
  ```bash
  curl -X GET "http://localhost:8000/v1/documents?collection=1&offset=0&limit=10" \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Get document by ID" label="Get document by ID">
  ```bash
  curl -X GET http://localhost:8000/v1/documents/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Delete document" label="Delete document">
  ```bash
  curl -X DELETE http://localhost:8000/v1/documents/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
</Tabs>

### JSON Format

The JSON format is suitable for bulk importing data. Unlike other file types, JSON will be decomposed into multiple documents:

```json
[
  {
    "text": "Content of the first document",
    "title": "Document 1"
  },
  {
    "text": "Content of the second document",
    "title": "Document 2",
    "metadata": {
      "author": "John Doe",
      "date": "2024-01-01"
    }
  }
]
```

:::info
Metadata is optional and only available for JSON files. It will be returned along with the chunk during search operations.
:::

## Chunking Strategy

The chunking strategy is configurable via parameters. Chunking breaks down documents into smaller pieces that can be efficiently vectorized and searched.

### Available Chunkers

| Chunker | Description |
| --- | --- |
| `NoSplitter` | The file is considered as a single chunk |
| `RecursiveCharacterTextSplitter` | Splits text recursively by different separators ([Langchain documentation](https://python.langchain.com/v0.1/docs/modules/data_connection/document_transformers/recursive_text_splitter/)) |

### Available Parameters

- `chunker`: Chunker type (default: `RecursiveCharacterTextSplitter`)
- `chunk_size`: Size of chunks (default: 2048)
- `chunk_overlap`: Overlap between chunks (default: 0)
- `chunk_min_size`: Minimum chunk size (default: 0)
- `separators`: List of separators (default: `["\n\n", "\n", ". ", " "]`)
- `preset_separators`: Preset language-specific separators (e.g., `markdown`, `python`)
- `is_separator_regex`: Whether separators are regex patterns (default: false)
- `metadata`: Additional metadata as JSON string

## Chunk Management

Chunks are the smallest units in the vector store, representing portions of text from documents. Each chunk is vectorized and can be retrieved during [search operations](./rag.md).

<Tabs>
  <TabItem value="Get chunks" label="Get chunks" default>
  ```bash
  curl -X GET "http://localhost:8000/v1/chunks/1?offset=0&limit=10" \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Get chunk by ID" label="Get chunk by ID">
  ```bash
  curl -X GET http://localhost:8000/v1/chunks/1/123 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
</Tabs>

## Next Steps

- Learn how to search through your documents: [RAG Search](./rag.md)
- Learn about collection management: [Collections](./collections.md)

