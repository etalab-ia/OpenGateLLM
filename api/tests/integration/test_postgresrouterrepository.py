from datetime import datetime

import pytest

from api.domain.role.entities import LimitType
from api.domain.router.entities import Model, ModelCosts, ModelType
from api.domain.userinfo.entities import Limit, UserInfo
from api.infrastructure.postgres import PostgresRouterRepository
from api.tests.integration.factories import (
    OrganizationFactory,
    ProviderFactory,
    RouterAliasFactory,
    RouterFactory,
    UserFactory,
)
from api.utils.exceptions import ModelNotFoundException, RouterNotFoundException


@pytest.fixture
def app_title():
    return "Test App"


@pytest.fixture
def repository(db_session, app_title):
    """Instance du repository à tester."""
    return PostgresRouterRepository(db_session, app_title)


@pytest.mark.asyncio(loop_scope="session")
class TestGetRouters:
    """Tests de la méthode get_routers avec vraies données."""

    async def test_get_all_routers_should_return_all_routers(self, repository, db_session):
        """Test de récupération de tous les routeurs."""
        # Arrange
        user_1 = UserFactory()
        user_2 = UserFactory()

        router_1 = RouterFactory(user=user_1, name="router_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002)
        router_2 = RouterFactory(
            user=user_1, name="router_2", type=ModelType.TEXT_EMBEDDINGS_INFERENCE, cost_prompt_tokens=0.0, cost_completion_tokens=0.0
        )
        router_3 = RouterFactory(
            user=user_2, name="router_3", type=ModelType.TEXT_EMBEDDINGS_INFERENCE, cost_prompt_tokens=0.0, cost_completion_tokens=0.0
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536)
        ProviderFactory(router=router_1, user=user_1, model_name="m2", max_context_length=128000, vector_size=384)
        ProviderFactory(router=router_2, user=user_1, model_name="m3")
        ProviderFactory(router=router_3, user=user_2, model_name="m4")

        # Act
        await db_session.flush()
        result_routers = await repository.get_routers(router_id=None, name=None)

        # Assert
        assert len(result_routers) == 3
        router_names = {r.name for r in result_routers}
        assert router_names == {router_1.name, router_2.name, router_3.name}

        r1 = next(r for r in result_routers if r.name == "router_1")
        assert r1.type == ModelType.TEXT_GENERATION
        assert r1.providers == 2
        assert r1.cost_prompt_tokens == 0.001
        assert r1.cost_completion_tokens == 0.002
        # TODO: comment sont choisies ces valeurs ?
        assert r1.max_context_length == 2048
        assert r1.vector_size == 1536

    async def test_get_router_should_return_the_requested_router_when_given_an_id(self, repository, db_session):
        """Test de récupération d'un routeur spécifique par ID."""
        # Arrange
        router = RouterFactory(name="specific_router")
        RouterAliasFactory(router=router, value="alias_1")
        RouterAliasFactory(router=router, value="alias_2")
        RouterAliasFactory(router=router, value="alias_3")
        ProviderFactory(router=router)

        # Act
        await db_session.flush()
        routers = await repository.get_routers(router_id=router.id, name=None)

        # Assert
        assert len(routers) == 1
        assert routers[0].id == router.id
        assert routers[0].name == "specific_router"
        assert len(routers[0].aliases) == 3
        assert set(routers[0].aliases) == {"alias_1", "alias_2", "alias_3"}

    async def test_get_router_by_id_should_raise_an_exception_router_is_not_found(self, repository, db_session):
        """Test d'erreur quand un routeur n'existe pas."""
        non_existing_router_id = 1
        # Act & Assert
        with pytest.raises(RouterNotFoundException):
            await repository.get_routers(router_id=non_existing_router_id, name=None)

    async def test_get_router_should_return_a_specific_router_when_given_a_router_name_and_id_is_none(self, repository, db_session):
        """Test de récupération d'un routeur par nom."""
        # Arrange
        user = UserFactory()
        router1 = RouterFactory(user=user, name="specific_router")
        router2 = RouterFactory(user=user, name="other_router")
        ProviderFactory(router=router1, user=user)
        ProviderFactory(router=router2, user=user)

        # Act
        routers = await repository.get_routers(router_id=None, name="specific_router")

        # Assert
        assert len(routers) == 1
        assert routers[0].name == "specific_router"

    async def test_get_router_should_raise_an_exception_when_name_not_found(self, repository, db_session):
        """Test d'erreur quand un routeur n'est pas trouvé par nom."""
        # Arrange
        user = UserFactory()
        router = RouterFactory(user=user, name="existing_router")
        ProviderFactory(router=router, user=user)

        # Act & Assert
        with pytest.raises(RouterNotFoundException):
            await repository.get_routers(router_id=None, name="nonexistent")

    async def test_get_router_should_return_a_router_when_given_an_alias(self, repository, db_session):
        """Test de récupération d'un routeur par alias."""
        # Arrange
        user = UserFactory()
        router = RouterFactory(user=user, name="router_1")
        RouterAliasFactory(router=router, value="my_alias")
        RouterAliasFactory(router=router, value="another_alias")
        ProviderFactory(router=router, user=user)

        # Act
        routers = await repository.get_routers(router_id=None, name="my_alias")

        # Assert
        assert len(routers) == 1
        assert routers[0].name == "router_1"
        assert "my_alias" in routers[0].aliases
        assert "another_alias" in routers[0].aliases


@pytest.mark.asyncio(loop_scope="session")
class TestGetAllModels:
    """Tests de la méthode get_all_models avec vraies données."""

    async def test_get_all_models_should_return_all_accessible_models(self, repository, db_session):
        """Test de récupération de tous les modèles accessibles par l'utilisateur."""
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        updated = datetime(2024, 1, 15, 10, 30, 0)
        organization = OrganizationFactory(name="DINUM")
        user_1 = UserFactory(organization=organization)
        user_2 = UserFactory(organization=organization)

        router_1 = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        router_2 = RouterFactory(
            user=user_1,
            name="router_name_2",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            created=created,
        )
        router_3 = RouterFactory(
            user=user_2,
            name="router_name_3",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            created=created,
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        ProviderFactory(router=router_1, user=user_1, model_name="m2", max_context_length=128000, vector_size=384, created=created)
        ProviderFactory(router=router_2, user=user_1, model_name="m3", max_context_length=16384, vector_size=1536, created=created)
        ProviderFactory(router=router_3, user=user_2, model_name="m4", max_context_length=1024, vector_size=384, created=created)
        RouterAliasFactory(router=router_1, value="alias1_m1")
        RouterAliasFactory(router=router_1, value="alias2_m1")
        RouterAliasFactory(router=router_1, value="alias3_m1")
        await db_session.flush()

        user_info = UserInfo(
            id=1,
            name="Test User",
            email="test@example.com",
            limits=[
                Limit(router=router_1.id, type=LimitType.TPM, value=1000),
                Limit(router=router_2.id, type=LimitType.TPM, value=None),
                Limit(router=router_3.id, type=LimitType.TPM, value=1000),
            ],
            permissions=[],
            created=int(created.timestamp()),
            updated=int(updated.timestamp()),
        )

        # Act
        models = await repository.get_all_models(name=None, user_info=user_info)
        # Assert
        assert len(models) == 3
        assert models == [
            Model(
                id="router_name_1",
                type="text-generation",
                aliases=["alias1_m1", "alias2_m1", "alias3_m1"],
                created=1705314600,
                owned_by="DINUM",
                max_context_length=2048,
                costs=ModelCosts(prompt_tokens=0.001, completion_tokens=0.002),
            ),
            Model(
                id="router_name_2",
                type="text-embeddings-inference",
                aliases=[],
                created=1705314600,
                owned_by="DINUM",
                max_context_length=16384,
                costs=ModelCosts(prompt_tokens=0.0, completion_tokens=0.0),
            ),
            Model(
                id="router_name_3",
                type="text-embeddings-inference",
                aliases=[],
                created=1705314600,
                owned_by="DINUM",
                max_context_length=1024,
                costs=ModelCosts(prompt_tokens=0.0, completion_tokens=0.0),
            ),
        ]

    async def test_get_all_models_should_filter_models_without_providers(self, repository, db_session):
        """Test que les modèles sans providers sont filtrés."""
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        updated = datetime(2024, 1, 15, 10, 30, 0)

        user_1 = UserFactory()

        router_1 = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        router_without_provider = RouterFactory(
            user=user_1,
            name="router_name_2",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            created=created,
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        ProviderFactory(router=router_1, user=user_1, model_name="m2", max_context_length=128000, vector_size=384, created=created)
        await db_session.flush()

        user_info = UserInfo(
            id=1,
            name="Test User",
            email="test@example.com",
            limits=[
                Limit(router=router_1.id, type=LimitType.TPM, value=1000),
                Limit(router=router_without_provider.id, type=LimitType.TPM, value=1000),
            ],
            permissions=[],
            created=int(created.timestamp()),
            updated=int(updated.timestamp()),
        )

        # Act
        models = await repository.get_all_models(name=None, user_info=user_info)
        # Assert
        model_ids = {m.id for m in models}
        assert len(models) == 1
        assert router_without_provider not in model_ids

    async def test_get_all_models_should_filter_models_without_access(self, repository, db_session):
        """Test que les modèles sans accès sont filtrés."""
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        updated = datetime(2024, 1, 15, 10, 30, 0)
        user_1 = UserFactory()
        router_with_access = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        router_without_access = RouterFactory(
            user=user_1,
            name="router_name_2",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            created=created,
        )
        ProviderFactory(router=router_with_access, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        ProviderFactory(router=router_with_access, user=user_1, model_name="m2", max_context_length=128000, vector_size=384, created=created)
        ProviderFactory(router=router_without_access, user=user_1, model_name="m3", max_context_length=16384, vector_size=1536, created=created)
        await db_session.flush()

        user_info = UserInfo(
            id=1,
            name="Test User",
            email="test@example.com",
            limits=[
                Limit(router=router_with_access.id, type=LimitType.TPM, value=1000),
            ],
            permissions=[],
            created=int(created.timestamp()),
            updated=int(updated.timestamp()),
        )

        # Act
        models = await repository.get_all_models(name=None, user_info=user_info)
        # Assert
        model_ids = {m.id for m in models}
        assert len(models) == 1
        assert router_without_access not in model_ids

    async def test_get_model_by_name_should_return_specific_model(self, repository, db_session):
        """Test de récupération d'un modèle spécifique par nom."""
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        updated = datetime(2024, 1, 15, 10, 30, 0)

        user_1 = UserFactory()

        router_1 = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        router_2 = RouterFactory(
            user=user_1,
            name="router_name_2",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            created=created,
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        ProviderFactory(router=router_1, user=user_1, model_name="m2", max_context_length=128000, vector_size=384, created=created)
        ProviderFactory(router=router_2, user=user_1, model_name="m3", max_context_length=16384, vector_size=1536, created=created)
        await db_session.flush()

        user_info = UserInfo(
            id=1,
            name="Test User",
            email="test@example.com",
            limits=[
                Limit(router=router_1.id, type=LimitType.TPM, value=1000),
                Limit(router=router_2.id, type=LimitType.TPM, value=None),
            ],
            permissions=[],
            created=int(created.timestamp()),
            updated=int(updated.timestamp()),
        )

        # Act
        await db_session.flush()
        models = await repository.get_all_models(name="router_name_1", user_info=user_info)

        # Assert
        assert len(models) == 1
        assert models[0].id == "router_name_1"

    async def test_get_model_by_alias_should_return_model(self, repository, db_session):
        """Test de récupération d'un modèle par alias."""
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        updated = datetime(2024, 1, 15, 10, 30, 0)

        user_1 = UserFactory()

        router_1 = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        ProviderFactory(router=router_1, user=user_1, model_name="m2", max_context_length=128000, vector_size=384, created=created)
        RouterAliasFactory(router=router_1, value="alias1_m1")
        RouterAliasFactory(router=router_1, value="alias2_m1")
        RouterAliasFactory(router=router_1, value="alias3_m1")
        await db_session.flush()

        user_info = UserInfo(
            id=1,
            name="Test User",
            email="test@example.com",
            limits=[
                Limit(router=router_1.id, type=LimitType.TPM, value=1000),
            ],
            permissions=[],
            created=int(created.timestamp()),
            updated=int(updated.timestamp()),
        )

        # Act
        await db_session.flush()
        models = await repository.get_all_models(name="alias1_m1", user_info=user_info)

        # Assert
        assert len(models) == 1
        assert models[0].id == "router_name_1"

    async def test_get_model_should_raise_exception_when_not_found(self, repository, db_session):
        """Test d'erreur quand un modèle n'existe pas."""
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        updated = datetime(2024, 1, 15, 10, 30, 0)
        user_1 = UserFactory()

        router_1 = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        await db_session.flush()

        user_info = UserInfo(
            id=1,
            name="Test User",
            email="test@example.com",
            limits=[
                Limit(router=router_1.id, type=LimitType.TPM, value=1000),
            ],
            permissions=[],
            created=int(created.timestamp()),
            updated=int(updated.timestamp()),
        )

        # Act & Assert
        await db_session.flush()
        with pytest.raises(ModelNotFoundException):
            await repository.get_all_models(name="nonexistent-model", user_info=user_info)

    async def test_get_model_should_raise_exception_when_no_provider(self, repository, db_session):
        """Test d'erreur quand un modèle spécifique n'a pas de provider."""
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        updated = datetime(2024, 1, 15, 10, 30, 0)
        user_1 = UserFactory()

        router_1 = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        await db_session.flush()
        user_info = UserInfo(
            id=1,
            name="Test User",
            email="test@example.com",
            limits=[
                Limit(router=router_1.id, type=LimitType.TPM, value=1000),
            ],
            permissions=[],
            created=int(created.timestamp()),
            updated=int(updated.timestamp()),
        )

        # Act & Assert
        await db_session.flush()
        with pytest.raises(ModelNotFoundException):
            await repository.get_all_models(name="model-without-provider", user_info=user_info)

    async def test_get_model_should_raise_exception_when_no_access(self, repository, db_session):
        """Test d'erreur quand l'utilisateur n'a pas accès au modèle spécifique."""
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        updated = datetime(2024, 1, 15, 10, 30, 0)
        user_1 = UserFactory()

        forbidden_router = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        ProviderFactory(router=forbidden_router, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        await db_session.flush()
        user_info = UserInfo(
            id=1,
            name="Test User",
            email="test@example.com",
            limits=[],
            permissions=[],
            created=int(created.timestamp()),
            updated=int(updated.timestamp()),
        )

        # Act & Assert
        await db_session.flush()
        with pytest.raises(ModelNotFoundException):
            await repository.get_all_models(name=forbidden_router.name, user_info=user_info)

    async def test_get_all_models_should_use_app_title_when_no_organization(self, repository, db_session, app_title):
        """Test que app_title est utilisé quand l'utilisateur n'a pas d'organisation."""
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        updated = datetime(2024, 1, 15, 10, 30, 0)
        user_1 = UserFactory(organization=None)

        router_1 = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )

        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        ProviderFactory(router=router_1, user=user_1, model_name="m2", max_context_length=128000, vector_size=384, created=created)
        await db_session.flush()

        user_info = UserInfo(
            id=1,
            name="Test User",
            email="test@example.com",
            limits=[
                Limit(router=router_1.id, type=LimitType.TPM, value=1000),
            ],
            permissions=[],
            created=int(created.timestamp()),
            updated=int(updated.timestamp()),
        )

        # Act
        await db_session.flush()
        models = await repository.get_all_models(name=router_1.name, user_info=user_info)

        # Assert
        assert len(models) == 1
        assert models[0].owned_by == app_title


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
