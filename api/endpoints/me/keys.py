from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.schemas.me.keys import CreateKey, CreateKeyResponse, Key, Keys
from api.utils.context import global_context, request_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import ENDPOINT__ME_KEYS, ROUTER__ME

router = APIRouter(prefix="/v1", tags=[ROUTER__ME.title()])


@router.post(path=ENDPOINT__ME_KEYS, dependencies=[Security(dependency=AccessController())], status_code=201, response_model=CreateKeyResponse)
async def create_key(
    request: Request,
    body: CreateKey = Body(description="The token creation request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Create a new API key.
    """

    token_id, token = await global_context.identity_access_manager.create_token(
        postgres_session=postgres_session,
        user_id=request_context.get().user_info.id,
        name=body.name,
        expires=body.expires,
    )

    return JSONResponse(status_code=201, content={"id": token_id, "key": token})


@router.delete(path=ENDPOINT__ME_KEYS + "/{key:path}", dependencies=[Security(dependency=AccessController())], status_code=204)
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


@router.get(path=ENDPOINT__ME_KEYS + "/{key:path}", dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Key)
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


@router.get(path=ENDPOINT__ME_KEYS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Keys)
async def get_keys(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the tokens to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the tokens to get."),
    order_by: Literal["id", "name", "created"] = Query(default="id", description="The field to order the tokens by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the tokens by."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Get all your tokens.
    """

    data = await global_context.identity_access_manager.get_tokens(
        postgres_session=postgres_session,
        user_id=request_context.get().user_info.id,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )
    data = [Key(id=key.id, name=key.name, token=key.token, expires=key.expires, created=key.created) for key in data]

    return JSONResponse(content=Keys(data=data).model_dump(), status_code=200)
