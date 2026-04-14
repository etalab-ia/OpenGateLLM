import pytest

from api.infrastructure.postgres import PostgresRolesRepository


@pytest.fixture
def repository(db_session):
    return PostgresRolesRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteRole:
    async def test_raises_not_implemented_error(self, repository, db_session):
        # Act & Assert
        with pytest.raises(NotImplementedError):
            await repository.delete_role(role_id=1)
