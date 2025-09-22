from fastapi import APIRouter, Request, Security, HTTPException
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
        # Compute number of items in the request according to OpenAI-compatible schema
        input_data = body.input

        def count_items(inp) -> int:
            # A single string or a single token array (List[int]) counts as 1 item
            if isinstance(inp, str):
                return 1
            if isinstance(inp, list):
                if len(inp) == 0:
                    return 0
                first = inp[0]
                # List[str] or List[List[int]] => multiple items
                if isinstance(first, str) or isinstance(first, list):
                    return len(inp)
                # List[int] (tokens) => single item
                return 1
            # Fallback: treat anything else as a single item
            return 1

        items_count = count_items(input_data)
        max_items = getattr(client, "max_items", None)

        if max_items is not None and items_count > max_items:
            raise HTTPException(
                status_code=400,
                detail=f"Too many items in embeddings request: {items_count} provided, maximum allowed is {max_items}. Split the batch into chunks of at most {max_items} items.",
            )

        response = await client.forward_request(method="POST", json=body.model_dump())
        return JSONResponse(content=Embeddings(**response.json()).model_dump(), status_code=response.status_code)

    model = await global_context.model_registry(model=body.model)
    return await model.safe_client_access(endpoint=ENDPOINT__EMBEDDINGS, handler=handler)
