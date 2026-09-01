from typing import Annotated, Literal

from pydantic import Field, ValidationError

from api.domain import BaseModel
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.rerank.entities import Rerank, RerankResult
from api.infrastructure.http.adapters.rerank import RerankAdapter


class TeiCreateRerankBody(BaseModel):
    query: Annotated[str, Field(..., examples=["What is Deep Learning?"])]
    raw_scores: Annotated[bool, Field(False, examples=[False])]
    return_text: Annotated[bool, Field(False, examples=[False])]
    texts: Annotated[list[str], Field(..., examples=[["Deep Learning is ..."]])]
    truncate: Annotated[bool | None, Field(False, examples=[False])]
    truncation_direction: Literal["left", "right"] = "right"


class TeiRerankAdapter(RerankAdapter):
    TARGET_ENDPOINT_ROUTE = "/rerank"

    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest | ProviderAdapterValidationRequestError:
        try:
            body = TeiCreateRerankBody.model_validate(
                {
                    "query": original_request.payload.query,
                    "texts": original_request.payload.documents,
                    **original_request.payload.model_dump(exclude_none=True),
                }
            ).model_dump()
        except ValidationError as e:
            return ProviderAdapterValidationRequestError(provider_type=self.provider.type, errors=e.errors())

        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)

        return ProviderFormattedRequest(method=self.TARGET_ENDPOINT_METHOD, url=target_url, body=body)

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
    ) -> ProviderFormattedResponse | ProviderAdapterValidationResponseError:
        results = sorted(original_response.data, key=lambda x: x["score"], reverse=True)[: original_request.payload.top_n]
        for result in results:
            result["relevance_score"] = result.pop("score")

        results = [RerankResult(**result) for result in results]
        request_id = self._extract_request_id(original_response=original_response)
        data = Rerank(id=request_id, model=original_request.payload.model, results=results)

        try:
            data = self.RESPONSE_TYPE.model_validate(data)
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        return ProviderFormattedResponse(id=request_id, data=data)
