from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from api.helpers._accesscontroller import AccessController
from api.schemas.completions import CompletionRequest, Completions
from api.utils.context import global_context
from api.utils.variables import ENDPOINT__COMPLETIONS

router = APIRouter(prefix="/v1", tags=["Legacy"])


@router.post(path=ENDPOINT__COMPLETIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Completions)
async def completions(request: Request, body: CompletionRequest) -> JSONResponse:
    """
    Completion API similar to OpenAI's API.
    """

    async def handler(client):
        response = await client.forward_request(method="POST", json=body.model_dump())
        return JSONResponse(content=Completions(**response.json()).model_dump(), status_code=response.status_code)

    model = await global_context.model_registry(model=body.model)
    return await model.safe_client_access(endpoint=ENDPOINT__COMPLETIONS, handler=handler)
