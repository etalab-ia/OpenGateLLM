from fastapi import APIRouter

from api.utils.variables import RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.ADMIN.title()])

from . import keys, providers, roles, routers, sso, users  # noqa: F401 E402
