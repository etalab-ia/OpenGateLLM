from api.schemas import BaseModel
from api.schemas.admin.roles import Role
from api.schemas.admin.users import User


class AuthMeResponse(BaseModel):
    user: User
    role: Role
