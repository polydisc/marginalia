# Marginalia — Backend

The v1 slice of a library management system, covering **catalog**
(Work / Manifestation / Item), **patrons**, and **circulation** (check out /
check in / renew / hold). It is a Python/FastAPI backend structured with
**Clean Architecture** so the domain is independent of FastAPI and the database;
per [ADR 0001](../docs/adr/0001-python-fastapi-clean-architecture.md) the
discipline is self-imposed (FastAPI does not enforce layering). SQLite is the
embedded default and the persistence adapter is swappable.

## Architecture

The code is split into four layers and obeys the **dependency rule**:
dependencies point inward, and the innermost `domain` layer imports no
framework (no `fastapi`, `pydantic`, or `sqlalchemy`).

- **domain** — plain `@dataclass` entities, value objects/enums, loan policy,
  domain services, repository **ports** (Protocols), and domain errors. Imports
  nothing outward.
- **application** — use cases, plain-dataclass DTOs, and the Unit-of-Work port.
  Imports `domain` only.
- **infrastructure** — SQLAlchemy 2.0 models, ORM↔domain mappers, repository and
  Unit-of-Work implementations, config, clock, and the loan-policy provider
  (SQLite by default). Imports inward only.
- **interface** — FastAPI routers, Pydantic schemas, exception handlers, and the
  composition root / dependency wiring (`api/deps.py`). Imports inward only.

Wiring (DI) happens in the composition root; `main.py` is the app factory.

```
app/
  domain/
    entities/        # work, manifestation, item, patron, loan, hold
    value_objects.py
    policy.py
    services.py
    repositories.py  # repository ports (Protocols)
    errors.py
    clock.py
  application/
    use_cases/       # catalog, patrons, circulation
    dto.py
    unit_of_work.py
  infrastructure/
    db/              # base, engine, models, mappers, repositories, unit_of_work
    config.py        # Settings (LMS_ env prefix; sqlite default)
    clock.py
    policy_provider.py
  interface/
    api/
      routers/       # catalog, patrons, circulation, items
      schemas.py     # Pydantic I/O schemas
      deps.py        # composition root (DI)
      errors.py      # domain-error -> HTTP handlers
  main.py            # FastAPI app factory
```

## Setup

Uses [uv](https://docs.astral.sh/uv/). Python is pinned to 3.12 (ADR 0001 risk
note: newer wheels may lag).

```sh
cd backend
uv venv --python 3.12
uv pip install -e ".[dev]"
```

## Run

The app is wired as a FastAPI factory (`create_app`), so importing the module
has no side effects — boot it with `--factory`:

```sh
uv run uvicorn app.main:create_app --factory --reload
```

Then open the interactive docs at <http://127.0.0.1:8000/docs>.

By default the app uses an embedded SQLite database (`sqlite:///./library.db`).
Set `LMS_DATABASE_URL` to point at another database — e.g. Postgres:

```sh
LMS_DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/library" \
  uv run uvicorn app.main:create_app --factory --reload
```

## Test

```sh
uv run pytest                              # unit + integration + API tests
uv run pytest --cov=app --cov-report=term-missing   # with coverage
```

Coverage feeds the `backend` flag on the [Codecov badge](../README.md); CI
uploads `--cov-report=xml`. Abstract `Protocol`/ABC bodies and `TYPE_CHECKING`
imports are excluded as structural (see `[tool.coverage.report]` in
`pyproject.toml`).

## Security and validation

The API is built for a same-origin demo deployment: FastAPI serves the SPA and
the client uses relative paths, so the backend does not enable broad CORS. All
request-body text fields and path identifiers are bounded at the interface
layer, persistence uses SQLAlchemy expressions rather than interpolated SQL, and
the database enforces the highest-risk concurrency invariants:

- one open loan per item (`uq_open_loan_per_item`);
- one open hold per patron per manifestation
  (`uq_open_hold_per_patron_manifestation`).

Authentication/authorization is intentionally thin in v1: the OPAC identifies a
patron by card number only, and staff screens assume a trusted demo operator.
For a real deployment, add staff auth, patron auth, rate limiting, audit logs,
and managed secrets before exposing these endpoints.

## Database migrations

The persistent (real) database schema is managed by
[Alembic](https://alembic.sqlalchemy.org/). The app factory runs migrations to
`head` on startup, so `uvicorn app.main:create_app --factory` is self-contained:
a fresh `library.db` is created and brought up to head automatically. (A legacy
pre-Alembic `library.db` built by the old `create_all` — tables present but no
`alembic_version` — is stamped to head rather than recreated.)

Migrations target the database from `Settings.database_url` (env
`LMS_DATABASE_URL`); `alembic.ini` does not hardcode a URL (`env.py` sets it).
Batch mode (`render_as_batch=True`) is enabled so SQLite `ALTER`s work.

```sh
cd backend

# Apply all pending migrations (also runs automatically on app startup)
uv run alembic upgrade head

# After changing app/infrastructure/db/models.py, generate a migration
uv run alembic revision --autogenerate -m "describe the change"

# Roll back one revision, or all the way to an empty DB
uv run alembic downgrade -1
uv run alembic downgrade base
```

Autogenerate can miss partial/conditional indexes — after generating, review the
script and confirm constraints like `loans.uq_open_loan_per_item`
(`WHERE returned_at IS NULL`), `holds.uq_open_hold_per_patron_manifestation`
(`WHERE status IN ('pending', 'ready')`), and column server defaults are present.
The generated `alembic/versions/*.py` files **are** committed.

The fast in-memory test database still uses `Base.metadata.create_all`
(`tests/conftest.py`); migrations are only for the real/persistent DB.

> With multiple workers / Postgres, run `alembic upgrade head` as a separate
> deploy step rather than relying on startup — concurrent startup migrations can
> race.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/works` | Create a Work |
| `POST` | `/manifestations` | Catalog a Manifestation |
| `POST` | `/manifestations/{manifestation_id}/items` | Add an Item (copy) |
| `GET`  | `/items/{barcode}` | Get an Item + derived availability |
| `POST` | `/patrons` | Register a Patron |
| `POST` | `/loans` | Check out an Item (`{item_barcode, patron_card}`) |
| `POST` | `/loans/{item_barcode}/return` | Check in (close the Loan) |
| `POST` | `/loans/{item_barcode}/renew` | Renew (extend the due date) |
| `POST` | `/holds` | Place a Hold (`{manifestation_id, patron_card}`) |
| `POST` | `/holds/{hold_id}/cancel` | Cancel an open hold (releases a ready copy) |
| `POST` | `/holds/expire` | Sweep: expire ready holds past their pickup-by date |
| `GET`  | `/holds/ready` | The hold shelf (ready holds) |
| `POST` | `/items/{barcode}/state` | Change item state (lost/in-repair/withdraw/shelve) |
| `PUT`  | `/works/{id}` · `/manifestations/{id}` · `/patrons/{card}` | Edit a record |
| `POST` | `/patrons/{card}/suspend` · `/reinstate` | Patron lifecycle |
| `GET`  | `/catalog` · `/patrons/{card}` · `/patrons/{card}/loans` · `/holds` | Read models |

> Full, authoritative list with schemas: `/docs` (OpenAPI) when the app is running.

## Scheduled tasks

The hold-expiry sweep is also runnable outside the web app (for cron / a timer):

```sh
cd backend && uv run python -m app.tasks   # prints: expired=<n> reassigned=<n>
```

It runs against an **already-migrated** database (the app applies migrations on
startup); the task itself does not create or migrate the schema.

Example crontab (daily at 02:00):

```cron
0 2 * * *  cd /path/to/backend && uv run python -m app.tasks >> /var/log/lms-expire.log 2>&1
```

## Key invariants

- **No double loan**: at most one open Loan per Item — enforced both by a DB
  partial unique index (`returned_at IS NULL`) as the concurrency backstop and
  by a domain assertion before the write (clear errors + unit testing). Both,
  not either ([ADR 0003](../docs/adr/0003-loan-aggregate-db-constraint.md)).
- **No duplicate open holds**: one Patron can hold at most one pending/ready
  place in the queue for a Manifestation. The use case gives a clear 409 and
  the DB partial unique index backs it under concurrency.
- **Derived circulation state**: `on_loan` / `on_hold_shelf` are never stored on
  the Item; availability is computed from the Item's intrinsic state plus any
  open Loan and ready Hold.
- **Policy-driven limits**: loan period, renewal limit, concurrent-loan limit,
  and `not_for_loan` come from a `LoanPolicy` keyed by
  (patron category × material type) — never hard-coded in entities.
- **Overdue blocks borrowing**: a Patron holding any overdue open Loan is blocked
  from new checkouts. No money is modeled (no fines).

## References

- Glossary: [CONTEXT.md](../CONTEXT.md)
- Design doc: [v1 backend — catalog, patrons, circulation](../docs/design/0002-v1-backend-catalog-patrons-circulation.md)
- Architecture decisions: [docs/adr/](../docs/adr/)
