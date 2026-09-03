# OpenGateLLM

Coding conventions for this repository. New and changed code follows clean architecture as implemented below.

---

## Architecture

```
domain/           entities, errors, repository ports, query ports + views (no FastAPI, no SQL)
use_cases/        Command, UseCase, UseCaseSuccess, execute()
infrastructure/
  fastapi/        endpoints, schemas, HTTP exceptions, AccessController
  postgres/       Postgres*Repository / Postgres*Query adapters, AutocommitSession
dependencies.py   DI factories (transactional vs autocommit session)
```

**Dependency rule:** `infrastructure → use_cases → domain`.

| Layer | Location |
|-------|----------|
| Domain | `api/domain/<context>/` |
| Use cases | `api/use_cases/<area>/` |
| Endpoints | `api/infrastructure/fastapi/endpoints/` |
| API schemas | `api/infrastructure/fastapi/schemas/` |
| Postgres adapters | `api/infrastructure/postgres/_postgres<entity>repository.py` |
| Read models | `api/domain/<context>/views.py` + `_<noun>query.py` |
| DI | `api/dependencies.py` |

Admin CRUD is grouped per resource: `api/use_cases/admin/roles/`, `api/infrastructure/fastapi/endpoints/admin/roles.py`, `api/infrastructure/fastapi/schemas/admin/roles.py`. Everything else stays flat under its area (`api/use_cases/auth/`, `api/infrastructure/fastapi/endpoints/models.py`, `api/infrastructure/fastapi/schemas/models.py`).

Reference implementations of these patterns:

| Pattern | Example |
|---------|---------|
| Create with domain errors | `api/infrastructure/fastapi/endpoints/admin/keys.py` + `api/use_cases/admin/keys/_createkeyusecase.py` |
| List + get-by-id | `api/infrastructure/fastapi/endpoints/admin/routers.py` (`GetRoutersUseCase` + `GetOneRouterUseCase`), self-service `api/infrastructure/fastapi/endpoints/keys.py` |
| Paginated list | `api/infrastructure/fastapi/endpoints/admin/roles.py`, `api/infrastructure/fastapi/endpoints/admin/users.py` (`EntitiesPage`, `*sResponse`) |
| Full CRUD | `api/infrastructure/fastapi/endpoints/admin/roles.py`, `api/infrastructure/fastapi/endpoints/admin/routers.py` |
| Read-only projection | `api/infrastructure/fastapi/endpoints/models.py` (`ModelQuery` + `ModelView`) |
| Model-forward (autocommit) | embeddings, OCR, rerank, audio transcriptions |

Self-service `/v1/keys` reuses the admin key use cases (`CreateKeyUseCase`, `GetKeysUseCase`, `GetOneKeyUseCase`). Pass `user_id=authenticated_user.id` on the command to scope the operation to the current user. Admin get-one omits `user_id` (it defaults to `None`) so it can load any key.

### `api/endpoints/` — legacy, scheduled for removal

Do not confuse `api/endpoints/` (pre-clean-architecture) with `api/infrastructure/fastapi/endpoints/` (current). **Never add a route or a module to `api/endpoints/`.** Three items remain:

| Remaining | Exposes | Migrate to |
|-----------|---------|------------|
| `api/endpoints/admin/organizations.py` | `PATCH /v1/admin/organizations/{organization}` | `api/infrastructure/fastapi/endpoints/admin/organizations.py` — the other organization routes already live there |
| `api/endpoints/chat.py` | `POST /v1/chat/completions` | `api/infrastructure/fastapi/endpoints/chat.py` + `api/use_cases/chat/` — model-forward, so `AutocommitSession` |
| `api/endpoints/monitoring.py` | no route — `setup_prometheus`, called by `_setup_monitoring` | not a router; needs a home under `api/infrastructure/` |

These files run on the legacy stack (`api/helpers/_accesscontroller.py`, `api/schemas/`, `api/utils/dependencies.py`, `global_context.identity_access_manager`). Migrating one means porting it to the patterns in this file — do not carry its imports over, and do not copy them into new code.

The directory disappears once all three are moved and these go with them:

- `RouterName.CHAT` pointing at `api.endpoints.chat` (`api/utils/variables.py`)
- the `@TODO: legacy import` block registering `api.endpoints.admin` (`api/app.py`)
- `from api.endpoints.monitoring import setup_prometheus` (`api/app.py`)

`api/endpoints/me/` and `api/endpoints/proconnect/` are already empty — their contents were migrated.

If a task makes you touch one of these files, migrate it rather than extend it (principle 4).

---

## Adding a feature

```
- [ ] Domain entity + errors in api/domain/<context>/
- [ ] Repository port in api/domain/<context>/_<entity>repository.py — or query port + view for a read-only projection (see Query and view)
- [ ] SQL model in api/sql/models.py if the schema changes, then an Alembic revision: uv run alembic -c api/alembic.ini revision --autogenerate -m "<slug>" — test upgrade AND downgrade locally
- [ ] Postgres adapter in api/infrastructure/postgres/_postgres<entity>repository.py
- [ ] Use case in api/use_cases/<area>/_<verb><noun>usecase.py
- [ ] Export from domain/__init__.py, use_cases/__init__.py, postgres/__init__.py
- [ ] DI factory in api/dependencies.py — pick transactional vs autocommit session (see Postgres session)
- [ ] API schemas in api/infrastructure/fastapi/schemas/
- [ ] HTTP exceptions in api/infrastructure/fastapi/endpoints/exceptions.py
- [ ] Endpoint in api/infrastructure/fastapi/endpoints/
- [ ] EndpointRoute member in api/utils/variables.py for the path
- [ ] Route registration (see below) — a new endpoint module is invisible until its router is registered
- [ ] Tests: unit use case (every distinct execute() branch) + integration endpoint (happy path, auth, error mapping) + repository if new query/column + domain entity if new method + ForwardScenario if the use case calls a provider
```

Read existing code for the same resource (or the closest pattern above) before writing.

### Route registration

`_register_routers` (`api/app.py`) iterates over the `RouterName` enum (`api/utils/variables.py`), imports each `module_path`, and reads the module-level `router` attribute. A module with no `RouterName` member is never imported, so its routes do not exist.

```python
class RouterName(StrEnum):
    KEYS = ("keys", "api.infrastructure.fastapi.endpoints.keys")
```

Two cases:

**New top-level module** (`api/infrastructure/fastapi/endpoints/<area>.py`) — declare its own router and register it:

```python
router = APIRouter(prefix="/v1", tags=[RouterName.KEYS.title()])
```
plus a `RouterName` member pointing at the module. Without the `router` attribute, `_register_routers` raises `AttributeError` at startup.

**New admin resource** (`api/infrastructure/fastapi/endpoints/admin/<resource>.py`) — do **not** add a `RouterName` member. Import the shared router and add the module to the side-effect import list in `api/infrastructure/fastapi/endpoints/admin/__init__.py`:

```python
# api/infrastructure/fastapi/endpoints/admin/<resource>.py
from api.infrastructure.fastapi.endpoints.admin import router

# api/infrastructure/fastapi/endpoints/admin/__init__.py — the module is invisible until it is listed here
from . import keys, organizations, providers, roles, routers, users  # noqa: F401 E402
```

`RouterName` members are toggled by `disabled_routers` / `hidden_routers` in settings, so one member = one independently switchable surface. All admin resources deliberately share `RouterName.ADMIN`.

Adding a route to an **existing** module needs neither: declare the `EndpointRoute` member and the handler.

`_register_routers` ends with a hardcoded block registering the legacy `api.endpoints.admin` router alongside the enum. That block is temporary — see [`api/endpoints/`](#apiendpoints--legacy-scheduled-for-removal). Do not add a second one.

---

## Naming

| Kind | Pattern | Example |
|------|---------|---------|
| Use case file | `_<verb><noun>usecase.py` | `_getrolesusecase.py`, `_getoneroleusecase.py` |
| Use case class | `<Verb><Noun>UseCase` | `GetRolesUseCase`, `GetOneRoleUseCase` |
| Command | `<Verb><Noun>Command` | `GetRolesCommand`, `GetOneRoleCommand` |
| Success | `<Verb><Noun>UseCaseSuccess` | `GetRolesUseCaseSuccess`, `GetOneRoleUseCaseSuccess` |
| Domain error | `<Noun><Problem>Error` | `RoleNotFoundError` |
| Read model | `<Noun>View` | `ModelView`, `AuthenticatedUserView` |
| Query port | `<Noun>Query` in `_<noun>query.py` | `ModelQuery`, `AuthenticatedUserQuery` |
| HTTP exception | `<Noun><Problem>HTTPException` | `RoleNotFoundHTTPException` |
| Request body | `<Verb><Noun>Body` | `CreateRoleBody` |
| Response | `<Noun>Response` / `<Noun>sResponse` | `RoleResponse`, `RolesResponse` |
| DI factory | `<verb>_<noun>_use_case_factory` | `get_roles_use_case_factory`, `get_one_role_use_case_factory` |
| Entity unit tests | `api/tests/unit/domain/<domain>/test_<domain>entities.py` | `test_ocrentities.py`, `test_userentities.py` |

Verbs: `Create`, `Update`, `Delete`, `GetOne` (single / get-by-id), `Get<Plural>` (list). When a resource has both a list and a get-by-id use case, the single-resource name is `GetOne<Noun>` — never `Get<Noun>` (`GetRoleUseCase` → `GetOneRoleUseCase`, `GetModelUseCase` → `GetOneModelUseCase`). Pair them: `GetRolesUseCase` + `GetOneRoleUseCase`, `GetModelsUseCase` + `GetOneModelUseCase`.

The domain and API term for an API credential is **key** (`Key`, `KeyResponse`, `/admin/keys`). Do not introduce `token` for that resource.

---

## Domain

| Kind | Location | Form |
|------|----------|------|
| Entity | `api/domain/<context>/entities.py` | Pydantic `BaseModel` (from `api.domain`) |
| Error | `api/domain/<context>/errors.py` | `@dataclass` |
| Repository port | `api/domain/<context>/_<entity>repository.py` | `ABC` |
| `Command` / `UseCaseSuccess` | `api/use_cases/<area>/` | `@dataclass` |

**Entities are Pydantic models, never `@dataclass`.** A `@dataclass` validates nothing at construction, so it silently accepts a wrong type and skips the `UtcDatetime` normalization — an entity built with a naive `datetime` would then serialize to a shifted Unix timestamp. `BaseModel` also gives `model_copy(update=...)`, which the `with_*` helpers (`Router.with_name`, `Provider.with_timeout`, `Role.with_limits`) rely on.

`@dataclass` is for the plain carriers that never hold invariants: domain errors, and the `Command` / `UseCaseSuccess` pairs of the use-case layer.

---

## Schemas

Location: `api/infrastructure/fastapi/schemas/`.

| Kind | Pattern |
|------|---------|
| Create request | `Create<Noun>Body` |
| Update request | `Update<Noun>Body` |
| Single response | `<Noun>Response` |
| List response | `<Noun>sResponse` |

### `object` discriminator

Every response includes `object`:

| Type | `object` value |
|------|----------------|
| Single resource | resource name (singular): `"role"`, `"user"`, `"key"`, `"router"` |
| Paginated list | `"list"` |

**Single resource:**
```json
{ "object": "key", "id": 1, "name": "my-key", "user": 42, "created": 1704067200 }
```

**Paginated list:**
```json
{
  "object": "list",
  "total": 42,
  "offset": 0,
  "limit": 10,
  "data": [{ "object": "role", "id": 1, "...": "..." }]
}
```

Never return a bare array. Items inside `data` keep their own `object` discriminator. List wrappers always include `total`, `offset`, and `limit`.

### `data` field

- Present only on list wrappers (`*sResponse`)
- Type: `list[<Noun>Response]`
- Built in the endpoint: `[RoleResponse.model_validate(r, from_attributes=True) for r in page.data]`

### `_id` suffix

| Context | Convention | Examples |
|---------|------------|----------|
| Domain entity | `*_id` | `user_id`, `role_id`, `router_id` |
| Path params | `*_id` | `role_id`, `router_id`, `user_id` |
| Query filters | `*_id` | `?role_id=1`, `?organization_id=2` |
| Response FK fields | `*_id` (usually) | `user_id` in `RouterResponse`, `organization_id` in `UserResponse` |
| Request body FK | often shortened | `CreateKeyBody.user`, `CreateUserBody.role` |

Map at the boundary:
```python
# endpoint → command
CreateKeyCommand(user_id=body.user, ...)

# domain → response (@model_validator)
"user": data.user_id  # Key entity → KeyResponse
```

### Update requests are full replacements

`Update<Noun>Body` requires **every persisted field** — there is no partial update on clean-architecture endpoints.

- No `default=None` meaning "skip this field". A missing field is a 422.
- `| None` only where `null` is a valid stored value, and it then **sets** the column to `null` (clear the organization, the budget, the QoS policy…).
- Lists replace the stored list; an empty list clears it (role `permissions` / `limits`, router `aliases`).
- The use case applies the command as a replacement: `entity.with_x(command.x)` for every field, never `if command.x is not None`.
- Exception: write-only secrets (`password`, `current_password`) stay optional — omitting them leaves the secret unchanged.

Do not reuse a `Create<Noun>Body` for an update: its optional fields carry the wrong meaning.

Callers (playground `edit_entity`, e2e tests) must send the whole current form state, not a diff.

### Timestamps

- API: Unix seconds as `int` (`created`, `updated`, `expires`)
- Domain and Postgres: timezone-aware UTC `datetime` — annotate entity fields with `UtcDatetime` from `api/domain/__init__.py`, and always build "now" with `datetime.now(tz=UTC)`
- Repositories select and write the `timestamptz` columns directly — no `extract(epoch)` / `to_timestamp()`
- Convert at the boundary only: `@field_validator` (request) or `@model_validator(mode="before")` (response). Request validators keep the field typed `int` (OpenAPI) and return a UTC `datetime` for the command. Keys also reject past timestamps (`CreateKeyBody`); user `expires` converts without that check so a past value expires the user — see `CreateUserBody` / `UserUpdateRequest` / `KeyResponse`. Command timestamp fields are typed `UtcDatetime` to match the entity; the dataclass does not convert.
- Playground displays local time through `playground/app/shared/utils/timestamps.py`

Full rationale: `adr/2026-08-27-datetime-handling.md`.

### Aliases

When JSON key ≠ Python field name:
```python
router_type: Annotated[ModelType, Field(alias="type", ...)]
```

### Mapping domain → API

- Names align → `Response.model_validate(entity, from_attributes=True)`
- Names differ → `@model_validator(mode="before")` (see `KeyResponse.from_key` in `api/infrastructure/fastapi/schemas/admin/keys.py`)

---

## Use case

One file per operation. Return domain errors — never raise them.

```python
@dataclass
class VerbNounCommand: ...

@dataclass
class VerbNounUseCaseSuccess:
    entity: Entity

type VerbNounUseCaseResult = VerbNounUseCaseSuccess | SomeError

class VerbNounUseCase:
    def __init__(self, repository: SomeRepository):
        self.repository = repository

    async def execute(self, command: VerbNounCommand) -> VerbNounUseCaseResult:
        result = await self.repository.some_method(...)
        match result:
            case Entity() as entity:
                return VerbNounUseCaseSuccess(entity=entity)
            case SomeError() as error:
                return error
```

Prefer `match`/`case` over `isinstance` when branching on a repository result or domain error.

Export `Command`, `UseCase`, `UseCaseSuccess` from `__init__.py`.

### Keep business logic inline in `execute()`

Put the full business flow in a single `execute()` method so it can be read top-to-bottom in one pass. Do **not** extract private orchestration methods that hide control flow (`_sync_user`, `_create_user`, `_resolve_*`, etc.).

Allowed outside `execute()`:
- `__init__` (dependencies + config)
- **`@staticmethod`** helpers on the use case class when they are pure/unit operations reused several times — not business orchestration
- **Documented override hooks** — see below

Do **not** put helpers at module level; keep them as static methods on the use case class.

```python
class CreateExampleUseCase:
    # pure/unit operation reused across the flow — @staticmethod is fine
    @staticmethod
    def _normalize_claim(value: object | None) -> str | None:
        if not isinstance(value, str):
            return None
        return value.strip() or None

    async def execute(self, command: CreateExampleCommand) -> CreateExampleUseCaseResult:
        # bad — business steps hidden behind private methods
        # user = await self._sync_user(user, command)

        # good — full flow visible in execute(); call static helpers for repeated unit work
        claim = self._normalize_claim(command.claims.get("role"))
        result = await self.user_repository.get_user_by_iss_and_sub(...)
        match result:
            case User() as user:
                ...
            case UserNotFoundError():
                # the create path goes here — inline, not extracted
                ...
```

### Override hooks

`AuthSsoLoginUseCase` (`api/use_cases/auth/_authssologinusecase.py`) is the one deliberate exception. It exposes four **public async** methods outside `execute()` — `has_access`, `get_user_name`, `get_role_id`, `get_organization_id` — with default implementations that operators replace to plug in their own SSO policy. They are a documented extension point (see `docs.opengatellm.org/features/users_management/sso`), not hidden orchestration.

Do **not** inline them. Conversely, do not introduce new hooks of this kind unless the extension point is a published, documented contract.

---

## Postgres session

Two session factories. Choose **in the use-case factory** in `api/dependencies.py`. Repositories stay agnostic: they take `AsyncSession` (`AutocommitSession` is a subclass).

| Factory | Session | Use when |
|---------|---------|----------|
| `get_postgres_session` | transactional `AsyncSession` | Admin CRUD, auth login/SSO, bootstrap, anything with `@with_lock` or multi-statement atomicity |
| `get_autocommit_postgres_session` | `AutocommitSession` | Use cases that call AI models (provider forward / inference) |

**Why:** a transactional session stays checked out and `idle in transaction` for the whole request. Inference can take minutes and pin a pool connection. `AutocommitSession` commits after each `execute` / `scalar` / `get`, so the connection returns to the pool **before** the provider call. Everything wired to it is a read — the router and provider lookups, and the `AccessController` key and user lookups. Writes and multi-statement work take the transactional factory.

Autocommit wiring:

- Model-forward use cases: `create_embeddings_use_case_factory`, `create_ocr_use_case_factory`, `create_rerank_use_case_factory`, `create_audio_transcriptions_use_case_factory`
- `AccessController` lookups: `_authentication_key_repository`, `_authenticated_user_query` (they run on the same request as model-forward)

```python
def create_embeddings_use_case_factory(
    postgres_session: AutocommitSession = Depends(get_autocommit_postgres_session),
    ...
) -> CreateEmbeddingsUseCase:
    return CreateEmbeddingsUseCase(
        provider_repository=_provider_repository(postgres_session),
        router_repository=_router_repository(postgres_session),
        ...
    )
```

Keep a **separate** transactional factory for the same repository when used by admin CRUD (`_key_repository` vs `_authentication_key_repository`).

Do **not**:

- Mix both sessions in one use case
- Use `AutocommitSession` with `@with_lock` — advisory locks are transaction-scoped; the decorator raises `TransactionRequiredError` rather than silently dropping the lock
- Call `begin()`, `begin_nested()`, `stream()`, `stream_scalars()`, or `connection()` on `AutocommitSession` (same error)

When adding a model-forward use case, also add a `ForwardScenario` in `api/tests/integration/postgres/test_autocommit_releases_connection_during_model_forward.py`.

---

## Repository

- **Port:** `api/domain/<context>/_<entity>repository.py` — ABC, returns `Entity | DomainError`
- **Adapter:** `api/infrastructure/postgres/_postgres<entity>repository.py` — SQLAlchemy, maps `IntegrityError` → domain errors. `<entity>` is **singular** (`_postgreskeyrepository.py`, `_postgresrouterrepository.py`). `_postgresrolesrepository.py` and `_postgresusersrepository.py` predate the rule — do not copy their plural
- **Pagination:** `EntitiesPage["Entity"]` alias (e.g. `RolePage = EntitiesPage["Role"]`). List queries use `func.count().over().label("total")` plus `fetch_page_with_total` (see `_postgreskeyrepository.py`)
- `@with_lock` needs a transactional session — never wire a locked method through `get_autocommit_postgres_session`
- No `*` keyword-only separator on method signatures

### `IntegrityError` mapping

Map only **known** constraint / FK names to domain errors. If the `IntegrityError` does not match an explicit case, **re-raise** it — never swallow unknown integrity failures as a generic domain error.

Avoid adding `begin_nested()` just to keep the session usable after a mapped `IntegrityError`. HTTP handlers already roll back through `get_postgres_session` when they raise. Bootstrap does not keep using the session after a mapped conflict: it returns `Skipped` and the lifespan rolls back the aborted transaction. Do not substitute `AutocommitSession` to recover from `IntegrityError`: `@with_lock` requires a transactional session.

```python
except IntegrityError as e:
    if "token_user_id_fkey" in str(e.orig):
        return UserNotFoundError(id=user_id)
    if "unique_token_name_per_user" in str(e.orig):
        return KeyAlreadyExistsError(name=name)
    raise  # unknown constraint → bubble up as 500
```

Reference adapters: `_postgreskeyrepository.py`, `_postgresproviderrepository.py`, `_postgresrouterrepository.py`, `_postgresusersrepository.py`.

---

## Query and view (read model)

A **repository** loads the aggregate a write flow mutates. A **query** loads a denormalized read model for a read-only endpoint. Use a query when the response joins several tables, or derives fields the aggregate must not own.

| Kind | Location | Pattern |
|------|----------|---------|
| View | `api/domain/<context>/views.py` | `<Noun>View`, `BaseModel` + `ConfigDict(frozen=True)` |
| Port | `api/domain/<context>/_<noun>query.py` | `<Noun>Query` ABC, returns `View \| DomainError` |
| Adapter | `api/infrastructure/postgres/_postgres<noun>query.py` | `Postgres<Noun>Query` |
| DI factory | `api/dependencies.py` | `_<noun>_query` |
| Tests | `api/tests/integration/postgres/test_postgres<noun>query.py` | same rules as an adapter |

Reference: `ModelQuery` / `ModelView` / `PostgresModelQuery` (models API), `AuthenticatedUserQuery` / `AuthenticatedUserView` (`AccessController`).

A view is read-only: no `update_*` methods, no domain invariants. It may carry the id of the aggregate it was projected from (`ModelView.router_id`) so the use case can run access control on it.

**Do not put a derived field on an entity just to expose it.** `vector_size` and `max_context_length` belong to `Provider`; `Router` does not mirror them. Consistency between providers of the same router is checked in the use case by reading the router's existing providers, and the models API reads the capability from the provider through `ModelQuery`.

---

## Endpoint

Thin handler — delegate to use case, map errors to HTTP.

```python
@router.get(path=EndpointRoute.ADMIN_ROLES, ...)
async def get_roles(
    offset: int = Query(default=0, ge=0, ...),
    limit: int = Query(default=10, ge=1, le=100, ...),
    sort_by: SortField = Query(default=SortField.ID, ...),
    sort_order: SortOrder = Query(default=SortOrder.ASC, ...),
    get_roles_use_case: GetRolesUseCase = Depends(get_roles_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> RolesResponse:
    command = GetRolesCommand(offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order)
    try:
        result = await get_roles_use_case.execute(command)
    except Exception:
        logger.exception("Unexpected error while executing get_roles use case", extra={...})
        raise InternalServerHTTPException()
    match result:
        case GetRolesUseCaseSuccess(role_page=page):
            return RolesResponse(
                total=page.total, offset=offset, limit=limit,
                data=[RoleResponse.model_validate(r, from_attributes=True) for r in page.data],
            )
```

- Auth: `AccessController` from `api.infrastructure.fastapi` (`only_admin=True` for admin routes, `allow_expired=True` when expired users must still reach the route, e.g. GET `/v1/me`)
- Auth user: `authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user)` when only the user is needed. Keep `get_request_context` only when the full `RequestContext` is required.
- Sort query params: `sort_by` / `sort_order`
- Document errors: `responses=get_documentation_responses([...])`
- `case RoleNotFoundError(id=role_id, name=name)` **captures** `None`; it does not require an id. Pass both through to the HTTP exception (which already has a generic `"Role not found."` fallback). Map the fields the use case actually returns (`id=` from FK failures, not `name=` unless that path exists).

---

## Error handling

1. Domain errors — `@dataclass` in `domain/<context>/errors.py`, **returned** not raised
2. Use cases — propagate via `match`/`case`
3. Repositories — return `Entity | Error`
4. Endpoints — map domain error → `*HTTPException` in `api/infrastructure/fastapi/endpoints/exceptions.py`
5. Unexpected — `logger.exception` + `InternalServerHTTPException`

---

## Tests

Each layer tests **its** responsibility. Do not re-run use-case branches through HTTP.

| Layer | Path | Tests | Does not test |
|-------|------|-------|----------------|
| Unit use case | `api/tests/unit/use_case/<area>/test_<usecase>.py` | Every distinct `execute()` branch | SQL, HTTP status, Pydantic 422 |
| Unit domain | `api/tests/unit/domain/<domain>/test_<domain>entities.py` | Entity methods (`need_to_update`) | Use-case orchestration |
| Integration endpoint | `api/tests/integration/endpoints/.../test_<action>_<resource>.py` | Happy path, auth, error mapping, endpoint-only guards | Create/update/link business flows |
| Integration repository | `api/tests/integration/postgres/` | Persist/read, constraints, new columns | Use-case policy |
| Model-forward pool | `api/tests/integration/postgres/test_autocommit_releases_connection_during_model_forward.py` | Connection released during provider call | Use-case branches |
| HTTP adapter | `api/tests/integration/http/test_<adapter>.py` | Each distinct status / network branch (`respx`) | Callers of the adapter |

Mirror an existing test for the same verb (`test_get_roles.py`, `test_create_key.py`, `test_create_user.py`).

### Style

- Packages: every test directory **must** contain an (empty) `__init__.py`. Without it pytest's default `prepend` import mode derives the module name from the basename alone, so two same-named files in two non-package directories collide (`import file mismatch`, e.g. `unit/.../keys/test_get_key.py` vs `integration/endpoints/keys/test_get_key.py`). Add it in the same change as the new directory
- File names: entity tests **must** be `test_<domain>entities.py` (`test_ocrentities.py`, `test_userentities.py`) — not `test_<entity>.py`
- Test names: unit `test_should_<behavior>` ; endpoint `test_happy_path`, `test_error_maps_to_correct_http_status`, `test_rejects_non_admin_user` ; postgres `test_returns_*` / `test_creates_*`
- Mocks: every mock object and mock fixture is prefixed with `mock_` (`mock_use_case`, `mock_authenticated_user`)
- Comments: `# Arrange` / `# Act` / `# Assert` (same as `test_createuserusecase.py`)
- Async integration: `@pytest.mark.asyncio(loop_scope="session")` (including HTTP adapters)
- Postgres: `repository` fixture from `db_session` — do not construct the repo inside each test
- Factories: SQL `UserSQLFactory` / `RoleSQLFactory` / `KeySQLFactory` ; unit `UserFactory`. Add a factory field when the column is new
- Do not use a mutable module-level dict to pass IDs from a fixture into a DI factory — close over the values (see `api/tests/integration/endpoints/test_auth_sso_login.py`)

### Unit use case

Port doubles are autospecced against the **domain port**, never bare `MagicMock()` / `AsyncMock()`:

```python
@pytest.fixture
def mock_router_repository():
    return create_autospec(RouterRepository, instance=True, spec_set=True)
```

`create_autospec` derives the double from the ABC under `api/domain/`, so an unknown attribute raises
`AttributeError` and a call that does not match the port signature raises `TypeError`. A bare mock accepts
both silently, and the test stops pinning down the boundary it exists to protect. Spec the port, never an
`api/infrastructure/` adapter. Async port methods become `AsyncMock` children on their own — keep using
`assert_awaited_once_with`.

If the autospec rejects a call, fix the call — or the port declaration if that is what is wrong (a missing
`self` on an abstract method silently shifts every parameter). Never loosen the spec to make a test pass.

`api/tests/unit/use_case/test_providerrequestforwadingusecase.py` is the reference. Tests still on bare
mocks are migrated when they are next touched.

Cover:

- Happy path (assert calls **and** payloads: `assert_awaited_once_with`, expire timestamps)
- Each early return and each `match` arm that is a **different** branch (`try/except`, create vs update error)
- One representative error per identical `case error: return error` block — do not add `OrganizationNotFoundError` **and** `UserAlreadyExistsError` if both only propagate `create_user`

Do **not** add a test that only changes an unused constructor argument (`auth_login_type` stored but never read). That locks unimplemented behavior.

Entity helpers used by the use case belong in domain unit tests, not extra use-case scenarios for every field.

`ModelTokenizer.compute_tokens` must match the real tokenizer contract: empty `texts` → `0`. Do **not** use a constant `return_value` (it would count completion tokens on `[]`). Do **not** skip the tokenizer call in production when `get_completions()` is empty.

```python
@pytest.fixture
def mock_model_tokenizer():
    tokenizer = create_autospec(ModelTokenizer, instance=True, spec_set=True)
    tokenizer.compute_tokens.side_effect = lambda texts: len(texts)
    return tokenizer
```

Assert usage from the texts actually passed (`len(get_prompts())`, `len(get_completions())`). Rerank / embeddings return `[]` completions → `completion_tokens=0`. OCR / audio have real completions — use `side_effect = [prompt_count, completion_count]` when the two calls need different values.

### Integration endpoint

Necessary:

1. `test_happy_path` — real use case + DB (`AsyncClient`). Assert response shape (`object`, ids, token prefix), not every side effect already covered in unit tests
2. `test_error_maps_to_correct_http_status` — mock the use case:

```python
mock_use_case = AsyncMock()
mock_use_case.execute.return_value = use_case_result
app.dependency_overrides[create_user_use_case_factory] = lambda: mock_use_case
```

One parametrize row **per mapped domain error type**. Use the error shape the use case/repo returns (`OrganizationNotFoundError(id=99)`, not `name="…"` if the adapter sets `id=`). `case Foo(id=x, name=y)` still matches `Foo()` with `None`s — a `name=` test hides a mapping that never forwards `id`.
3. Auth 401/403 when `AccessController` applies (not on public auth login)
4. Guards that run **before** the use case (missing `Cookie` → 401)

Do **not**:

- Replay use-case branches over HTTP (SSO create-user, link-by-email, email update) unless the test asserts a side effect the unit tests cannot see
- Extra HTTP-exception constructor variants (`RoleNotFoundError()`, `RoleNotFoundError(name=…)`) when the endpoint has a single `case`
- 422 unless the constraint is business-sensitive (e.g. create-user password). Skip generic Pydantic required-field tests
- 500 / `InternalServerHTTPException`

### Integration repository

- Happy persist + not-found / duplicate for the method under test
- New columns on **create and update** round-trips — one assertion on the new field is enough; do not re-assert on every getter
- Known `IntegrityError` mappings (unique, FK)
- One negative for a compound lookup (`iss`+`sub`) — not both wrong-iss and wrong-sub

### Model-forward autocommit

When adding a use case that calls a provider (OCR, embeddings, rerank, audio, chat, …), add a `ForwardScenario` to `test_autocommit_releases_connection_during_model_forward.py`. That test probes `pg_stat_activity` **during** the mocked provider call: autocommit wiring must show `checkedout == 0` and no `idle in transaction`.

### HTTP adapters

One test per distinct branch (202+email, 401, missing header, unexpected status, network error). Two exceptions that share `except Exception` do not need two tests (`ConnectError` vs timeout).

```bash
uv run pytest api/tests/unit/use_case/<area>/
uv run pytest api/tests/unit/domain/<domain>/
uv run pytest api/tests/integration/endpoints/...
uv run pytest api/tests/integration/postgres/
uv run pytest api/tests/unit/infrastructure/postgres/
uv run pytest api/tests/integration/http/
```

---

## Principles

Craft:

1. Smallest correct diff. Do not mix feature work with unrelated cleanup.
2. Names reveal intent. Prefer explicit code over clever shortcuts. Explicit naming is what keeps comments rare here: a comment earns its place only when it explains a *why* the code cannot — a constraint, a workaround, a non-obvious ordering. Never narrate what the next line does.
3. No speculative complexity. Implement what the current requirement needs (YAGNI). Extract a shared helper only when the same pattern already exists in more than one place.
4. Leave touched code better than you found it, within the scope of the change. Align leftover modules with this file when you edit them; do not extend them.
5. Fail explicitly. Return known domain errors; re-raise unknown failures. Do not swallow exceptions or invent a generic error to hide them.
6. Tests specify behavior. One layer per concern; happy path + auth + error mapping at the HTTP boundary; skip trivial assertions.

Architecture:

7. Follow existing code for the same resource (or the closest pattern in [Architecture](#architecture)).
8. Thin use cases — delegate to repositories; keep business flow inline in `execute()`.
9. Model-forward use cases use `AutocommitSession` so inference does not pin a pooled Postgres connection.

This file:

10. `AGENTS.md` is the source of truth for repository conventions. When a new pattern or convention emerges and is kept, add it here in the same change. If you replace a pattern, update or delete the obsolete rule so the file stays aligned with the code.
