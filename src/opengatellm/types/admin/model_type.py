# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing_extensions import Literal, TypeAlias

__all__ = ["ModelType"]

ModelType: TypeAlias = Literal[
    "automatic-speech-recognition",
    "image-text-to-text",
    "image-to-text",
    "text-embeddings-inference",
    "text-generation",
    "text-classification",
]
