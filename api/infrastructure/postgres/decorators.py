from collections.abc import Callable
from functools import wraps
import inspect
from typing import Any

from sqlalchemy import text

from api.infrastructure.postgres._autocommitsession import AutocommitSession, TransactionRequiredError


def with_lock(namespace: str, key: str) -> Callable:
    """Decorator acquiring a Postgres transaction-scoped advisory lock before the method runs.

    The wrapped method must be an async instance method of a class exposing ``self.postgres_session``
    (an ``AsyncSession``). The lock is automatically released at the end of the current transaction.

    The lock being transaction-scoped, the session must be transactional: an ``AutocommitSession``
    would commit right after the lock statement and release the lock before the method even runs, so
    the decorator refuses it rather than silently dropping the mutual exclusion.

    :param namespace: Prefix scoping the lock across tables (e.g. ``"role"``, ``"user"``).
    :param key: Name of a parameter of the wrapped method whose value will be used as the lock key.
        Dotted paths are supported to access an attribute of the argument (e.g. ``"user.id"``).

    Example::

        @with_lock(namespace="user", key="user.id")
        async def update_user(self, user: User) -> User:
            ...
    """
    arg_name, *attr_path = key.split(".")

    def decorator(func: Callable) -> Callable:
        signature = inspect.signature(func)
        if arg_name not in signature.parameters:
            raise ValueError(f"with_lock: parameter '{arg_name}' not found in {func.__qualname__}{signature}")

        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            if isinstance(self.postgres_session, AutocommitSession):
                raise TransactionRequiredError(
                    f"{func.__qualname__} is protected by an advisory lock and requires a transactional session, got an AutocommitSession."
                )

            bound = signature.bind(self, *args, **kwargs)
            bound.apply_defaults()
            value = bound.arguments[arg_name]
            for attr in attr_path:
                value = getattr(value, attr)

            await self.postgres_session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"{namespace}:{value}"})
            return await func(self, *args, **kwargs)

        return wrapper

    return decorator
