from fastapi import APIRouter

from api.utils.variables import RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.ME.title()])

from . import info, keys, usage  # noqa F401 E402
