from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.auth import Login, LoginResponse
from api.utils.context import global_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.AUTH.title()])


@router.post(path=EndpointRoute.AUTH_LOGIN)
async def login(request: Request, body: Login, postgres_session: AsyncSession = Depends(get_postgres_session)) -> LoginResponse:
    """
    Receive encrypted token from playground encoded with shared key via POST body.
    The token contains user id. Refresh and return playground api key associated with the user.
    """

    token_id, token = await global_context.identity_access_manager.login(postgres_session=postgres_session, email=body.email, password=body.password)

    return JSONResponse(status_code=200, content=LoginResponse(id=token_id, key=token).model_dump())
