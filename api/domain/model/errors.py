from dataclasses import dataclass


@dataclass
class InconsistentModelVectorSizeError:
    expected_vector_size: int
    actual_vector_size: int
    router_name: str


@dataclass
class ModelNotFoundError:
    name: str


@dataclass
class InconsistentModelMaxContextLengthError:
    expected_max_context_length: int
    actual_max_context_length: int
    router_name: str


@dataclass
class TooBusyModelError:
    status_code: int
    detail: str


@dataclass
class UnknownModelError:
    status_code: int
    detail: str


@dataclass
class StatusCodeModelError:
    status_code: int
    detail: str
