from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.schemas.auth import AuthMeResponse
from app.sql.session import get_db_session
from app.utils.context import global_context, request_context
from app.utils.variables import ENDPOINT__AUTH_ME

router = APIRouter()


@router.get(path=ENDPOINT__AUTH_ME, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=AuthMeResponse)
async def get_current_role(request: Request, session: AsyncSession = Depends(get_db_session)) -> JSONResponse:
    """
    Get information about the current user.
    """

    roles = await global_context.identity_access_manager.get_roles(session=session, role_id=request_context.get().role_id)
    users = await global_context.identity_access_manager.get_users(session=session, user_id=request_context.get().user_id)

    return JSONResponse(content={"user": users[0].model_dump(), "role": roles[0].model_dump()}, status_code=200)
