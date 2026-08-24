from fastapi import Depends, Path, Request, Response, Security
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.me import router
from api.helpers._accesscontroller import AccessController
from api.utils.context import global_context, request_context
from api.utils.dependencies import get_postgres_session


@router.delete(path="/me/keys" + "/{key}", dependencies=[Security(dependency=AccessController())], status_code=204)
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
