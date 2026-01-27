# Search

## Search Methods

OpenGateLLM supports multiple search methods:

| Method | Description |
| --- | --- |
| `semantic` | Vector similarity search using embeddings |
| `lexical` | Keyword-based search (BM25) |
| `hybrid` | Combination of semantic and lexical search |

## Search query

- `prompt`: Search query (required)
- `collections`: List of collection IDs to search in (required)
- `method`: Search method (default: `semantic`)
- `limit`: Number of results to return (default: 10, max: 200)
- `offset`: Pagination offset (default: 0)
- `rff_k`: RRF constant for hybrid search (default: 20)
- `score_threshold`: Minimum similarity score (0.0-1.0, only for semantic)

<Tabs>
  <TabItem value="Semantic search" label="Semantic search" default>
  ```bash
  curl -X POST http://localhost:8000/v1/search \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "prompt": "What is machine learning?",
      "collections": [1, 2],
      "method": "semantic",
      "limit": 10,
      "score_threshold": 0.7
    }'
  ```
  </TabItem>
  <TabItem value="Hybrid search" label="Hybrid search">
  ```bash
  curl -X POST http://localhost:8000/v1/search \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "prompt": "Python programming",
      "collections": [1],
      "method": "hybrid",
      "limit": 10,
      "rff_k": 20
    }'
  ```
  </TabItem>
  <TabItem value="Web search" label="With web search">
  ```bash
  curl -X POST http://localhost:8000/v1/search \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "prompt": "Latest AI developments",
      "collections": [1],
      "method": "semantic",
      "limit": 10
    }'
  ```
  </TabItem>
</Tabs>

:::info
See [Configuration](../../getting-started/configuration.md) for more details.
:::

## Search filters and boosts

## Boosting priority

Priority can be boosted by adding a `source_priority` field to the document metadata. The priority is a number between 1 and 10, where 1 is the highest priority and 10 is the lowest priority. Each priority level increases the score by a factor of 0.1, following a logarithmic scale (log1p). For lexical search, the score is adjusted by ±0.01, and for semantic search, by ±0.02. This adjustment is mainly useful for breaking ties between very similar vectors.

![Boost curve (rescore contribution)](/functionalities/search/search_semantic_boost_priority.png)