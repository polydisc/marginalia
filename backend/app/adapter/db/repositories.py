"""SQLAlchemy repository implementations (the adapters behind the ports).

Each takes a Session and maps ORM rows to/from domain objects. Reads/writes
are flushed (to assign ids) but committed only by the Unit of Work.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapter.db import mappers
from app.adapter.db.models import (
    HoldModel,
    ItemModel,
    LoanModel,
    ManifestationModel,
    PatronModel,
    WorkModel,
)
from app.domain.entities import Hold, Item, Loan, Manifestation, Patron, Work


class SqlAlchemyWorkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, work: Work) -> Work:
        row = WorkModel(title=work.title, author=work.author)
        self._session.add(row)
        self._session.flush()
        return mappers.work_to_domain(row)

    def get(self, work_id: int) -> Work | None:
        row = self._session.get(WorkModel, work_id)
        return mappers.work_to_domain(row) if row else None

    def update(self, work: Work) -> None:
        row = self._session.get(WorkModel, work.id)
        if row is None:
            return
        row.title = work.title
        row.author = work.author


class SqlAlchemyManifestationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, manifestation: Manifestation) -> Manifestation:
        row = ManifestationModel(
            work_id=manifestation.work_id,
            title=manifestation.title,
            material_type=manifestation.material_type.value,
            isbn=manifestation.isbn,
            publisher=manifestation.publisher,
        )
        self._session.add(row)
        self._session.flush()
        return mappers.manifestation_to_domain(row)

    def get(self, manifestation_id: int) -> Manifestation | None:
        row = self._session.get(ManifestationModel, manifestation_id)
        return mappers.manifestation_to_domain(row) if row else None

    def update(self, manifestation: Manifestation) -> None:
        row = self._session.get(ManifestationModel, manifestation.id)
        if row is None:
            return
        row.title = manifestation.title
        row.material_type = manifestation.material_type.value
        row.isbn = manifestation.isbn
        row.publisher = manifestation.publisher


class SqlAlchemyItemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: Item) -> Item:
        row = ItemModel(
            manifestation_id=item.manifestation_id,
            barcode=item.barcode,
            state=item.state.value,
        )
        self._session.add(row)
        self._session.flush()
        return mappers.item_to_domain(row)

    def get(self, item_id: int) -> Item | None:
        row = self._session.get(ItemModel, item_id)
        return mappers.item_to_domain(row) if row else None

    def get_by_barcode(self, barcode: str) -> Item | None:
        row = self._session.scalar(
            select(ItemModel).where(ItemModel.barcode == barcode)
        )
        return mappers.item_to_domain(row) if row else None

    def update(self, item: Item) -> None:
        row = self._session.get(ItemModel, item.id)
        if row is None:
            return
        row.state = item.state.value


class SqlAlchemyPatronRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, patron: Patron) -> Patron:
        row = PatronModel(
            card_number=patron.card_number,
            category=patron.category.value,
            status=patron.status.value,
            expires_on=patron.expires_on,
        )
        self._session.add(row)
        self._session.flush()
        return mappers.patron_to_domain(row)

    def update(self, patron: Patron) -> None:
        row = self._session.get(PatronModel, patron.id)
        if row is None:
            return
        row.category = patron.category.value
        row.status = patron.status.value
        row.expires_on = patron.expires_on

    def get(self, patron_id: int) -> Patron | None:
        row = self._session.get(PatronModel, patron_id)
        return mappers.patron_to_domain(row) if row else None

    def get_by_card_number(self, card_number: str) -> Patron | None:
        row = self._session.scalar(
            select(PatronModel).where(PatronModel.card_number == card_number)
        )
        return mappers.patron_to_domain(row) if row else None


class SqlAlchemyLoanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, loan: Loan) -> Loan:
        row = LoanModel(
            item_id=loan.item_id,
            patron_id=loan.patron_id,
            loaned_at=loan.loaned_at,
            due_date=loan.due_date,
            returned_at=loan.returned_at,
            renewal_count=loan.renewal_count,
        )
        self._session.add(row)
        self._session.flush()
        return mappers.loan_to_domain(row)

    def update(self, loan: Loan) -> None:
        row = self._session.get(LoanModel, loan.id)
        if row is None:
            return
        row.due_date = loan.due_date
        row.returned_at = loan.returned_at
        row.renewal_count = loan.renewal_count

    def get_open_by_item(self, item_id: int) -> Loan | None:
        row = self._session.scalar(
            select(LoanModel).where(
                LoanModel.item_id == item_id,
                LoanModel.returned_at.is_(None),
            )
        )
        return mappers.loan_to_domain(row) if row else None

    def list_open_by_patron(self, patron_id: int) -> Sequence[Loan]:
        rows = self._session.scalars(
            select(LoanModel).where(
                LoanModel.patron_id == patron_id,
                LoanModel.returned_at.is_(None),
            )
        ).all()
        return [mappers.loan_to_domain(r) for r in rows]


class SqlAlchemyHoldRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, hold: Hold) -> Hold:
        row = HoldModel(
            manifestation_id=hold.manifestation_id,
            patron_id=hold.patron_id,
            placed_at=hold.placed_at,
            queue_position=hold.queue_position,
            status=hold.status.value,
            assigned_item_id=hold.assigned_item_id,
            pickup_by=hold.pickup_by,
        )
        self._session.add(row)
        self._session.flush()
        return mappers.hold_to_domain(row)

    def update(self, hold: Hold) -> None:
        row = self._session.get(HoldModel, hold.id)
        if row is None:
            return
        row.status = hold.status.value
        row.assigned_item_id = hold.assigned_item_id
        row.queue_position = hold.queue_position
        row.pickup_by = hold.pickup_by

    def get(self, hold_id: int) -> Hold | None:
        row = self._session.get(HoldModel, hold_id)
        return mappers.hold_to_domain(row) if row else None

    def list_pending_by_manifestation(
        self, manifestation_id: int
    ) -> Sequence[Hold]:
        rows = self._session.scalars(
            select(HoldModel)
            .where(
                HoldModel.manifestation_id == manifestation_id,
                HoldModel.status == "pending",
            )
            .order_by(HoldModel.queue_position)
        ).all()
        return [mappers.hold_to_domain(r) for r in rows]

    def get_ready_for_item(self, item_id: int) -> Hold | None:
        row = self._session.scalar(
            select(HoldModel).where(
                HoldModel.assigned_item_id == item_id,
                HoldModel.status == "ready",
            )
        )
        return mappers.hold_to_domain(row) if row else None

    def get_open_by_patron_and_manifestation(
        self, patron_id: int, manifestation_id: int
    ) -> Hold | None:
        row = self._session.scalar(
            select(HoldModel).where(
                HoldModel.patron_id == patron_id,
                HoldModel.manifestation_id == manifestation_id,
                HoldModel.status.in_(("pending", "ready")),
            )
        )
        return mappers.hold_to_domain(row) if row else None

    def list_ready_expired(self, on: date) -> Sequence[Hold]:
        rows = self._session.scalars(
            select(HoldModel).where(
                HoldModel.status == "ready",
                HoldModel.pickup_by.is_not(None),
                HoldModel.pickup_by < on,
            )
        ).all()
        return [mappers.hold_to_domain(r) for r in rows]

    def next_queue_position(self, manifestation_id: int) -> int:
        highest = self._session.scalar(
            select(func.max(HoldModel.queue_position)).where(
                HoldModel.manifestation_id == manifestation_id
            )
        )
        return (highest or 0) + 1
