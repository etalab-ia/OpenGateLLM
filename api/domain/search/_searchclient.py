from abc import ABC, abstractmethod

from api.domain.search.entities import SearchArgs, Searches
from api.domain.search.errors import SearchStatusCodeError, SearchUnreachableError

type SearchClientResult = Searches | SearchStatusCodeError | SearchUnreachableError


class SearchClient(ABC):
    @abstractmethod
    async def search(self, key_value: str, query: str, args: SearchArgs) -> SearchClientResult:
        pass
