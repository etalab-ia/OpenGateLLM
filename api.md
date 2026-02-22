# Admin

## Organizations

Types:

```python
from opengatellm.types.admin import (
    Organization,
    OrganizationCreateResponse,
    OrganizationListResponse,
)
```

Methods:

- <code title="post /v1/admin/organizations">client.admin.organizations.<a href="./src/opengatellm/resources/admin/organizations.py">create</a>(\*\*<a href="src/opengatellm/types/admin/organization_create_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/organization_create_response.py">OrganizationCreateResponse</a></code>
- <code title="get /v1/admin/organizations/{organization}">client.admin.organizations.<a href="./src/opengatellm/resources/admin/organizations.py">retrieve</a>(organization) -> <a href="./src/opengatellm/types/admin/organization.py">Organization</a></code>
- <code title="patch /v1/admin/organizations/{organization}">client.admin.organizations.<a href="./src/opengatellm/resources/admin/organizations.py">update</a>(organization, \*\*<a href="src/opengatellm/types/admin/organization_update_params.py">params</a>) -> None</code>
- <code title="get /v1/admin/organizations">client.admin.organizations.<a href="./src/opengatellm/resources/admin/organizations.py">list</a>(\*\*<a href="src/opengatellm/types/admin/organization_list_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/organization_list_response.py">OrganizationListResponse</a></code>
- <code title="delete /v1/admin/organizations/{organization}">client.admin.organizations.<a href="./src/opengatellm/resources/admin/organizations.py">delete</a>(organization) -> None</code>

## Providers

Types:

```python
from opengatellm.types.admin import (
    Metric,
    Provider,
    ProviderCarbonFootprintZone,
    ProviderType,
    ProviderCreateResponse,
    ProviderListResponse,
)
```

Methods:

- <code title="post /v1/admin/providers">client.admin.providers.<a href="./src/opengatellm/resources/admin/providers.py">create</a>(\*\*<a href="src/opengatellm/types/admin/provider_create_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/provider_create_response.py">ProviderCreateResponse</a></code>
- <code title="get /v1/admin/providers/{provider}">client.admin.providers.<a href="./src/opengatellm/resources/admin/providers.py">retrieve</a>(provider) -> <a href="./src/opengatellm/types/admin/provider.py">Provider</a></code>
- <code title="patch /v1/admin/providers/{provider}">client.admin.providers.<a href="./src/opengatellm/resources/admin/providers.py">update</a>(provider, \*\*<a href="src/opengatellm/types/admin/provider_update_params.py">params</a>) -> None</code>
- <code title="get /v1/admin/providers">client.admin.providers.<a href="./src/opengatellm/resources/admin/providers.py">list</a>(\*\*<a href="src/opengatellm/types/admin/provider_list_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/provider_list_response.py">ProviderListResponse</a></code>
- <code title="delete /v1/admin/providers/{provider}">client.admin.providers.<a href="./src/opengatellm/resources/admin/providers.py">delete</a>(provider) -> None</code>

## Roles

Types:

```python
from opengatellm.types.admin import (
    Limit,
    PermissionType,
    Role,
    RoleCreateResponse,
    RoleListResponse,
)
```

Methods:

- <code title="post /v1/admin/roles">client.admin.roles.<a href="./src/opengatellm/resources/admin/roles.py">create</a>(\*\*<a href="src/opengatellm/types/admin/role_create_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/role_create_response.py">RoleCreateResponse</a></code>
- <code title="get /v1/admin/roles/{role}">client.admin.roles.<a href="./src/opengatellm/resources/admin/roles.py">retrieve</a>(role) -> <a href="./src/opengatellm/types/admin/role.py">Role</a></code>
- <code title="patch /v1/admin/roles/{role}">client.admin.roles.<a href="./src/opengatellm/resources/admin/roles.py">update</a>(role, \*\*<a href="src/opengatellm/types/admin/role_update_params.py">params</a>) -> None</code>
- <code title="get /v1/admin/roles">client.admin.roles.<a href="./src/opengatellm/resources/admin/roles.py">list</a>(\*\*<a href="src/opengatellm/types/admin/role_list_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/role_list_response.py">RoleListResponse</a></code>
- <code title="delete /v1/admin/roles/{role}">client.admin.roles.<a href="./src/opengatellm/resources/admin/roles.py">delete</a>(role) -> None</code>

## Routers

Types:

```python
from opengatellm.types.admin import (
    ModelType,
    Router,
    RouterLoadBalancingStrategy,
    RouterCreateResponse,
    RouterListResponse,
)
```

Methods:

- <code title="post /v1/admin/routers">client.admin.routers.<a href="./src/opengatellm/resources/admin/routers.py">create</a>(\*\*<a href="src/opengatellm/types/admin/router_create_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/router_create_response.py">RouterCreateResponse</a></code>
- <code title="get /v1/admin/routers/{router}">client.admin.routers.<a href="./src/opengatellm/resources/admin/routers.py">retrieve</a>(router) -> <a href="./src/opengatellm/types/admin/router.py">Router</a></code>
- <code title="patch /v1/admin/routers/{router}">client.admin.routers.<a href="./src/opengatellm/resources/admin/routers.py">update</a>(router, \*\*<a href="src/opengatellm/types/admin/router_update_params.py">params</a>) -> None</code>
- <code title="get /v1/admin/routers">client.admin.routers.<a href="./src/opengatellm/resources/admin/routers.py">list</a>(\*\*<a href="src/opengatellm/types/admin/router_list_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/router_list_response.py">RouterListResponse</a></code>
- <code title="delete /v1/admin/routers/{router}">client.admin.routers.<a href="./src/opengatellm/resources/admin/routers.py">delete</a>(router) -> None</code>

## Tokens

Types:

```python
from opengatellm.types.admin import Token, TokenCreateResponse, TokenListResponse
```

Methods:

- <code title="post /v1/admin/tokens">client.admin.tokens.<a href="./src/opengatellm/resources/admin/tokens.py">create</a>(\*\*<a href="src/opengatellm/types/admin/token_create_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/token_create_response.py">TokenCreateResponse</a></code>
- <code title="get /v1/admin/tokens/{token}">client.admin.tokens.<a href="./src/opengatellm/resources/admin/tokens.py">retrieve</a>(token) -> <a href="./src/opengatellm/types/admin/token.py">Token</a></code>
- <code title="get /v1/admin/tokens">client.admin.tokens.<a href="./src/opengatellm/resources/admin/tokens.py">list</a>(\*\*<a href="src/opengatellm/types/admin/token_list_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/token_list_response.py">TokenListResponse</a></code>
- <code title="delete /v1/admin/tokens/{token}">client.admin.tokens.<a href="./src/opengatellm/resources/admin/tokens.py">delete</a>(token) -> None</code>

## Users

Types:

```python
from opengatellm.types.admin import UserCreateResponse
```

Methods:

- <code title="post /v1/admin/users">client.admin.users.<a href="./src/opengatellm/resources/admin/users.py">create</a>(\*\*<a href="src/opengatellm/types/admin/user_create_params.py">params</a>) -> <a href="./src/opengatellm/types/admin/user_create_response.py">UserCreateResponse</a></code>
- <code title="get /v1/admin/users/{user}">client.admin.users.<a href="./src/opengatellm/resources/admin/users.py">retrieve</a>(user) -> object</code>
- <code title="patch /v1/admin/users/{user}">client.admin.users.<a href="./src/opengatellm/resources/admin/users.py">update</a>(user, \*\*<a href="src/opengatellm/types/admin/user_update_params.py">params</a>) -> None</code>
- <code title="get /v1/admin/users">client.admin.users.<a href="./src/opengatellm/resources/admin/users.py">list</a>(\*\*<a href="src/opengatellm/types/admin/user_list_params.py">params</a>) -> object</code>
- <code title="delete /v1/admin/users/{user}">client.admin.users.<a href="./src/opengatellm/resources/admin/users.py">delete</a>(user) -> None</code>

# Audio

Types:

```python
from opengatellm.types import Usage, AudioTranscribeResponse
```

Methods:

- <code title="post /v1/audio/transcriptions">client.audio.<a href="./src/opengatellm/resources/audio.py">transcribe</a>(\*\*<a href="src/opengatellm/types/audio_transcribe_params.py">params</a>) -> <a href="./src/opengatellm/types/audio_transcribe_response.py">AudioTranscribeResponse</a></code>

# Auth

Types:

```python
from opengatellm.types import AuthLoginResponse
```

Methods:

- <code title="post /v1/auth/login">client.auth.<a href="./src/opengatellm/resources/auth.py">login</a>(\*\*<a href="src/opengatellm/types/auth_login_params.py">params</a>) -> <a href="./src/opengatellm/types/auth_login_response.py">AuthLoginResponse</a></code>

# Chat

Types:

```python
from opengatellm.types import (
    ChatCompletionTokenLogprob,
    ChoiceLogprobs,
    ChatCreateCompletionResponse,
)
```

Methods:

- <code title="post /v1/chat/completions">client.chat.<a href="./src/opengatellm/resources/chat.py">create_completion</a>(\*\*<a href="src/opengatellm/types/chat_create_completion_params.py">params</a>) -> <a href="./src/opengatellm/types/chat_create_completion_response.py">ChatCreateCompletionResponse</a></code>

# Chunks

Types:

```python
from opengatellm.types import Chunk, ChunkListResponse
```

Methods:

- <code title="get /v1/chunks/{document}/{chunk}">client.chunks.<a href="./src/opengatellm/resources/chunks.py">retrieve</a>(chunk, \*, document) -> <a href="./src/opengatellm/types/chunk.py">Chunk</a></code>
- <code title="get /v1/chunks/{document}">client.chunks.<a href="./src/opengatellm/resources/chunks.py">list</a>(document, \*\*<a href="src/opengatellm/types/chunk_list_params.py">params</a>) -> <a href="./src/opengatellm/types/chunk_list_response.py">ChunkListResponse</a></code>

# Collections

Types:

```python
from opengatellm.types import Collection, CollectionVisibility, CollectionListResponse
```

Methods:

- <code title="post /v1/collections">client.collections.<a href="./src/opengatellm/resources/collections.py">create</a>(\*\*<a href="src/opengatellm/types/collection_create_params.py">params</a>) -> object</code>
- <code title="get /v1/collections/{collection_id}">client.collections.<a href="./src/opengatellm/resources/collections.py">retrieve</a>(collection_id) -> <a href="./src/opengatellm/types/collection.py">Collection</a></code>
- <code title="patch /v1/collections/{collection_id}">client.collections.<a href="./src/opengatellm/resources/collections.py">update</a>(collection_id, \*\*<a href="src/opengatellm/types/collection_update_params.py">params</a>) -> None</code>
- <code title="get /v1/collections">client.collections.<a href="./src/opengatellm/resources/collections.py">list</a>(\*\*<a href="src/opengatellm/types/collection_list_params.py">params</a>) -> <a href="./src/opengatellm/types/collection_list_response.py">CollectionListResponse</a></code>
- <code title="delete /v1/collections/{collection_id}">client.collections.<a href="./src/opengatellm/resources/collections.py">delete</a>(collection_id) -> None</code>

# Documents

Types:

```python
from opengatellm.types import DocumentCreateResponse, DocumentRetrieveResponse
```

Methods:

- <code title="post /v1/documents">client.documents.<a href="./src/opengatellm/resources/documents/documents.py">create</a>(\*\*<a href="src/opengatellm/types/document_create_params.py">params</a>) -> <a href="./src/opengatellm/types/document_create_response.py">DocumentCreateResponse</a></code>
- <code title="get /v1/documents/{document_id}">client.documents.<a href="./src/opengatellm/resources/documents/documents.py">retrieve</a>(document_id) -> <a href="./src/opengatellm/types/document_retrieve_response.py">DocumentRetrieveResponse</a></code>
- <code title="get /v1/documents">client.documents.<a href="./src/opengatellm/resources/documents/documents.py">list</a>(\*\*<a href="src/opengatellm/types/document_list_params.py">params</a>) -> object</code>
- <code title="delete /v1/documents/{document_id}">client.documents.<a href="./src/opengatellm/resources/documents/documents.py">delete</a>(document_id) -> None</code>

## Chunks

Methods:

- <code title="post /v1/documents/{document_id}/chunks">client.documents.chunks.<a href="./src/opengatellm/resources/documents/chunks.py">create</a>(document_id, \*\*<a href="src/opengatellm/types/documents/chunk_create_params.py">params</a>) -> object</code>
- <code title="get /v1/documents/{document_id}/chunks/{chunk_id}">client.documents.chunks.<a href="./src/opengatellm/resources/documents/chunks.py">retrieve</a>(chunk_id, \*, document_id) -> object</code>
- <code title="get /v1/documents/{document_id}/chunks">client.documents.chunks.<a href="./src/opengatellm/resources/documents/chunks.py">list</a>(document_id, \*\*<a href="src/opengatellm/types/documents/chunk_list_params.py">params</a>) -> object</code>
- <code title="delete /v1/documents/{document_id}/chunks/{chunk_id}">client.documents.chunks.<a href="./src/opengatellm/resources/documents/chunks.py">delete</a>(chunk_id, \*, document_id) -> None</code>

# Embeddings

Types:

```python
from opengatellm.types import EmbeddingCreateResponse
```

Methods:

- <code title="post /v1/embeddings">client.embeddings.<a href="./src/opengatellm/resources/embeddings.py">create</a>(\*\*<a href="src/opengatellm/types/embedding_create_params.py">params</a>) -> <a href="./src/opengatellm/types/embedding_create_response.py">EmbeddingCreateResponse</a></code>

# Me

Types:

```python
from opengatellm.types import MeGetUsageResponse
```

Methods:

- <code title="get /v1/me/usage">client.me.<a href="./src/opengatellm/resources/me/me.py">get_usage</a>(\*\*<a href="src/opengatellm/types/me_get_usage_params.py">params</a>) -> <a href="./src/opengatellm/types/me_get_usage_response.py">MeGetUsageResponse</a></code>

## Info

Types:

```python
from opengatellm.types.me import InfoRetrieveResponse
```

Methods:

- <code title="get /v1/me/info">client.me.info.<a href="./src/opengatellm/resources/me/info.py">retrieve</a>() -> <a href="./src/opengatellm/types/me/info_retrieve_response.py">InfoRetrieveResponse</a></code>
- <code title="patch /v1/me/info">client.me.info.<a href="./src/opengatellm/resources/me/info.py">update</a>(\*\*<a href="src/opengatellm/types/me/info_update_params.py">params</a>) -> None</code>

## Keys

Types:

```python
from opengatellm.types.me import Key, KeyCreateResponse, KeyListResponse
```

Methods:

- <code title="post /v1/me/keys">client.me.keys.<a href="./src/opengatellm/resources/me/keys.py">create</a>(\*\*<a href="src/opengatellm/types/me/key_create_params.py">params</a>) -> <a href="./src/opengatellm/types/me/key_create_response.py">KeyCreateResponse</a></code>
- <code title="get /v1/me/keys/{key}">client.me.keys.<a href="./src/opengatellm/resources/me/keys.py">retrieve</a>(key) -> <a href="./src/opengatellm/types/me/key.py">Key</a></code>
- <code title="get /v1/me/keys">client.me.keys.<a href="./src/opengatellm/resources/me/keys.py">list</a>(\*\*<a href="src/opengatellm/types/me/key_list_params.py">params</a>) -> <a href="./src/opengatellm/types/me/key_list_response.py">KeyListResponse</a></code>
- <code title="delete /v1/me/keys/{key}">client.me.keys.<a href="./src/opengatellm/resources/me/keys.py">delete</a>(key) -> None</code>

# Models

Types:

```python
from opengatellm.types import Model, ModelListResponse
```

Methods:

- <code title="get /v1/models/{model}">client.models.<a href="./src/opengatellm/resources/models.py">retrieve</a>(model) -> <a href="./src/opengatellm/types/model.py">Model</a></code>
- <code title="get /v1/models">client.models.<a href="./src/opengatellm/resources/models.py">list</a>() -> <a href="./src/opengatellm/types/model_list_response.py">ModelListResponse</a></code>

# Ocr

Types:

```python
from opengatellm.types import ResponseFormat, OcrExtractTextResponse
```

Methods:

- <code title="post /v1/ocr">client.ocr.<a href="./src/opengatellm/resources/ocr.py">extract_text</a>(\*\*<a href="src/opengatellm/types/ocr_extract_text_params.py">params</a>) -> <a href="./src/opengatellm/types/ocr_extract_text_response.py">OcrExtractTextResponse</a></code>

# ParseBeta

Types:

```python
from opengatellm.types import ParseBetaParseResponse
```

Methods:

- <code title="post /v1/parse-beta">client.parse_beta.<a href="./src/opengatellm/resources/parse_beta.py">parse</a>(\*\*<a href="src/opengatellm/types/parse_beta_parse_params.py">params</a>) -> <a href="./src/opengatellm/types/parse_beta_parse_response.py">ParseBetaParseResponse</a></code>

# Rerank

Types:

```python
from opengatellm.types import RerankCreateResponse
```

Methods:

- <code title="post /v1/rerank">client.rerank.<a href="./src/opengatellm/resources/rerank.py">create</a>(\*\*<a href="src/opengatellm/types/rerank_create_params.py">params</a>) -> <a href="./src/opengatellm/types/rerank_create_response.py">RerankCreateResponse</a></code>

# Search

Types:

```python
from opengatellm.types import Search, SearchMethod, SearchPerformResponse
```

Methods:

- <code title="post /v1/search">client.search.<a href="./src/opengatellm/resources/search.py">perform</a>(\*\*<a href="src/opengatellm/types/search_perform_params.py">params</a>) -> <a href="./src/opengatellm/types/search_perform_response.py">SearchPerformResponse</a></code>

# Metrics

Methods:

- <code title="get /metrics">client.metrics.<a href="./src/opengatellm/resources/metrics.py">retrieve</a>() -> object</code>

# Health

Methods:

- <code title="get /health">client.health.<a href="./src/opengatellm/resources/health.py">check</a>() -> object</code>
