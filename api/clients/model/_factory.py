"""
Model Provider Client Factory.

Explicit factory for creating model provider clients.
Replaces the magic import_module() method with type-safe, explicit mapping.
"""

import logging
from typing import TYPE_CHECKING

from api.schemas.admin.providers import ProviderType

if TYPE_CHECKING:
    from api.clients.model._basemodelprovider import BaseModelProvider

logger = logging.getLogger(__name__)


class ModelProviderClientFactory:
    """
    Factory for creating model provider clients.

    This replaces the magic import_module() pattern with explicit,
    type-safe creation of provider instances.

    Benefits:
    - Type-safe: IDE can follow references
    - Explicit: All providers visible in one place
    - Testable: Easy to mock and test
    - Clear errors: Descriptive error messages
    - Refactorable: Rename class → IDE updates everywhere
    """

    # Lazy-loaded registry to avoid circular imports
    _REGISTRY: dict[ProviderType, type["BaseModelProvider"]] | None = None

    @classmethod
    def _initialize_registry(cls) -> None:
        """
        Initialize the provider registry.

        Lazy initialization to avoid circular import issues.
        Called on first use of the factory.
        """
        if cls._REGISTRY is not None:
            return

        # Import providers here to avoid circular imports
        from api.clients.model._albertmodelprovider import AlbertModelProvider
        from api.clients.model._mistralmodelprovider import MistralModelProvider
        from api.clients.model._openaimodelprovider import OpenaiModelProvider
        from api.clients.model._teimodelprovider import TeiModelProvider
        from api.clients.model._vllmmodelprovider import VllmModelProvider

        cls._REGISTRY = {
            ProviderType.ALBERT: AlbertModelProvider,
            ProviderType.MISTRAL: MistralModelProvider,
            ProviderType.OPENAI: OpenaiModelProvider,
            ProviderType.TEI: TeiModelProvider,
            ProviderType.VLLM: VllmModelProvider,
        }

        logger.debug(f"Initialized ModelProviderClientFactory with {len(cls._REGISTRY)} providers")

    @classmethod
    def create(
        cls,
        provider_type: ProviderType,
        url: str,
        key: str | None,
        timeout: int,
        model_name: str,
        model_carbon_footprint_zone: str | None = None,
        model_carbon_footprint_total_params: int | None = None,
        model_carbon_footprint_active_params: int | None = None,
    ) -> "BaseModelProvider":
        """
        Create a model provider client instance.

        Args:
            provider_type: Type of provider (OPENAI, MISTRAL, etc.)
            url: Base URL of the provider API
            key: API key (optional for some providers)
            timeout: Request timeout in seconds
            model_name: Name of the model to use
            model_carbon_footprint_zone: Zone for carbon footprint calculation
            model_carbon_footprint_total_params: Total params for carbon footprint
            model_carbon_footprint_active_params: Active params for carbon footprint

        Returns:
            An instance of the appropriate provider client

        Raises:
            ValueError: If provider_type is not supported

        Example:
            >>> client = ModelProviderClientFactory.create(
            ...     provider_type=ProviderType.OPENAI,
            ...     url="https://api.openai.com",
            ...     key="sk-...",
            ...     timeout=30,
            ...     model_name="gpt-4",
            ... )
            >>> isinstance(client, OpenaiModelProvider)
            True
        """
        # Ensure registry is initialized
        cls._initialize_registry()

        # Get provider class from registry
        provider_class = cls._REGISTRY.get(provider_type)

        if provider_class is None:
            supported_types = list(cls._REGISTRY.keys())
            raise ValueError(f"Unsupported provider type: {provider_type}. " f"Supported types: {supported_types}")

        # Create and return instance
        return provider_class(
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_carbon_footprint_zone=model_carbon_footprint_zone,
            model_carbon_footprint_total_params=model_carbon_footprint_total_params,
            model_carbon_footprint_active_params=model_carbon_footprint_active_params,
        )

    @classmethod
    def get_provider_class(cls, provider_type: ProviderType) -> type["BaseModelProvider"]:
        """
        Get the provider class without instantiating it.

        This is useful for compatibility with code that expects a class
        rather than an instance (e.g., the old import_module() pattern).

        Args:
            provider_type: Type of provider

        Returns:
            The provider class

        Raises:
            ValueError: If provider_type is not supported
        """
        cls._initialize_registry()

        provider_class = cls._REGISTRY.get(provider_type)

        if provider_class is None:
            supported_types = list(cls._REGISTRY.keys())
            raise ValueError(f"Unsupported provider type: {provider_type}. " f"Supported types: {supported_types}")

        return provider_class

    @classmethod
    def register(
        cls,
        provider_type: ProviderType,
        provider_class: type["BaseModelProvider"],
    ) -> None:
        """
        Register a new provider type.

        This allows plugins or extensions to register custom providers
        at runtime.

        Args:
            provider_type: The provider type enum value
            provider_class: The provider class to register

        Example:
            >>> class CustomProvider(BaseModelProvider):
            ...     pass
            >>> ModelProviderClientFactory.register(
            ...     ProviderType.CUSTOM,
            ...     CustomProvider
            ... )
        """
        cls._initialize_registry()
        cls._REGISTRY[provider_type] = provider_class
        logger.info(f"Registered custom provider: {provider_type}")

    @classmethod
    def supported_types(cls) -> list[ProviderType]:
        """
        Get list of supported provider types.

        Returns:
            List of all registered provider types
        """
        cls._initialize_registry()
        return list(cls._REGISTRY.keys())

    @classmethod
    def is_supported(cls, provider_type: ProviderType) -> bool:
        """
        Check if a provider type is supported.

        Args:
            provider_type: The provider type to check

        Returns:
            True if supported, False otherwise
        """
        cls._initialize_registry()
        return provider_type in cls._REGISTRY
