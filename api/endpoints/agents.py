from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from api.helpers._accesscontroller import AccessController
from api.schemas.agents import AgentsChatCompletion, AgentsChatCompletionRequest, AgentsTools
from api.utils.context import global_context
from api.utils.variables import ENDPOINT__AGENTS_COMPLETIONS, ENDPOINT__AGENTS_TOOLS, ROUTER__AGENTS

router = APIRouter(prefix="/v1", tags=[ROUTER__AGENTS.title()])


@router.post(path=ENDPOINT__AGENTS_COMPLETIONS, dependencies=[Security(dependency=AccessController())], response_model=AgentsChatCompletion)
async def agents_completions(request: Request, body: AgentsChatCompletionRequest) -> JSONResponse:
    """
    Creates a model response for the given chat conversation with call to the MCP bridge.
    """

    response = await global_context.agent_manager.get_completion(body)

    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get(path=ENDPOINT__AGENTS_TOOLS, dependencies=[Security(dependency=AccessController())], response_model=AgentsTools)
async def agents_tools(request: Request) -> JSONResponse:
    """
    Returns the list of tools available in the MCP bridge.
    """

    response = await global_context.agent_manager.get_tools_from_bridge()

    return JSONResponse(content=AgentsTools(data=response).model_dump(), status_code=200)
