# Loan is an independent aggregate; no-double-loan enforced by a DB constraint

A **Loan** is its own aggregate, referencing its Item and Patron by ID rather
than living inside the Item aggregate. The core invariant — *one Item cannot be
on two open Loans at once* — is enforced by a **partial unique constraint** at
the database (`UNIQUE(item_id) WHERE returned_at IS NULL`) **and** asserted in
the domain before the write. "On loan" is never stored as a flag on the Item;
it is derived from the existence of an open Loan.

## Why

- A Clean Architecture purist would put the invariant entirely in the domain and
  have the Item aggregate own its loan state. We chose the DB constraint as the
  authoritative guard instead, because an in-memory domain check alone **cannot
  prevent a race** between two concurrent check-outs (both pass the check, both
  write). A unique constraint is the only place the invariant holds under
  concurrency.
- The domain assertion is kept **as well** (not instead) — for clear error
  messages and for unit-testing the rule without a database. The principle is
  *both, not either*.
- Keeping Loan as a separate aggregate (vs. nesting it under Item) keeps each
  aggregate small and independently loadable, and avoids storing a duplicate
  "on loan" truth that could drift from the Loan record.

## Consequences

- The invariant lives partly in infrastructure (the migration), so a reader of
  the domain layer alone won't see the full guarantee — this ADR is the
  signpost. Do not "fix" it by removing the constraint in favour of a pure
  domain check.
- Determining whether an Item is loanable requires a read against the Loan
  aggregate (a cross-aggregate read, which is allowed).
