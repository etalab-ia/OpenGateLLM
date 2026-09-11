from json import JSONDecodeError
import logging

import httpx
from pydantic import ValidationError

from api.domain.search import SearchClient, SearchClientResult
from api.domain.search.entities import SearchArgs, Searches
from api.domain.search.errors import SearchStatusCodeError, SearchUnreachableError

logger = logging.getLogger(__name__)


class HttpSearchClient(SearchClient):
    SEARCH_ENDPOINT_ROUTE = "/v1/search"
    TIMEOUT = 60

    def __init__(self, url: str) -> None:
        self.url = url

    async def search(self, key_value: str, query: str, args: SearchArgs) -> SearchClientResult:
        async with httpx.AsyncClient() as async_client:
            try:
                response = await async_client.post(
                    url=f"{self.url}{self.SEARCH_ENDPOINT_ROUTE}",
                    headers={"Authorization": f"Bearer {key_value}"},
                    json={"query": query, **args.model_dump(mode="json")},
                    timeout=self.TIMEOUT,
                )
            except Exception as e:
                logger.warning(msg=f"Failed to reach the search service: {type(e).__name__}.")
                return SearchUnreachableError(detail=type(e).__name__)

        if response.status_code // 100 != 2:
            try:
                detail = response.json()["detail"]
            except (JSONDecodeError, KeyError, TypeError):
                detail = response.text
            return SearchStatusCodeError(status_code=response.status_code, detail=detail)

        try:
            return Searches(**response.json())
        except (JSONDecodeError, ValidationError) as e:
            logger.warning(msg=f"Search service returned an unexpected payload: {type(e).__name__}.")
            return SearchUnreachableError(detail=type(e).__name__)
