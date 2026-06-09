from api.domain.provider.entities import ProviderFormattedRequest, ProviderOriginalRequest
from api.infrastructure.http.adapters.chat import ChatCompletionsAdapter


class MistralChatCompletionsAdapter(ChatCompletionsAdapter):
    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest:
        # @TODO: build body with model_fields_set to exclude unset fields
        # see https://docs.mistral.ai/api#operation-chat_completion_v1_chat_completions_post
        body = {
            "frequency_penalty": original_request.body.frequency_penalty or 0.0,
            "max_tokens": original_request.body.max_tokens,
            "messages": original_request.body.messages,
            "model": self.provider.model_name,
            "n": original_request.body.n,
            "parallel_tool_calls": original_request.body.parallel_tool_calls or False,
            "prediction": original_request.body.prediction or {},
            "presence_penalty": original_request.body.presence_penalty or 0.0,
            "prompt_mode": original_request.body.prompt_mode,
            "random_seed": original_request.body.random_seed or original_request.body.seed,
            "response_format": original_request.body.response_format or {"type": "text"},
            "safe_prompt": original_request.body.safe_prompt or False,
            "stop": original_request.body.stop or [],
            "stream": original_request.body.stream or False,
            "temperature": original_request.body.temperature,
            "tool_choice": original_request.body.tool_choice,
            "tools": original_request.body.tools,
            "top_p": original_request.body.top_p or 1.0,
        }
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)

        return ProviderFormattedRequest(method=self.TARGET_ENDPOINT_METHOD, url=target_url, body=body)
