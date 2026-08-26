from api.domain.provider.entities import ProviderRequest
from api.infrastructure.http import HttpProviderRequest
from api.infrastructure.http.adapters.chat import ChatCompletionsAdapter


class MistralChatCompletionsAdapter(ChatCompletionsAdapter):
    def to_http_request(self, request: ProviderRequest) -> HttpProviderRequest:
        body = request.payload.model_dump(exclude_none=True)
        body["random_seed"] = body["random_seed"] or body["seed"]
        supported_fields = [
            "frequency_penalty",
            "max_tokens",
            "messages",
            "model",
            "n",
            "parallel_tool_calls",
            "prediction",
            "presence_penalty",
            "prompt_mode",
            "random_seed",
            "response_format",
            "safe_prompt",
            "stop",
            "stream",
            "temperature",
            "tool_choice",
            "tools",
            "top_p",
        ]
        # TODO: check body format with SDK model
        body = {key: value for key, value in body.items() if key in supported_fields}
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)

        return HttpProviderRequest(method=self.TARGET_ENDPOINT_METHOD, url=target_url, body=body)
