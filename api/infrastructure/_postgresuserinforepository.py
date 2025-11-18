from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.userinfo import UserInfo
from api.domain.userinfo import UserInfoRepository as UserInfoRepositoryBase


class PostgresUserInfoRepository(UserInfoRepositoryBase):

    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_user_info(self, user_id: int | None = None, email: str | None = None) -> UserInfo:
        assert user_id is not None or email is not None, "user_id or email is required"

        if user_id == 0:  # master user
            user = UserInfo(
                id=0,
                email="master",
                name="master",
                organization=0,
                budget=None,
                permissions=[],
                limits=[],
                expires=None,
                created=0,
                updated=0,
                priority=0,
            )
        else:
            users = await self.get_users(user_id=user_id, email=email)
            user = users[0]

            roles = await self.get_roles(role_id=user.role)
            role = roles[0]

            # user cannot see limits on models that are not accessible by the role
            limits = [limit for limit in role.limits if limit.value is None or limit.value > 0]

            user = UserInfo(
                id=user.id,
                email=user.email,
                name=user.name,
                organization=user.organization,
                budget=user.budget,
                permissions=role.permissions,
                limits=limits,
                expires=user.expires,
                created=user.created,
                updated=user.updated,
                priority=user.priority,
            )

        return user
