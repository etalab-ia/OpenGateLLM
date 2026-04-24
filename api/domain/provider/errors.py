from dataclasses import dataclass


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
class ModelProviderNotFoundError:
    model_name: str


@dataclass
class ProviderAlreadyExistsError:
    model_name: str
    url: str
    router_id: int


@dataclass
class ProviderNotFoundError:
    id: int
