# Marginalia — Specification

The **authoritative behavioral specification** for the v1 system: what it must
do, as testable requirements. Written for **spec-driven development** — each
requirement is the source of truth, and is traced to the executable test(s) that
verify it. When behaviour changes, change the requirement here first, then its
tests, then the code.

> Companion documents — keep them in their lane:
> - **[CONTEXT.md](CONTEXT.md)** — ubiquitous language (glossary). Defines the
>   terms used below.
> - **[docs/adr/](docs/adr/)** — architecture decisions (*why*).
> - **[docs/design/0002-…](docs/design/0002-v1-backend-catalog-patrons-circulation.md)** —
>   implementation design (*how to build*).
> - **This file** — behavioral spec (*what it must do*).

## Scope

**In scope (v1):** cataloguing (Work → Manifestation → Item), patrons, and
circulation (check out / return / renew / hold), plus the record management and
hold lifecycle that make those usable, served by a React SPA over a
FastAPI + Clean Architecture backend.

**In scope (v1.1):** an **OPAC** (patron-facing public catalogue) layered over
the same backend — search, place a hold, and a card-number "My library" view
(§7). No backend changes; it reuses the existing read/write endpoints.

**Out of scope (deferred by design):** acquisitions, serials, inter-library
loan, multi-branch, monetary fines, the FRBR Expression layer, patron passwords
/ accounts, and authentication/authorization beyond a thin placeholder. See
[CONTEXT.md](CONTEXT.md) and [docs/design/0002](docs/design/0002-v1-backend-catalog-patrons-circulation.md).

## How to read a requirement

Each requirement has a stable ID (`SPEC-<AREA>-NNN`), a single testable
statement, and **Verified by** — the test(s) that hold it true. Test paths are
relative to `backend/` (pytest) or `frontend/` (Playwright). The whole suite
runs in CI (`.github/workflows/ci.yml`) on every PR.

---

## 1 · Cataloguing

The catalog is layered (FRBR): a Work has Manifestations (editions), each with
Items (copies). Entities are separate aggregates referenced by ID
([ADR 0002](docs/adr/0002-frbr-three-layer-bibliographic-model.md)).

- **SPEC-CAT-001** — A Work can be created with a title and author.
  _Verified by:_ `tests/api/test_api.py`, `tests/api/test_read_endpoints.py`.
- **SPEC-CAT-002** — A Manifestation can be catalogued under an existing Work
  with a material type (book / reference / audiovisual) and optional
  ISBN/publisher; cataloguing under a missing Work is rejected (404).
  _Verified by:_ `tests/api/test_api.py`.
- **SPEC-CAT-003** — An Item (copy) can be added to a Manifestation with a unique
  barcode; a duplicate barcode is rejected (409), an unknown Manifestation 404.
  _Verified by:_ `tests/api/test_api.py`.
- **SPEC-CAT-004** — The catalog is readable as a Work→Manifestation→Item tree,
  each Item carrying its **derived** availability.
  _Verified by:_ `tests/api/test_read_endpoints.py::test_catalog_returns_work_tree_with_derived_availability`;
  `frontend/e2e/circulation.spec.ts` (“catalog tree reflects derived on_loan”).
- **SPEC-CAT-005** — A Work (title/author) and a Manifestation
  (title/material/ISBN/publisher) can be edited; identity (`work_id`) is not
  changed; unknown records 404.
  _Verified by:_ `tests/api/test_editing.py`;
  `frontend/e2e/circulation.spec.ts` (“edit a manifestation and a work”).

### 1.1 · Item state

An Item stores exactly one **intrinsic** state; `on_loan` / `on_hold_shelf` are
never stored (see §5).

- **SPEC-ITEM-001** — Intrinsic state transitions follow the table:
  available ↔ in_repair, available ↔ lost, in_repair → lost, lost → available,
  any non-terminal → withdrawn; **withdrawn is terminal**; same-state is a no-op.
  Illegal transitions are rejected (409).
  _Verified by:_ `tests/unit/test_item.py`; `tests/api/test_item_state.py::test_invalid_transition_returns_409`.
- **SPEC-ITEM-002** — Taking a copy out of circulation (in_repair / lost /
  withdrawn) requires it to be **idle**: not on an open loan and not set aside
  for a ready hold (otherwise 409). A copy lost while on loan is handled as
  return-then-mark-lost, so an open loan and intrinsic `lost` never coexist.
  _Verified by:_ `tests/api/test_item_state.py::test_cannot_change_state_while_on_loan`,
  `::test_mark_in_repair_blocks_checkout_then_shelve_allows`;
  `frontend/e2e/circulation.spec.ts` (“mark a copy in repair … unloanable”).

---

## 2 · Patrons

A Patron holds borrowing privileges: a card number, a category, a status
(active/suspended), and an optional card expiry.

- **SPEC-PAT-001** — A Patron can be registered with a unique card number and a
  category (general/student/child); a duplicate card is rejected (409).
  _Verified by:_ `tests/api/test_api.py::test_duplicate_card_returns_409`.
- **SPEC-PAT-002** — A Patron’s category and card expiry can be edited; unknown
  card 404.
  _Verified by:_ `tests/api/test_editing.py::test_update_patron_category_and_expiry_blocks_when_expired`;
  `frontend/e2e/circulation.spec.ts` (“edit a patron category”).
- **SPEC-PAT-003** — A Patron can be **suspended** and **reinstated**; a
  suspended Patron cannot borrow, renew, or place a hold (422 `PatronSuspended`).
  _Verified by:_ `tests/integration/test_patron_lifecycle.py`, `tests/api/test_api.py`.
- **SPEC-PAT-004** — A card is valid **through** its expiry day; the day after,
  the Patron is blocked from borrowing (422 `PatronExpired`).
  _Verified by:_ `tests/unit/test_patron.py::test_expiry_day_is_still_valid`,
  `tests/integration/test_patron_lifecycle.py`.

---

## 3 · Circulation

- **SPEC-CIRC-001** — An available copy can be checked out to an active Patron,
  producing a Loan with a due date = today + the loan period from the policy for
  (patron category × material type).
  _Verified by:_ `tests/integration/test_circulation.py::test_checkout_then_checkin_round_trip`;
  `frontend/e2e/circulation.spec.ts` (“check out from the desk …”).
- **SPEC-CIRC-002** — **A copy cannot be on two open loans at once.** Enforced in
  the domain (clear 409) **and** by a database partial-unique index as the
  concurrency backstop ([ADR 0003](docs/adr/0003-loan-aggregate-db-constraint.md)).
  _Verified by:_ `tests/integration/test_circulation.py::test_double_checkout_blocked_in_domain`,
  `::test_partial_unique_index_is_the_concurrency_backstop`.
- **SPEC-CIRC-003** — Reference material is **not for loan**: checkout is rejected
  (422 `NotForLoan`).
  _Verified by:_ `tests/integration/test_circulation.py::test_reference_material_is_not_for_loan`;
  `frontend/e2e/circulation.spec.ts`.
- **SPEC-CIRC-004** — A Patron holding any **overdue** open loan is blocked from
  new checkouts; a Patron at the policy’s concurrent-loan limit is blocked.
  No money is modeled.
  _Verified by:_ `tests/unit/test_patron.py`, `tests/integration/test_circulation.py::test_overdue_loan_blocks_further_borrowing`.
- **SPEC-CIRC-005** — A loan can be returned (closing it) and renewed (extending
  the due date) up to the policy’s renewal limit; over the limit is rejected.
  _Verified by:_ `tests/unit/test_loan.py`, `tests/integration/test_circulation.py::test_renew_until_limit_then_blocked`.
- **SPEC-CIRC-006** — “Overdue” is a derived status: an open loan whose due date
  has passed (relative to the system clock); never stored.
  _Verified by:_ `tests/unit/test_loan.py::test_is_overdue_only_while_open_and_past_due`,
  `tests/api/test_read_endpoints.py::test_patron_loans_overdue_follows_the_injected_clock`.

---

## 4 · Holds

A Hold is a request for a Manifestation (any copy), fulfilled by an Item.

- **SPEC-HOLD-001** — A Patron can place a Hold on a Manifestation, taking the
  next queue position. A suspended/expired Patron cannot. A Patron cannot hold
  multiple open (pending/ready) queue slots for the same Manifestation; a
  duplicate open hold is rejected (409) and backed by a partial unique index.
  _Verified by:_ `tests/integration/test_holds.py`,
  `tests/api/test_hold_cancel.py::test_duplicate_open_hold_returns_409`,
  `test_patron_lifecycle.py`.
- **SPEC-HOLD-002** — On check-in, if pending holds exist for the Manifestation,
  the returned copy is **set aside** for the queue head (becomes ready with a
  pickup-by date) rather than re-shelved.
  _Verified by:_ `tests/integration/test_holds.py::test_checkin_assigns_returned_item_to_queue_head`;
  `frontend/e2e/circulation.spec.ts` (“place a hold … fulfil it from the hold shelf”).
- **SPEC-HOLD-003** — A copy set aside for one Patron’s ready hold cannot be
  checked out by another (409); the hold owner’s checkout fulfils the hold.
  _Verified by:_ `tests/integration/test_holds.py::test_held_item_cannot_be_taken_by_another_patron`,
  `::test_hold_owner_can_check_out_and_fulfills_hold`.
- **SPEC-HOLD-004** — A pending hold blocks renewal of the matching open loan
  (422).
  _Verified by:_ `tests/integration/test_holds.py::test_pending_hold_blocks_renewal`.
- **SPEC-HOLD-005** — A ready hold not collected by its pickup-by date **expires**
  on a maintenance sweep; its copy goes to the next pending hold (fresh window)
  or back to the shelf. The sweep is idempotent and never double-assigns a copy.
  _Verified by:_ `tests/integration/test_holds.py::test_unclaimed_ready_hold_expires_and_item_returns_to_shelf`,
  `::test_expired_hold_is_reassigned_to_next_in_queue`,
  `::test_two_ready_holds_expire_with_one_waiter_no_double_assign`.
- **SPEC-HOLD-006** — An **open** hold (pending or ready) can be cancelled; a
  cancelled ready hold releases its copy like expiry. A fulfilled/expired/already-
  cancelled hold cannot be cancelled (409); unknown hold 404.
  _Verified by:_ `tests/integration/test_hold_cancel.py`, `tests/api/test_hold_cancel.py`;
  `frontend/e2e/circulation.spec.ts` (“place a hold … and cancel it”).
- **SPEC-HOLD-007** — The expiry sweep is runnable both via the API
  (`POST /holds/expire`) and as a standalone task for cron
  (`python -m app.tasks`), reusing the same use case.
  _Verified by:_ `tests/integration/test_tasks.py`.

---

## 5 · Cross-cutting invariants

These hold across all of the above and are first-class acceptance criteria.

- **SPEC-INV-001 · Derived availability.** `on_loan` and `on_hold_shelf` are
  never stored on an Item; availability is composed from the Item’s intrinsic
  state + the existence of an open Loan + an assigned ready Hold. The write-side
  domain service and the read-model projection derive it identically (intrinsic
  state wins over derived).
  _Verified by:_ `tests/unit/test_availability.py`; consistency exercised by the
  catalog/loan read tests.
- **SPEC-INV-002 · Dependency rule.** No module under `app/domain` or
  `app/application` imports a framework (`fastapi`, `pydantic`, `sqlalchemy`).
  ([ADR 0001](docs/adr/0001-python-fastapi-clean-architecture.md))
  _Verified by:_ `tests/unit/test_domain_is_framework_free.py`.
- **SPEC-INV-003 · Policy-driven limits.** Loan period, renewal limit,
  concurrent-loan limit and not-for-loan come from the loan policy
  (category × material), never hard-coded in entities.
  _Verified by:_ `tests/unit/test_policy.py`.
- **SPEC-INV-004 · API boundary validation.** Request bodies and path
  identifiers reject empty/whitespace-only or oversized values before they reach
  use cases or persistence; valid surrounding whitespace is normalized.
  _Verified by:_ `tests/api/test_input_validation.py`.
- **SPEC-INV-005 · Schema migrations.** The real database schema is owned by
  Alembic; the app applies migrations on startup so a fresh DB is
  self-contained. The no-double-loan and no-duplicate-open-hold partial unique
  indexes and the `patrons.status` default are preserved by migrations.
  _Verified by:_ CI (`backend` job runs against the migrated schema; the E2E job
  boots the app which migrates on startup).
- **SPEC-INV-006 · All-in-one delivery.** The built SPA is served by FastAPI on
  one origin; the client uses same-origin relative paths.
  _Verified by:_ `frontend/e2e/circulation.spec.ts` (the whole suite runs against
  `uvicorn app.main:create_app --factory`).

---

## 6 · OPAC

The **OPAC** (Online Public Access Catalog) is the patron-facing public
catalogue: a distinct shell in the **same SPA on the same origin**, built
entirely over the existing read/write endpoints — **no backend change**. Patrons
identify themselves by **card number only** (no password); there is no patron
name in the domain, so a signed-in patron is shown as card number + category.

- **SPEC-OPAC-001** — Any patron can search/browse the catalogue without signing
  in: title/author/ISBN search and material filter over `GET /catalog`, each
  title showing its derived availability.
  _Verified by:_ `frontend/e2e/opac.spec.ts`
  (“search the catalogue … place a hold …”).
- **SPEC-OPAC-002** — A patron signs in with a card number, validated via
  `GET /patrons/{card}`; an unknown card is rejected and nothing is persisted. A
  valid card is remembered across reloads (localStorage) until sign-out.
  _Verified by:_ `frontend/e2e/opac.spec.ts`
  (“an unknown card is rejected at sign-in”).
- **SPEC-OPAC-003** — A signed-in patron can place a hold on a Manifestation from
  the OPAC (`POST /holds`); availability re-renders and the hold appears on their
  My library view with its queue position.
  _Verified by:_ `frontend/e2e/opac.spec.ts`
  (“… place a hold, see it in My library …”).
- **SPEC-OPAC-004** — My library shows the signed-in patron’s current loans (due
  date, overdue) and holds (queue position / ready + pickup-by), and an **open**
  hold can be cancelled there (`POST /holds/{id}/cancel`, per SPEC-HOLD-006).
  _Verified by:_ `frontend/e2e/opac.spec.ts` (“… then cancel it”).
- **SPEC-OPAC-005** — Borrowing rules are enforced by the backend, not
  re-implemented in the OPAC: a suspended/expired patron can still browse and
  open My library, but a hold attempt is refused (422) and surfaced as a friendly
  message.
  _Verified by:_ `frontend/e2e/opac.spec.ts`
  (“a suspended patron can browse but is blocked from placing a hold”).
- **SPEC-OPAC-006** — The OPAC and the staff console are separate shells selected
  by the route (`#/opac…` vs the staff screens); switching between them leaves
  the staff experience unchanged.
  _Verified by:_ `frontend/e2e/opac.spec.ts`
  (“the staff console is still reachable and unchanged”); the staff suite
  (`frontend/e2e/circulation.spec.ts`) continues to pass.

## 7 · Traceability

- Every requirement above names its verifying test(s). The suite (backend
  pytest + frontend Playwright) is the **executable spec**; CI runs it on every
  PR and blocks merge on failure.
- New behaviour: add/modify a `SPEC-*` requirement here → add/modify its
  test(s) → implement. Removing behaviour removes its requirement and tests
  together.
- Glossary terms are defined once in [CONTEXT.md](CONTEXT.md); decisions are
  recorded in [docs/adr/](docs/adr/); this file does not duplicate them.
