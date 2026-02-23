from fastapi import APIRouter
from starlette.responses import JSONResponse

from api.utils.variables import RouterName

router = APIRouter(tags=[RouterName.HEALTH.title()])


@router.get(path="/health")
def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok"}, status_code=200)
