from fastapi import Body, Depends, Path, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role.entities import PermissionType
from api.endpoints.admin import router
from api.helpers._accesscontroller import AccessController
from api.schemas.admin.tokens import CreateToken, TokensResponse
from api.utils.context import global_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute


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
    path=EndpointRoute.ADMIN_TOKENS + "/{token}",
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
