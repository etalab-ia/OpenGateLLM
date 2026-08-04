from typing import Any, NoReturn

from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession


class TransactionRequiredError(RuntimeError):
    """Raised when code that needs a transactional boundary runs on an AutocommitSession."""


class AutocommitSession(AsyncSession):
    async def execute(self, *args: Any, **kwargs: Any) -> Result:
        result = await super().execute(*args, **kwargs)
        await self.commit()

        return result

    async def scalar(self, *args: Any, **kwargs: Any) -> Any:
        result = await super().scalar(*args, **kwargs)
        await self.commit()

        return result

    async def get(self, *args: Any, **kwargs: Any) -> Any:
        result = await super().get(*args, **kwargs)
        await self.commit()

        return result

    @staticmethod
    def _reject(entry_point: str, reason: str) -> NoReturn:
        raise TransactionRequiredError(
            f"{entry_point} {reason}, but this session commits after every statement. Use the transactional session factory instead."
        )

    def begin(self, *args: Any, **kwargs: Any) -> NoReturn:
        self._reject("begin()", "opens a transaction spanning several statements")

    def begin_nested(self, *args: Any, **kwargs: Any) -> NoReturn:
        self._reject("begin_nested()", "needs a transaction to hold the savepoint")

    async def stream(self, *args: Any, **kwargs: Any) -> NoReturn:
        self._reject("stream()", "keeps a server side cursor open on the connection")

    async def stream_scalars(self, *args: Any, **kwargs: Any) -> NoReturn:
        self._reject("stream_scalars()", "keeps a server side cursor open on the connection")

    async def connection(self, *args: Any, **kwargs: Any) -> NoReturn:
        self._reject("connection()", "hands out the pooled connection itself")
