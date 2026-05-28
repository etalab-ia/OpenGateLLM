from http import HTTPMethod
from typing import Annotated
from urllib.parse import urljoin
from uuid import uuid4

from pydantic import StringConstraints, ValidationError

from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider.entities import (
    Provider,
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalRequest,
    ProviderOriginalResponse,
)
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.usage.entities import EnvironmentalImpacts, Usage
from api.utils.variables import EndpointRoute


class EndpointAdapter:
    SOURCE_ENDPOINT: EndpointRoute
    TARGET_ENDPOINT_ROUTE: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True)]
    TARGET_ENDPOINT_METHOD: HTTPMethod
    REQUEST_TYPE: type | None
    RESPONSE_TYPE: type | None

    def __init__(
        self,
        cost_completion_tokens: float,
        cost_prompt_tokens: float,
        provider: Provider,
        model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer | None = None,
        model_tokenizer: ModelTokenizer | None = None,
    ):
        self.cost_completion_tokens = cost_completion_tokens
        self.cost_prompt_tokens = cost_prompt_tokens
        self.model_environmental_impacts_computer = model_environmental_impacts_computer
        self.model_tokenizer = model_tokenizer
        self.provider = provider

    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest | ProviderAdapterValidationRequestError:
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)
        formatted_request = ProviderFormattedRequest(
            method=self.TARGET_ENDPOINT_METHOD,
            url=target_url,
            body=original_request.body.model_dump() if original_request.body else {},
            form=original_request.form if original_request.form else {},
            files=original_request.files if original_request.files else {},
        )

        if "model" not in formatted_request.body:
            formatted_request.body["model"] = self.provider.model_name

        return formatted_request

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        prompt_tokens: int = 0,
    ) -> ProviderFormattedResponse | ProviderAdapterValidationResponseError:
        try:
            formatted_response = ProviderFormattedResponse(data=self.RESPONSE_TYPE(**original_response.data), metrics=original_response.metrics)
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        request_id = self._extract_request_id(original_response=original_response)
        formatted_response.data.id = request_id
        formatted_response.data.model = original_request.body.model

        usage = self._compute_usage(formatted_response=formatted_response, prompt_tokens=prompt_tokens)
        formatted_response.data.usage = usage

        return formatted_response

    def _compute_usage(self, formatted_response: ProviderFormattedResponse, prompt_tokens: int) -> Usage:
        completion_tokens = self.compute_completion_tokens(formatted_response=formatted_response)
        total_tokens = prompt_tokens + completion_tokens

        if self.model_environmental_impacts_computer is None:
            environmental_impacts = EnvironmentalImpacts(kgCO2eq=0, kWh=0)
        else:
            environmental_impacts = self.model_environmental_impacts_computer.compute(
                model_active_params=self.provider.model_active_params,
                model_total_params=self.provider.model_total_params,
                model_zone=self.provider.model_hosting_zone,
                completion_tokens=completion_tokens,
                request_latency=formatted_response.metrics.latency,
            )
        cost = self._compute_request_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_prompt_tokens=self.cost_prompt_tokens,
            cost_completion_tokens=self.cost_completion_tokens,
        )

        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            impacts=environmental_impacts,
        )

    def compute_prompt_tokens(self, original_request: ProviderOriginalRequest) -> int:
        if self.model_tokenizer is None:
            return 0

        prompts = original_request.body.get_prompts()
        prompt_tokens = len(self.model_tokenizer.encode(" ".join(prompts).strip()))

        return prompt_tokens

    def compute_completion_tokens(self, formatted_response: ProviderFormattedResponse) -> int:
        if self.model_tokenizer is None:
            return 0

        completions = self.RESPONSE_TYPE.get_completions(formatted_response=formatted_response)
        completion_tokens = len(self.model_tokenizer.encode(" ".join(completions).strip()))

        return completion_tokens

    @staticmethod
    def _compute_request_cost(prompt_tokens: int, completion_tokens: int, cost_prompt_tokens: float, cost_completion_tokens: float) -> float:
        return round(prompt_tokens / 1000000 * cost_prompt_tokens + completion_tokens / 1000000 * cost_completion_tokens, ndigits=6)

    @staticmethod
    def _build_target_url(base_url: str, target_endpoint_route: str | None) -> str:
        base_url = base_url + "/" if not base_url.endswith("/") else base_url
        url = base_url if target_endpoint_route is None else urljoin(base=base_url, url=target_endpoint_route.lstrip("/"))
        return url

    @staticmethod
    def _extract_request_id(original_response: ProviderOriginalResponse) -> str:
        return original_response.data.get("id", f"request-{str(uuid4()).replace('-', '')}")
