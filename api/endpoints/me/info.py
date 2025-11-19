from fastapi import APIRouter, Body, Depends, Request, Response, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.schemas.me.info import UpdateUserInfo, UserInfo
from api.utils.context import global_context, request_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import ENDPOINT__ME_INFO, ROUTER__ME

router = APIRouter(prefix="/v1", tags=[ROUTER__ME.title()])


@router.get(path=ENDPOINT__ME_INFO, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=UserInfo)
async def get_user(request: Request, postgres_session: AsyncSession = Depends(get_postgres_session)) -> JSONResponse:
    """
    Get information about the current user.
    """

    user_info = await global_context.identity_access_manager.get_user_info(
        postgres_session=postgres_session, user_id=request_context.get().user_info.id
    )

    return JSONResponse(content=user_info.model_dump(), status_code=200)


@router.patch(path=ENDPOINT__ME_INFO, dependencies=[Security(dependency=AccessController())], status_code=204)
async def update_user(
    request: Request,
    body: UpdateUserInfo = Body(description="The user update request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    """
    Update information about the current user.
    """

    await global_context.identity_access_manager.update_user(
        postgres_session=postgres_session,
        user_id=request_context.get().user_info.id,
        email=body.email,
        name=body.name,
        current_password=body.current_password,
        password=body.password,
    )

    return Response(status_code=204)
