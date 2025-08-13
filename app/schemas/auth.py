from app.schemas import BaseModel
from app.schemas.admin.roles import Role
from app.schemas.admin.users import User


class AuthMeResponse(BaseModel):
    user: User
    role: Role
