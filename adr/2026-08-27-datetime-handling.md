# ADR - 2026-08-27 - Datetime handling across API, domain and playground

* **Status:** Accepted
* **Date:** 2026-08-27
* **Authors:** Development Team
* **Related:**
  * [#960 — [clean-architecture] Standardize datetime handling across API and playground](https://github.com/etalab-ia/OpenGateLLM/issues/960)
  * [ADR 2026-01-07 — Migration to Clean Architecture](2026-01-07-clean-architecture-migration.md)
* **Decision Outcome:** Unix timestamps (`int`) at the HTTP boundary only, timezone-aware UTC `datetime` in the domain and in Postgres, local-timezone rendering in the playground.

---

## Context

Before this decision, the same instant was represented differently depending on which file you opened:

* `api/infrastructure/fastapi/schemas/admin/keys.py` already did the right thing — accept `int`, convert to UTC `datetime` in a validator, keep `datetime` in the domain and in SQL, convert back to `int` in the response — but nothing said it was *the* convention.
* Several domain entities (`Role`, `Router`, `Provider`, `User`, `Model`, `AuthenticatedUserView`) carried `int` timestamps, so the Postgres adapters had to flatten `timestamptz` columns to epoch seconds (`cast(func.extract("epoch", column), Integer)`) on the way out and re-inflate them (`func.to_timestamp(...)`) on the way in. `api/domain/role/entities.py` carried a `TODO` waiting for exactly this decision.
* Several `datetime.now()` calls produced naive local datetimes. None of them corrupted data — asyncpg encodes a naive value using the Python process timezone, which is what `datetime.now()` returns, so the two conversions cancel out and the stored instant is correct. But the value's meaning then depends on the process timezone rather than on the code, and a single `datetime.utcnow()` (naive *UTC*) slipping in would be silently shifted. One genuine bug did hide there: `Chunk.created` used `Field(default=datetime.now())`, evaluated once at import, so every chunk inherited the process start time.
* The playground formatted dates with `datetime.fromtimestamp(...)`, which happens to render local time but says nothing about which timezone it assumes, and did so with a copy of the same expression in each feature state.

The cost of that spread: no single place to reason about "what timezone is this value in?", conversions duplicated in adapters that should be dumb mappers, and a class of bug (naive datetime into an aware column) that only shows up outside UTC.

## Decision

One representation per layer, converted at exactly one place — the layer boundary.

| Layer | Representation |
|-------|----------------|
| HTTP request / response (JSON) | Unix seconds, `int` |
| API schemas (`api/infrastructure/fastapi/schemas/`) | `int` on the wire, converted in a validator |
| Use cases, domain entities, repository ports | timezone-aware UTC `datetime` |
| Postgres (`api/sql/models.py`) | `DateTime(timezone=True)` (`UtcDateTime`) |
| Playground display | the viewer's local timezone |

### Domain and persistence: aware UTC `datetime`

Domain timestamp fields use the `UtcDatetime` alias from `api/domain/__init__.py`:

```python
UtcDatetime = Annotated[datetime, BeforeValidator(_parse_unix_timestamp), AfterValidator(_to_utc)]
```

It normalizes anything Pydantic accepts as a `datetime` to UTC, treats a naive value as already-UTC, and converts a Unix timestamp (`int`) the same way. An entity can never hold an ambiguous timestamp — and `int(value.timestamp())` at the boundary is always correct. The same alias covers the provider-facing boundary: provider `/v1/models` payloads carry `created` as OpenAI-style Unix seconds, and the HTTP adapters hand that `int` straight to `Model`, where `UtcDatetime` turns it into an aware UTC datetime.

Repositories select and write the `timestamptz` columns **directly**. No `extract(epoch)` on read, no `to_timestamp()` on write:

```python
# api/infrastructure/postgres/_postgresrolesrepository.py
select(RoleTable.id, RoleTable.name, RoleTable.created, RoleTable.updated)
```

Anything producing a "now" writes `datetime.now(tz=UTC)`, never a naive `datetime.now()`.

### API boundary: `int`, converted in the schema

**Request** — a `@field_validator` validates the timestamp and returns the `datetime` the command layer receives. The field stays annotated `int`, so the OpenAPI schema still documents an integer.

```python
# api/infrastructure/fastapi/schemas/admin/keys.py — reject past + convert
@field_validator("expires", mode="after")
def must_be_future_and_convert_to_datetime(cls, expires) -> None | datetime:
    if expires is None:
        return expires
    if expires <= int(datetime.now(tz=UTC).timestamp()):
        raise ValueError("Expiration time must be in the future.")
    return datetime.fromtimestamp(timestamp=expires, tz=UTC)
```

User `expires` uses the same conversion without the future check, so a past timestamp expires the account immediately (and a full-replacement PATCH can resubmit an already-expired user).

**Response** — a `@model_validator(mode="before")` maps the domain entity to the wire shape, converting each `datetime` with `int(value.timestamp())`:

```python
# api/infrastructure/fastapi/schemas/admin/keys.py — the reference implementation
@model_validator(mode="before")
@classmethod
def from_key(cls, data):
    if isinstance(data, Key):
        return {
            ...,
            "expires": int(data.expires.timestamp()) if data.expires is not None else None,
            "created": int(data.created.timestamp()),
        }
    return data
```

Endpoints keep calling `Response.model_validate(entity, from_attributes=True)`; the validator recognizes the entity and does the mapping. Schemas following this pattern: `admin/keys.py`, `admin/organizations.py`, `admin/roles.py`, `admin/routers.py`, `admin/providers.py`, `admin/users.py`, `me.py`, `models.py`, `usage.py`.

### Playground: local timezone, one helper

`playground/app/shared/utils/timestamps.py` owns every conversion: `format_datetime`, `format_date`, `format_local_date`, `local_now`, `to_local_datetime`, `date_to_timestamp`. Feature states call it instead of writing `datetime.fromtimestamp(...)` inline. It uses `astimezone()` with no argument, which resolves the system timezone *for the instant being converted*, so offsets stay correct across DST boundaries.

### Legacy schemas

`api/schemas/` (the pre-clean-architecture DTOs, still used by `_identityaccessmanager.py`, `_modelregistry.py` and `/v1/admin/organizations`) already exposes `int` at the boundary, which matches the convention. Those modules are HTTP DTOs only and never cross into `api/domain`, so they keep their `int` fields and are removed resource by resource as clean-architecture migration proceeds. Their naive `datetime.now()` defaults were made UTC-explicit as part of this ADR.

## Consequences

**Easier**

* One answer to "what timezone is this?" per layer; the boundary is the only place a conversion happens.
* Postgres adapters became plain column mappers — the `extract(epoch)` / `to_timestamp()` round trips are gone, and `PostgresRolesRepository._row_to_role` is now used by every one of its query methods (the `TODO` on `Role` is resolved).
* Naive datetimes can no longer reach an entity ambiguously: `UtcDatetime` normalizes on the way in, and `timestamptz` columns only ever receive aware values. Note the two layers disagree on what a naive value *means* — asyncpg reads it as process-local, `UtcDatetime` reads it as UTC — which is exactly why no naive value should exist in the first place.
* Date arithmetic and comparison (`user.expires < datetime.now(tz=UTC)`) happen on `datetime`, not on epoch integers.

**Harder / to watch**

* Every new response schema that carries a timestamp needs its `@model_validator(mode="before")`. Without it, `model_validate(entity, from_attributes=True)` would hand Pydantic a `datetime` for an `int` field and fail — loudly, which is the point.
* Sub-second precision is lost at the API boundary (`int(...timestamp())` truncates). That is the existing public contract and is unchanged by this ADR.

**Unchanged**

The public API is untouched: every `created`, `updated` and `expires` field is still Unix seconds as `int`, in both directions. The generated OpenAPI schema for those fields is identical before and after, type for type.
