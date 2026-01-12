#!/usr/bin/env python3
"""
Examples of using ModelProviderClientFactory.

This file demonstrates the new factory pattern for creating model providers,
replacing the old magic import_module() method.
"""

from api.clients.model import ModelProviderClientFactory
from api.schemas.admin.providers import ProviderType


def example_1_basic_usage():
    """Example 1: Basic usage - creating a provider."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    # Create an OpenAI provider
    provider = ModelProviderClientFactory.create(
        provider_type=ProviderType.OPENAI,
        url="https://api.openai.com",
        key="sk-test-key",
        timeout=30,
        model_name="gpt-4",
    )

    print(f"✅ Created provider: {provider.__class__.__name__}")
    print(f"   Model name: {provider.name}")
    print(f"   URL: {provider.url}")
    print(f"   Timeout: {provider.timeout}")
    print()


def example_2_different_providers():
    """Example 2: Creating different provider types."""
    print("=" * 60)
    print("Example 2: Multiple Provider Types")
    print("=" * 60)

    providers_config = [
        {
            "type": ProviderType.OPENAI,
            "url": "https://api.openai.com",
            "model": "gpt-4",
        },
        {
            "type": ProviderType.MISTRAL,
            "url": "https://api.mistral.ai",
            "model": "mistral-large",
        },
        {
            "type": ProviderType.TEI,
            "url": "http://localhost:8080",
            "model": "bge-base-en-v1.5",
        },
    ]

    for config in providers_config:
        provider = ModelProviderClientFactory.create(
            provider_type=config["type"],
            url=config["url"],
            key="test-key" if config["type"] != ProviderType.TEI else None,
            timeout=30,
            model_name=config["model"],
        )
        print(f"✅ {config['type'].value:10} -> {provider.__class__.__name__}")

    print()


def example_3_with_carbon_footprint():
    """Example 3: Creating provider with carbon footprint parameters."""
    print("=" * 60)
    print("Example 3: With Carbon Footprint Parameters")
    print("=" * 60)

    provider = ModelProviderClientFactory.create(
        provider_type=ProviderType.OPENAI,
        url="https://api.openai.com",
        key="sk-test",
        timeout=30,
        model_name="gpt-4",
        model_carbon_footprint_zone="FRA",  # France datacenter
        model_carbon_footprint_total_params=175,  # GPT-4 has ~175B params
        model_carbon_footprint_active_params=175,
    )

    print("✅ Created provider with carbon tracking:")
    print(f"   Model: {provider.name}")
    print(f"   Zone: {provider.carbon_footprint_zone}")
    print(f"   Total params: {provider.carbon_footprint_total_params}B")
    print(f"   Active params: {provider.carbon_footprint_active_params}B")
    print()


def example_4_error_handling():
    """Example 4: Error handling with unsupported types."""
    print("=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)

    try:
        provider = ModelProviderClientFactory.create(
            provider_type="unsupported_provider",  # Invalid type
            url="https://example.com",
            key="test",
            timeout=30,
            model_name="test-model",
        )
    except ValueError as e:
        print(f"❌ Expected error caught: {e}")

    print()


def example_5_checking_support():
    """Example 5: Checking supported provider types."""
    print("=" * 60)
    print("Example 5: Checking Supported Types")
    print("=" * 60)

    # Get all supported types
    supported = ModelProviderClientFactory.supported_types()
    print(f"Supported provider types ({len(supported)}):")
    for provider_type in supported:
        print(f"  - {provider_type.value}")

    # Check specific type
    print()
    print("Checking specific types:")
    print(f"  OPENAI supported? {ModelProviderClientFactory.is_supported(ProviderType.OPENAI)}")
    print(f"  MISTRAL supported? {ModelProviderClientFactory.is_supported(ProviderType.MISTRAL)}")

    print()


def example_6_getting_class():
    """Example 6: Getting provider class without instantiation."""
    print("=" * 60)
    print("Example 6: Getting Provider Class")
    print("=" * 60)

    # Get class (not instance)
    provider_class = ModelProviderClientFactory.get_provider_class(ProviderType.OPENAI)

    print(f"✅ Got provider class: {provider_class.__name__}")
    print(f"   Base classes: {[c.__name__ for c in provider_class.__bases__]}")

    # Create instance from class
    instance = provider_class(
        url="https://api.openai.com",
        key="sk-test",
        timeout=30,
        model_name="gpt-4",
        model_carbon_footprint_zone=None,
        model_carbon_footprint_total_params=None,
        model_carbon_footprint_active_params=None,
    )

    print(f"✅ Created instance: {instance.name}")
    print()


def example_7_migration_comparison():
    """Example 7: Old vs New pattern comparison."""
    print("=" * 60)
    print("Example 7: Migration Comparison")
    print("=" * 60)

    import warnings

    # OLD WAY (deprecated)
    print("Old way (deprecated):")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from api.clients.model import BaseModelProvider

        provider_class = BaseModelProvider.import_module(ProviderType.OPENAI)
        old_provider = provider_class(
            url="https://api.openai.com",
            key="sk-test",
            timeout=30,
            model_name="gpt-4",
            model_carbon_footprint_zone=None,
            model_carbon_footprint_total_params=None,
            model_carbon_footprint_active_params=None,
        )

        if w:
            print(f"  ⚠️  {w[0].message}")

    print(f"  Created: {old_provider.__class__.__name__}")

    # NEW WAY (recommended)
    print()
    print("New way (recommended):")
    new_provider = ModelProviderClientFactory.create(
        provider_type=ProviderType.OPENAI,
        url="https://api.openai.com",
        key="sk-test",
        timeout=30,
        model_name="gpt-4",
    )

    print(f"  ✅ Created: {new_provider.__class__.__name__}")
    print("  No warnings!")

    print()


def example_8_dynamic_creation():
    """Example 8: Dynamic provider creation (common in ModelRegistry)."""
    print("=" * 60)
    print("Example 8: Dynamic Provider Creation")
    print("=" * 60)

    # Simulating configuration from database
    provider_configs = [
        {
            "type": "openai",
            "url": "https://api.openai.com",
            "key": "sk-key1",
            "model_name": "gpt-4",
            "timeout": 30,
        },
        {
            "type": "mistral",
            "url": "https://api.mistral.ai",
            "key": "key2",
            "model_name": "mistral-large",
            "timeout": 60,
        },
    ]

    print("Creating providers from configuration:")
    for config in provider_configs:
        # Convert string to enum
        provider_type = ProviderType(config["type"])

        provider = ModelProviderClientFactory.create(
            provider_type=provider_type,
            url=config["url"],
            key=config["key"],
            timeout=config["timeout"],
            model_name=config["model_name"],
        )

        print(f"  ✅ {config['model_name']:20} ({config['type']:10}) -> {provider.__class__.__name__}")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" ModelProviderClientFactory Examples")
    print("=" * 60 + "\n")

    example_1_basic_usage()
    example_2_different_providers()
    example_3_with_carbon_footprint()
    example_4_error_handling()
    example_5_checking_support()
    example_6_getting_class()
    example_7_migration_comparison()
    example_8_dynamic_creation()

    print("=" * 60)
    print(" All examples completed! ✅")
    print("=" * 60)
