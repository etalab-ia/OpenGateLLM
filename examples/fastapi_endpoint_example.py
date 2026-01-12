"""
Example FastAPI endpoints using ModelProviderClientFactory.

This demonstrates how to use the factory in real FastAPI endpoints
with proper dependency injection.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.clients.model import ModelProviderClientFactory
from api.schemas.admin.providers import ProviderType

# ============================================================================
# Request/Response Models
# ============================================================================


class ChatRequest(BaseModel):
    """Request body for chat completion."""

    provider_type: ProviderType
    provider_url: str
    provider_key: str | None = None
    model_name: str
    messages: list[dict[str, str]]
    timeout: int = 30


class ChatResponse(BaseModel):
    """Response for chat completion."""

    model: str
    content: str
    provider_type: str


# ============================================================================
# Example 1: Direct Factory Usage in Endpoint
# ============================================================================

router = APIRouter(prefix="/examples", tags=["examples"])


@router.post("/chat/simple")
async def chat_simple(request: ChatRequest) -> ChatResponse:
    """
    Simple example: Create provider directly in endpoint.

    This is the most straightforward approach - create the provider
    when you need it.
    """

    # Create provider using factory
    provider = ModelProviderClientFactory.create(
        provider_type=request.provider_type,
        url=request.provider_url,
        key=request.provider_key,
        timeout=request.timeout,
        model_name=request.model_name,
    )

    # Use provider (simplified - in real code you'd need redis_client)
    # response = await provider.forward_request(
    #     method="POST",
    #     endpoint="/v1/chat/completions",
    #     redis_client=redis_client,
    #     json={"messages": request.messages},
    # )

    # For this example, just return a mock response
    return ChatResponse(
        model=provider.name,
        content=f"Response from {provider.name}",
        provider_type=request.provider_type.value,
    )


# ============================================================================
# Example 2: Factory as Dependency
# ============================================================================


def get_factory():
    """
    Dependency that provides the factory.

    This is useful when you want to inject the factory itself
    rather than a specific provider instance.
    """
    return ModelProviderClientFactory


@router.post("/chat/with-factory-dependency")
async def chat_with_factory(
    request: ChatRequest,
    factory=Depends(get_factory),
) -> ChatResponse:
    """
    Example with factory injected as dependency.

    The factory is injected by FastAPI, making it easy to mock in tests.
    """

    # Create provider from injected factory
    provider = factory.create(
        provider_type=request.provider_type,
        url=request.provider_url,
        key=request.provider_key,
        timeout=request.timeout,
        model_name=request.model_name,
    )

    return ChatResponse(
        model=provider.name,
        content=f"Response from {provider.name} (via injected factory)",
        provider_type=request.provider_type.value,
    )


# ============================================================================
# Example 3: Pre-configured Provider Dependency
# ============================================================================


def get_openai_provider(api_key: str = "sk-default"):
    """
    Dependency that provides a pre-configured OpenAI provider.

    This is useful when you have a fixed configuration and want
    to inject a ready-to-use provider.
    """
    return ModelProviderClientFactory.create(
        provider_type=ProviderType.OPENAI,
        url="https://api.openai.com",
        key=api_key,
        timeout=30,
        model_name="gpt-4",
    )


class SimpleRequest(BaseModel):
    """Simple request with just messages."""

    messages: list[dict[str, str]]


@router.post("/chat/openai-only")
async def chat_openai(
    request: SimpleRequest,
    provider=Depends(get_openai_provider),
) -> ChatResponse:
    """
    Example with pre-configured provider dependency.

    The provider is already configured for OpenAI, so the endpoint
    only needs to focus on business logic.
    """

    # Provider is ready to use!
    return ChatResponse(
        model=provider.name,
        content=f"Response from {provider.name}",
        provider_type="openai",
    )


# ============================================================================
# Example 4: Dynamic Provider from Query Parameter
# ============================================================================


def create_provider_from_params(
    provider_type: str,
    url: str,
    model_name: str,
    api_key: str | None = None,
    timeout: int = 30,
):
    """
    Dependency that creates provider from query parameters.

    This allows clients to specify provider configuration via query params.
    """
    try:
        provider_type_enum = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider type: {provider_type}. " f"Supported: {[p.value for p in ModelProviderClientFactory.supported_types()]}",
        )

    return ModelProviderClientFactory.create(
        provider_type=provider_type_enum,
        url=url,
        key=api_key,
        timeout=timeout,
        model_name=model_name,
    )


@router.post("/chat/dynamic")
async def chat_dynamic(
    request: SimpleRequest,
    provider=Depends(create_provider_from_params),
) -> ChatResponse:
    """
    Example with dynamic provider configuration from query params.

    Usage:
        POST /chat/dynamic?provider_type=openai&url=https://api.openai.com&model_name=gpt-4&api_key=sk-...

    The provider is created based on query parameters, making this
    endpoint very flexible.
    """

    return ChatResponse(
        model=provider.name,
        content=f"Dynamic response from {provider.name}",
        provider_type="dynamic",
    )


# ============================================================================
# Example 5: Multiple Providers Pattern
# ============================================================================


class MultiProviderRequest(BaseModel):
    """Request for multiple providers."""

    messages: list[dict[str, str]]
    providers: list[dict[str, str]]  # List of {type, url, model_name}


@router.post("/chat/multi-provider")
async def chat_multi_provider(
    request: MultiProviderRequest,
    factory=Depends(get_factory),
) -> list[ChatResponse]:
    """
    Example using multiple providers in parallel.

    This demonstrates how to create multiple providers and use them
    concurrently (in a real implementation, you'd use asyncio.gather).
    """

    responses = []

    for provider_config in request.providers:
        try:
            # Create provider for each config
            provider = factory.create(
                provider_type=ProviderType(provider_config["type"]),
                url=provider_config["url"],
                key=provider_config.get("key"),
                timeout=30,
                model_name=provider_config["model_name"],
            )

            # In real code, you'd call provider.forward_request here
            responses.append(
                ChatResponse(
                    model=provider.name,
                    content=f"Response from {provider.name}",
                    provider_type=provider_config["type"],
                )
            )

        except ValueError as e:
            # Skip invalid providers
            continue

    return responses


# ============================================================================
# Example 6: Provider Info Endpoint
# ============================================================================


class ProviderInfo(BaseModel):
    """Provider information."""

    type: str
    supported: bool
    class_name: str | None = None


@router.get("/providers/info")
async def get_providers_info(factory=Depends(get_factory)) -> list[ProviderInfo]:
    """
    Get information about all supported providers.

    This demonstrates how to use the factory's metadata methods.
    """

    all_types = [
        ProviderType.OPENAI,
        ProviderType.MISTRAL,
        ProviderType.TEI,
        ProviderType.VLLM,
        ProviderType.ALBERT,
    ]

    info = []
    for provider_type in all_types:
        is_supported = factory.is_supported(provider_type)

        provider_info = ProviderInfo(
            type=provider_type.value,
            supported=is_supported,
        )

        if is_supported:
            provider_class = factory.get_provider_class(provider_type)
            provider_info.class_name = provider_class.__name__

        info.append(provider_info)

    return info


@router.get("/providers/supported")
async def get_supported_providers(factory=Depends(get_factory)) -> list[str]:
    """
    Get list of supported provider types.

    Simple endpoint that returns supported provider types as strings.
    """

    return [p.value for p in factory.supported_types()]


# ============================================================================
# Example 7: Provider Validation Endpoint
# ============================================================================


class ValidateProviderRequest(BaseModel):
    """Request to validate a provider configuration."""

    provider_type: str
    url: str
    model_name: str
    api_key: str | None = None


class ValidationResult(BaseModel):
    """Result of provider validation."""

    valid: bool
    error: str | None = None
    provider_class: str | None = None


@router.post("/providers/validate")
async def validate_provider(
    request: ValidateProviderRequest,
    factory=Depends(get_factory),
) -> ValidationResult:
    """
    Validate that a provider can be created with given configuration.

    This is useful for validating user input before saving configuration.
    """

    try:
        # Try to create the provider
        provider_type = ProviderType(request.provider_type)

        if not factory.is_supported(provider_type):
            return ValidationResult(
                valid=False,
                error=f"Provider type not supported: {request.provider_type}",
            )

        provider = factory.create(
            provider_type=provider_type,
            url=request.url,
            key=request.api_key,
            timeout=5,  # Short timeout for validation
            model_name=request.model_name,
        )

        return ValidationResult(
            valid=True,
            provider_class=provider.__class__.__name__,
        )

    except ValueError as e:
        return ValidationResult(
            valid=False,
            error=str(e),
        )
    except Exception as e:
        return ValidationResult(
            valid=False,
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )


# ============================================================================
# Testing Tips
# ============================================================================


# To test these endpoints, you can use pytest with FastAPI TestClient:
#
# from fastapi.testclient import TestClient
# from unittest.mock import Mock
#
# def test_chat_with_factory_mock():
#     """Test endpoint with mocked factory."""
#
#     # Create mock factory
#     mock_factory = Mock()
#     mock_provider = Mock()
#     mock_provider.name = "test-model"
#     mock_factory.create.return_value = mock_provider
#
#     # Override dependency
#     app.dependency_overrides[get_factory] = lambda: mock_factory
#
#     # Test endpoint
#     client = TestClient(app)
#     response = client.post("/chat/with-factory-dependency", json={...})
#
#     assert response.status_code == 200
#     mock_factory.create.assert_called_once()


# ============================================================================
# Usage Example
# ============================================================================


if __name__ == "__main__":
    """
    To run this example:

    1. Add to your FastAPI app:
        from examples.fastapi_endpoint_example import router
        app.include_router(router)

    2. Start the server:
        uvicorn api.main:app --reload

    3. Test with curl:
        curl -X POST http://localhost:8000/examples/chat/simple \\
          -H "Content-Type: application/json" \\
          -d '{
            "provider_type": "openai",
            "provider_url": "https://api.openai.com",
            "provider_key": "sk-...",
            "model_name": "gpt-4",
            "messages": [{"role": "user", "content": "Hello!"}],
            "timeout": 30
          }'

    4. Or use the interactive docs:
        http://localhost:8000/docs
    """

    from fastapi import FastAPI
    import uvicorn

    app = FastAPI(title="ModelProviderClientFactory Examples")
    app.include_router(router)

    print("=" * 60)
    print("Starting example server...")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
