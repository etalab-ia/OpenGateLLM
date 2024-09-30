from fastapi import APIRouter, HTTPException, Security
import httpx

from app.schemas.embeddings import Embeddings, EmbeddingsRequest
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from app.utils.variables import EMBEDDINGS_MODEL_TYPE

router = APIRouter()


@router.post("/embeddings")
async def embeddings(request: EmbeddingsRequest, user: str = Security(check_api_key)) -> Embeddings:
    """
    Embedding API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/embeddings/create for the API specification.
    """

    request = dict(request)
    client = clients["models"][request["model"]]
    if client.type != EMBEDDINGS_MODEL_TYPE:
        raise HTTPException(status_code=400, detail=f"Model type must be {EMBEDDINGS_MODEL_TYPE}")

    url = f"{client.base_url}embeddings"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    if not client.check_context_length(model=request["model"], messages=request["messages"]):
        raise HTTPException(status_code=400, detail="Context length too large")

    async_client = httpx.AsyncClient(timeout=20)
    response = await async_client.request(method="POST", url=url, headers=headers, json=request)
    response.raise_for_status()
    data = response.json()
    return Embeddings(**data)
