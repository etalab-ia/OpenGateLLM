import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Retrieval-Augmented Generation (RAG)

RAG (Retrieval-Augmented Generation) search allows you to retrieve relevant chunks from your [collections](./collections.md) based on a query. This enables language models to generate responses grounded in your specific documents and knowledge base.

## Search Methods

OpenGateLLM supports multiple search methods:

| Method | Description |
| --- | --- |
| `semantic` | Vector similarity search using embeddings |
| `lexical` | Keyword-based search (BM25) |
| `hybrid` | Combination of semantic and lexical search |

## Search Parameters

- `prompt`: Search query (required)
- `collections`: List of collection IDs to search in (required)
- `method`: Search method (default: `semantic`)
- `limit`: Number of results to return (default: 10, max: 200)
- `offset`: Pagination offset (default: 0)
- `rff_k`: RRF constant for hybrid search (default: 20)
- `score_threshold`: Minimum similarity score (0.0-1.0, only for semantic)

## Search Flow

[//]: # TODO - Update Mermaid Graph to remove web search
```mermaid
graph TD
    A[Search Request] --> B{Web Search?}
    B -->|Yes| C[Create Web Collection]
    B -->|No| D[Query Vector Store]
    C --> D
    D --> E{Method?}
    E -->|semantic| F[Semantic Search]
    E -->|lexical| G[Lexical Search]
    E -->|hybrid| H[Hybrid Search]
    F --> J[Return Results]
    G --> J
    H --> J
    I --> K[Synthesis & Reranking]
    K --> J
    J --> L{Web Collection?}
    L -->|Yes| M[Delete Web Collection]
    L -->|No| N[End]
    M --> N
```

## Performing Searches



## Next Steps

- Learn how to create and manage collections: [Collections](./collections.md)
- Learn how to import and process documents: [Parsing and Chunking](./parsing-and-chunking.md)

