from fastapi import Depends, Path, Request, Response, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.me import router
from api.helpers._accesscontroller import AccessController
from api.schemas.me.keys import Key
from api.utils.context import global_context, request_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute


@router.delete(path=EndpointRoute.ME_KEYS + "/{key}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def delete_key(
    request: Request,
    key: int = Path(description="The key ID of the key to delete."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    """
    Delete a API key.
    """

    await global_context.identity_access_manager.delete_token(
        postgres_session=postgres_session, user_id=request_context.get().user_info.id, token_id=key
    )

    return Response(status_code=204)


@router.get(path=EndpointRoute.ME_KEYS + "/{key}", dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Key)
async def get_key(
    request: Request,
    key: int = Path(description="The key ID of the key to get."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Get your token by id.
    """

    keys = await global_context.identity_access_manager.get_tokens(
        postgres_session=postgres_session, user_id=request_context.get().user_info.id, token_id=key
    )
    key = keys[0]
    key = Key(id=key.id, name=key.name, token=key.token, expires=key.expires, created=key.created)

    return JSONResponse(content=key.model_dump(), status_code=200)
