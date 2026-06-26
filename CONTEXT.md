# Marginalia

A library management system modeled on the real-world vocabulary of an
integrated library system (ILS), drawing on Next-L and the FRBR/LRM
bibliographic model. The v1 slice covers cataloguing, patrons, and circulation.

## Language

### Bibliographic model

The catalog is layered, not flat. A single "book" is represented across three
entities, related one-to-many top to bottom and referenced **by ID** (separate
aggregates), never physically nested.

**Work**:
An abstract intellectual creation, independent of any edition or copy
(e.g. Sōseki's _Kokoro_ as a creation). Carries author and original title.
_Avoid_: Book, title.

**Manifestation**:
A specific published embodiment of a Work — one edition (e.g. the 2004 Shinchō
Bunko printing, with its ISBN, publisher, and displayed title). The practical
center of cataloguing; circulation policy attaches here.
_Avoid_: Book, edition record.

**Item**:
A single physical copy on the shelf, identified by barcode, carrying its own
state (on-shelf, on-loan, lost, …) and holding location. Loans attach to an
Item, never to a Work or Manifestation.
_Avoid_: BookItem, copy, exemplar.

> An Item stores exactly one **intrinsic** state — a physical/administrative
> fact only it knows: `available`, `in_repair`, `lost`, or `withdrawn`
> (terminal). The circulation states `on_loan` and `on_hold_shelf` are
> **derived** (from an open Loan / an assigned ready Hold), never stored on the
> Item. Effective availability for a new loan = intrinsic `available` AND no
> open Loan AND no assigned ready Hold. `in_transit` and `on_order` are out of
> v1 scope (multi-branch / acquisitions).
>
> Expression (the FRBR layer between Work and Manifestation — a specific
> intellectual form such as a translation) is **deliberately excluded** from v1:
> it adds cataloguing weight but has no effect on circulation.

### Actors

**Patron**:
A person holding borrowing privileges — a library card number, a patron
category (general / student / child), and borrowing limits. The subject of
circulation, and a core domain entity that carries its own rules (e.g. whether
it may borrow). A Patron typically has no system login.
_Avoid_: Member, Account, User, borrower.

**Patron status / card expiry**:
A Patron is **active** or **suspended**, and may carry a card **expiry** date
(`expires_on`; the last valid day, so expiry only bites the day after). A
suspended or expired Patron cannot borrow, renew, or place a hold. Status is
changed by an explicit reinstate/suspend action, not derived.
_Avoid_: blocked, banned, deactivated.

**Staff**:
A person who logs into the operational system to perform actions. A thin
identity/authorization concern living outside the circulation domain — the
circulation entities never reference it. Not a domain entity in v1.
_Avoid_: Librarian, Account, User.

> Person (a shared natural-person identity uniting Patron and Staff) is
> **deliberately not modeled** in v1.

### Circulation

**Circulation**:
The umbrella term for lending activity — checking out, returning, renewing, and
holding. Not the name of any single record.

**Loan**:
The record of one Item being lent to one Patron, with a loan date, due date,
and return date (absent while on loan). An independent aggregate that
references its Item and Patron by ID only. "On loan" is derived from the
existence of an open Loan — never stored as a flag on the Item.
_Avoid_: Issue, charge, borrowing, BookLending.

**Hold**:
A Patron's request to borrow a Manifestation (a specific edition, any copy)
when one becomes available. An independent aggregate referencing its Patron and
Manifestation by ID, carrying a queue position. Placed against a Manifestation,
fulfilled by an Item: on check-in, the returned Item is assigned to the
queue-head Hold and set aside on the hold shelf rather than re-shelved.
_Avoid_: Reservation, BookReservation, request.

**Pickup-by / hold expiry**:
When a Hold is readied, the assigned copy is held until a **pickup-by** date
(today + a library-wide pickup window). A ready Hold not collected by then
**expires**: the copy is handed to the next waiting Hold (re-readied with a
fresh pickup-by) or returns to the shelf if the queue is empty. Expiry is a
maintenance sweep, not automatic on read.
_Avoid_: hold timeout, reservation deadline.

**Check out / Check in / Renew**:
The actions that open a Loan, close it, and extend its due date. The verbs of
circulation; `Loan` is the noun.
_Avoid_: borrow/return as entity names, issue/discharge.

**Overdue**:
A status, not a record: a Loan whose due date has passed while still open. A
Patron holding any overdue Loan is blocked from borrowing. Derived, never
stored.
_Avoid_: late, delinquent.

> Monetary fines are **deliberately not modeled** in v1 — overdue is handled by
> blocking borrowing, not by charging money. Lost-item replacement costs are
> likewise out of scope (the Item's "lost" state exists, but carries no charge).
>
> The "one Item cannot be on two open Loans at once" invariant is enforced by a
> partial unique constraint at the database (the concurrency backstop) **and**
> asserted in the domain before the write (for clear errors and unit testing) —
> both, not either.

**Loan policy**:
The rules governing a loan, keyed by the pair (patron category × material
type): loan period, renewal limit, and concurrent-loan limit — including
"not for loan" (e.g. reference works). A domain concept whose _values_ are
supplied from configuration/storage, not hard-coded.
_Avoid_: circulation rule (as the type name), issuing rule.

**Patron category**:
The class a Patron belongs to (general / student / child …), one axis of loan
policy.
_Avoid_: patron type, membership level.

**Material type**:
The class of resource (book / reference / audiovisual …), the other axis of
loan policy. An attribute of the bibliographic record, not of circulation.
_Avoid_: item type, media type.

### Access

The system is split by audience: **staff-facing** operational screens (v1) and
a **public-facing** OPAC (v1.1). The two read the same catalog data but differ
in who uses them and what they may do.

**Circulation Desk**:
The staff-facing screen for the people-and-lending side of the counter. A clerk
loads a Patron by card, then checks out / returns / renews Items by barcode,
works the hold shelf (ready holds, cancellations, the expiry sweep), edits or
suspends/reinstates a Patron, and registers new Patrons. The UI home for
**Circulation** and **Patron** actions.
_Avoid_: checkout page, loans screen, teller.

**Catalog** (staff):
The staff-facing screen for the resource side — creating and editing the
Work → Manifestation → Item hierarchy, searching/filtering holdings, changing
an Item's intrinsic state (repair / lost / withdrawn), and placing holds on a
Patron's behalf. The editable, operational view of the bibliographic data.
_Avoid_: inventory, books page. Distinct from the **OPAC** (below), which is the
read-only, patron-facing counterpart.

**OPAC** (Online Public Access Catalog):
The public-facing search interface patrons use to search the catalog
themselves. Distinct from the staff-facing operational system: same catalog
data as the staff **Catalog** screen, but read-only plus self-service holds —
no cataloguing, no item-state, no patron administration. Delivered in v1.1 as a
separate patron-facing shell in the same SPA, layered over the existing backend
(see [SPEC.md](SPEC.md) §6). Patrons identify by **card number only** — no
password, and no patron name in the domain (a signed-in patron is shown as card
number + category).
_Avoid_: search page, front-end catalog.
