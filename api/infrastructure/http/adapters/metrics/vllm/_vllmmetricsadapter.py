from prometheus_client.parser import text_string_to_metric_families

from api.domain.provider.entities import ProviderMetrics, ProviderRawResponse, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.infrastructure.http.adapters.metrics import MetricsAdapter


class VllmMetricsAdapter(MetricsAdapter):
    def to_domain_response(
        self,
        raw_response: ProviderRawResponse,
        request: ProviderRequest,
    ) -> ProviderResponse | ProviderAdapterValidationResponseError:
        try:
            families = list(text_string_to_metric_families(text=raw_response.text))
        except ValueError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=[{"msg": str(e)}])

        running_requests, waiting_requests = 0.0, 0.0
        for family in families:
            for sample in family.samples:
                if sample.name == "vllm:num_requests_running" and sample.labels.get("model_name") == self.provider.model_name:
                    running_requests += sample.value
                elif sample.name == "vllm:num_requests_waiting" and sample.labels.get("model_name") == self.provider.model_name:
                    waiting_requests += sample.value

        request_id = self._extract_request_id(raw_response=raw_response)

        return ProviderResponse(id=request_id, data=ProviderMetrics(waiting_requests=waiting_requests, running_requests=running_requests))
