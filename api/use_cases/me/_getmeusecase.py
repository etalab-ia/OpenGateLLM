from dataclasses import dataclass

from api.domain.user.views import AuthenticatedUserView


@dataclass
class GetMeCommand:
    authenticated_user: AuthenticatedUserView


@dataclass
class GetMeUseCaseSuccess:
    authenticated_user: AuthenticatedUserView


type GetMeUseCaseResult = GetMeUseCaseSuccess


class GetMeUseCase:
    async def execute(self, command: GetMeCommand) -> GetMeUseCaseResult:
        return GetMeUseCaseSuccess(authenticated_user=command.authenticated_user)
