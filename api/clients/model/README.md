# Model Provider Clients

This module provides HTTP clients for communicating with various LLM model providers (OpenAI, Mistral, TEI, vLLM, Albert).

## Architecture

```
api/clients/model/
├── _basemodelprovider.py          # Base class with common functionality
├── _factory.py                    # Factory for creating provider instances ⭐ NEW
├── _openaimodelprovider.py        # OpenAI-specific implementation
├── _mistralmodelprovider.py       # Mistral-specific implementation
├── _teimodelprovider.py           # TEI (Text Embeddings Inference)
├── _vllmmodelprovider.py          # vLLM implementation
└── _albertmodelprovider.py        # Albert-specific implementation
```

## Usage

### ✅ Recommended: Using the Factory

```python
from api.clients.model import ModelProviderClientFactory
from api.schemas.admin.providers import ProviderType

# Create a provider instance
provider = ModelProviderClientFactory.create(
    provider_type=ProviderType.OPENAI,
    url="https://api.openai.com",
    key="sk-...",
    timeout=30,
    model_name="gpt-4",
)

# Use the provider
response = await provider.forward_request(
    method="POST",
    endpoint="/v1/chat/completions",
    redis_client=redis_client,
    json={"messages": [{"role": "user", "content": "Hello!"}]},
)
```

### ❌ Deprecated: Magic Import

```python
from api.clients.model import BaseModelProvider

# DON'T USE THIS - Deprecated!
provider_class = BaseModelProvider.import_module(ProviderType.OPENAI)
provider = provider_class(url=..., key=..., ...)
```

## Factory Benefits

The `ModelProviderClientFactory` provides several advantages over the old `import_module()` method:

| Feature | Old (`import_module()`) | New (`Factory`) |
|---------|------------------------|-----------------|
| Type Safety | ❌ String-based, breaks at runtime | ✅ Type-safe, IDE can follow |
| Refactoring | ❌ Must manually update strings | ✅ IDE updates automatically |
| Error Messages | ❌ Cryptic `ModuleNotFoundError` | ✅ Clear errors with supported types |
| Testing | ❌ Depends on filesystem | ✅ Pure unit tests |
| IDE Support | ❌ No "Go to definition" | ✅ Full IDE support |
| Extensibility | ❌ Convention-based | ✅ Explicit registration |

## Supported Providers

The factory supports the following provider types:

- **OPENAI** - OpenAI API (GPT-4, GPT-3.5, etc.)
- **MISTRAL** - Mistral AI API
- **TEI** - Text Embeddings Inference (HuggingFace)
- **VLLM** - vLLM inference server
- **ALBERT** - Albert API (French government LLM)

Check supported types programmatically:

```python
supported = ModelProviderClientFactory.supported_types()
print(supported)  # [ProviderType.OPENAI, ProviderType.MISTRAL, ...]

is_supported = ModelProviderClientFactory.is_supported(ProviderType.OPENAI)
print(is_supported)  # True
```

## API Reference

### `ModelProviderClientFactory`

#### `.create(provider_type, url, key, timeout, model_name, ...)`

Creates a provider instance.

**Parameters:**
- `provider_type` (ProviderType): Type of provider to create
- `url` (str): Base URL of the provider API
- `key` (str | None): API key (optional for some providers)
- `timeout` (int): Request timeout in seconds
- `model_name` (str): Name of the model to use
- `model_carbon_footprint_zone` (str | None): Zone for carbon calculations
- `model_carbon_footprint_total_params` (int | None): Total model parameters
- `model_carbon_footprint_active_params` (int | None): Active model parameters

**Returns:** An instance of the appropriate provider class

**Raises:** `ValueError` if provider_type is not supported

#### `.get_provider_class(provider_type)`

Gets the provider class without instantiating it.

**Parameters:**
- `provider_type` (ProviderType): Type of provider

**Returns:** The provider class (not an instance)

**Raises:** `ValueError` if provider_type is not supported

#### `.supported_types()`

Returns list of all supported provider types.

**Returns:** `list[ProviderType]`

#### `.is_supported(provider_type)`

Checks if a provider type is supported.

**Parameters:**
- `provider_type` (ProviderType): Type to check

**Returns:** `bool`

#### `.register(provider_type, provider_class)`

Registers a custom provider (for plugins/extensions).

**Parameters:**
- `provider_type` (ProviderType): The provider type enum
- `provider_class` (type[BaseModelProvider]): The provider class

## Examples

See `examples/using_model_provider_factory.py` for comprehensive examples including:

1. Basic usage
2. Creating different provider types
3. Using carbon footprint parameters
4. Error handling
5. Checking supported types
6. Getting provider classes
7. Migration from old pattern
8. Dynamic provider creation

Run examples:
```bash
PYTHONPATH=. python examples/using_model_provider_factory.py
```

## Migration Guide

Migrating from the old `import_module()` pattern? See:

- **Migration Guide**: `docs/migration_model_provider_factory.md`
- **Tests**: `api/tests/unit/clients/test_model_provider_factory.py`

## Dependency Injection

Use with FastAPI dependency injection:

```python
from fastapi import Depends
from api.dependencies import get_model_provider_factory

@app.post("/forward")
async def forward_request(
    factory = Depends(get_model_provider_factory),
):
    provider = factory.create(
        provider_type=ProviderType.OPENAI,
        url="https://api.openai.com",
        key="sk-...",
        timeout=30,
        model_name="gpt-4",
    )
    # ...
```

### FastAPI Endpoint Examples

See comprehensive endpoint examples:

- **Generic patterns**: `examples/fastapi_endpoint_example.py`
  - 7 different dependency injection patterns
  - Simple to advanced usage
  - Multiple providers handling
  - Query parameter configuration

- **Real-world integration**: `examples/real_world_endpoint_example.py`
  - Integration with Redis, Postgres
  - Router-based model selection (like ModelRegistry)
  - Provider health checks
  - Admin endpoints for testing providers
  - Migration helpers

Run the example server:
```bash
python examples/fastapi_endpoint_example.py
# Then visit http://localhost:8000/docs
```

## Testing

Run tests:

```bash
# Run factory tests
pytest api/tests/unit/clients/test_model_provider_factory.py -v

# Check for deprecation warnings
pytest -W error::DeprecationWarning
```

## Custom Providers

To add a custom provider (for plugins):

```python
class MyCustomProvider(BaseModelProvider):
    ENDPOINT_TABLE = {
        # Define endpoints...
    }

    # Implement required methods...

# Register it
ModelProviderClientFactory.register(
    ProviderType.CUSTOM,
    MyCustomProvider,
)

# Use it
provider = ModelProviderClientFactory.create(
    provider_type=ProviderType.CUSTOM,
    url="https://my-api.com",
    key="key",
    timeout=30,
    model_name="my-model",
)
```

## Backward Compatibility

The old `import_module()` method is deprecated but still works during the migration period. It delegates to the factory internally.

**Timeline:**
- **2026-01-08**: Factory introduced, `import_module()` deprecated
- **TBD**: Migration of existing code
- **TBD**: Removal of `import_module()`

## Contributing

When adding a new provider:

1. Create `_<provider>modelprovider.py` implementing `BaseModelProvider`
2. Add to factory registry in `_factory.py`
3. Export in `__init__.py`
4. Add tests in `test_model_provider_factory.py`
5. Update this README

## Related Documentation

- **Base Provider**: `_basemodelprovider.py` - Common functionality
- **Provider Types**: `api/schemas/admin/providers.py` - ProviderType enum
- **Usage Tracking**: How usage/cost/carbon is calculated
- **Clean Architecture**: `adr/001-clean-architecture-migration.md`