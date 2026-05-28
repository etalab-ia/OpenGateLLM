from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.domain.provider.errors import ProviderAdapterValidationRequestError
from api.domain.rerank.entities import Rerank, RerankResult
from api.infrastructure.http.adapters import (
    AudioTranscriptionsAdapter,
    ChatCompletionsAdapter,
    EmbeddingsAdapter,
    ModelsAdapter,
    OcrAdapter,
    RerankAdapter,
)


class TeiCreateRerankBody(BaseModel):
    query: str = Field(..., examples=["What is Deep Learning?"])
    raw_scores: bool = Field(False, examples=[False])
    return_text: bool = Field(False, examples=[False])
    texts: list[str] = Field(..., examples=[["Deep Learning is ..."]])
    truncate: bool | None = Field(False, examples=[False])
    truncation_direction: Literal["left", "right"] = "right"


class TeiAudioTranscriptionAdapter(AudioTranscriptionsAdapter):
    TARGET_ENDPOINT_ROUTE = None


class TeiChatCompletionAdapter(ChatCompletionsAdapter):
    TARGET_ENDPOINT_ROUTE = None


class TeiEmbeddingsAdapter(EmbeddingsAdapter):
    pass


class TeiModelsAdapter(ModelsAdapter):
    TARGET_ENDPOINT_ROUTE = "/info"

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        prompt_tokens: int = 0,
    ) -> ProviderFormattedResponse:
        return ProviderFormattedResponse(
            data=Models(
                data=[
                    Model(
                        id=original_response.data["model_id"],
                        created=0,
                        owned_by="tei",
                        max_context_length=original_response.data["max_input_length"],
                        type=ModelType.TEXT_GENERATION,  # dummy value, not used
                    )
                ]
            ),
            metrics=original_response.metrics,
        )


class TeiOcrAdapter(OcrAdapter):
    TARGET_ENDPOINT_ROUTE = None


class TeiRerankAdapter(RerankAdapter):
    TARGET_ENDPOINT_ROUTE = "/rerank"

    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest | ProviderAdapterValidationRequestError:
        try:
            body = TeiCreateRerankBody.model_validate({"query": original_request.body.query, "texts": original_request.body.documents})
        except ValidationError as e:
            return ProviderAdapterValidationRequestError(provider_type=self.provider.type, errors=e.errors())

        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)

        return ProviderFormattedRequest(method=self.TARGET_ENDPOINT_METHOD, url=target_url, body=body.model_dump())

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        prompt_tokens: int = 0,
    ) -> ProviderFormattedResponse:
        results = sorted(original_response.data, key=lambda x: x["score"], reverse=True)[: original_request.body.top_n]
        results = [RerankResult(relevance_score=rank["score"], index=rank["index"]) for rank in results]
        request_id = f"request-{str(uuid4()).replace('-', '')}"

        formatted_response = ProviderFormattedResponse(
            data=Rerank(
                id=request_id,
                model=original_request.body.model,
                results=results,
            ),
            metrics=original_response.metrics,
        )

        usage = self._compute_usage(formatted_response=formatted_response, prompt_tokens=prompt_tokens)
        formatted_response.data.usage = usage

        return formatted_response
