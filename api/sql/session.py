# Global variable to store the current get_db function for dependency injection
from api.utils.context import global_context

# TODO: move into utils/dependencies.py as get_postgres_session()
# TODO: rename to get_postgres_session


async def get_db_session():
    """FastAPI dependency to get database session."""

    session_factory = global_context.postgres_session_factory
    async with session_factory() as session:
        yield session

        if session.in_transaction():
            await session.close()
