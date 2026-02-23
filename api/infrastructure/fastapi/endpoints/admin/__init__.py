from fastapi import APIRouter

from api.utils.variables import RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.ADMIN.title()])

from . import providers, routers  # noqa: F401 E402
