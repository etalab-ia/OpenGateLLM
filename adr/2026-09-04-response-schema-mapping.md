# ADR - 2026-09-04 - Mapping domain entities to response schemas

* **Status:** Accepted
* **Date:** 2026-09-04
* **Authors:** Development Team
* **Related:**
  * [#1058 — [clean-architecture] Reduce response schema mapper boilerplate](https://github.com/etalab-ia/OpenGateLLM/issues/1058)
  * [ADR 2026-08-27 — Datetime handling across API, domain and playground](2026-08-27-datetime-handling.md) — supersedes its **Response** paragraph; the rest of that ADR stands
  * [#960 — [clean-architecture] Standardize datetime handling across API and playground](https://github.com/etalab-ia/OpenGateLLM/issues/960)
* **Decision Outcome:** `model_validate(entity, from_attributes=True)` does the field-by-field mapping; a response schema declares only what genuinely differs from its entity, on the field itself.

---

## Context

[ADR 2026-08-27](2026-08-27-datetime-handling.md) settled where a `datetime` becomes an `int`, and prescribed a `@model_validator(mode="before")` per response schema to do it. [#960](https://github.com/etalab-ia/OpenGateLLM/issues/960) then generalized that mapper to every migrated resource. The pattern had a real origin — `KeyResponse` renamed `user_id` to `user`, which no automatic mapping could express — and `AGENTS.md` prescribed it.

Applied to all ten response schemas, the cost became visible. Measured on `main` on 2026-09-04:

| | count |
|---|---|
| `@model_validator(mode="before")` mappers | 10 |
| lines of code they represent | 158 |
| dict entries across all of them | 102 |
| entries that are a pure `data.x` → `"x"` copy | **70 (68 %)** |

The 32 entries that did something fell into four shapes only: `datetime` → Unix `int` (18), an `object` discriminator literal identical to the field's own `Literal` default (9), one field rename, and four nested structures.

So four fifths of those lines restated what the field declarations directly above them already said. The costs:

* **Drift.** The mapper is a second, implicit declaration of the schema. Adding a field and forgetting the dict does not raise — the field silently falls back to its default, or to `None`.
* **Duplication.** `int(data.created.timestamp())` written 18 times, `"object": "<name>"` 9 times, across 10 files.
* **Reviewability.** A 20-line dict where 16 lines are noise hides the two that matter.
* **Onboarding.** It reads as if the explicit mapping were required, when `model_validate(entity, from_attributes=True)` alone covers most schemas.

## Decision

Endpoints keep calling `Response.model_validate(entity, from_attributes=True)` — that call is unchanged and remains the single mapping point. What changes is that Pydantic, not a hand-written dict, reads the entity's attributes. A response schema declares **only the differences**, and declares them on the field:

| Difference | Declared as |
|---|---|
| `datetime` → Unix seconds | `Annotated[UnixTimestamp, Field(...)]` (or `UnixTimestamp \| None`) |
| `object` discriminator | the field's own `Literal` default — `object: Annotated[Literal["key"], Field(default="key", ...)]` |
| JSON key ≠ entity attribute | `Field(alias="type")` — `from_attributes` reads the attribute named by the alias |
| Nested value object | declare the nested schema; `from_attributes` propagates into it (`RoleResponse.limits`, `MeResponse.limits`, `Model.costs`) |

### `UnixTimestamp`

The API-boundary counterpart of the domain's `UtcDatetime`, in `api/infrastructure/fastapi/schemas/__init__.py`:

```python
def _to_unix_timestamp(value: datetime | int) -> int:
    return int(value.timestamp()) if isinstance(value, datetime) else value


UnixTimestamp = Annotated[int, BeforeValidator(_to_unix_timestamp)]
```

The field stays typed `int`, so the generated OpenAPI schema still documents an integer — identical to what the mapper produced, type for type and description for description. It is idempotent on an `int`, which matters because FastAPI re-validates a response after dumping it.

```python
# api/infrastructure/fastapi/schemas/admin/keys.py
expires: Annotated[UnixTimestamp | None, Field(default=None, description="Time of expiration, as Unix timestamp. If None, the key never expires.")]
created: Annotated[UnixTimestamp, Field(description="Time of creation, as Unix timestamp.")]
```

### Responses carry the entity's field name

The one rename that motivated the original pattern is removed rather than automated: `KeyResponse.user` became `user_id`, the name the `Key` entity uses. Response FK fields are always `*_id`; only request bodies shorten (`CreateKeyBody.user`), and the endpoint expands them when building the command. This is a breaking change on `/v1/keys`, `/v1/admin/keys` and — through `AuthLoginResponse` — `/v1/auth/login` and `/v1/auth/sso/login`.

### The one exception: restructuring

A `@model_validator(mode="before")` is still correct when a response **restructures** the entity rather than renaming it. One case exists today: `UsageResponse` nests `UsageRecord`'s flat counters under `usage`. It passes the record itself down under that name instead of re-listing the other fields, so `from_attributes` still does all the field work and no field list can drift:

```python
@model_validator(mode="before")
@classmethod
def nest_usage_counters(cls, data):
    if isinstance(data, UsageRecord):
        return data.model_copy(update={"usage": data})
    return data
```

## Consequences

**Easier**

* 161 lines removed from `api/infrastructure/fastapi/schemas/`, and nine of the ten mappers with them. No mixed conventions left in the folder.
* A field added to a response schema can no longer serialize silently to `None`: there is no second list to forget. A field with no matching attribute and no default raises.
* The four recurring conversions are written once, not once per schema.
* A diff on a response schema shows the fields, not the noise around them.

**Harder / to watch**

* Every new response timestamp field must be annotated `UnixTimestamp`, not `int`. Without it, `model_validate(entity, from_attributes=True)` hands Pydantic a `datetime` for an `int` field and fails — loudly, which is the point.
* Pydantic now reads attributes off entities that carry more than the schema declares. It only fetches *declared* fields — it cannot enumerate extras off an arbitrary object — so nothing leaks, and this was checked per schema: `ProviderResponse` does not expose `key` / `basic_auth`, `UserResponse` (which keeps `extra="forbid"`) does not expose `claims` / `password`, `Model` does not expose `router_id`. A new response schema must still be read against its entity with that question in mind.
* `from_attributes=True` is now load-bearing at every call site. Four `OrganizationResponse.model_validate(organization)` calls omitted it and worked only because the validator recognized the entity; they were fixed.

**Unchanged**

The public API, apart from the `user` → `user_id` rename stated above. The generated `openapi.json` was diffed before and after: identical, types and descriptions alike, except the six lines of that rename.
