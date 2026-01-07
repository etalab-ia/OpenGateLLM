# ADR-001: Migration to Clean Architecture

**Status:** In Progress
**Date:** 2026-01-07
**Authors:** Development Team
**Decision Outcome:** Migrate OpenGateLLM codebase to Clean Architecture pattern

---

## Context

OpenGateLLM has evolved from a FastAPI application to a production-ready API gateway serving multiple LLM backends with complex features including RAG, OCR, audio transcription, and organization management. 
The original architecture coupled business logic directly within FastAPI endpoint handlers and databases repositories, making the codebase increasingly difficult to:

1. **Test in isolation** - Business logic tightly coupled to HTTP layer required complex mocking (databases, LLM models)
2. **Maintain and extend** - Core business rules mixed with infrastructure concerns
3. **Understand** - No clear separation between what the system does vs. how it does it
4. 
### Previous Architecture

```
api/
├── endpoints/              # FastAPI route handlers
│   ├── models.py           # HTTP logic + business logic + data access
│   ├── chat.py
│   └── ...
├── schemas/               # Pydantic request/response models
├── helpers/               # Utility classes (mixed concerns)
└── sql/                   # Direct SQL queries
```

**Key issues:**
- Business logic embedded in endpoint handlers (e.g., `endpoints/models.py`)
- Business logic also scattered in database repository functions
- Direct database access from endpoints
- No clear abstraction boundaries
- Testing required HTTP mocking even for pure business logic
- More integration tests than unit tests
- Circular dependencies between modules

---

## Decision

Adopt **Clean Architecture** (Hexagonal Architecture, Ports & Adapters...) to establish clear separation of concerns through distinct layers:

```
api/
├── domain/                        # Enterprise Business Layer
│   ├── router/
│   │   ├── entities.py           # Router, Model, ModelCosts entities
│   │   └── _routerrepository.py  # Abstract repository interface
│   ├── user/
│   ├── key/
│   └── ...
│
├── use_cases/                     # Application Business Layer
│   └── models/
│       └── _getmodelsusecase.py  # GetModelsUseCase orchestrates business logic
│
├── infrastructure/                # Frameworks & Drivers Layer
│   ├── fastapi/
│   │   ├── endpoints/
│   │   │   └── models.py         # HTTP handlers (thin layer)
│   │   └── schemas/              # HTTP DTOs
│   └── postgres/
│       └── _postgresrouterrepository.py  # Concrete implementation
│
└── tests/
    ├── unit/                      # Fast, isolated tests
    │   └── use_case/
    └── integration/               # Database integration tests
```

### Architectural Principles

1. **Dependency Rule**: Dependencies point inward. Domain has zero external dependencies.
2. **Interface Segregation**: Abstract repositories in domain, concrete implementations in infrastructure
3. **Single Responsibility**: Each layer has one reason to change
4. **Testability**: Business logic testable without infrastructure

---

## Implementation Strategy

### Current Status: GetModelsUseCase Migration

Migrated first use case to establish the pattern:
- Domain entities (`api/domain/router/entities.py`)
- Repository interface (`api/domain/router/_routerrepository.py`)
- Use case with pure business logic (`api/use_cases/models/_getmodelsusecase.py`)
- PostgreSQL implementation (`api/infrastructure/postgres/_postgresrouterrepository.py`)
- Thin FastAPI handler (`api/infrastructure/fastapi/endpoints/models.py`)

**Testing impact:** 10x faster unit tests, no database mocking required.

### Migration Approach

**Incremental strategy:**
- Migrate legacy features one by one
- New features will follow Clean architecture principles
- Priority: Chat completions → Embeddings → API keys → User/Org → RAG → Audio → OCR
- Keep legacy `endpoints/` intact until fully migrated
- No new code in old architecture

---

## Consequences

### Positive

- **Testability**: Unit tests 10x faster, no database/HTTP mocking, business logic coverage from ~40% to 90%+
- **Maintainability**: Clear separation between "what" (use cases) and "how" (infrastructure)
- **Flexibility**: Business logic reusable in CLI, background jobs, or alternative frameworks
- **Type Safety**: Explicit result types (`Success | ModelNotFound`) replace implicit HTTP status codes

### Negative

- **More files**: Each feature requires entity, repository interface, use case, implementation, endpoint
- **Learning curve**: Team needs Clean Architecture understanding
- **Initial overhead**: Setup takes longer than direct FastAPI endpoint
- **Coordination**: Domain layer must remain dependency-free (enforced via pre-commit hooks)
- **Temporary inconsistency**: Two architectural patterns coexist during migration

---

## Testing Strategy

### Test Data Management with Factories

The project uses **Factory Boy** to generate test data, with separate factories for each testing layer:

**Unit test factories** (`tests/unit/use_case/factories.py`):
- Create **domain entities** directly (Router, User, UserInfo, etc.)
- No database interaction
- Pure Python objects using `factory.Factory`
- Example: `RouterFactory` creates `Router` domain entities

**Integration test factories** (`tests/integration/factories.py`):
- Create **SQLAlchemy models** for database persistence
- Use `SQLAlchemyModelFactory` for automatic session management
- Support relationships and database constraints
- Example: `RouterFactory` creates `Router` SQL models and persists to test database

Both factory sets support **traits** for common scenarios (e.g., `admin_user`, `free` router, `with_providers`), making tests readable and maintainable.

### Unit Tests (No External Dependencies)

```python
# tests/unit/use_case/test_getmodelsusecase.py
from unittest.mock import AsyncMock, Mock
from api.tests.unit.use_case.factories import RouterFactory, UserInfoFactory

@pytest.fixture
def router_repository():
    repo = Mock()
    repo.get_all_routers = AsyncMock()
    repo.get_organization_name = AsyncMock()
    return repo

@pytest.fixture
def sample_routers():
    return [
        RouterFactory(
            id=1,
            name="gpt-4",
            aliases=["gpt-4-turbo"],
            providers=2,
            max_context_length=8192,
        ),
        RouterFactory(
            id=2,
            name="claude-3",
            providers=1,
        ),
    ]

async def test_should_return_all_models_the_user_has_access_to(
    router_repository, user_info_repository, sample_routers, user_info_with_access
):
    # Arrange - Factories create domain entities, mocks simulate repositories
    user_info_repository.get_user_info.return_value = user_info_with_access
    router_repository.get_all_routers.return_value = sample_routers
    router_repository.get_organization_name.side_effect = ["OpenAI", "Anthropic"]

    use_case = GetModelsUseCase(
        user_id=1,
        router_repository=router_repository,
        user_info_repository=user_info_repository,
    )

    # Act
    result = await use_case.execute()

    # Assert
    assert isinstance(result, Success)
    assert len(result.models) == 2

```

**Benefits:**
- No database setup
- Runs in <100ms
- Tests only business rules
- Factories eliminate boilerplate test data creation
- Mock repositories allow precise control over test scenarios
- Easy to cover edge cases

### Integration Tests (Real Infrastructure)

```python
# tests/integration/test_postgresrouterrepository.py
from api.tests.integration.factories import (
    OrganizationFactory,
    ProviderFactory,
    RouterFactory,
    UserFactory,
)

async def test_get_all_routers_should_return_all_routers(repository, db_session):
    # Arrange - Factories create and persist SQLAlchemy models with relationships
    user_1 = UserFactory()

    router_1 = RouterFactory(
        user=user_1,
        name="router_1",
        type=ModelType.TEXT_GENERATION,
        cost_prompt_tokens=0.001,
    )

    ProviderFactory(router=router_1, user=user_1, max_context_length=2048)

    await db_session.flush()

    # Act
    result_routers = await repository.get_all_routers()

    # Assert
    assert len(result_routers) == 2
    r1 = next(r for r in result_routers if r.name == "router_1")
    assert r1.type == ModelType.TEXT_GENERATION
    assert r1.providers == 2
    assert r1.max_context_length == 2048
```

**Benefits:**
- Validates SQL queries and complex joins
- Tests database-specific logic (aggregations, relationships)
- Factories handle complex relationships (User → Organization, Router → Provider)
- Automatic cleanup via session management

### Running Tests

**Unit tests**:
```bash
pytest api/tests/unit/use_case
```

With code coverage:
```bash
pytest api/tests/unit/use_case --cov=api --cov-report=html --cov-report=term-missing --config-file=pyproject.toml --cov-branch
```

**Integration tests** (require PostgreSQL, Redis, Elasticsearch):
```bash
pytest api/tests/integration 
```
With code coverage:
```bash
pytest api/tests/integration --cov=api --cov-report=html --cov-report=term-missing --config-file=pyproject.toml --cov-branch
```

---

## Migration Guidelines

### Do's
- ✅ Keep domain entities simple (dataclasses, no framework dependencies)
- ✅ Use dependency injection for repositories
- ✅ Return typed results from use cases (`Success | Error`)
- ✅ Write unit tests for use cases with mocked repositories
- ✅ Write integration tests for repository implementations
- ✅ Use abstract base classes for repository interfaces

### Don'ts
- ❌ Import SQLAlchemy/FastAPI in domain layer
- ❌ Put business logic in FastAPI endpoints
- ❌ Access database directly from use cases
- ❌ Return HTTP status codes from use cases
- ❌ Mix concerns within a single layer

### Code Review Checklist
- [ ] Domain entities have no external dependencies
- [ ] Use case has unit tests with mocked repositories
- [ ] Repository implementation has integration tests
- [ ] FastAPI endpoint is a thin HTTP adapter
- [ ] Type hints used throughout
- [ ] Result types explicitly defined

---

## References

- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture - Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [FastAPI Best Practices - Repository Pattern](https://github.com/zhanymkanov/fastapi-best-practices#11-use-dependencies-for-data-validation-vs-db)

---

## Revision History

| Date       | Author           | Changes                              |
|------------|------------------|--------------------------------------|
| 2025-01-07 | Development Team | Initial ADR based on GetModelsUseCase migration |
