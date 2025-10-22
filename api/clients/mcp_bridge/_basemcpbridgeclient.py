from abc import ABC, abstractmethod
import importlib

from api.schemas.agents import AgentsTool
from api.schemas.core.configuration import MCPBridgeType


class BaseMCPBridgeClient(ABC):
    @staticmethod
    def import_module(type: MCPBridgeType) -> "type[BaseMCPBridgeClient]":
        """
        Import the module for the given MCP bridge type.
        """
        module = importlib.import_module(f"api.clients.mcp_bridge._{type.value}mcpbridgeclient")
        return getattr(module, f"{type.capitalize()}MCPBridgeClient")

    def __init__(self, url: str, headers: dict[str, str], timeout: int, *args, **kwargs):
        self.url = url
        self.headers = headers
        self.timeout = timeout

    @abstractmethod
    async def get_tool_list(self) -> list[AgentsTool]:
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, params: str):
        pass
