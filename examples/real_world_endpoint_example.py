"""
Real-world example: Using ModelProviderClientFactory in actual endpoints.

This shows how to integrate the factory with the existing Albert API
architecture, including Redis, Postgres, and proper dependency injection.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.clients.model import ModelProviderClientFactory
from api.dependencies import get_postgres_session
from api.schemas.admin.providers import ProviderType
from api.utils.context import global_context

# ============================================================================
# Real-world Dependencies (matching Albert API patterns)
# ============================================================================


async def get_redis_client() -> AsyncRedis:
    """Get Redis client from global context."""
    return global_context.redis_client


def get_provider_factory():
    """Get the model provider factory."""
    return ModelProviderClientFactory


# ============================================================================
# Example 1: Forward Request Endpoint (Real Implementation)
# ============================================================================

router = APIRouter(prefix="/v1", tags=["model-requests"])


class ForwardRequest(BaseModel):
    """Request to forward to a model provider."""

    provider_id: int
    messages: list[dict[str, str]]
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int | None = None


@router.post("/forward")
async def forward_to_provider(
    request: ForwardRequest,
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: AsyncRedis = Depends(get_redis_client),
    factory=Depends(get_provider_factory),
):
    """
    Forward a request to a model provider.

    This is a real-world example that:
    1. Fetches provider config from database
    2. Creates provider using factory
    3. Forwards request to the provider
    4. Returns response with usage tracking
    """

    # 1. Get provider configuration from database
    from sqlalchemy import select

    from api.sql.models import Provider as ProviderTable

    query = select(ProviderTable).where(ProviderTable.id == request.provider_id)
    result = await postgres_session.execute(query)
    provider_config = result.scalar_one_or_none()

    if not provider_config:
        raise HTTPException(status_code=404, detail=f"Provider {request.provider_id} not found")

    # 2. Create provider using factory
    provider = factory.create(
        provider_type=ProviderType(provider_config.type),
        url=provider_config.url,
        key=provider_config.key,
        timeout=provider_config.timeout,
        model_name=provider_config.model_name,
        model_carbon_footprint_zone=provider_config.model_carbon_footprint_zone,
        model_carbon_footprint_total_params=provider_config.model_carbon_footprint_total_params,
        model_carbon_footprint_active_params=provider_config.model_carbon_footprint_active_params,
    )

    # Set provider metadata (from ModelRegistry pattern)
    provider.id = provider_config.id

    # 3. Forward request to provider
    try:
        if request.stream:
            # Streaming response
            return provider.forward_stream(
                method="POST",
                endpoint="/v1/chat/completions",
                redis_client=redis_client,
                json={
                    "messages": request.messages,
                    "stream": True,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                },
            )
        else:
            # Non-streaming response
            response = await provider.forward_request(
                method="POST",
                endpoint="/v1/chat/completions",
                redis_client=redis_client,
                json={
                    "messages": request.messages,
                    "stream": False,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                },
            )

            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider error: {str(e)}")


# ============================================================================
# Example 2: Admin Endpoint to Test Provider
# ============================================================================


class TestProviderRequest(BaseModel):
    """Request to test a provider configuration."""

    provider_type: ProviderType
    url: str
    key: str | None = None
    model_name: str
    timeout: int = 30


class TestProviderResponse(BaseModel):
    """Response from provider test."""

    reachable: bool
    max_context_length: int | None = None
    vector_size: int | None = None
    error: str | None = None


@router.post("/admin/providers/test")
async def test_provider_connection(
    request: TestProviderRequest,
    factory=Depends(get_provider_factory),
) -> TestProviderResponse:
    """
    Test if a provider is reachable and get its metadata.

    This is useful in admin UI to validate provider configuration
    before saving it to the database.
    """

    try:
        # Create provider
        provider = factory.create(
            provider_type=request.provider_type,
            url=request.url,
            key=request.key,
            timeout=request.timeout,
            model_name=request.model_name,
        )

        # Try to get metadata (checks if provider is reachable)
        max_context_length = await provider.get_max_context_length()

        # For embedding models, get vector size
        from api.schemas.admin.providers import ProviderType

        vector_size = None
        if request.provider_type in [ProviderType.TEI, ProviderType.ALBERT, ProviderType.OPENAI]:
            try:
                vector_size = await provider.get_vector_size()
            except Exception:
                pass  # Not all providers support embeddings

        return TestProviderResponse(
            reachable=True,
            max_context_length=max_context_length,
            vector_size=vector_size,
        )

    except Exception as e:
        return TestProviderResponse(
            reachable=False,
            error=str(e),
        )


# ============================================================================
# Example 3: Router-based Model Selection (like ModelRegistry)
# ============================================================================


class ChatCompletionRequest(BaseModel):
    """Standard OpenAI-compatible chat completion request."""

    model: str  # Can be router name or alias
    messages: list[dict[str, str]]
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int | None = None


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: AsyncRedis = Depends(get_redis_client),
    factory=Depends(get_provider_factory),
):
    """
    OpenAI-compatible chat completions endpoint.

    This mimics the real ModelRegistry.get_model_provider() logic:
    1. Look up router by name/alias
    2. Apply load balancing to select provider
    3. Create provider using factory
    4. Forward request
    """

    # 1. Get router by name or alias
    from sqlalchemy import or_, select

    from api.sql.models import Provider as ProviderTable
    from api.sql.models import Router as RouterTable
    from api.sql.models import RouterAlias as RouterAliasTable

    router_query = (
        select(RouterTable)
        .outerjoin(RouterAliasTable, RouterAliasTable.router_id == RouterTable.id)
        .where(or_(RouterTable.name == request.model, RouterAliasTable.value == request.model))
        .limit(1)
    )

    result = await postgres_session.execute(router_query)
    router = result.scalar_one_or_none()

    if not router:
        raise HTTPException(status_code=404, detail=f"Model '{request.model}' not found")

    # 2. Get providers for this router
    providers_query = select(ProviderTable).where(ProviderTable.router_id == router.id)
    result = await postgres_session.execute(providers_query)
    providers = result.scalars().all()

    if not providers:
        raise HTTPException(status_code=404, detail=f"No providers available for model '{request.model}'")

    # 3. Simple load balancing (in real code, use apply_routing_without_queuing)
    # For this example, just pick the first provider
    provider_config = providers[0]

    # 4. Create provider using factory
    provider = factory.create(
        provider_type=ProviderType(provider_config.type),
        url=provider_config.url,
        key=provider_config.key,
        timeout=provider_config.timeout,
        model_name=provider_config.model_name,
        model_carbon_footprint_zone=provider_config.model_carbon_footprint_zone,
        model_carbon_footprint_total_params=provider_config.model_carbon_footprint_total_params,
        model_carbon_footprint_active_params=provider_config.model_carbon_footprint_active_params,
    )

    # Set metadata from router (for cost calculation)
    provider.id = provider_config.id
    provider.cost_prompt_tokens = router.cost_prompt_tokens
    provider.cost_completion_tokens = router.cost_completion_tokens

    # 5. Forward request
    if request.stream:
        return provider.forward_stream(
            method="POST",
            endpoint="/v1/chat/completions",
            redis_client=redis_client,
            json={
                "messages": request.messages,
                "stream": True,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
        )
    else:
        response = await provider.forward_request(
            method="POST",
            endpoint="/v1/chat/completions",
            redis_client=redis_client,
            json={
                "messages": request.messages,
                "stream": False,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
        )
        return response.json()


# ============================================================================
# Example 4: Background Task with Factory
# ============================================================================


@router.post("/admin/providers/{provider_id}/health-check")
async def health_check_provider(
    provider_id: int,
    postgres_session: AsyncSession = Depends(get_postgres_session),
    factory=Depends(get_provider_factory),
) -> dict:
    """
    Run a health check on a provider.

    This could be run periodically by a background task (Celery)
    to monitor provider availability.
    """

    from sqlalchemy import select

    from api.sql.models import Provider as ProviderTable

    # Get provider config
    query = select(ProviderTable).where(ProviderTable.id == provider_id)
    result = await postgres_session.execute(query)
    provider_config = result.scalar_one_or_none()

    if not provider_config:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Create provider
    provider = factory.create(
        provider_type=ProviderType(provider_config.type),
        url=provider_config.url,
        key=provider_config.key,
        timeout=5,  # Short timeout for health check
        model_name=provider_config.model_name,
    )

    # Check health
    try:
        max_context_length = await provider.get_max_context_length()

        return {
            "provider_id": provider_id,
            "healthy": True,
            "max_context_length": max_context_length,
        }

    except Exception as e:
        return {
            "provider_id": provider_id,
            "healthy": False,
            "error": str(e),
        }


# ============================================================================
# Example 5: Migration Helper - Using Old and New Pattern Side-by-Side
# ============================================================================


@router.post("/debug/compare-patterns")
async def compare_old_and_new_pattern(
    provider_type: ProviderType,
    url: str,
    key: str | None,
    model_name: str,
    factory=Depends(get_provider_factory),
) -> dict:
    """
    Debug endpoint that shows both old and new patterns work the same.

    This is useful during migration to verify behavior is identical.
    """

    import warnings

    # Suppress deprecation warning for this comparison
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)

        # Old pattern (deprecated)
        from api.clients.model import BaseModelProvider

        old_provider_class = BaseModelProvider.import_module(provider_type)
        old_provider = old_provider_class(
            url=url,
            key=key,
            timeout=30,
            model_name=model_name,
            model_carbon_footprint_zone=None,
            model_carbon_footprint_total_params=None,
            model_carbon_footprint_active_params=None,
        )

    # New pattern (recommended)
    new_provider = factory.create(
        provider_type=provider_type,
        url=url,
        key=key,
        timeout=30,
        model_name=model_name,
    )

    return {
        "old_pattern": {
            "class": old_provider.__class__.__name__,
            "model_name": old_provider.name,
            "url": old_provider.url,
        },
        "new_pattern": {
            "class": new_provider.__class__.__name__,
            "model_name": new_provider.name,
            "url": new_provider.url,
        },
        "identical": (
            old_provider.__class__ == new_provider.__class__ and old_provider.name == new_provider.name and old_provider.url == new_provider.url
        ),
    }


# ============================================================================
# Usage in Tests
# ============================================================================


"""
Testing these endpoints with mocked factory:

```python
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
import pytest

@pytest.fixture
def mock_factory():
    factory = Mock()
    mock_provider = Mock()
    mock_provider.name = "test-model"
    mock_provider.forward_request = AsyncMock(
        return_value=Mock(json=lambda: {"choices": [{"message": {"content": "test"}}]})
    )
    factory.create.return_value = mock_provider
    return factory

def test_forward_endpoint(mock_factory):
    # Override dependency
    app.dependency_overrides[get_provider_factory] = lambda: mock_factory

    client = TestClient(app)
    response = client.post("/v1/forward", json={
        "provider_id": 1,
        "messages": [{"role": "user", "content": "test"}],
    })

    assert response.status_code == 200
    mock_factory.create.assert_called_once()
```
"""


# ============================================================================
# Integration with Existing Code
# ============================================================================


"""
To integrate with existing ModelRegistry:

1. In ModelRegistry.get_model_provider():

   OLD:
   ```python
   model_provider = ModelProvider.import_module(type=provider.type)(
       url=provider.url,
       key=provider.key,
       # ...
   )
   ```

   NEW:
   ```python
   from api.clients.model import ModelProviderClientFactory

   model_provider = ModelProviderClientFactory.create(
       provider_type=provider.type,
       url=provider.url,
       key=provider.key,
       # ...
   )
   ```

2. In ModelRegistry.create_provider():

   OLD:
   ```python
   provider = ModelProvider.import_module(type=type)(
       url=url,
       key=key,
       # ...
   )
   max_context_length = await provider.get_max_context_length()
   ```

   NEW:
   ```python
   provider = ModelProviderClientFactory.create(
       provider_type=type,
       url=url,
       key=key,
       # ...
   )
   max_context_length = await provider.get_max_context_length()
   ```

That's it! The rest of the code stays the same.
"""


if __name__ == "__main__":
    print("""
Real-world FastAPI Examples for ModelProviderClientFactory
==========================================================

These examples show how to use the factory in actual Albert API endpoints:

1. Forward Request Endpoint
   - Fetches provider from DB
   - Creates provider with factory
   - Forwards request with usage tracking

2. Admin Provider Test
   - Validates provider configuration
   - Tests connectivity
   - Gets metadata (context length, vector size)

3. Chat Completions (OpenAI-compatible)
   - Router-based model selection
   - Load balancing
   - Streaming support

4. Health Check
   - Background task pattern
   - Periodic monitoring

5. Migration Helper
   - Side-by-side comparison
   - Verification during migration

To use these in your app:
    from examples.real_world_endpoint_example import router
    app.include_router(router)
""")
