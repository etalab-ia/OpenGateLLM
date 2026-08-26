from typing import Literal

from pydantic import Field, ValidationError

from api.domain import BaseModel
from api.domain.provider.entities import ProviderRawResponse, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.rerank.entities import Rerank, RerankResult
from api.infrastructure.http._httpproviderrequest import HttpProviderRequest
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

    def to_http_request(self, request: ProviderRequest) -> HttpProviderRequest | ProviderAdapterValidationRequestError:
        try:
            body = TeiCreateRerankBody.model_validate(
                {
                    "query": request.payload.query,
                    "texts": request.payload.documents,
                    **request.payload.model_dump(exclude_none=True),
                }
            ).model_dump()
        except ValidationError as e:
            return ProviderAdapterValidationRequestError(provider_type=self.provider.type, errors=e.errors())

        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)

        return HttpProviderRequest(method=self.TARGET_ENDPOINT_METHOD, url=target_url, body=body)

    def to_domain_response(
        self,
        raw_response: ProviderRawResponse,
        request: ProviderRequest,
    ) -> ProviderResponse | ProviderAdapterValidationResponseError:
        results = sorted(raw_response.data, key=lambda x: x["score"], reverse=True)[: request.payload.top_n]
        for result in results:
            result["relevance_score"] = result.pop("score")

        results = [RerankResult(**result) for result in results]
        request_id = self._extract_request_id(raw_response=raw_response)
        data = Rerank(id=request_id, model=request.payload.model, results=results)

        try:
            data = self.RESPONSE_TYPE.model_validate(data)
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        return ProviderResponse(id=request_id, data=data)
