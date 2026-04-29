from http import HTTPMethod

from api.infrastructure.http.model.adapters import (
    AudioTranscriptionAdapter,
    ChatCompletionAdapter,
    EmbeddingsAdapter,
    ModelsAdapter,
    OcrAdapter,
    RerankAdapter,
)

from api.domain.provider.entities import ModelHttpExchange, ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalResponse
from api.infrastructure.fastapi.schemas.models import ModelsResponse
from api.schemas.audio import AudioTranscription, AudioTranscriptionResponseFormat
from api.schemas.chat import ChatCompletion
from api.schemas.embeddings import Embeddings
from api.schemas.ocr import OCR
from api.schemas.rerank import Reranks
from api.schemas.usage import Usage
from api.tests.integration.factories.mistral import MistralOcrResponseFactory
from api.tests.integration.factories.openai import OpenaiModelResponseFactory, OpenaiModelsResponseFactory
from api.tests.integration.factories.tei import TeiEmbeddingsResponseFactory
from api.tests.integration.factories.vllm import VllmAudioTranscriptionsResponseFactory, VllmChatCompletionsResponseFactory, VllmRerankResponseFactory
from api.tests.unit.infrastructure.http.model.factories import ModelHttpExchangeFactory, OriginalModelRequestFactory


class TestAudioTranscriptionAdapter:
    def test_should_format_valid_original_request_with_json_response_format(self):
        # Arrange
        original_request = OriginalModelRequestFactory(audio_transcriptions=True)
        method, url, model_name = HTTPMethod.POST, "https://test.com/v1/audio/transcription", "test-model"
        adapter = AudioTranscriptionAdapter()

        # Act
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=model_name)

        # Assert
        assert result == ProviderFormattedRequest(
            method=method,
            url=url,
            form={
                "model": "test-model",
                "language": "fr",
                "prompt": original_request.form["prompt"],
                "temperature": 0.3,
                "response_format": "json",
            },
            files={"file": ("audio.wav", b"test-audio-content", "audio/wav")},
        )

    def test_should_format_valid_original_request_with_text_response_format(self):
        # Arrange
        original_request = OriginalModelRequestFactory(audio_transcriptions=True)
        original_request.form["response_format"] = AudioTranscriptionResponseFormat.TEXT.value
        method, url, model_name = HTTPMethod.POST, "https://test.com/v1/audio/transcription", "test-model"
        adapter = AudioTranscriptionAdapter()

        # Act
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=model_name)

        # Assert
        assert result == ProviderFormattedRequest(
            method=method,
            url=url,
            form={
                "model": "test-model",
                "language": "fr",
                "prompt": original_request.form["prompt"],
                "temperature": 0.3,
                "response_format": "json",
            },
            files={"file": ("audio.wav", b"test-audio-content", "audio/wav")},
        )

    def test_should_format_valid_original_response_with_json_response_format(self):
        """Using the Vllm response factory because the responses are not overriden by VLLM child provider class (see VllmModelHttpClient)."""
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(audio_transcriptions=True),
            original_response=ProviderOriginalResponse(data=VllmAudioTranscriptionsResponseFactory(), latency=10),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = AudioTranscriptionAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == ProviderFormattedResponse(
            data=AudioTranscription(
                id=mock_request_id,
                model="openweight-audio",
                text=exchange.original_response.data["text"],
                usage=mock_usage.model_dump(),
            ),
        )

    def test_should_format_original_response_with_text_response_format(self):
        """Using the Vllm response factory because the responses are not overriden by VLLM child provider class (see VllmModelHttpClient)."""
        # Arrange
        exchange = ModelHttpExchange(
            original_request=OriginalModelRequestFactory(audio_transcriptions=True),
            original_response=ProviderOriginalResponse(data=VllmAudioTranscriptionsResponseFactory(), latency=10),
        )
        exchange.original_request.form["response_format"] = AudioTranscriptionResponseFormat.TEXT.value
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = AudioTranscriptionAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == ProviderFormattedResponse(text=exchange.original_response.data["text"], data=None)


class TestChatCompletionAdapter:
    def test_should_format_valid_original_request(self):
        # Arrange
        original_request = OriginalModelRequestFactory(chat_completions=True)
        method, url, model_name = HTTPMethod.POST, "https://test.com/v1/chat/completions", "test-model"
        adapter = ChatCompletionAdapter()

        # Act
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=model_name)

        # Assert
        assert result == ProviderFormattedRequest(
            method=method,
            url=url,
            body={
                "model": "test-model",
                "messages": original_request.body["messages"],
                "frequency_penalty": None,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "DummyResponseFormat",
                        "schema": {
                            "properties": {
                                "dummy_list": {"items": {"type": "string"}, "title": "Dummy List", "type": "array"},
                                "dummy_str": {"title": "Dummy Str", "type": "string"},
                                "dummy_optional_bool": {"default": False, "title": "Dummy Optional Bool", "type": "boolean"},
                                "dummy_nullable_int": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "Dummy Nullable Int"},
                            },
                            "required": ["dummy_list", "dummy_str", "dummy_nullable_int"],
                            "title": "DummyResponseFormat",
                            "type": "object",
                        },
                    },
                },
                "tool_choice": "required",
                "tools": [
                    {
                        "type": "function",
                        "name": "get_horoscope",
                        "description": "Get today's horoscope for an astrological sign.",
                        "parameters": {
                            "type": "object",
                            "properties": {"sign": {"type": "string", "description": "An astrological sign like Taurus or Aquarius"}},
                            "required": ["sign"],
                        },
                    },
                ],
                "seed": 10,
                "stop": None,
                "stream": False,
                "logit_bias": None,
                "logprobs": False,
                "top_logprobs": None,
                "presence_penalty": 0.0,
                "max_completion_tokens": None,
                "n": 1,
                "stream_options": None,
                "temperature": None,
                "top_p": None,
                "parallel_tool_calls": False,
                "user": None,
                "search": False,
                "search_args": None,
            },
        )

    def test_should_format_valid_original_response(self):
        """Using the Vllm response factory because the responses are not overriden by VLLM child provider class (see VllmModelHttpClient)."""
        # Arrange
        exchange = ModelHttpExchange(
            original_request=OriginalModelRequestFactory(chat_completions=True),
            original_response=ProviderOriginalResponse(data=VllmChatCompletionsResponseFactory(created=1774879102), latency=10),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = ChatCompletionAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == ProviderFormattedResponse(
            data=ChatCompletion(
                id=mock_request_id,
                model="openweight-large",
                choices=[
                    {
                        "finish_reason": "stop",
                        "index": 0,
                        "logprobs": None,
                        "message": {
                            "annotations": None,
                            "audio": None,
                            "content": exchange.original_response.data["choices"][0]["message"]["content"],
                            "function_call": None,
                            "reasoning": exchange.original_response.data["choices"][0]["message"]["reasoning"],
                            "refusal": None,
                            "role": "assistant",
                            "tool_calls": [],
                        },
                        "stop_reason": None,
                        "token_ids": None,
                    }
                ],
                created=1774879102,
                kv_transfer_params=None,
                object="chat.completion",
                prompt_logprobs=None,
                prompt_token_ids=None,
                service_tier=None,
                system_fingerprint=None,
                usage=mock_usage.model_dump(),
            ),
            text=None,
        )


class TestEmbeddingsAdapter:
    def test_should_format_valid_original_request(self):
        # Arrange
        original_request = OriginalModelRequestFactory(embeddings=True)
        method, url, model_name = HTTPMethod.POST, "https://test.com/v1/embeddings", "test-model"
        adapter = EmbeddingsAdapter()

        # Act
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=model_name)

        # Assert
        assert result == ProviderFormattedRequest(
            method=method,
            url=url,
            body={"model": "test-model", "input": original_request.body["input"], "dimensions": 1536, "encoding_format": "float"},
        )

    def test_should_format_valid_original_response(model_http_client, mocker):
        """Using the TEI response factory because the responses are not overriden by TEI child provider class (see TeiModelHttpClient)."""

        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(embeddings=True),
            original_response=ProviderOriginalResponse(data=TeiEmbeddingsResponseFactory(model_id="tei-model-1234", dimensions=3), latency=10),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = EmbeddingsAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == ProviderFormattedResponse(
            data=Embeddings(
                id=mock_request_id,
                model="openweight-embeddings",
                data=[{"embedding": exchange.original_response.data["data"][0]["embedding"], "index": 0, "object": "embedding"}],
                usage=mock_usage.model_dump(),
            ),
            text=None,
        )


class TestModelsAdapter:
    def test_should_format_valid_original_request(self):
        # Arrange
        original_request = OriginalModelRequestFactory(models=True)
        method, url, model_name = HTTPMethod.GET, "https://test.com/v1/models", "test-model"
        adapter = ModelsAdapter()

        # Act
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=model_name)

        # Assert
        assert result == ProviderFormattedRequest(method=method, url=url)

    def test_should_format_valid_original_response(self):
        """Using the OpenAI response factory because the responses are not overriden by OpenAI child provider class (see OpenaiModelHttpClient)."""

        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(models=True),
            original_response=ProviderOriginalResponse(
                data=OpenaiModelsResponseFactory(
                    data=[
                        OpenaiModelResponseFactory(model_id="gpt-4-0613", created=1686588896, owned_by="openai"),
                        OpenaiModelResponseFactory(model_id="gpt-4", created=1687882411, owned_by="system"),
                    ]
                ),
            ),
        )
        mock_request_id = "request-1234567890"
        mock_usage = None
        adapter = ModelsAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == ProviderFormattedResponse(
            data=ModelsResponse(
                object="list",
                data=[
                    {"created": 1686588896, "type": None, "aliases": [], "id": "gpt-4-0613", "object": "model", "owned_by": "openai"},
                    {"created": 1687882411, "type": None, "aliases": [], "id": "gpt-4", "object": "model", "owned_by": "system"},
                ],
            ),
            text=None,
        )


class TestOcrAdapter:
    def test_should_format_valid_original_request(self):
        # Arrange
        original_request = OriginalModelRequestFactory(ocr=True)
        method, url, model_name = HTTPMethod.POST, "https://test.com/v1/ocr", "test-model"
        adapter = OcrAdapter()

        # Act
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=model_name)

        # Assert
        assert result == ProviderFormattedRequest(
            method=method,
            url=url,
            body={
                "model": "test-model",
                "bbox_annotation_format": None,
                "document": original_request.body["document"],
                "document_annotation_format": None,
                "image_limit": 10,
                "image_min_size": None,
                "include_image_base64": True,
                "pages": [1, 2, 3],
            },
        )

    def test_should_format_valid_original_response(self):
        """Using the Mistral response factory because the responses are not overriden by Mistral child provider class (see MistralModelHttpClient)."""
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(ocr=True),
            original_response=ProviderOriginalResponse(
                data=MistralOcrResponseFactory(page_count=2, usage_info={"doc_size_bytes": 135171, "pages_processed": 2}),
                latency=10,
            ),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = OcrAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == ProviderFormattedResponse(
            data=OCR(
                document_annotation=None,
                id=mock_request_id,
                model="openweight-ocr",
                pages=exchange.original_response.data["pages"],
                usage_info={"doc_size_bytes": 135171, "pages_processed": 2},
                usage=mock_usage.model_dump(),
            ),
            text=None,
        )


class TestRerankAdapter:
    def test_should_format_valid_original_request(self):
        # Arrange
        original_request = OriginalModelRequestFactory(rerank=True)
        method, url, model_name = HTTPMethod.POST, "https://test.com/v1/rerank", "test-model"
        adapter = RerankAdapter()

        # Act
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=model_name)

        # Assert
        assert result == ProviderFormattedRequest(
            method=method,
            url=url,
            body={
                "model": "test-model",
                "query": original_request.body["query"],
                "documents": original_request.body["documents"],
                "top_n": 2,
            },
        )

    def test_should_format_valid_original_response(self):
        """Using the Vllm response factory because the responses are not overriden by VLLM child provider class (see VllmModelHttpClient)."""
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(rerank=True),
            original_response=ProviderOriginalResponse(data=VllmRerankResponseFactory(count=3), latency=10),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = RerankAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == ProviderFormattedResponse(
            data=Reranks(
                id=mock_request_id,
                model="openweight-rerank",
                results=exchange.original_response.data["results"],
                usage=mock_usage.model_dump(),
            )
        )
