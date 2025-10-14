import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Document Management

OpenGateLLM provides a comprehensive document management system to help you perform Retrieval-Augmented Generation (RAG). This allows you to store, process, and search through your documents to enhance AI responses with relevant context.

## What is RAG?

Retrieval-Augmented Generation (RAG) is a technique that combines a language model with an external knowledge source. Instead of relying only on its internal training data, the model first retrieves relevant information from a database or document store, then uses that context to generate more accurate, up-to-date, and domain-specific responses.

## Prerequisites

To use document management features, you need to configure a vector store. OpenGateLLM supports two vector databases:
- [Qdrant](https://qdrant.tech/documentation/guides/installation/#docker-and-docker-compose)
- [Elasticsearch](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-with-docker)

For detailed setup instructions, see the [Vector Store documentation](../../dependencies/vector_store.md).

## Concepts

Document management organizes data in a hierarchical structure with three main entities:

- **[Collection](./collections.md)**: Storage space for documents and chunks
- **Document**: Text extracted from a file
- **Chunk**: A portion of text split from a document

```mermaid
%%{ init : { "theme" : "forest", "flowchart" : { "curve" : "stepBefore" }}}%%

graph TD
    collection(Collection) --> document1(Document 1)
    collection --> document2(Document 2)
    collection --> document3(Document ...)
    document1 --> chunk1(Chunk 1)
    document1 --> chunk2(Chunk 2)
    document1 --> chunk3(Chunk ...)

    document2 --> chunk4(Chunk 1)
    document2 --> chunk5(Chunk 2)

	style document1 fill:#DBA123
	style document2 fill:#DBA123
	style document3 fill:#DBA123
	style chunk1 fill:#23AADB
	style chunk2 fill:#23AADB
	style chunk3 fill:#23AADB
    style chunk4 fill:#23AADB
    style chunk5 fill:#23AADB
```

## How it Works

OpenGateLLM allow to upload files and process them into documents and chunks. Chunks are the smallest units in the vector store, representing portions of text from documents. Each chunk is vectorized and can be retrieved during [search operations](./rag.md) to add more context of you LLM requests. When you import a file, it goes through multiple phases:

```mermaid
graph LR
    file(File Upload) --> parsing(Parsing)
    parsing --> document(Document)
    document --> chunking(Chunking)
    chunking --> chunks(Chunks)
    chunks --> vectorization(Vectorization)
    vectorization --> vectorStore(Vector Store)
```

1. **File**: The original file (PDF, JSON, Markdown, HTML, etc.)
2. **Parsing**: Text extraction from the file
3. **Document**: Extracted text with metadata
4. **Chunking**: Splitting the document into smaller pieces
5. **Chunks**: Text portions with their vectors
6. **Vectorization**: Converting chunks to embeddings using an embedding model
7. **Indexation**: Storing chunks and vectors in the database

When you upload a file to create a document, the system processes it through multiple stages involving validation, parsing, chunking, vectorization, and storage. Here's the complete flow:

```mermaid
sequenceDiagram
    actor User
    participant API as API Endpoint
    participant DM as Document Manager
    participant PM as Parser Manager
    participant VS as Vector Store
    participant EM as Embedding Model
    participant DB as PostgreSQL
    
    User->>+API: POST /v1/documents
    Note over User,API: Upload file with collection ID<br/>and chunking parameters
    
    API->>API: Validate file size
    alt File too large
        API-->>User: 413 File size limit exceeded
    end
    
    API->>+DM: parse_file()
    DM->>+PM: Parse file content
    PM-->>-DM: ParsedDocument
    DM-->>-API: Parsed document
    
    API->>+DM: create_document()
    
    DM->>+DB: Check collection exists<br/>and user has access
    alt Collection not found
        DB-->>DM: Not found
        DM-->>API: 404 Collection not found
        API-->>User: 404 Collection not found
    end
    DB-->>-DM: Collection valid
    
    DM->>DM: Split document into chunks
    Note over DM: Uses chunker strategy:<br/>RecursiveCharacterTextSplitter<br/>or NoSplitter
    
    alt Chunking fails
        DM-->>API: 400 Chunking failed
        API-->>User: 400 Chunking failed
    end
    
    DM->>+DB: Insert document record
    DB-->>-DM: document_id
    
    DM->>DM: Add metadata to chunks<br/>(collection_id, document_id,<br/>created_at)
    
    loop For each batch of chunks (32 max)
        DM->>+EM: Create embeddings
        EM-->>-DM: Vector embeddings
        
        DM->>+VS: Upsert chunks with vectors
        alt Vectorization fails
            VS-->>DM: Error
            DM->>DB: Delete document record
            DM-->>API: 400 Vectorization failed
            API-->>User: 400 Vectorization failed
        end
        VS-->>-DM: Success
    end
    
    DM-->>-API: document_id
    API-->>-User: 201 Document created
    Note over User,API: Response: {"id": document_id}
```

The processing involves several key components:

- **API Endpoint**: Handles HTTP requests and validation
- **Document Manager**: Orchestrates the document creation process
- **Parser Manager**: Extracts text from various file formats (PDF, JSON, Markdown, HTML)
- **Vector Store**: Stores chunks and their vector embeddings (Qdrant or Elasticsearch)
- **Embedding Model**: Converts text chunks into vector representations
- **PostgreSQL**: Stores document metadata and relationships
