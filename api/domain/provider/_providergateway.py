from dataclasses import dataclass


@dataclass
class ProviderCapabilities:
    max_context_length: int | None
    vector_size: int | None = None
