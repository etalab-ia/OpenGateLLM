from typing import Literal, Optional

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.schemas.admin.roles import PermissionType
from app.schemas.admin.tokens import Token, TokenRequest, Tokens, TokensResponse
from app.sql.session import get_db_session
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__ADMIN_TOKENS

router = APIRouter()


@router.post(
    path=ENDPOINT__ADMIN_TOKENS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=201,
    response_model=TokensResponse,
)
async def create_token(
    request: Request,
    body: TokenRequest = Body(description="The token creation request."),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Create a new token.
    """

    token_id, token = await global_context.identity_access_manager.create_token(
        session=session,
        user_id=body.user,
        name=body.name,
        expires_at=body.expires_at,
    )

    return JSONResponse(status_code=201, content={"id": token_id, "token": token})


@router.delete(
    path=ENDPOINT__ADMIN_TOKENS + "/{token:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def delete_token(
    request: Request,
    user: int = Path(description="The user ID of the user to delete the token for."),
    token: int = Path(description="The token ID of the token to delete."),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Delete a token.
    """

    await global_context.identity_access_manager.delete_token(session=session, user_id=user, token_id=token)

    return Response(status_code=204)


@router.get(
    path=ENDPOINT__ADMIN_TOKENS + "/{token:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
    response_model=Token,
)
async def get_token(
    request: Request,
    token: int = Path(description="The token ID of the token to get."),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Get your token by id.
    """

    tokens = await global_context.identity_access_manager.get_tokens(session=session, token_id=token)

    return JSONResponse(content=tokens[0].model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__ADMIN_TOKENS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
    response_model=Tokens,
)
async def get_tokens(
    request: Request,
    user: Optional[int] = Query(default=None, description="The user ID of the user to get the tokens for."),
    offset: int = Query(default=0, ge=0, description="The offset of the tokens to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the tokens to get."),
    order_by: Literal["id", "name", "created_at"] = Query(default="id", description="The field to order the tokens by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the tokens by."),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Get all your tokens.
    """

    data = await global_context.identity_access_manager.get_tokens(
        session=session,
        user_id=user,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )

    return JSONResponse(content=Tokens(data=data).model_dump(), status_code=200)
