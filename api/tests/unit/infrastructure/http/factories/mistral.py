from http import HTTPMethod

import factory
from faker import Faker

from api.infrastructure.http.model import FormattedModelRequest, OriginalModelResponse

fake = Faker()


# Formatted request factories
class MistralFormattedModelRequestFactory(factory.DictFactory):
    class Meta:
        model = FormattedModelRequest

    method = factory.Faker("random_element", elements=list(HTTPMethod))
    endpoint = factory.Faker("url")
    body = factory.LazyFunction(lambda: {})
    form = factory.LazyFunction(lambda: {})
    files = factory.LazyFunction(lambda: {})

    class Params:
        models = factory.Trait(
            method=HTTPMethod.GET,
            endpoint="/v1/models",
        )


# Original response factories
class MistralAudioTranscriptionOriginalResponseFactory(factory.Factory):
    class Meta:
        model = OriginalModelResponse

    data = factory.LazyFunction(lambda: {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "created": 1773667856,
        "model": "mistral-test-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": fake.paragraph(),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 42,
            "completion_tokens": 128,
            "total_tokens": 170,
        },
    })


class MistralModelsOriginalResponseFactory(factory.Factory):
    class Meta:
        model = OriginalModelResponse

    data = factory.LazyFunction(lambda: {
        "object": "list",
        "data": [
            {
                "id": "mistral-medium-2508",
                "object": "model",
                "created": 1773667856,
                "owned_by": "mistralai",
                "capabilities": {
                    "completion_chat": True,
                    "function_calling": True,
                    "completion_fim": False,
                    "fine_tuning": True,
                    "vision": True,
                    "ocr": False,
                    "classification": False,
                    "moderation": False,
                    "audio": False,
                },
                "name": "mistral-medium-2508",
                "description": "Update on Mistral Medium 3 with improved capabilities.",
                "max_context_length": 131072,
                "aliases": ["mistral-medium-latest"],
                "deprecation": None,
                "deprecation_replacement_model": None,
                "default_model_temperature": 0.3,
                "type": "base",
            },
            {
                "id": "mistral-embed-2312",
                "object": "model",
                "created": 1773667856,
                "owned_by": "mistralai",
                "capabilities": {
                    "completion_chat": False,
                    "function_calling": False,
                    "completion_fim": False,
                    "fine_tuning": False,
                    "vision": False,
                    "ocr": False,
                    "classification": False,
                    "moderation": False,
                    "audio": False,
                },
                "name": "mistral-embed-2312",
                "description": "Our state-of-the-art semantic for extracting representation of text extracts.",
                "max_context_length": 8192,
                "aliases": ["mistral-embed-2312", "mistral-embed-latest"],
                "default_model_temperature": None,
            },
            {
                "id": "mistral-ocr-2512",
                "object": "model",
                "created": 1773667856,
                "owned_by": "mistralai",
                "capabilities": {
                    "completion_chat": False,
                    "function_calling": True,
                    "completion_fim": False,
                    "fine_tuning": False,
                    "vision": True,
                    "ocr": True,
                    "classification": False,
                    "moderation": False,
                    "audio": False,
                },
                "name": "mistral-ocr-2512",
                "description": "Official mistral-ocr-2512 Mistral AI model",
                "max_context_length": 16384,
                "aliases": ["mistral-ocr-latest"],
                "default_model_temperature": 0.0,
            },
        ],
    })


class MistralOriginalResponseFactory:
    def __new__(cls, audio_transcription=False, models=False, **kwargs):
        if audio_transcription:
            return MistralAudioTranscriptionOriginalResponseFactory(**kwargs)
        if models:
            return MistralModelsOriginalResponseFactory(**kwargs)
        return OriginalModelResponse()
