from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.core.configuration import Model as ModelRouterSchema
from api.schemas.core.configuration import ModelProvider as ModelProviderSchema
from api.sql.models import Model as ModelRouterTable
from api.sql.models import ModelClient as ModelClientTable
from api.sql.models import ModelRouterAlias as ModelRouterAliasTable


class ModelDatabaseManager:
    @staticmethod
    async def get_routers(
        postgres_session: AsyncSession,
    ) -> list[ModelRouterSchema]:
        """
        Returns the ModelRouterSchemas stored in the database.

        Args:
            postgres_session(AsyncSession): The database postgres_session.
        """
        routers = []

        # Get all ModelRouter rows and convert it from a list of 1-dimensional vectors to a list of ModelRouters
        db_routers = [row[0] for row in (await postgres_session.execute(select(ModelRouterTable))).fetchall()]

        if not db_routers:
            return []

        for router in db_routers:
            # Get all ModelAlias rows and convert from a list of 1-dimensional vectors to a list of values
            db_aliases = [
                row[0].alias  # Get alias directly, instead of ModelRouterAlias object
                for row in (
                    await postgres_session.execute(select(ModelRouterAliasTable).where(ModelRouterAliasTable.model_router_name == router.name))
                ).fetchall()
            ]

            db_clients = [
                row[0]
                for row in (
                    await postgres_session.execute(select(ModelClientTable).where(ModelClientTable.model_router_name == router.name))
                ).fetchall()
            ]

            assert db_clients, f"No ModelClients found in database for ModelRouter {router.name}"

            providers = [ModelProviderSchema.model_validate(client) for client in db_clients]
            routers.append(
                ModelRouterSchema.model_validate(
                    {
                        **router.__dict__,
                        "providers": providers,
                        "aliases": db_aliases,
                    }
                )
            )

        return routers

    @staticmethod
    async def add_router(postgres_session: AsyncSession, router: ModelRouterSchema):
        """
        Adds a ModelRouterSchema to the database.

        Args:
            postgres_session(AsyncSession): The database postgres_session.
            router(ModelRouterSchema): the schema (= row) to add.
        """

        router_result = (await postgres_session.execute(select(ModelRouterTable).where(ModelRouterTable.name == router.name))).fetchall()

        assert not router_result, "tried adding already existing router"

        await postgres_session.execute(insert(ModelRouterTable).values(**router.model_dump(exclude={"providers", "aliases"})))

        for alias in router.aliases:
            await postgres_session.execute(insert(ModelRouterAliasTable).values(alias=alias, model_router_name=router.name))

        for client in router.providers:
            await postgres_session.execute(insert(ModelClientTable).values(**client.model_dump(), model_router_name=router.name))
        await postgres_session.commit()

    @staticmethod
    async def add_client(postgres_session: AsyncSession, router_name: str, client: ModelProviderSchema):
        """
        Adds a ModelProviderSchema to a ModelRouter.

        Args:
            postgres_session(AsyncSession): The database postgres_session.
            router_name(str): the name (= id) of the ModelRouterSchema to add the provider to.
            client(ModelProviderSchema): the provider to add.
        """
        client_result = (
            await postgres_session.execute(
                select(ModelClientTable)
                .where(ModelClientTable.model_router_name == router_name)
                .where(ModelClientTable.model_name == client.model_name)
                .where(ModelClientTable.url == client.url)
            )
        ).fetchall()

        assert not client_result, "tried adding already existing client"

        await postgres_session.execute(insert(ModelClientTable).values(**client.model_dump(), model_router_name=router_name))
        await postgres_session.commit()

    @staticmethod
    async def add_alias(postgres_session: AsyncSession, router_name: str, alias: str):
        """
        Adds an alias to an existing router.

        Args:
            postgres_session(AsyncSession): The database postgres_session.
            router_name(str): The name (= id) of the ModelRouterSchema to add the alias to.
            alias(str): The alias to add.
        """
        alias_result = (
            await postgres_session.execute(
                select(ModelRouterAliasTable)
                .where(ModelRouterAliasTable.model_router_name == router_name)
                .where(ModelRouterAliasTable.alias == alias)
            )
        ).fetchall()

        assert not alias_result, "tried to add already-existing alias"
        await postgres_session.execute(insert(ModelRouterAliasTable).values(alias=alias, model_router_name=router_name))

        await postgres_session.commit()

    @staticmethod
    async def delete_router(postgres_session: AsyncSession, router_name: str):
        """
        Deletes a router.

        Args:
            postgres_session(AsyncSession): The database postgres_session.
            router_name(str): the name (= id) of the ModelRouterSchema to delete.
        """
        # Check if objects exist
        router_result = (await postgres_session.execute(select(ModelRouterTable).where(ModelRouterTable.name == router_name))).fetchall()
        alias_result = (
            await postgres_session.execute(select(ModelRouterAliasTable).where(ModelRouterAliasTable.model_router_name == router_name))
        ).fetchall()
        client_result = (await postgres_session.execute(select(ModelClientTable).where(ModelClientTable.model_router_name == router_name))).fetchall()

        assert router_result, f"ModelRouter {router_name} not found in DB"

        await postgres_session.execute(delete(ModelRouterTable).where(ModelRouterTable.name == router_name))

        if alias_result:
            await postgres_session.execute(delete(ModelRouterAliasTable).where(ModelRouterAliasTable.model_router_name == router_name))
        if client_result:
            await postgres_session.execute(delete(ModelClientTable).where(ModelClientTable.model_router_name == router_name))

        await postgres_session.commit()

    @staticmethod
    async def delete_client(postgres_session: AsyncSession, router_name: str, model_name: str, model_url: str):
        """
        Deletes a ModelProviderSchema from a ModelRouter.

        Args:
            postgres_session(AsyncSession): The database postgres_session.
            router_name(str): the name (= id) of the ModelRouterSchema that manages the targeted provider.
            model_name(str): the name of the targeted provider.
            model_url(str): the url of the targeted provider.
                model_name and model_url together uniquely identify a provider.
        """
        client_result = (
            await postgres_session.execute(
                select(ModelClientTable)
                .where(ModelClientTable.model_router_name == router_name)
                .where(ModelClientTable.model_name == model_name)
                .where(ModelClientTable.url == model_url)
            )
        ).fetchall()

        assert client_result, "tried to delete non-existing client"
        await postgres_session.execute(
            delete(ModelClientTable)
            .where(ModelClientTable.model_router_name == router_name)
            .where(ModelClientTable.model_name == model_name)
            .where(ModelClientTable.url == model_url)
        )

        await postgres_session.commit()

    @staticmethod
    async def delete_alias(postgres_session: AsyncSession, router_name: str, alias_identifier):
        await postgres_session.execute(delete(ModelRouterAliasTable).where(ModelRouterAliasTable.model_router_name == router_name))

        await postgres_session.commit()
