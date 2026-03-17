from api.domain.user import UserRepository


class HasAdminUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self) -> bool:
        return await self.user_repository.has_admin_user()
