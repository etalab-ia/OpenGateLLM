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
    url = factory.Faker("url")
    body = factory.LazyFunction(lambda: {})
    form = factory.LazyFunction(lambda: {})
    files = factory.LazyFunction(lambda: {})

    class Params:
        models = factory.Trait(method=HTTPMethod.GET, url="/v1/models")


# Original response factories
class MistralOriginalResponseFactory(factory.DictFactory):
    class Meta:
        model = OriginalModelResponse

    data = factory.LazyFunction(lambda: {})
    latency = factory.LazyFunction(lambda: None)

    class Params:
        audio_transcription = factory.Trait(
            data=factory.LazyFunction(
                lambda: {
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
                }
            )
        )
        models = factory.Trait(
            data=factory.LazyFunction(
                lambda: {
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
                }
            )
        )
        ocr = factory.Trait(
            data=factory.LazyFunction(
                lambda: {
                    "document_annotation": None,
                    "model": "mistral-ocr-2512",
                    "pages": [
                        {
                            "dimensions": {"dpi": 200, "height": 1969, "width": 1575},
                            "footer": None,
                            "header": None,
                            "hyperlinks": ["http://en.wikibooks.org/", "http://en.wikibooks.org/wiki/Sensory_Systems"],
                            "images": [
                                {
                                    "bottom_right_x": 946,
                                    "bottom_right_y": 1695,
                                    "id": "img-0.jpeg",
                                    "image_annotation": None,
                                    "image_base64": f"data:image/jpeg;base64,{fake.binary(length=64)}",
                                    "top_left_x": 151,
                                    "top_left_y": 1071,
                                }
                            ],
                            "index": 0,
                            "markdown": fake.paragraph(),
                            "tables": [],
                        },
                        {
                            "dimensions": {"dpi": 200, "height": 1969, "width": 1575},
                            "footer": None,
                            "header": None,
                            "hyperlinks": [],
                            "images": [],
                            "index": 1,
                            "markdown": fake.paragraph(),
                            "tables": [],
                        },
                    ],
                    "usage_info": {"doc_size_bytes": 135171, "pages_processed": 2},
                }
            )
        )
