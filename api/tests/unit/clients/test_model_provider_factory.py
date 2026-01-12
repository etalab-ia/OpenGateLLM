"""
Unit tests for ModelProviderClientFactory.

Tests the explicit factory pattern that replaces the magic import_module() method.
"""

import pytest

from api.clients.model import (
    AlbertModelProvider,
    MistralModelProvider,
    ModelProviderClientFactory,
    OpenaiModelProvider,
    TeiModelProvider,
    VllmModelProvider,
)
from api.schemas.admin.providers import ProviderType


class TestModelProviderClientFactory:
    """Test suite for ModelProviderClientFactory."""

    def test_create_openai_provider(self):
        """Test creating an OpenAI provider."""
        provider = ModelProviderClientFactory.create(
            provider_type=ProviderType.OPENAI,
            url="https://api.openai.com",
            key="sk-test-key",
            timeout=30,
            model_name="gpt-4",
        )

        assert isinstance(provider, OpenaiModelProvider)
        assert provider.name == "gpt-4"
        assert provider.url == "https://api.openai.com"
        assert provider.timeout == 30

    def test_create_mistral_provider(self):
        """Test creating a Mistral provider."""
        provider = ModelProviderClientFactory.create(
            provider_type=ProviderType.MISTRAL,
            url="https://api.mistral.ai",
            key="test-key",
            timeout=60,
            model_name="mistral-large",
        )

        assert isinstance(provider, MistralModelProvider)
        assert provider.name == "mistral-large"

    def test_create_tei_provider(self):
        """Test creating a TEI provider."""
        provider = ModelProviderClientFactory.create(
            provider_type=ProviderType.TEI,
            url="http://localhost:8080",
            key=None,
            timeout=30,
            model_name="bge-base-en-v1.5",
        )

        assert isinstance(provider, TeiModelProvider)
        assert provider.name == "bge-base-en-v1.5"
        assert provider.headers == {}  # No key = no Authorization header

    def test_create_vllm_provider(self):
        """Test creating a vLLM provider."""
        provider = ModelProviderClientFactory.create(
            provider_type=ProviderType.VLLM,
            url="http://localhost:8000",
            key=None,
            timeout=120,
            model_name="meta-llama/Llama-2-7b-chat-hf",
        )

        assert isinstance(provider, VllmModelProvider)

    def test_create_albert_provider(self):
        """Test creating an Albert provider."""
        provider = ModelProviderClientFactory.create(
            provider_type=ProviderType.ALBERT,
            url="https://albert.api.etalab.gouv.fr",
            key="test-key",
            timeout=45,
            model_name="AgentPublic/albertlight-7b",
        )

        assert isinstance(provider, AlbertModelProvider)

    def test_create_with_carbon_footprint_params(self):
        """Test creating a provider with carbon footprint parameters."""
        provider = ModelProviderClientFactory.create(
            provider_type=ProviderType.OPENAI,
            url="https://api.openai.com",
            key="sk-test",
            timeout=30,
            model_name="gpt-4",
            model_carbon_footprint_zone="FRA",
            model_carbon_footprint_total_params=175,
            model_carbon_footprint_active_params=175,
        )

        assert provider.carbon_footprint_zone == "FRA"
        assert provider.carbon_footprint_total_params == 175
        assert provider.carbon_footprint_active_params == 175

    def test_unsupported_provider_type_raises_value_error(self):
        """Test that creating an unsupported provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ModelProviderClientFactory.create(
                provider_type="unsupported_type",  # Invalid type
                url="https://example.com",
                key="test",
                timeout=30,
                model_name="test-model",
            )

        assert "Unsupported provider type" in str(exc_info.value)
        assert "Supported types" in str(exc_info.value)

    def test_get_provider_class(self):
        """Test getting provider class without instantiation."""
        provider_class = ModelProviderClientFactory.get_provider_class(ProviderType.OPENAI)

        assert provider_class is OpenaiModelProvider
        assert issubclass(provider_class, OpenaiModelProvider)

    def test_supported_types(self):
        """Test getting list of supported provider types."""
        supported = ModelProviderClientFactory.supported_types()

        assert ProviderType.OPENAI in supported
        assert ProviderType.MISTRAL in supported
        assert ProviderType.TEI in supported
        assert ProviderType.VLLM in supported
        assert ProviderType.ALBERT in supported
        assert len(supported) == 5

    def test_is_supported(self):
        """Test checking if provider type is supported."""
        assert ModelProviderClientFactory.is_supported(ProviderType.OPENAI) is True
        assert ModelProviderClientFactory.is_supported(ProviderType.MISTRAL) is True

    def test_factory_is_reusable(self):
        """Test that factory can be called multiple times."""
        provider1 = ModelProviderClientFactory.create(
            provider_type=ProviderType.OPENAI,
            url="https://api.openai.com",
            key="key1",
            timeout=30,
            model_name="gpt-4",
        )

        provider2 = ModelProviderClientFactory.create(
            provider_type=ProviderType.OPENAI,
            url="https://api.openai.com",
            key="key2",
            timeout=60,
            model_name="gpt-3.5-turbo",
        )

        # Different instances
        assert provider1 is not provider2
        assert provider1.name == "gpt-4"
        assert provider2.name == "gpt-3.5-turbo"
        assert provider1.timeout == 30
        assert provider2.timeout == 60


class TestBackwardCompatibility:
    """Test backward compatibility with import_module()."""

    def test_import_module_still_works_but_deprecated(self):
        """Test that old import_module() still works but shows deprecation warning."""
        import warnings

        from api.clients.model import BaseModelProvider

        # Capture deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            provider_class = BaseModelProvider.import_module(ProviderType.OPENAI)

            # Check warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            assert "ModelProviderClientFactory" in str(w[0].message)

        # Check it still returns correct class
        assert provider_class is OpenaiModelProvider

    def test_import_module_delegates_to_factory(self):
        """Test that import_module() delegates to factory."""
        import warnings

        from api.clients.model import BaseModelProvider

        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # Both methods should return same class
        class_from_import = BaseModelProvider.import_module(ProviderType.MISTRAL)
        class_from_factory = ModelProviderClientFactory.get_provider_class(ProviderType.MISTRAL)

        assert class_from_import is class_from_factory
        assert class_from_import is MistralModelProvider
