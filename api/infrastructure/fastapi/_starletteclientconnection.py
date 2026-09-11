from starlette.requests import Request

from api.domain._clientconnection import ClientConnection


class StarletteClientConnection(ClientConnection):
    def __init__(self, request: Request):
        self._request = request

    async def is_disconnected(self) -> bool:
        return await self._request.is_disconnected()
