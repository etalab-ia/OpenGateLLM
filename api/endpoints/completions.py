from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from api.helpers._accesscontroller import AccessController
from api.schemas.completions import CompletionRequest, Completions
from api.utils.variables import ENDPOINT__COMPLETIONS
from api.utils.exceptions import TaskFailedException
from api.services.model_invocation import invoke_model_request

router = APIRouter(prefix="/v1", tags=["Legacy"])


@router.post(path=ENDPOINT__COMPLETIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Completions)
async def completions(request: Request, body: CompletionRequest) -> JSONResponse:
    """
    Completion API similar to OpenAI's API.
    """

    user_info = getattr(request.state, "user", None)
    user_priority = getattr(user_info, "priority", 0) if user_info else 0
    try:
        client = await invoke_model_request(model_name=body.model, endpoint=ENDPOINT__COMPLETIONS, user_priority=user_priority)
    except TaskFailedException as e:
        return JSONResponse(content=e.detail, status_code=e.status_code)
    client.endpoint = ENDPOINT__COMPLETIONS
    response = await client.forward_request(method="POST", json=body.model_dump())
    status = response.status_code
    payload = response.json()
    return JSONResponse(content=Completions(**payload).model_dump(), status_code=status)
