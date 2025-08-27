from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.helpers._accesscontroller import AccessController
from app.schemas.admin.roles import PermissionType
from app.sql.models import Token as TokenTable
from app.sql.session import get_db_session

router = APIRouter()


@router.get(path="/admin/ui-users", dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))], status_code=200)
async def get_ui_users(request: Request, session: AsyncSession = Depends(get_db_session)) -> JSONResponse:
    """Return a list of API user IDs that have a token named 'playground'.

    This endpoint is intended for the UI to quickly determine which users have a Playground API key.
    """
    # Select distinct user_id from token table where name == 'playground' and token not expired
    stmt = (
        select(TokenTable.user_id)
        .where(
            TokenTable.name == "playground",
            or_(TokenTable.expires_at.is_(None), TokenTable.expires_at >= func.now()),
        )
        .distinct()
    )

    result = await session.execute(stmt)
    user_ids = [row[0] for row in result.fetchall()]

    return JSONResponse(content={"data": user_ids}, status_code=200)
