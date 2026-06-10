from prometheus_client.parser import text_string_to_metric_families

from api.domain.provider.entities import (
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderMetrics,
    ProviderOriginalRequest,
    ProviderOriginalResponse,
)
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.infrastructure.http.adapters.metrics import MetricsAdapter


class MistralMetricsAdapter(MetricsAdapter):
    # TEMPORARY PATCH FOR MISTRAL METRICS ENDPOINT
    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest:
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)
        formatted_request = ProviderFormattedRequest(method=self.TARGET_ENDPOINT_METHOD, url=target_url, auth=self.provider.basic_auth)

        return formatted_request

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
    ) -> ProviderFormattedResponse | ProviderAdapterValidationResponseError:
        try:
            families = list(text_string_to_metric_families(text=original_response.text))
        except ValueError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=[{"msg": str(e)}])

        running_requests, waiting_requests = 0.0, 0.0
        for family in families:
            for sample in family.samples:
                if sample.name == "vllm:num_requests_running" and sample.labels.get("model_name") == self.provider.model_name:
                    running_requests += sample.value
                elif sample.name == "vllm:num_requests_waiting" and sample.labels.get("model_name") == self.provider.model_name:
                    waiting_requests += sample.value

        return ProviderFormattedResponse(data=ProviderMetrics(waiting_requests=waiting_requests, running_requests=running_requests))
