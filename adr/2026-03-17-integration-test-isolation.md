# ADR - 2026-03-17 - Integration Test Isolation via Transaction Rollback

* **Status:** Accepted
* **Date:** 2026-03-17
* **Authors:** Development Team
* **Decision Outcome:** Isolate each integration test by rolling back an external Postgres transaction

---

## Context

Integration tests require a real database. Two problems arise:

1. **Isolation**: data created by one test must not affect the following ones.
2. **Performance**: cleaning up the database between each test must be fast.

### Considered Approaches

| Option | Approach | Drawback |
|--------|----------|----------|
| A | `drop_all` / `create_all` between each test | Dozens of DDL statements per function — prohibitive at scale |
| B | `DELETE` / `TRUNCATE` between each test | Requires knowing FK ordering — non-trivial overhead at scale |
| **C** ✓ | **Transaction rollback** | None — O(1) cost from Postgres's perspective |

---

## Decision

Use the **transaction rollback** pattern to isolate each test, implemented in `api/tests/integration/conftest.py`.

---

## Implementation

### Three Distinct Levels

**Connection** — the TCP pipe to Postgres. Opening a connection is expensive, which is why SQLAlchemy uses a pool: connections are reused across requests.

**Transaction** — an ACID contract with Postgres, delimited by `BEGIN` / `COMMIT` or `ROLLBACK`. It lives on a connection. If the connection is lost, the transaction disappears. This is managed by Postgres.

**SQLAlchemy Session** — an ORM abstraction that does not exist on the Postgres side. It manages the identity map (a single Python instance per loaded object), the unit of work (accumulating changes before flushing), and object lifecycle. The session drives the connection and transaction via a `SessionTransaction` object, but does not own them strictly: after a `commit()`, it releases the connection back to the pool and starts a new cycle.

### Layer Structure

```
engine (connection pool)
└── connection  (TCP connection, pinned manually)
    └── transaction  (BEGIN — outer transaction)
        └── savepoint  (SAVEPOINT sp1 — created by begin_nested())
            └── [test code]
```

### conftest Mechanics

```python
# 1. Connection and outer transaction opened manually
async with test_postgres_engine.connect() as connection:
    postgres_outer_transaction = await connection.begin()   # BEGIN

    # 2. Session bound to this specific connection
    session = AsyncSession(bind=connection, expire_on_commit=False)
    await session.begin_nested()                            # SAVEPOINT sp1
```

By binding the session to the connection via `bind=connection`, the normal mechanism is bypassed: the session no longer borrows a connection from the pool — it always uses this one. Its transactions (savepoints) are therefore nested inside the outer transaction.

### The Listener — Core Mechanism

```python
@event.listens_for(session.sync_session, "after_transaction_end")
def restart_savepoint(sess, trans):
    if trans.nested and not trans._parent.nested:
        sess.begin_nested()                         # SAVEPOINT sp2, sp3...
```

SQLAlchemy emits `after_transaction_end` whenever a savepoint ends. When the tested code calls `commit()`, the current savepoint terminates — the listener immediately creates a new one. The tested code can call `commit()` as many times as it wants without ever leaving the transactional bubble.

The condition `trans.nested and not trans._parent.nested` targets only the first-level savepoint, ignoring any sub-savepoints the tested code may create internally.

Note: `event.listens_for` operates on `session.sync_session` because the SQLAlchemy event system only works on the underlying synchronous API.

### Full SQL View of a Test

```sql
BEGIN;
  SAVEPOINT sp1;
    INSERT INTO user ...        -- factory
    INSERT INTO router ...      -- factory
    SELECT * FROM router ...    -- assertion or HTTP request
  RELEASE SAVEPOINT sp1;        -- session.commit() in tested code
  SAVEPOINT sp2;                -- restart_savepoint listener
    ...
ROLLBACK;                       -- end of test, everything disappears
```

### Bridge Between the Fixture and the FastAPI Application

For endpoint tests, the test session must be the same one used by HTTP handlers. The `ContextVar` serves this role:

```python
_current_db_session: ContextVar[AsyncSession | None] = ContextVar(...)

# In db_session (fixture)
token = _current_db_session.set(session)

# In override_get_postgres_session (replaces get_postgres_session)
session = _current_db_session.get()
yield session
```

A `ContextVar` gives each asyncio coroutine its own isolated value. It is the async equivalent of `threading.local()`.

### Ordered Teardown

```python
finally:
    _current_db_session.reset(token)
    event.remove(session.sync_session, "after_transaction_end", restart_savepoint)
    for factory in all_sql_factories:
        factory._meta.sqlalchemy_session = None
    await session.close()              # rolls back the ORM SessionTransaction
    if request.config.getoption("--commit-db"):
        await postgres_outer_transaction.commit()   # debug mode: keep data visible in psql
    else:
        await postgres_outer_transaction.rollback() # ROLLBACK of the Postgres transaction
```

The order `session.close()` before `transaction.rollback()` is intentional: the session does not own the outer transaction (created directly on the connection before the session existed). `session.close()` cleans up ORM state without touching the Postgres transaction, which survives and is rolled back separately.

### override_get_postgres_session

```python
async def override_get_postgres_session():
    session = _current_db_session.get()
    try:
        yield session
        if session.in_transaction():
            await session.flush()    # makes writes visible, without committing
    except Exception:
        if session.in_transaction():
            await session.rollback() # rolls back this request, not the whole test
        raise
```

In production, `get_postgres_session` commits after each request. Here only a `flush()` is performed — writes are visible within the session but never leave the savepoint. On exception, the rollback undoes only the changes from that request; the listener immediately recreates a new savepoint, allowing the test to continue.

---

## Consequences

### Positive

- **Performance**: O(1) rollback, no DDL between tests.
- **Perfect isolation**: each test starts from a clean state guaranteed by Postgres.
- **Realistic endpoint tests**: the same session flows through the entire stack (handler → use case → repository), as in production.
- **Decoupled from lifespan**: the test infrastructure is independent of the application lifespan (`skip_lifespan=True`).

### Negative

- **Complexity**: the savepoint + listener + ContextVar mechanism is non-trivial to understand without documentation.
- **Coupling to SQLAlchemy internals**: `session.sync_session`, `after_transaction_end`, `trans.nested` — these internal APIs may change between major versions.
- **`bind=connection` deprecated**: SQLAlchemy 2.0 marks the `bind` parameter on `AsyncSession` as deprecated. A migration away from `AsyncSession(bind=connection)` toward explicit connection passing may be required in the future.

---

## References

- [SQLAlchemy — Session and Transaction](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)
- [SQLAlchemy — Joining a Session into an External Transaction](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

---

## Revision History

| Date | Author | Changes |
| --- | --- | --- |
| 2026-03-17 | Development Team | Initial ADR |