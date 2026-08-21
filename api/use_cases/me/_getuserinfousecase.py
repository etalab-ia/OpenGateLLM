from dataclasses import dataclass

from api.domain.user.views import AuthenticatedUserView


@dataclass
class GetUserInfoCommand:
    authenticated_user: AuthenticatedUserView


@dataclass
class GetUserInfoUseCaseSuccess:
    authenticated_user: AuthenticatedUserView


type GetUserInfoUseCaseResult = GetUserInfoUseCaseSuccess


class GetUserInfoUseCase:
    async def execute(self, command: GetUserInfoCommand) -> GetUserInfoUseCaseResult:
        return GetUserInfoUseCaseSuccess(authenticated_user=command.authenticated_user)
