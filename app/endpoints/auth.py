from fastapi import APIRouter, Depends, Request, Security, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.schemas.auth import AuthMeResponse
from app.sql.session import get_db_session
from app.utils.context import global_context, request_context
from app.utils.variables import ENDPOINT__AUTH_ME
from app.helpers.auth_encryption import decrypt_playground_data

router = APIRouter()


@router.get(path=ENDPOINT__AUTH_ME, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=AuthMeResponse)
async def get_current_role(request: Request, session: AsyncSession = Depends(get_db_session)) -> JSONResponse:
    """
    Get information about the current user.
    """

    roles = await global_context.identity_access_manager.get_roles(session=session, role_id=request_context.get().role_id)
    users = await global_context.identity_access_manager.get_users(session=session, user_id=request_context.get().user_id)

    return JSONResponse(content={"user": users[0].model_dump(), "role": roles[0].model_dump()}, status_code=200)


@router.post(path="/auth/playground-login")
async def playground_login(request: Request, session: AsyncSession = Depends(get_db_session)):
    """
    Receive encrypted token from playground encoded with shared key via POST body.
    The token contains user id. Refresh and return playground api key associated with the user.
    """
    try:
        # Get encrypted token from JSON body
        try:
            body = await request.json()
        except Exception:
            body = None
        encrypted_token = (body or {}).get("encrypted_token")
        if not encrypted_token:
            raise HTTPException(status_code=400, detail="Missing encrypted_token in request body")

        # Decrypt the token to get user data
        try:
            decrypted_data = decrypt_playground_data(encrypted_token, ttl=600)  # 10 minutes TTL
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        # Extract user ID from decrypted data
        user_id = decrypted_data.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user_id in token")

        # Get user from database
        iam = global_context.identity_access_manager
        user = await iam.get_user(session=session, user_id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Refresh the playground token for this user
        token_id, app_token = await iam.refresh_token(session=session, user_id=user.id, name="playground")

        return {"status": "success", "api_key": app_token, "token_id": token_id, "user_id": user.id}

    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except Exception as e:
        # Fallback protection, although most paths raise HTTPException
        raise HTTPException(status_code=500, detail=f"Playground login failed: {str(e)}")
