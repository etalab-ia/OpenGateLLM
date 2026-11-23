# ADR - 2026-11-20 - OpenFGA data migrations

* **Status:** Accepted
* **Date:** 2026-11-20
* **Authors:** Tibo PENDINO
* **Related:**
  * [#1474 — [openfga] Decide how OpenFGA data migrations ship with OpenGateLLM](https://github.com/etalab-ia/OpenGateLLM/issues/1474)
  * [#1199](https://github.com/etalab-ia/OpenGateLLM/issues/1199) (providers), [#1451](https://github.com/etalab-ia/OpenGateLLM/issues/1451) (routers), [#1462](https://github.com/etalab-ia/OpenGateLLM/issues/1462) (roles) — the next resources that will need one
* **Decision Outcome:** OpenFGA data migrations live in `api/infrastructure/openfga/migrations/`, read Postgres with raw SQL and write through the OpenFGA SDK, and run in the `db-migrate` one-shot service, after the Alembic upgrade and the model publication, before the API starts.

---

## Context

From v0.9.4 the API reads OpenFGA relations that rows created before OpenFGA do not hold:

| Relation                                  | Missing for existing data →                                                                                              |
|-------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `platform:api#admin@user:<id>`            | every pre-existing admin other than the bootstrap one gets a 403 on `/v1/admin/users` and `POST /v1/admin/organizations` |
| `organization:<id>#platform@platform:api` | every pre-existing organization answers 403 on `DELETE /v1/admin/organizations/{id}`                                     |

OpenGateLLM shipped no backfill for them, so a self-hosted instance upgrading had no way to write them. This decision brings the first two: `m001_platform_admins` and `m002_organizations_platform`. Providers, routers and roles will each add relations of the same kind, so the mechanism had to be settled first.

## Decision

### 1. Location

`api/infrastructure/openfga/migrations/`, next to `model.fga`. The model already lives in this repository so that a relation changes in the same commit as the code reading it; a data migration has the same coupling. Rejected: `scripts/` (outside the package the image runs) and `adr/scripts/` (one-shot scripts tied to an ADR, not an iterative series).

### 2. Technology

The structure already run in production is kept:

* one module per migration, `m<NNN>_<slug>.py`, exposing `DESCRIPTION` and `async def run(connection, openfga, dry_run) -> dict[str, int]`;
* the rows are read from the OpenGateLLM database with plain SQL (`asyncpg`): the queries are ours, no input reaches them;
* the tuples are written through the OpenFGA SDK, after a `check` of each one;
* a runner, `python -m api.infrastructure.openfga.migrations`, reads the configuration file (`CONFIG_FILE`), resolves the store by name and its latest model, runs every migration in name order, and supports `--dry-run` and `--only`.

Rejected:

* **Alembic revisions calling the SDK.** They break offline `alembic upgrade --sql` (rule 2 of *Migrations* in `AGENTS.md`), an OpenFGA write is outside the Postgres transaction so a failed revision leaves tuples behind, and every Alembic upgrade would need OpenFGA up.
* **Alembic writing OpenFGA's tables directly.** That schema is internal to OpenFGA and unversioned for clients; it bypasses its API and its model validation.

### 3. Deployment

The `db-migrate` service of `compose.example.yml` runs, in order and stopping at the first failure:

1. `alembic upgrade head`;
2. `scripts/setup_openfga.sh`, which creates the store if missing and publishes `model.fga` when it differs — the data migrations need the model, and on a fresh install nothing else would have published it yet;
3. the OpenFGA data migrations.

The `api` service waits for `db-migrate` to complete successfully. `scripts/startup_api.sh` still runs `setup_openfga.sh`, a no-op when the model is unchanged, so a deployment that does not run `db-migrate` keeps working.

Every migration is idempotent and non-destructive: no ledger is kept, every deployment re-runs all of them at the cost of one `check` per row, and a second run writes nothing (`granted=0`). The source rows are never deleted, and no Alembic contract may drop a table or column a migration still reads.

### 4. Lifetime

The migrations are temporary: they are deleted once every supported upgrade path has run them. That window is not defined yet. How a migration renames or removes a relation is not settled either; until it is, a migration only adds tuples.

## Consequences

* A self-hosted instance gets the backfill by running `db-migrate`, as it already does for the schema.
* A PR adding a relation that existing rows must hold ships its data migration in the same PR (`AGENTS.md`, *OpenFGA data migrations*).
* `db-migrate` now depends on OpenFGA being up.
* With no ledger, the cost of a deployment grows with the number of rows each migration reads, until the migration is deleted.
