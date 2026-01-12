# Migration Guide: ModelProviderClientFactory

## Overview

This guide explains how to migrate from the old `BaseModelProvider.import_module()` magic method to the new explicit `ModelProviderClientFactory`.

## Why Migrate?

The old `import_module()` method has several issues:

- ❌ **String-based imports**: Fragile, breaks at runtime if files renamed
- ❌ **No IDE support**: Can't "Go to definition" or refactor
- ❌ **Cryptic errors**: `ModuleNotFoundError` doesn't explain what went wrong
- ❌ **Hard to test**: Depends on filesystem structure
- ❌ **Convention over configuration**: Requires exact naming patterns

The new factory provides:

- ✅ **Type-safe**: IDE can follow references
- ✅ **Explicit**: All providers visible in one place
- ✅ **Clear errors**: Descriptive error messages with supported types
- ✅ **Testable**: Easy to mock and test
- ✅ **Refactorable**: IDE updates all references automatically

## Migration Examples

### Example 1: Simple Migration

**Before (deprecated):**
```python
from api.clients.model import BaseModelProvider
from api.schemas.admin.providers import ProviderType

# Magic import - fragile!
provider_class = BaseModelProvider.import_module(ProviderType.OPENAI)
provider = provider_class(
    url="https://api.openai.com",
    key="sk-...",
    timeout=30,
    model_name="gpt-4",
    model_carbon_footprint_zone="WOR",
    model_carbon_footprint_total_params=None,
    model_carbon_footprint_active_params=None,
)
```

**After (recommended):**
```python
from api.clients.model import ModelProviderClientFactory
from api.schemas.admin.providers import ProviderType

# Explicit factory - type-safe!
provider = ModelProviderClientFactory.create(
    provider_type=ProviderType.OPENAI,
    url="https://api.openai.com",
    key="sk-...",
    timeout=30,
    model_name="gpt-4",
    model_carbon_footprint_zone="WOR",
    model_carbon_footprint_total_params=None,
    model_carbon_footprint_active_params=None,
)
```

### Example 2: Migration in ModelRegistry

**Before:**
```python
# api/helpers/models/_modelregistry.py
class ModelRegistry:
    async def create_provider(self, router_id, type, url, key, ...):
        # Magic import
        provider = ModelProvider.import_module(type=type)(
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_carbon_footprint_zone=model_carbon_footprint_zone,
            model_carbon_footprint_total_params=model_carbon_footprint_total_params,
            model_carbon_footprint_active_params=model_carbon_footprint_active_params,
        )

        max_context_length = await provider.get_max_context_length()
        # ...
```

**After:**
```python
# api/helpers/models/_modelregistry.py
from api.clients.model import ModelProviderClientFactory

class ModelRegistry:
    async def create_provider(self, router_id, type, url, key, ...):
        # Explicit factory
        provider = ModelProviderClientFactory.create(
            provider_type=type,
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_carbon_footprint_zone=model_carbon_footprint_zone,
            model_carbon_footprint_total_params=model_carbon_footprint_total_params,
            model_carbon_footprint_active_params=model_carbon_footprint_active_params,
        )

        max_context_length = await provider.get_max_context_length()
        # ...
```

### Example 3: Using with FastAPI Dependency Injection

**New pattern for endpoints:**
```python
from fastapi import APIRouter, Depends
from api.dependencies import get_model_provider_factory

router = APIRouter()

@router.post("/forward")
async def forward_request(
    request: RequestBody,
    factory = Depends(get_model_provider_factory),
):
    """Forward request to model provider."""

    # Create provider on demand
    provider = factory.create(
        provider_type=request.provider_type,
        url=request.url,
        key=request.key,
        timeout=30,
        model_name=request.model_name,
    )

    response = await provider.forward_request(
        method="POST",
        endpoint="/v1/chat/completions",
        redis_client=...,
        json=request.json_body,
    )

    return response
```

### Example 4: Testing with Factory

**Before (hard to test):**
```python
def test_create_provider():
    # Had to ensure actual files exist
    provider_class = BaseModelProvider.import_module(ProviderType.OPENAI)
    assert provider_class.__name__ == "OpenaiModelProvider"
```

**After (easy to test):**
```python
def test_create_provider():
    # Pure unit test, no filesystem needed
    provider = ModelProviderClientFactory.create(
        provider_type=ProviderType.OPENAI,
        url="https://api.openai.com",
        key="sk-test",
        timeout=30,
        model_name="gpt-4",
    )

    assert isinstance(provider, OpenaiModelProvider)
    assert provider.name == "gpt-4"
    assert provider.url == "https://api.openai.com"
```

## Migration Checklist

### Phase 1: Add Factory (✅ Done)
- [x] Create `ModelProviderClientFactory` in `api/clients/model/_factory.py`
- [x] Export factory in `api/clients/model/__init__.py`
- [x] Add dependency injection helpers in `api/dependencies.py`
- [x] Deprecate `import_module()` but keep it working
- [x] Add comprehensive tests

### Phase 2: Migrate Existing Code
- [ ] Find all usages of `import_module()`:
  ```bash
  grep -r "import_module" api/
  ```
- [ ] Replace with `ModelProviderClientFactory.create()`
- [ ] Update tests to use factory
- [ ] Verify no deprecation warnings:
  ```bash
  pytest -W error::DeprecationWarning
  ```

### Phase 3: Remove Old Method
- [ ] Once all code migrated, remove `import_module()` entirely
- [ ] Remove `importlib` import from `_basemodelprovider.py`
- [ ] Update documentation

## Finding Usages to Migrate

```bash
# Find all import_module() usages
grep -rn "import_module" api/ --include="*.py" | grep -v test | grep -v "__pycache__"

# Check for deprecation warnings
python -W error::DeprecationWarning -m pytest api/tests/
```

## Common Migration Patterns

### Pattern 1: Direct instantiation
```python
# Before
cls = BaseModelProvider.import_module(provider_type)
instance = cls(url=..., key=..., ...)

# After
instance = ModelProviderClientFactory.create(
    provider_type=provider_type,
    url=...,
    key=...,
    ...,
)
```

### Pattern 2: Getting class (not instance)
```python
# Before
cls = BaseModelProvider.import_module(provider_type)
# Use cls for something...

# After
cls = ModelProviderClientFactory.get_provider_class(provider_type)
# Use cls for something...
```

### Pattern 3: Dynamic provider creation
```python
# Before
for provider_config in providers:
    cls = BaseModelProvider.import_module(provider_config.type)
    provider = cls(**provider_config.dict())

# After
for provider_config in providers:
    provider = ModelProviderClientFactory.create(
        provider_type=provider_config.type,
        **provider_config.dict()
    )
```

## Troubleshooting

### Import Error
**Error:** `Cannot find reference 'ModelProviderClientFactory'`

**Solution:** Make sure you import from the correct module:
```python
from api.clients.model import ModelProviderClientFactory
```

### Type Error
**Error:** `Expected ProviderType, got str`

**Solution:** Convert string to enum:
```python
from api.schemas.admin.providers import ProviderType

provider_type = ProviderType(provider_type_string)
```

### Deprecation Warning
**Warning:** `DeprecationWarning: import_module() is deprecated`

**Solution:** Replace with factory:
```python
# Instead of:
cls = BaseModelProvider.import_module(type)

# Use:
provider = ModelProviderClientFactory.create(provider_type=type, ...)
```

## FAQ

**Q: Can I still use `import_module()` during migration?**

A: Yes, it's deprecated but still works. It now delegates to the factory internally.

**Q: Will this break my existing code?**

A: No, the old method still works. You'll just see deprecation warnings.

**Q: How do I suppress deprecation warnings temporarily?**

A: Use warnings filter (not recommended for production):
```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
```

**Q: Can I register custom providers?**

A: Yes, use `ModelProviderClientFactory.register()`:
```python
class MyCustomProvider(BaseModelProvider):
    pass

ModelProviderClientFactory.register(
    ProviderType.CUSTOM,
    MyCustomProvider
)
```

## Timeline

- **2026-01-08**: Factory introduced, `import_module()` deprecated
- **TBD**: Migration of existing code
- **TBD**: Remove `import_module()` entirely

## Support

If you encounter issues during migration:
1. Check this guide
2. Review test examples in `api/tests/unit/clients/test_model_provider_factory.py`
3. Ask in team chat