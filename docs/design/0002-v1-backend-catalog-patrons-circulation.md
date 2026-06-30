---
status: draft
issue: "#2"
date: 2026-06-26
deciders: igarash1
touch_paths:
  - backend/app/domain/
  - backend/app/application/
  - backend/app/adapter/
  - backend/app/interface/
  - backend/tests/
---

# v1 Backend (Catalog + Patrons + Circulation): Design Doc

> The "what & why" lives in issue #1/#2 and [CONTEXT.md](../../CONTEXT.md);
> architecture decisions live in [ADR 0001–0003](../adr/). This doc is **how to
> build** the v1 backend.

## Overview

A FastAPI backend implementing the v1 slice of the library system — cataloguing
(Work/Manifestation/Item), patrons, and circulation (check out / check in /
renew / hold) — structured with Clean Architecture so the domain is independent
of FastAPI and the database. SQLite is the embedded default; the persistence
adapter is swappable.

## Background

The domain model and the cross-cutting decisions are settled (CONTEXT.md, ADRs
0001–0003). What remains is the implementation design: the layer boundaries, the
public interface (use cases + HTTP endpoints), the persistence schema, and how
the invariants are enforced and tested.

## Goals / Non-goals

- **Goal**: a runnable, tested backend covering catalog, patron registration,
  and the four circulation actions, with the domain layer free of framework/ORM
  imports (ADR 0001) and the no-double-loan invariant enforced both in the
  domain and by a DB partial unique index (ADR 0003).
- **Non-goal**: OPAC/search UI, acquisitions, serials, inter-library loan,
  multi-branch, monetary fines, the FRBR Expression layer, authn/authz beyond a
  thin placeholder, and the React frontend (separate later slice).

## Design (interface and data)

### Layering (dependency rule points inward — ADR 0001)

```text
backend/app/
  domain/          # entities, value objects, policy, services, repository PORTS, errors
  application/     # use cases, DTOs, Unit-of-Work port
  adapter/         # SQLAlchemy models + mappers + repo/UoW implementations (SQLite)
  interface/       # FastAPI routers, Pydantic schemas, composition root (DI)
  main.py          # app factory
```

`domain` imports nothing outward. `application` imports `domain`. `adapter`
and `interface` import inward only. Wiring happens in the composition root
(`interface/api/deps.py`).

### Domain (innermost)

Plain `@dataclass` entities — no Pydantic, no SQLAlchemy:

- **Work**(id, title, author)
- **Manifestation**(id, work_id, title, isbn, publisher, material_type)
- **Item**(id, manifestation_id, barcode, state: `ItemState`) — intrinsic state
  only; `on_loan`/`on_hold_shelf` are never stored here.
- **Patron**(id, card_number, category: `PatronCategory`) — `can_borrow(...)`
- **Loan**(id, item_id, patron_id, loaned_at, due_date, returned_at|None,
  renewal_count) — `is_open`, `is_overdue(on)`, `renew(...)`, `close(...)`
- **Hold**(id, manifestation_id, patron_id, placed_at, queue_position,
  status: `HoldStatus`, assigned_item_id|None)

Value objects / enums: `ItemState{available,in_repair,lost,withdrawn}`,
`PatronCategory{general,student,child}`, `MaterialType{book,reference,audiovisual}`,
`HoldStatus{pending,ready,fulfilled,cancelled}`.

`LoanPolicy` (value object) keyed by `(PatronCategory, MaterialType)` →
`{loan_period_days, renewal_limit, max_concurrent_loans, not_for_loan}`. Supplied
via a `LoanPolicyProvider` port; default matrix lives in adapter/config.

Repository **ports** (Protocols — DIP/ISP): `WorkRepository`,
`ManifestationRepository`, `ItemRepository`, `PatronRepository`,
`LoanRepository`, `HoldRepository`. Domain service `AvailabilityService`
composes intrinsic state + open Loan + ready Hold to answer "loanable?".

Domain errors: `ItemNotAvailable`, `PatronCannotBorrow`, `NotForLoan`,
`RenewalLimitReached`, `LoanNotOpen`, `HoldNotFound`, etc.

### Application (use cases)

Each use case is a callable class depending on ports + a Unit of Work:

- `CatalogManifestation(work, manifestation)` / `AddItem(manifestation_id, barcode)`
- `RegisterPatron(card_number, category)`
- `CheckOut(item_barcode, patron_card)` → opens a Loan (computes due date from
  policy; asserts availability + patron eligibility)
- `CheckIn(item_barcode)` → closes the Loan; if a pending Hold exists for the
  Manifestation, assigns this Item to the queue-head Hold (→ `ready`)
- `RenewLoan(item_barcode)` → extends due date (blocked past renewal limit; v1
  also blocks renewal when a pending Hold exists for the Manifestation)
- `PlaceHold(manifestation_id, patron_card)` → enqueues a Hold

Input/output via plain dataclass DTOs (not Pydantic) so the application layer
stays framework-free.

### Interface (HTTP)

| Method & path | Use case |
|---|---|
| `POST /works` | create Work |
| `POST /manifestations` | catalog Manifestation |
| `POST /manifestations/{id}/items` | add Item |
| `POST /patrons` | register Patron |
| `POST /loans` `{item_barcode, patron_card}` | check out |
| `POST /loans/{item_barcode}/return` | check in |
| `POST /loans/{item_barcode}/renew` | renew |
| `POST /holds` `{manifestation_id, patron_card}` | place hold |
| `GET /items/{barcode}` | item + derived availability |

Pydantic schemas live only here. Domain errors map to HTTP 4xx via exception
handlers (e.g. `ItemNotAvailable` → 409, `PatronCannotBorrow` → 422).

### Persistence (adapter)

SQLAlchemy 2.0 ORM models mirror entities in their own module, mapped to/from
domain objects explicitly (no ORM objects leak past the repository). SQLite by
default via `DATABASE_URL` (ADR 0001: embedded by default, separable).

No-double-loan backstop (ADR 0003):

```python
Index("uq_open_loan_per_item", "item_id", unique=True,
      sqlite_where=text("returned_at IS NULL"),
      postgresql_where=text("returned_at IS NULL"))
```

## Behavioral invariants

- **Dependency rule (ADR 0001)**: no module under `domain/` imports `fastapi`,
  `pydantic`, or `sqlalchemy`. Enforced by a test that scans imports.
- **No double loan (ADR 0003)**: at most one open Loan per Item — asserted in the
  domain before write **and** guaranteed by the partial unique index under
  concurrency. Both, not either.
- **Derived truth (CONTEXT.md)**: `on_loan` / `on_hold_shelf` are never stored on
  Item; availability is computed from Item intrinsic state + Loan + Hold.
- **Policy-driven limits**: due date, renewal limit, concurrent-loan limit, and
  not-for-loan come from `LoanPolicy`, never hard-coded in entities.
- **Overdue blocks borrowing (CONTEXT.md)**: a Patron holding any overdue open
  Loan cannot check out; no money is modeled.
- **Holds are Manifestation-level**, fulfilled by an Item on check-in.

## Testing approach

- **Unit (no DB)**: due-date computation per policy; `not_for_loan` rejects
  checkout; concurrent-loan limit; overdue patron blocked; renewal limit;
  renewal blocked when a pending Hold exists; availability composition; Loan
  open/close/overdue transitions. The domain double-loan assertion.
- **Architecture test**: import-scan asserting `domain/` is framework-free.
- **Integration (SQLite)**: full check-out → check-in cycle through the use
  cases; the **partial unique index rejects a second open Loan** for the same
  Item (insert-level test); hold placed → fulfilled on check-in (Item set aside,
  Hold `ready`).
- **API (httpx TestClient)**: happy-path checkout returns 201 + due date; double
  checkout returns 409; checkout for not-for-loan returns 422.

## Acceptance criteria

- [ ] `domain/` imports no `fastapi`/`pydantic`/`sqlalchemy` (test passes).
- [ ] Checking out an available item opens a Loan with a policy-derived due date.
- [ ] A second checkout of an on-loan item fails (domain 409) and the DB index
      independently rejects a duplicate open Loan.
- [ ] Reference (`not_for_loan`) material cannot be checked out (422).
- [ ] A patron with an overdue open loan is blocked from new checkouts.
- [ ] Renewal past the policy limit, or while a pending Hold exists, is rejected.
- [ ] Check-in of an item with a pending Hold assigns it to the queue head and
      sets the item aside (state derived as `on_hold_shelf`), Hold → `ready`.
- [ ] `pytest` green; `uvicorn app.main:create_app --factory` boots and `/docs`
      renders.
- [ ] Does not violate the invariants above.
- [ ] README documents how to install (uv), test, and run.

## Risks and rollout

- **Risk**: Python 3.14 wheels for SQLAlchemy/pydantic may lag — mitigated by
  pinning the uv venv to Python 3.12.
- **Risk**: mapping ORM↔domain by hand is boilerplate that can drift — kept
  honest by repository round-trip integration tests.
- **Rollout**: single PR for the backend slice; frontend (React) and the
  deferred ILS modules are separate later slices. No production deploy yet.

### Known v1 limitations (deferred deliberately)

- **Item state vs. circulation edges.** Marking a copy lost/in-repair/withdrawn
  requires it to be idle (not on loan, not on a ready hold) — a copy lost while
  on loan is handled as return-then-mark-lost, so an open loan and intrinsic
  `lost` never coexist. Withdrawing the last available copy of a Manifestation
  that still has *pending* holds can strand those holds (nothing left to fulfil
  them); not auto-resolved in v1.
- **Time is server-local.** `SystemClock` uses naive local time, so due-date and
  overdue boundaries follow the server's timezone. Acceptable for a single-
  instance v1; revisit (UTC + tz-aware columns) before multi-region deployment.
- **Holds have no concurrency backstop.** Unlike loans (ADR 0003's unique
  index), the hold queue relies on the domain check alone, so two simultaneous
  check-ins of the same manifestation could race on queue-head assignment. Safe
  under SQLite's single-writer default; needs a constraint / row lock before a
  concurrent write store.
- **Schema migrations via Alembic.** The persistent/real DB schema is managed by
  [Alembic](https://alembic.sqlalchemy.org/) (migrations under
  `backend/alembic/versions/`). The app factory runs `alembic upgrade head` on
  startup, so `uvicorn app.main:create_app --factory` stays self-contained and a
  fresh `library.db` is brought to head automatically (a legacy pre-Alembic DB
  is stamped rather than recreated). Add a schema change with
  `alembic revision --autogenerate -m "..."` (batch mode is enabled for SQLite
  ALTERs). The in-memory test DB still uses `Base.metadata.create_all` for speed
  (the schema matches the models). Note the initial migration preserves the
  `loans.uq_open_loan_per_item` partial unique index (`WHERE returned_at IS
  NULL`) and the `patrons.status` server default.

## References

- Related issues: #1 (Requirements), #2 (Tech Design)
- Related ADRs: [0001](../adr/0001-python-fastapi-clean-architecture.md),
  [0002](../adr/0002-frbr-three-layer-bibliographic-model.md),
  [0003](../adr/0003-loan-aggregate-db-constraint.md)
- Glossary: [CONTEXT.md](../../CONTEXT.md)
