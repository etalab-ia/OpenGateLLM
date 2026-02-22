# Health

Types:

```python
from albert_api.types import HealthCheckResponse
```

Methods:

- <code title="get /health">client.health.<a href="./src/albert_api/resources/health.py">check</a>() -> <a href="./src/albert_api/types/health_check_response.py">object</a></code>

# Models

Types:

```python
from albert_api.types import Model, Models, ModelRetrieveResponse, ModelListResponse
```

Methods:

- <code title="get /v1/models/{model}">client.models.<a href="./src/albert_api/resources/models.py">retrieve</a>(model) -> <a href="./src/albert_api/types/model_retrieve_response.py">ModelRetrieveResponse</a></code>
- <code title="get /v1/models">client.models.<a href="./src/albert_api/resources/models.py">list</a>(\*\*<a href="src/albert_api/types/model_list_params.py">params</a>) -> <a href="./src/albert_api/types/model_list_response.py">ModelListResponse</a></code>

# ChatCompletions

Types:

```python
from albert_api.types import ChatCompletion, ChatCompletionChunk, ChatCompletionCreateResponse
```

Methods:

- <code title="post /v1/chat/completions">client.chat_completions.<a href="./src/albert_api/resources/chat_completions.py">create</a>(\*\*<a href="src/albert_api/types/chat_completion_create_params.py">params</a>) -> <a href="./src/albert_api/types/chat_completion_create_response.py">ChatCompletionCreateResponse</a></code>

# Completions

Types:

```python
from albert_api.types import Completions
```

Methods:

- <code title="post /v1/completions">client.completions.<a href="./src/albert_api/resources/completions.py">create</a>(\*\*<a href="src/albert_api/types/completion_create_params.py">params</a>) -> <a href="./src/albert_api/types/completions.py">Completions</a></code>

# Embeddings

Types:

```python
from albert_api.types import Embeddings
```

Methods:

- <code title="post /v1/embeddings">client.embeddings.<a href="./src/albert_api/resources/embeddings.py">create</a>(\*\*<a href="src/albert_api/types/embedding_create_params.py">params</a>) -> <a href="./src/albert_api/types/embeddings.py">Embeddings</a></code>

# Search

Types:

```python
from albert_api.types import Searches
```

Methods:

- <code title="post /v1/search">client.search.<a href="./src/albert_api/resources/search.py">execute</a>(\*\*<a href="src/albert_api/types/search_execute_params.py">params</a>) -> <a href="./src/albert_api/types/searches.py">Searches</a></code>

# Collections

Types:

```python
from albert_api.types import (
    Collection,
    Collections,
    CollectionCreateResponse,
    CollectionListResponse,
    CollectionDeleteResponse,
)
```

Methods:

- <code title="post /v1/collections">client.collections.<a href="./src/albert_api/resources/collections.py">create</a>(\*\*<a href="src/albert_api/types/collection_create_params.py">params</a>) -> <a href="./src/albert_api/types/collection_create_response.py">object</a></code>
- <code title="get /v1/collections">client.collections.<a href="./src/albert_api/resources/collections.py">list</a>() -> <a href="./src/albert_api/types/collection_list_response.py">CollectionListResponse</a></code>
- <code title="delete /v1/collections/{collection}">client.collections.<a href="./src/albert_api/resources/collections.py">delete</a>(collection) -> <a href="./src/albert_api/types/collection_delete_response.py">object</a></code>

# Files

Types:

```python
from albert_api.types import FileCreateResponse
```

Methods:

- <code title="post /v1/files">client.files.<a href="./src/albert_api/resources/files.py">create</a>(\*\*<a href="src/albert_api/types/file_create_params.py">params</a>) -> <a href="./src/albert_api/types/file_create_response.py">object</a></code>

# Documents

Types:

```python
from albert_api.types import Documents, DocumentDeleteResponse
```

Methods:

- <code title="get /v1/documents/{collection}">client.documents.<a href="./src/albert_api/resources/documents.py">list</a>(collection, \*\*<a href="src/albert_api/types/document_list_params.py">params</a>) -> <a href="./src/albert_api/types/documents.py">Documents</a></code>
- <code title="delete /v1/documents/{collection}/{document}">client.documents.<a href="./src/albert_api/resources/documents.py">delete</a>(document, \*, collection) -> <a href="./src/albert_api/types/document_delete_response.py">object</a></code>

# Chunks

Types:

```python
from albert_api.types import Chunks
```

Methods:

- <code title="get /v1/chunks/{collection}/{document}">client.chunks.<a href="./src/albert_api/resources/chunks.py">retrieve</a>(document, \*, collection, \*\*<a href="src/albert_api/types/chunk_retrieve_params.py">params</a>) -> <a href="./src/albert_api/types/chunks.py">Chunks</a></code>
