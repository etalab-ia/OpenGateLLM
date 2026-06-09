from typing import Literal

from pydantic import Field, ValidationError

from api.domain import BaseModel
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.rerank.entities import Rerank, RerankResult
from api.infrastructure.http.adapters.rerank import RerankAdapter


class TeiCreateRerankBody(BaseModel):
    query: str = Field(..., examples=["What is Deep Learning?"])
    raw_scores: bool = Field(False, examples=[False])
    return_text: bool = Field(False, examples=[False])
    texts: list[str] = Field(..., examples=[["Deep Learning is ..."]])
    truncate: bool | None = Field(False, examples=[False])
    truncation_direction: Literal["left", "right"] = "right"


class TeiRerankAdapter(RerankAdapter):
    TARGET_ENDPOINT_ROUTE = "/rerank"

    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest | ProviderAdapterValidationRequestError:
        try:
            body = TeiCreateRerankBody.model_validate(
                {
                    "query": original_request.body.query,
                    "texts": original_request.body.documents,
                    **original_request.body.model_dump(),
                }
            )
        except ValidationError as e:
            return ProviderAdapterValidationRequestError(provider_type=self.provider.type, errors=e.errors())

        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)

        return ProviderFormattedRequest(method=self.TARGET_ENDPOINT_METHOD, url=target_url, body=body.model_dump())

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        prompt_tokens: int = 0,
        latency: int = 0,
    ) -> ProviderFormattedResponse:
        results = sorted(original_response.data, key=lambda x: x["score"], reverse=True)[: original_request.body.top_n]
        for result in results:
            result["relevance_score"] = result.pop("score")

        results = [RerankResult(**result) for result in results]
        request_id = self._extract_request_id(original_response=original_response)
        data = Rerank(id=request_id, model=original_request.body.model, results=results)

        try:
            data = self.RESPONSE_TYPE.model_validate(data)
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        formatted_response = ProviderFormattedResponse(data=data)
        usage = self._compute_usage(prompt_tokens=prompt_tokens, completion_tokens=0, latency=latency)
        formatted_response.data.usage = usage

        return formatted_response
