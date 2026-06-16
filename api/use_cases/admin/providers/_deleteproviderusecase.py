from dataclasses import dataclass

from api.domain.provider import ProviderRepository
from api.domain.provider.entities import Provider
from api.domain.provider.errors import ProviderNotFoundError


@dataclass
class DeleteProviderCommand:
    provider_id: int


@dataclass
class DeleteProviderUseCaseSuccess:
    deleted_provider: Provider


type DeleteProviderUseCaseResult = DeleteProviderUseCaseSuccess | ProviderNotFoundError


class DeleteProviderUseCase:
    def __init__(self, provider_repository: ProviderRepository):
        self.provider_repository = provider_repository

    async def execute(self, command: DeleteProviderCommand) -> DeleteProviderUseCaseResult:
        provider = await self.provider_repository.delete_provider(command.provider_id)

        match provider:
            case Provider() as deleted_provider:
                return DeleteProviderUseCaseSuccess(deleted_provider=deleted_provider)
            case ProviderNotFoundError(id=not_found_id):
                return ProviderNotFoundError(id=not_found_id)
