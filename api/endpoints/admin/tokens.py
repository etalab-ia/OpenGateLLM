from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.schemas.admin.roles import PermissionType
from api.schemas.admin.tokens import CreateToken, Token, Tokens, TokensResponse
from api.utils.context import global_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.ADMIN.title()])


@router.post(
    path=EndpointRoute.ADMIN_TOKENS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=201,
    response_model=TokensResponse,
)
async def create_token(
    request: Request,
    body: CreateToken = Body(description="The token creation request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Create a new token.
    """

    token_id, token = await global_context.identity_access_manager.create_token(
        postgres_session=postgres_session,
        user_id=body.user,
        name=body.name,
        expires=body.expires,
    )

    return JSONResponse(status_code=201, content={"id": token_id, "token": token})


@router.delete(
    path=EndpointRoute.ADMIN_TOKENS + "/{token:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def delete_token(
    request: Request,
    user: int = Path(description="The user ID of the user to delete the token for."),
    token: int = Path(description="The token ID of the token to delete."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    """
    Delete a token.
    """

    await global_context.identity_access_manager.delete_token(postgres_session=postgres_session, user_id=user, token_id=token)

    return Response(status_code=204)


@router.get(
    path=EndpointRoute.ADMIN_TOKENS + "/{token:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
    response_model=Token,
)
async def get_token(
    request: Request,
    token: int = Path(description="The token ID of the token to get."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Get your token by id.
    """

    tokens = await global_context.identity_access_manager.get_tokens(postgres_session=postgres_session, token_id=token)

    return JSONResponse(content=tokens[0].model_dump(), status_code=200)


@router.get(
    path=EndpointRoute.ADMIN_TOKENS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
    response_model=Tokens,
)
async def get_tokens(
    request: Request,
    user: int | None = Query(default=None, description="The user ID of the user to get the tokens for."),
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
        user_id=user,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )

    return JSONResponse(content=Tokens(data=data).model_dump(), status_code=200)
