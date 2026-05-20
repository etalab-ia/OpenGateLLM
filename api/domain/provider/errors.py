from dataclasses import dataclass

from api.domain.provider.entities import ProviderType
from api.utils.variables import EndpointRoute


@dataclass
class UnsupportedEndpointError:
    endpoint: EndpointRoute
    provider_type: ProviderType | None = None


@dataclass
class InvalidProviderTypeError:
    provider_type: str
    router_type: str


@dataclass
class ProviderNotReachableError:
    model_name: str
    status_code: int
    detail: str


@dataclass
class ProviderAlreadyExistsError:
    model_name: str
    url: str
    router_id: int


@dataclass
class ProviderNotFoundError:
    id: int
