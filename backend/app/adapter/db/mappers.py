"""Explicit ORM <-> domain mapping.

Hand-written so domain objects never carry SQLAlchemy state (ADR 0001). Kept
honest by repository round-trip integration tests.
"""

from __future__ import annotations

from app.adapter.db.models import (
    HoldModel,
    ItemModel,
    LoanModel,
    ManifestationModel,
    PatronModel,
    WorkModel,
)
from app.domain.entities import Hold, Item, Loan, Manifestation, Patron, Work
from app.domain.value_objects import (
    HoldStatus,
    ItemState,
    MaterialType,
    PatronCategory,
    PatronStatus,
)


def work_to_domain(m: WorkModel) -> Work:
    return Work(id=m.id, title=m.title, author=m.author)


def manifestation_to_domain(m: ManifestationModel) -> Manifestation:
    return Manifestation(
        id=m.id,
        work_id=m.work_id,
        title=m.title,
        material_type=MaterialType(m.material_type),
        isbn=m.isbn,
        publisher=m.publisher,
    )


def item_to_domain(m: ItemModel) -> Item:
    return Item(
        id=m.id,
        manifestation_id=m.manifestation_id,
        barcode=m.barcode,
        state=ItemState(m.state),
    )


def patron_to_domain(m: PatronModel) -> Patron:
    return Patron(
        id=m.id,
        card_number=m.card_number,
        category=PatronCategory(m.category),
        status=PatronStatus(m.status),
        expires_on=m.expires_on,
    )


def loan_to_domain(m: LoanModel) -> Loan:
    return Loan(
        id=m.id,
        item_id=m.item_id,
        patron_id=m.patron_id,
        loaned_at=m.loaned_at,
        due_date=m.due_date,
        returned_at=m.returned_at,
        renewal_count=m.renewal_count,
    )


def hold_to_domain(m: HoldModel) -> Hold:
    return Hold(
        id=m.id,
        manifestation_id=m.manifestation_id,
        patron_id=m.patron_id,
        placed_at=m.placed_at,
        queue_position=m.queue_position,
        status=HoldStatus(m.status),
        assigned_item_id=m.assigned_item_id,
        pickup_by=m.pickup_by,
    )
