from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from api.helpers._accesscontroller import AccessController
from api.schemas.embeddings import Embeddings, EmbeddingsRequest
from api.utils.context import global_context
from api.utils.variables import ENDPOINT__EMBEDDINGS, ROUTER__EMBEDDINGS

router = APIRouter(prefix="/v1", tags=[ROUTER__EMBEDDINGS.title()])


@router.post(path=ENDPOINT__EMBEDDINGS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Embeddings)
async def embeddings(request: Request, body: EmbeddingsRequest) -> JSONResponse:
    """
    Creates an embedding vector representing the input text.
    """

    async def handler(client):
        response = await client.forward_request(method="POST", json=body.model_dump())
        return JSONResponse(content=Embeddings(**response.json()).model_dump(), status_code=response.status_code)

    model = await global_context.model_registry(model=body.model)
    return await model.safe_client_access(endpoint=ENDPOINT__EMBEDDINGS, handler=handler)
