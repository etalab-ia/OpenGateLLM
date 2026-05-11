from dataclasses import dataclass

from api.domain.provider.entities import ProviderType
from api.utils.variables import EndpointRoute


@dataclass
class InconsistentModelVectorSizeError:
    expected_vector_size: int
    actual_vector_size: int
    router_name: str


@dataclass
class ModelNotFoundError:
    pass


@dataclass
class InconsistentModelMaxContextLengthError:
    expected_max_context_length: int
    actual_max_context_length: int
    router_name: str


# @TODO: move to provider.errors.py
@dataclass
class UnsupportedEndpointError:
    endpoint: EndpointRoute
    provider_type: ProviderType | None = None
