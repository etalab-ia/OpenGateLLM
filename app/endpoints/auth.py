from fastapi import APIRouter, Depends, Request, Security, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.schemas.auth import AuthMeResponse
from app.sql.session import get_db_session
from app.utils.context import global_context, request_context
from app.utils.variables import ENDPOINT__AUTH_ME, ROUTER__AUTH

router = APIRouter()


@router.get(path=ENDPOINT__AUTH_ME, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=AuthMeResponse)
async def get_current_role(request: Request, session: AsyncSession = Depends(get_db_session)) -> JSONResponse:
    """
    Get information about the current user.
    """

    roles = await global_context.identity_access_manager.get_roles(session=session, role_id=request_context.get().role_id)
    users = await global_context.identity_access_manager.get_users(session=session, user_id=request_context.get().user_id)

    return JSONResponse(content={"user": users[0].model_dump(), "role": roles[0].model_dump()}, status_code=200)


@router.post(path=f"/{ROUTER__AUTH}/login")
async def login(request: Request, session: AsyncSession = Depends(get_db_session)):
    """
    Receive encrypted token from playground encoded with shared key via POST body.
    The token contains user id. Refresh and return playground api key associated with the user.
    """
    try:
        body = await request.json()
        user_password = (body or {}).get("password")
        user_email = (body or {}).get("email")

        if not user_email:
            raise HTTPException(status_code=400, detail="Missing user_name in request body")

        # Verify credentials via identity access manager (playground user.name == fastAPI user.email)
        iam = global_context.identity_access_manager
        user = await iam.verify_user_credentials(session=session, email=user_email, password=user_password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Refresh the playground token for this user
        token_id, app_token = await iam.refresh_token(session=session, user_id=user.id, name="playground")

        return {"status": "success", "api_key": app_token, "token_id": token_id, "user_id": user.id}
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except Exception as e:
        # Fallback protection, although most paths raise HTTPException
        raise HTTPException(status_code=500, detail=f"Playground login failed: {str(e)}")
