import json
from typing import List

import httpx

from api.clients.mcp_bridge import BaseMCPBridgeClient as MCPBridgeClient
from api.helpers.models import ModelRegistry
from api.schemas.agents import AgentsTool, AgentsChatCompletionRequest
from api.utils.exceptions import ToolNotFoundException, TaskFailedException
from api.utils.variables import ENDPOINT__CHAT_COMPLETIONS
from api.services.model_invocation import invoke_model_request


class AgentManager:
    def __init__(self, mcp_bridge: MCPBridgeClient, model_registry: ModelRegistry, max_iterations: int = 2):
        self.model_registry = model_registry
        self.mcp_bridge = mcp_bridge
        self.max_iterations = max_iterations

    async def get_completion(self, body: AgentsChatCompletionRequest):
        body = await self.set_tools_for_llm_request(body)
        http_llm_response = None
        number_of_iterations = 0
        while number_of_iterations < self.max_iterations:
            http_llm_response = await self.get_llm_http_response(body)
            llm_response = json.loads(http_llm_response.text)
            finish_reason = llm_response["choices"][0]["finish_reason"]
            number_of_iterations = number_of_iterations + 1
            if finish_reason in ["stop", "length"]:
                return http_llm_response
            elif finish_reason == "tool_calls":
                tool_config = llm_response["choices"][0]["message"]["tool_calls"][0]["function"]
                tool_name = tool_config["name"]
                tool_args = tool_config["arguments"]

                tool_call_result = await self.mcp_bridge.call_tool(tool_name, tool_args)
                body.messages.append({"role": "user", "content": tool_call_result["content"][0]["text"]})
        last_llm_response = http_llm_response.json()
        last_llm_response["choices"][0]["finish_reason"] = "max_iterations"
        # Some unit tests mock responses without a request object; provide a minimal fallback
        request_obj = None
        try:
            request_obj = http_llm_response.request  # may raise RuntimeError in httpx if unset
        except Exception:
            request_obj = httpx.Request("POST", "http://placeholder")

        llm_response_with_new_finish_reason = httpx.Response(
            status_code=http_llm_response.status_code,
            content=json.dumps(last_llm_response),
            headers=http_llm_response.headers,
            request=request_obj,
        )
        return llm_response_with_new_finish_reason

    async def get_llm_http_response(self, body: AgentsChatCompletionRequest):
        try:
            client = await invoke_model_request(model_name=body.model, endpoint=ENDPOINT__CHAT_COMPLETIONS)
        except TaskFailedException as e:
            return httpx.Response(status_code=e.status_code, content=json.dumps(e.detail))
        client.endpoint = ENDPOINT__CHAT_COMPLETIONS
        response = await client.forward_request(method="POST", json=body.model_dump())
        status = response.status_code
        payload = response.json()
        return httpx.Response(status_code=status, content=json.dumps(payload))

    async def set_tools_for_llm_request(self, body: AgentsChatCompletionRequest) -> AgentsChatCompletionRequest:
        if hasattr(body, "tools") and body.tools is not None:
            tools = await self.get_tools_from_bridge()
            available_tools = [{"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema}} for tool in tools]  # fmt:off

            requested_tools: List[dict] = []
            for tool in body.tools:
                if tool.get("type") is None:
                    continue
                elif tool.get("type") == "function":
                    continue
                # all tools requested
                elif tool.get("type") == "all":
                    requested_tools = available_tools
                    break
                else:
                    # specific tool requested
                    tool_found = False

                    # check if tool is available
                    for available_tool in available_tools:
                        if tool.get("type") == available_tool.get("function").get("name"):
                            tool = available_tool
                            tool_found = True
                            break

                    if not tool_found:
                        raise ToolNotFoundException(f"Tool not found {tool.get("type")}")

                    requested_tools.append(tool)

            body.tool_choice = getattr(body, "tool_choice", "auto")
            body.tools = requested_tools

        return body

    async def get_tools_from_bridge(self) -> List[AgentsTool]:
        tools = await self.mcp_bridge.get_tool_list()

        return tools
